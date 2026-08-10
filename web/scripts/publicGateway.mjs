import { createServer, request as createRequest } from "node:http";

const host = process.env.TRACESHIELD_PUBLIC_GATEWAY_HOST ?? "127.0.0.1";
const port = Number(process.env.TRACESHIELD_PUBLIC_GATEWAY_PORT ?? "5180");
const webOrigin = readOrigin("TRACESHIELD_WEB_ORIGIN", "http://127.0.0.1:5173");
const coreOrigin = readOrigin("TRACESHIELD_CORE_ORIGIN", "http://127.0.0.1:8787");
const readOnlyMethods = new Set(["GET", "HEAD", "OPTIONS"]);
const allowedCoreWrites = new Set(["POST /v1/assistant/chat/stream"]);
const sockets = new Set();

const server = createServer((clientRequest, clientResponse) => {
  const requestUrl = clientRequest.url ?? "/";
  const requestTarget = new URL(requestUrl, "http://gateway.invalid");
  const requestMethod = clientRequest.method ?? "GET";
  const isCoreRequest = requestTarget.pathname.startsWith("/v1/");
  const isAuditStream = requestTarget.pathname.startsWith("/v1/stream/");
  const isAssistantStream = requestMethod === "POST"
    && requestTarget.pathname === "/v1/assistant/chat/stream";
  const isAllowedCoreWrite = allowedCoreWrites.has(`${requestMethod} ${requestTarget.pathname}`);

  if (isAuditStream) {
    clientResponse.writeHead(204, { "cache-control": "no-store" });
    clientResponse.end();
    return;
  }

  if (isCoreRequest && !readOnlyMethods.has(requestMethod) && !isAllowedCoreWrite) {
    clientResponse.writeHead(403, {
      "cache-control": "no-store",
      "content-type": "application/json; charset=utf-8",
      "x-content-type-options": "nosniff",
    });
    clientResponse.end(JSON.stringify({ error: "public_gateway_read_only" }));
    return;
  }

  const origin = isCoreRequest ? coreOrigin : webOrigin;
  const target = new URL(requestUrl, origin);
  const upstreamRequest = createRequest(
    {
      protocol: target.protocol,
      hostname: target.hostname,
      port: target.port,
      method: requestMethod,
      path: `${target.pathname}${target.search}`,
      headers: {
        ...clientRequest.headers,
        host: target.host,
      },
    },
    (upstreamResponse) => {
      const headers = {
        ...upstreamResponse.headers,
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        ...(isCoreRequest
          ? { "cache-control": isAuditStream || isAssistantStream ? "no-cache, no-transform" : "no-store" }
          : {}),
      };
      clientResponse.writeHead(upstreamResponse.statusCode ?? 502, headers);
      upstreamResponse.pipe(clientResponse);
    },
  );

  upstreamRequest.on("error", (error) => {
    if (!clientResponse.headersSent) {
      clientResponse.writeHead(502, {
        "cache-control": "no-store",
        "content-type": "application/json; charset=utf-8",
      });
    }
    clientResponse.end(JSON.stringify({ error: "public_gateway_upstream_unavailable", message: error.message }));
  });

  clientRequest.on("aborted", () => upstreamRequest.destroy());
  clientRequest.pipe(upstreamRequest);
});

server.on("connection", (socket) => {
  sockets.add(socket);
  socket.once("close", () => sockets.delete(socket));
});

server.on("error", (error) => {
  console.error(`TraceShield public gateway failed: ${error.message}`);
  process.exitCode = 1;
});

server.listen(port, host, () => {
  const address = server.address();
  const listeningPort = typeof address === "object" && address ? address.port : port;
  console.log(
    `TraceShield public gateway listening at http://${host}:${listeningPort} (web=${webOrigin.origin}, core=${coreOrigin.origin}, readOnly=true, assistantStream=true)`,
  );
});

function stopServer() {
  for (const socket of sockets) {
    socket.destroy();
  }
  server.close();
  process.exit(0);
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, stopServer);
}

function readOrigin(name, fallback) {
  const origin = new URL(process.env[name] ?? fallback);
  if (origin.protocol !== "http:" && origin.protocol !== "https:") {
    throw new Error(`${name} must use http or https`);
  }
  return origin;
}
