import {apiGet} from "./client";
import type {AuditRun,AuditSession,Decision,RiskLevel} from "@/types/session";
import type {ToolCall} from "@/types/toolCall";

export interface CoreAuditEvent{tool_call_id:string;session_id:string;run_id:string;step_seq:number|null;tool_name:string;tool_kind:string;resource_hint:string|null;risk_hint:string|null;status:string;started_at:string;decision:string|null;risk_level:string|null;matched_rules:string[]|null;reason:string|null}
interface CoreSession{session_id:string;first_seen_at:string;last_seen_at:string;run_count:number;message_count:number;tool_call_count:number;latest_run_id:string|null;latest_run_started_at:string|null;risk_level:string;final_decision:string;latest_event_type:string|null}
const risk=(value:string|null):RiskLevel=>["critical","high","medium","low"].includes(value??"")?value as RiskLevel:"low";
const decision=(value:string|null):Decision=>value==="BLOCK"||value==="block"?"block":value==="ALLOW"||value==="allow"?"allow":"review";
const time=(value:string)=>{const date=new Date(value);return Number.isNaN(date.valueOf())?value:date.toLocaleTimeString("zh-CN",{hour12:false});};

export async function getAuditBundle(limit=200):Promise<{sessions:AuditSession[];runs:AuditRun[];toolCalls:ToolCall[]}>{
  const [{sessions:sessionRows},{events}]=await Promise.all([apiGet<{sessions:CoreSession[]}>("/v1/audit/sessions?filter=all"),apiGet<{events:CoreAuditEvent[]}>(`/v1/audit/events?limit=${limit}`)]);
  const sessions=new Map<string,AuditSession>(sessionRows.map(row=>[row.session_id,{id:row.session_id,title:sessionTitle(row.session_id),subtitle:sessionSubtitle(row),risk:risk(row.risk_level),time:time(row.last_seen_at),runIds:row.latest_run_id?[row.latest_run_id]:[]}]))
  const runs=new Map<string,AuditRun>(sessionRows.flatMap(row=>row.latest_run_id?[[row.latest_run_id,{id:row.latest_run_id,sessionId:row.session_id,title:runTitle(row.latest_run_id),startedAt:row.latest_run_started_at??row.first_seen_at,decision:decision(row.final_decision),risk:risk(row.risk_level),summary:row.tool_call_count?`${row.tool_call_count} 次工具调用 · ${row.message_count} 条消息事件`:`纯对话运行 · ${row.message_count} 条消息事件`} as AuditRun] as const]:[]));
  const toolCalls=events.map<ToolCall>((event)=>{
    const eventRisk=risk(event.risk_level);const eventDecision=decision(event.decision);
    const current=sessions.get(event.session_id);const ranks={low:0,medium:1,high:2,critical:3};
    if(!current)sessions.set(event.session_id,{id:event.session_id,title:sessionTitle(event.session_id),subtitle:`${event.tool_name} · ${event.resource_hint??event.tool_kind}`,risk:eventRisk,time:time(event.started_at),runIds:[event.run_id]});
    else{if(!current.runIds.includes(event.run_id))current.runIds.push(event.run_id);if(ranks[eventRisk]>ranks[current.risk])current.risk=eventRisk;}
    if(!runs.has(event.run_id))runs.set(event.run_id,{id:event.run_id,sessionId:event.session_id,title:runTitle(event.run_id),startedAt:event.started_at,decision:eventDecision,risk:eventRisk,summary:event.reason??"Core 审计运行"});
    return{id:event.tool_call_id,sessionId:event.session_id,runId:event.run_id,stepSeq:event.step_seq??undefined,time:time(event.started_at),toolName:event.tool_name,toolKind:normalizeKind(event.tool_kind),resource:event.resource_hint??"—",decision:eventDecision,riskLevel:eventRisk,latencyMs:0,policyHits:event.matched_rules??[],argumentsSummary:event.reason??"Core 事件元数据",nodeId:`tool:${event.tool_call_id}`};
  });
  return{sessions:[...sessions.values()],runs:[...runs.values()],toolCalls};
}
function sessionTitle(id:string):string{return id==="demo-agent-security-long-chain"?"AI 安全 Agent · 长链外传调查":id;}
function runTitle(id:string):string{return id==="run-ai-security-chain-001"?"跨域数据外传 · 28 步长链":`运行 ${id}`;}
function sessionSubtitle(row:CoreSession):string{if(row.tool_call_count>0)return `${row.tool_call_count} 次工具调用 · ${row.message_count} 条消息`;return `${row.latest_event_type??"对话"} · ${row.message_count} 条消息`;}
function normalizeKind(value:string):ToolCall["toolKind"]{if(value.includes("shell"))return"shell";if(value.includes("file")||value.includes("read"))return"filesystem";if(value.includes("network")||value.includes("http")||value.includes("send"))return"network";return"transform";}
