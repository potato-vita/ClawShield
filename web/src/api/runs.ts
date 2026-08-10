import {apiGet} from "./client";
import type {EvidenceStep} from "@/types/evidence";
import type {GraphEdge,GraphNode,GraphNodeType} from "@/types/graph";
import type {ConversationMessage,Decision,RiskLevel} from "@/types/session";

interface CoreGraphNode{id:string;type:string;label:string;tool_call_id?:string;resource_hint?:string|null;target_resource?:string|null;risk_level?:string;decision?:string|null;reason?:string|null;matched_rules?:string[];step_seq?:number}
interface CoreGraphEdge{id:string;source:string;target:string;type?:string}
interface CoreEvidenceStep{evidence_step_id:string;step_order:number;step_type:string;title:string;detail:unknown;decision?:string|null;risk_level?:string|null;tool_call_id?:string|null}
const risk=(value?:string|null):RiskLevel=>["critical","high","medium","low"].includes(value??"")?value as RiskLevel:"low";
const decision=(value?:string|null):Decision|undefined=>value?value.toUpperCase()==="BLOCK"?"block":value.toUpperCase()==="ALLOW"?"allow":"review":undefined;
const nodeType=(value:string,label:string):GraphNodeType=>value==="user_request"||value==="user_intent"?"user_intent":value==="policy_violation"?"policy_decision":value==="network_sink"?"network_sink":value==="sensitive_object"?"sensitive_object":label.toLowerCase().includes("send")||label.toLowerCase().includes("http")?"network_sink":"tool_call";
const nodeLabels:Record<string,string>={
  "User Intent":"用户意图",
  "User Request":"用户请求",
  intent_resource_inconsistency:"意图与资源不一致",
  intent_tool_inconsistency:"意图与工具不一致",
  step_step_inconsistency:"步骤间行为不一致",
  sensitive_data_egress:"敏感数据外发",
  prompt_injection:"提示词注入",
  unauthorized_high_impact_action:"未授权高影响操作",
};
const evidenceTitles:Record<string,string>={
  "Tool call received":"收到工具调用",
  "Policy evaluation completed":"策略评估完成",
  "ALLOW decision issued":"已下发允许决策",
  "WARN decision issued":"已下发警告决策",
  "ASK decision issued":"已发起人工审批",
  "BLOCK decision issued":"已下发阻止决策",
};

export async function getRiskGraph(runId:string):Promise<{nodes:GraphNode[];edges:GraphEdge[];graphSource?:string}>{const data=await apiGet<{graph_source?:string;nodes:CoreGraphNode[];edges:CoreGraphEdge[]}>(`/v1/runs/${encodeURIComponent(runId)}/risk-graph`);return{graphSource:data.graph_source,nodes:data.nodes.map(node=>({id:node.id,type:nodeType(node.type,node.label),label:nodeLabels[node.label]??node.label,detail:node.target_resource??node.resource_hint??node.reason??"Core 审计节点",risk:risk(node.risk_level),stepSeq:node.step_seq,decision:decision(node.decision),toolCallId:node.tool_call_id,evidenceStepId:undefined,policyId:node.matched_rules?.[0]})),edges:data.edges.map(edge=>({id:edge.id,source:edge.source,target:edge.target,label:edge.type,kind:edge.type==="blocked_by"?"evidence":"main"}))};}
export async function getEvidencePath(runId:string):Promise<EvidenceStep[]>{const data=await apiGet<{steps:CoreEvidenceStep[]}>(`/v1/runs/${encodeURIComponent(runId)}/evidence-path`);return data.steps.map((step,index)=>({id:step.evidence_step_id,step:String(step.step_order+1).padStart(2,"0"),type:normalizeStep(step.step_type),title:evidenceTitles[step.title]??step.title,detail:typeof step.detail==="string"?step.detail:JSON.stringify(step.detail),status:decision(step.decision)==="block"?"blocked":risk(step.risk_level)==="critical"?"critical":risk(step.risk_level)==="high"?"risk":"verified",nodeId:step.tool_call_id?`tool:${step.tool_call_id}`:`evidence:${index}`}));}
interface CoreConversationMessage{message_row_id:string;event_id:string;event_type:string;role:string|null;summary:unknown;occurred_at:string}
export async function getConversationSummary(runId:string):Promise<ConversationMessage[]>{const data=await apiGet<{messages:CoreConversationMessage[]}>(`/v1/runs/${encodeURIComponent(runId)}/conversation-summary`);return data.messages.map(message=>({id:message.message_row_id,role:message.role==="user"||message.event_type==="message_received"?"user":"assistant",summary:summaryText(message.summary,message.event_type)}));}
export function summaryText(value:unknown,fallback="Conversation event"):string{if(value&&typeof value==="object"){const record=value as Record<string,unknown>;if(typeof record.preview==="string")return record.preview;if(typeof record.value==="string")return record.value;if(Array.isArray(record.keys))return `Structured message: ${record.keys.map(String).join(", ")}`;}return fallback.replaceAll("_"," ");}
function normalizeStep(value:string):EvidenceStep["type"]{if(value.includes("decision"))return"decision";if(value.includes("network"))return"network";if(value.includes("object"))return"object";if(value.includes("intent"))return"intent";return"tool";}
