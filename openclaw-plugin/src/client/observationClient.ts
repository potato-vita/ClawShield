export interface ObservationClientOptions {
  baseUrl: string;
  timeoutMs: number;
  fetchImpl?: typeof fetch;
}

export class ObservationClient {
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly options: ObservationClientOptions) {
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  async detect(payload: Record<string, unknown>): Promise<void> {
    const response = await this.fetchImpl(new URL("/v1/method/observation", this.options.baseUrl), {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.options.timeoutMs),
    });
    if (!response.ok) throw new Error(`Observation detection failed with HTTP ${response.status}`);
  }
}

