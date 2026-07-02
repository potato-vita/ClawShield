import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root=resolve(import.meta.dirname,"..");
const checks=[
  ["dist/index.html","production build"],
  ["src/pages/RuntimeAudit.vue","runtime page"],
  ["src/pages/ToolCalls.vue","tool calls page"],
  ["src/pages/PolicyCenter.vue","policy center page"],
  ["src/api/stream.ts","SSE client"],
];
for(const [file,label] of checks){await access(resolve(root,file));console.log(`ok  ${label}`);}
const runtime=await readFile(resolve(root,"src/mock/runtimeMock.ts"),"utf8");
for(const marker of ["payroll-leak-demo","external_send","suspicious-exfil.com","BLOCKED"]){if(!runtime.includes(marker))throw new Error(`Missing demo marker: ${marker}`);}
console.log("ok  demo attack path");

const base=process.env.SMOKE_BASE_URL??"http://127.0.0.1:5173";
for(const path of ["/runtime","/sessions","/tool-calls","/policies","/core"]){
  const response=await fetch(`${base}${path}`,{signal:AbortSignal.timeout(3000)});
  const body=await response.text();
  if(!response.ok||!body.includes("TraceShield"))throw new Error(`${path} did not return the Vite application`);
  console.log(`ok  ${path}`);
}
console.log("TraceShield frontend smoke check passed.");
