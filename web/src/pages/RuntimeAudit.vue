<script setup lang="ts">
import { onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import AuditWorkspaceLayout from "@/layouts/AuditWorkspaceLayout.vue";
import ConversationSummary from "@/components/conversation/ConversationSummary.vue";
import EvidencePathTable from "@/components/evidence/EvidencePathTable.vue";
import InspectorPanel from "@/components/inspector/InspectorPanel.vue";
import MetricCard from "@/components/metrics/MetricCard.vue";
import AuditPathCanvas from "@/components/path/AuditPathCanvas.vue";
import RuntimeTabs, { type RuntimeTab } from "@/components/runtime/RuntimeTabs.vue";
import TimelinePanel from "@/components/runtime/TimelinePanel.vue";
import ToolCallsPanel from "@/components/runtime/ToolCallsPanel.vue";
import SessionPanel from "@/components/sessions/SessionPanel.vue";
import { useRuntimeStore } from "@/stores/runtimeStore";
import type { GraphNode } from "@/types/graph";

const store=useRuntimeStore();
const route=useRoute();
const {sessions,graphNodes,graphEdges,evidence,timeline,conversation,metrics,activeSessionId,selectedNodeId,selectedNode,selectedToolCall,selectedEvidence,activeToolCalls,activeRuntimeTab,error}=storeToRefs(store);
const selectNode=(node:GraphNode)=>store.selectNode(node.id);
const setTab=(tab:RuntimeTab)=>store.setRuntimeTab(tab);
onMounted(async()=>{await store.initialize();const toolCallId=typeof route.query.tool_call==="string"?route.query.tool_call:"";if(toolCallId)store.selectToolCall(toolCallId);});
</script>

<template>
  <AuditWorkspaceLayout>
    <template #sessions="{ collapsed, toggle }"><SessionPanel :collapsed="collapsed" :sessions="sessions" :active-id="activeSessionId" @toggle="toggle" @select="store.selectSession" /></template>
    <section class="runtime-shell">
      <div v-if="error" class="error-banner">{{error}} · Mock data kept the workspace available.</div>
      <div class="metric-grid"><MetricCard label="Tool calls · 24h" :value="metrics.toolCalls24h" trend="+8.2%" /><MetricCard label="Blocked" :value="metrics.blocked" tone="red" trend="critical" /><MetricCard label="High risk" :value="metrics.highRisk" tone="red" /><MetricCard label="Policy hits" :value="metrics.policyHits" tone="blue" /></div>
      <RuntimeTabs :model-value="activeRuntimeTab" @update:model-value="setTab" />
      <div class="runtime-view">
        <AuditPathCanvas v-if="activeRuntimeTab==='path'" :nodes="graphNodes" :edges="graphEdges" :selected-node-id="selectedNodeId" @select="selectNode" />
        <TimelinePanel v-else-if="activeRuntimeTab==='timeline'" :events="timeline" @select="store.selectNode" />
        <ToolCallsPanel v-else-if="activeRuntimeTab==='tool-calls'" :calls="activeToolCalls" @select="store.selectNode" />
        <ConversationSummary v-else :messages="conversation" />
      </div>
    </section>
    <template #inspector><InspectorPanel :node="selectedNode" :tool-call="selectedToolCall" :evidence="selectedEvidence" /></template>
    <template #evidence><EvidencePathTable :rows="evidence" :highlighted-step-id="selectedEvidence?.id" @select="store.selectNode" /></template>
  </AuditWorkspaceLayout>
</template>

<style scoped>
.runtime-shell{display:flex;flex-direction:column;gap:8px;height:100%;min-height:0}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(90px,1fr));gap:7px}.runtime-view{flex:1;min-height:0}.error-banner{padding:6px 9px;border:1px solid #f0c9cf;border-radius:8px;color:#9f172b;background:#fff4f3;font-size:8px}
</style>
