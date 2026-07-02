import {coreBaseUrl} from "./client";

export type StreamEventName="connected"|"audit_event"|"trace_event"|"metric_update"|"heartbeat";
export interface StreamHandlers{onStatus:(status:"connecting"|"connected"|"disconnected")=>void;onEvent:(name:StreamEventName,data:Record<string,unknown>)=>void}

export function connectAuditStream(handlers:StreamHandlers):()=>void{
  let source:EventSource|null=null;let retryTimer:number|undefined;let stopped=false;
  const open=()=>{
    if(stopped)return;handlers.onStatus("connecting");source=new EventSource(`${coreBaseUrl}/v1/stream/audit-events`);
    source.onopen=()=>handlers.onStatus("connected");
    const names:StreamEventName[]=["connected","audit_event","trace_event","metric_update","heartbeat"];
    for(const name of names)source.addEventListener(name,(event)=>{handlers.onStatus("connected");try{handlers.onEvent(name,JSON.parse((event as MessageEvent).data) as Record<string,unknown>);}catch{handlers.onEvent(name,{})}});
    source.onerror=()=>{handlers.onStatus("disconnected");source?.close();source=null;if(!stopped){window.clearTimeout(retryTimer);retryTimer=window.setTimeout(open,3000);}};
  };
  open();
  return()=>{stopped=true;window.clearTimeout(retryTimer);source?.close();source=null;handlers.onStatus("disconnected");};
}
