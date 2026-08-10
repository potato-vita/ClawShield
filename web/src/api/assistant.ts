import { coreBaseUrl } from "./client";

export type AssistantHistoryRole = "user" | "assistant";

export interface AssistantHistoryMessage {
  role: AssistantHistoryRole;
  content: string;
}

export interface AssistantChatRequest {
  conversation_id?: string;
  message: string;
  history?: AssistantHistoryMessage[];
  context?: Record<string, unknown>;
}

export interface AssistantStartEvent {
  conversationId?: string;
  model?: string;
}

export interface AssistantDoneEvent {
  conversationId?: string;
  finishReason?: string;
}

export interface AssistantStreamHandlers {
  onStart?: (event: AssistantStartEvent) => void;
  onDelta: (content: string) => void;
  onDone?: (event: AssistantDoneEvent) => void;
  onError?: (error: AssistantStreamError) => void;
}

export interface AssistantHealth {
  ok: boolean;
  configured?: boolean;
  model?: string;
  provider?: string;
}

export class AssistantStreamError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "AssistantStreamError";
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" ? value as Record<string, unknown> : {};
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

async function responseError(response: Response): Promise<AssistantStreamError> {
  let message = `Core returned ${response.status}`;
  let code = `HTTP_${response.status}`;
  try {
    const body = asRecord(await response.json());
    message = stringValue(body.message) ?? stringValue(body.error) ?? message;
    code = stringValue(body.code) ?? code;
  } catch {
    // Keep the HTTP fallback for non-JSON error responses.
  }
  return new AssistantStreamError(response.status, code, message);
}

export async function getAssistantHealth(signal?: AbortSignal): Promise<AssistantHealth> {
  const timeoutSignal = AbortSignal.timeout(5000);
  const requestSignal = signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal;
  let response: Response;
  try {
    response = await fetch(`${coreBaseUrl}/v1/assistant/health`, {
      headers: { Accept: "application/json" },
      signal: requestSignal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new AssistantStreamError(0, "CORE_UNREACHABLE", error instanceof Error ? error.message : "Core is unreachable");
  }
  if (!response.ok) throw await responseError(response);
  try {
    const body = asRecord(await response.json());
    if (typeof body.ok !== "boolean") {
      throw new Error("missing health status");
    }
    return {
      ok: body.ok,
      configured: typeof body.configured === "boolean" ? body.configured : undefined,
      model: stringValue(body.model),
      provider: stringValue(body.provider),
    };
  } catch {
    throw new AssistantStreamError(response.status, "INVALID_HEALTH_RESPONSE", "Core returned an invalid assistant health response");
  }
}

interface ParsedSseEvent {
  name: string;
  data: string;
}

function parseSseBlock(block: string): ParsedSseEvent | undefined {
  let name = "message";
  const data: string[] = [];
  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") name = value;
    if (field === "data") data.push(value);
  }
  if (data.length === 0) return undefined;
  return { name, data: data.join("\n") };
}

function parseEventData(raw: string): Record<string, unknown> {
  if (raw === "[DONE]") return { type: "done" };
  try {
    return asRecord(JSON.parse(raw));
  } catch {
    return { content: raw };
  }
}

function eventName(event: ParsedSseEvent, data: Record<string, unknown>): string {
  if (event.name !== "message") return event.name;
  return stringValue(data.type) ?? stringValue(data.event) ?? "delta";
}

/**
 * Streams an Eino-backed assistant reply through Core. This deliberately uses
 * fetch instead of EventSource because the assistant endpoint is a POST.
 */
export async function streamAssistantChat(
  request: AssistantChatRequest,
  handlers: AssistantStreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${coreBaseUrl}/v1/assistant/chat/stream`, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new AssistantStreamError(0, "CORE_UNREACHABLE", error instanceof Error ? error.message : "Core is unreachable");
  }

  if (!response.ok) throw await responseError(response);
  if (!response.body) throw new AssistantStreamError(response.status, "EMPTY_STREAM", "Core returned an empty assistant stream");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed = false;

  const dispatch = (block: string) => {
    const parsed = parseSseBlock(block);
    if (!parsed) return;
    const data = parseEventData(parsed.data);
    const name = eventName(parsed, data);

    if (name === "start") {
      handlers.onStart?.({
        conversationId: stringValue(data.conversation_id) ?? stringValue(data.conversationId),
        model: stringValue(data.model),
      });
      return;
    }
    if (name === "delta") {
      const content = stringValue(data.content) ?? stringValue(data.delta) ?? stringValue(data.text);
      if (content) handlers.onDelta(content);
      return;
    }
    if (name === "done") {
      completed = true;
      handlers.onDone?.({
        conversationId: stringValue(data.conversation_id) ?? stringValue(data.conversationId),
        finishReason: stringValue(data.finish_reason) ?? stringValue(data.finishReason),
      });
      return;
    }
    if (name === "error") {
      const error = new AssistantStreamError(
        response.status,
        stringValue(data.code) ?? "ASSISTANT_STREAM_ERROR",
        stringValue(data.message) ?? stringValue(data.error) ?? "The assistant stream failed",
      );
      handlers.onError?.(error);
      throw error;
    }
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary = buffer.match(/\r?\n\r?\n/);
      while (boundary?.index !== undefined) {
        dispatch(buffer.slice(0, boundary.index));
        buffer = buffer.slice(boundary.index + boundary[0].length);
        boundary = buffer.match(/\r?\n\r?\n/);
      }
      if (done) break;
    }
  } catch (error) {
    await reader.cancel().catch(() => undefined);
    throw error;
  } finally {
    reader.releaseLock();
  }

  if (buffer.trim()) dispatch(buffer);
  if (!completed && !signal.aborted) {
    throw new AssistantStreamError(response.status, "INCOMPLETE_STREAM", "The assistant connection closed before completion");
  }
}
