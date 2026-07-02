import { defineStore } from "pinia";
import { mockConversation, mockEvidence, mockGraphEdges, mockGraphNodes, mockMetrics, mockPolicies, mockRuns, mockRuntimeStatus, mockSessions, mockTimeline, mockToolCalls } from "@/mock/runtimeMock";
import type { RuntimeTab } from "@/components/runtime/RuntimeTabs.vue";
import { getDashboardMetrics } from "@/api/dashboard";
import { getAuditBundle } from "@/api/sessions";
import { getConversationSummary, getEvidencePath, getRiskGraph, summaryText } from "@/api/runs";
import { getCoreStatus } from "@/api/coreStatus";
import { useMockData } from "@/api/client";
import { connectAuditStream, type StreamEventName } from "@/api/stream";
import type { RiskLevel } from "@/types/session";
import type { ToolCall } from "@/types/toolCall";

export const useRuntimeStore = defineStore("runtime", {
  state: () => ({
    initialized: false,
    loading: false,
    error: "" as string,
    dataSource: "mock" as "mock" | "core" | "fallback",
    sessions: structuredClone(mockSessions),
    runs: structuredClone(mockRuns),
    graphNodes: structuredClone(mockGraphNodes),
    graphEdges: structuredClone(mockGraphEdges),
    evidence: structuredClone(mockEvidence),
    toolCalls: structuredClone(mockToolCalls),
    timeline: structuredClone(mockTimeline),
    conversation: structuredClone(mockConversation),
    policies: structuredClone(mockPolicies),
    metrics: structuredClone(mockMetrics),
    status: structuredClone(mockRuntimeStatus),
    activeSessionId: "payroll-leak-demo",
    activeRunId: "run-payroll-001",
    selectedNodeId: "send",
    activeRuntimeTab: "path" as RuntimeTab,
    streamState: "disconnected" as "connecting" | "connected" | "disconnected",
    streamStop: null as null | (()=>void),
  }),
  getters: {
    activeSession: (state) => state.sessions.find((item) => item.id === state.activeSessionId),
    activeRun: (state) => state.runs.find((item) => item.id === state.activeRunId),
    selectedNode: (state) => state.graphNodes.find((item) => item.id === state.selectedNodeId),
    selectedToolCall(state) {
      const selectedNode = state.graphNodes.find((item) => item.id === state.selectedNodeId);
      return state.toolCalls.find((item) => item.id === selectedNode?.toolCallId);
    },
    selectedEvidence(state) {
      const selectedNode = state.graphNodes.find((item) => item.id === state.selectedNodeId);
      return state.evidence.find((item) => item.id === selectedNode?.evidenceStepId);
    },
    activeToolCalls: (state) => state.toolCalls.filter((item) => item.runId === state.activeRunId),
  },
  actions: {
    async initialize() {
      if(this.initialized)return;
      this.initialized = true;
      if(useMockData)return;
      this.loading=true;
      try{
        const [metrics,status,bundle]=await Promise.all([getDashboardMetrics(),getCoreStatus(),getAuditBundle()]);
        this.metrics=metrics;this.status={...status,eventsIngested:metrics.toolCalls24h};this.sessions=bundle.sessions;this.runs=bundle.runs;this.toolCalls=bundle.toolCalls;this.dataSource="core";this.error="";
        if(this.sessions[0])await this.selectSession(this.sessions[0].id);else{this.graphNodes=[];this.graphEdges=[];this.evidence=[];this.timeline=[];this.conversation=[];}
        this.connectStream();
      }catch(error){this.dataSource="fallback";this.error=`Core API unavailable: ${error instanceof Error?error.message:"unknown error"}`;}
      finally{this.loading=false;}
    },
    async selectSession(sessionId: string) {
      this.activeSessionId = sessionId;
      const run = this.runs.find((item) => item.sessionId === sessionId);
      if (run) this.activeRunId = run.id;
      this.selectedNodeId = sessionId === "payroll-leak-demo" ? "send" : "intent";
      this.activeRuntimeTab = "path";
      if(this.dataSource==="core"&&run){
        try{const [graph,evidence,conversation]=await Promise.all([getRiskGraph(run.id),getEvidencePath(run.id),getConversationSummary(run.id)]);this.evidence=evidence;this.conversation=conversation;this.graphNodes=graph.nodes.map(node=>({...node,evidenceStepId:evidence.find(step=>step.nodeId===node.id)?.id}));this.graphEdges=graph.edges;this.timeline=conversation.map((message,index)=>({id:`conversation-${message.id}`,runId:run.id,time:String(index+1).padStart(2,"0"),title:message.role==="user"?"User message":"Assistant message",detail:message.summary,risk:"low"}));this.selectedNodeId=this.graphNodes[0]?.id??"";}
        catch(error){this.error=`Run details unavailable: ${error instanceof Error?error.message:"unknown error"}`;this.graphNodes=[];this.graphEdges=[];this.evidence=[];}
      }
    },
    selectNode(nodeId: string) {
      this.selectedNodeId = nodeId;
    },
    selectToolCall(toolCallId: string) {
      const call = this.toolCalls.find((item) => item.id === toolCallId);
      if (!call) return;
      this.selectSession(call.sessionId);
      this.activeRunId = call.runId;
      this.selectedNodeId = call.nodeId;
      this.activeRuntimeTab = "tool-calls";
    },
    setRuntimeTab(tab: RuntimeTab) {
      this.activeRuntimeTab = tab;
    },
    connectStream(){
      this.streamStop?.();
      this.streamStop=connectAuditStream({onStatus:(status)=>{this.streamState=status;},onEvent:(name,data)=>this.handleStreamEvent(name,data)});
    },
    handleStreamEvent(name:StreamEventName,data:Record<string,unknown>){
      if(name==="heartbeat"||name==="connected"){this.status.pluginLastSeen="just now";return;}
      if(name==="metric_update"){
        const value=(key:string,current:number)=>typeof data[key]==="number"?data[key] as number:current;
        this.metrics={toolCalls24h:value("tool_calls_24h",this.metrics.toolCalls24h),blocked:value("blocked_24h",this.metrics.blocked),highRisk:value("high_risk_24h",this.metrics.highRisk),policyHits:value("policy_hits_24h",this.metrics.policyHits)};return;
      }
      if(name==="trace_event"){
        this.status.pluginLastSeen="just now";
        const sessionId=String(data.session_id??"unknown-session");const runId=String(data.run_id??"unknown-run");const eventType=String(data.type??"trace_event");const detail=summaryText(data.summary,eventType);const existing=this.sessions.find(item=>item.id===sessionId);
        if(existing){existing.time="now";existing.unread=true;existing.subtitle=`${eventType.replaceAll("_"," ")} · live`;if(!existing.runIds.includes(runId))existing.runIds.unshift(runId);this.sessions=[existing,...this.sessions.filter(item=>item.id!==sessionId)];}else this.sessions.unshift({id:sessionId,title:sessionId,subtitle:`${eventType.replaceAll("_"," ")} · live conversation`,risk:"low",time:"now",runIds:[runId],unread:true});
        if(!this.runs.some(run=>run.id===runId))this.runs.unshift({id:runId,sessionId,title:`Run ${runId}`,startedAt:new Date().toISOString(),decision:"allow",risk:"low",summary:"Live conversation run"});
        if(sessionId===this.activeSessionId){this.timeline.push({id:String(data.event_id??`trace-${Date.now()}`),runId,time:new Date().toLocaleTimeString("zh-CN",{hour12:false}),title:eventType.replaceAll("_"," "),detail,risk:"low"});if(["message_received","llm_output","message_sending"].includes(eventType))this.conversation.push({id:String(data.event_id??`message-${Date.now()}`),role:data.role==="user"||eventType==="message_received"?"user":"assistant",summary:detail});}return;
      }
      const sessionId=String(data.session_id??"unknown-session");const runId=String(data.run_id??"unknown-run");const toolCallId=String(data.tool_call_id??`tool-${Date.now()}`);const risk=this.normalizeRisk(data.risk_level);const decision=String(data.decision??"").toUpperCase()==="BLOCK"?"block":String(data.decision??"").toUpperCase()==="ALLOW"?"allow":"review";
      const existing=this.sessions.find(item=>item.id===sessionId);if(existing){existing.time="now";existing.unread=true;existing.risk=risk;this.sessions=[existing,...this.sessions.filter(item=>item.id!==sessionId)];}else this.sessions.unshift({id:sessionId,title:sessionId,subtitle:`${String(data.tool_name??"tool")} · live event`,risk,time:"now",runIds:[runId],unread:true});
      const call:ToolCall={id:toolCallId,sessionId,runId,time:new Date().toLocaleTimeString("zh-CN",{hour12:false}),toolName:String(data.tool_name??"unknown_tool"),toolKind:String(data.tool_kind??"").includes("shell")?"shell":String(data.tool_kind??"").includes("file")?"filesystem":String(data.tool_kind??"").includes("network")?"network":"transform",resource:"Live Core event",decision,riskLevel:risk,latencyMs:0,policyHits:Array.isArray(data.matched_rules)?data.matched_rules.map(String):[],argumentsSummary:String(data.reason??"Live audit event"),nodeId:`tool:${toolCallId}`};
      this.toolCalls.unshift(call);this.metrics.toolCalls24h+=1;if(decision==="block")this.metrics.blocked+=1;if(risk==="high"||risk==="critical")this.metrics.highRisk+=1;this.metrics.policyHits+=call.policyHits.length;this.status.eventsIngested+=1;this.status.pluginLastSeen="just now";
      if(sessionId===this.activeSessionId)this.timeline.unshift({id:`timeline-${toolCallId}`,runId,time:call.time,title:`${call.toolName} · ${decision}`,detail:call.argumentsSummary,risk,nodeId:call.nodeId});
    },
    normalizeRisk(value:unknown):RiskLevel{return ["critical","high","medium","low"].includes(String(value))?String(value) as RiskLevel:"low";},
  },
});
