import { MethodEngineClient } from "../src/engine/methodEngineClient.js";

const client = new MethodEngineClient({ timeoutMs: 1_000 });
try {
  console.log(JSON.stringify(await client.start()));
} finally {
  await client.stop();
}

