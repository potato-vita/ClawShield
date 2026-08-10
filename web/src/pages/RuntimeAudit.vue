<script setup lang="ts">
import { computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useRoute } from "vue-router";
import { Activity, ListChecks, ShieldX, TriangleAlert } from "lucide-vue-next";
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
const {sessions,graphNodes,graphEdges,evidence,timeline,conversation,metrics,activeSessionId,selectedNodeId,selectedNode,selectedToolCall,selectedEvidence,activeToolCalls,activeRuntimeTab,error,loading,dataSource}=storeToRefs(store);
const selectNode=(node:GraphNode)=>store.selectNode(node.id);
const setTab=(tab:RuntimeTab)=>store.setRuntimeTab(tab);
const ratio=(value:number,total:number)=>total>0?Math.min(100,value/total*100):0;
const percent=(value:number)=>`${value.toFixed(value>=10?0:1)}%`;
const blockedRate=computed(()=>ratio(metrics.value.blocked,metrics.value.toolCalls24h));
const highRiskRate=computed(()=>ratio(metrics.value.highRisk,metrics.value.toolCalls24h));
const policyAverage=computed(()=>metrics.value.toolCalls24h>0?metrics.value.policyHits/metrics.value.toolCalls24h:0);
const sourceBadge=computed(()=>loading.value?"同步中":dataSource.value==="core"?"Core 实时":"演示样例");
onMounted(async()=>{await store.initialize();const toolCallId=typeof route.query.tool_call==="string"?route.query.tool_call:"";if(toolCallId)store.selectToolCall(toolCallId);});
</script>

<template>
  <AuditWorkspaceLayout>
    <template #sessions="{ collapsed, toggle }"><SessionPanel :collapsed="collapsed" :sessions="sessions" :active-id="activeSessionId" @toggle="toggle" @select="store.selectSession" /></template>
    <section class="runtime-shell">
      <div v-if="error" class="error-banner">{{error}} · 已使用演示数据保持工作台可用。</div>
      <div class="metric-grid">
        <MetricCard label="工具调用" :value="metrics.toolCalls24h" unit="次" :icon="Activity" :badge="sourceBadge" :caption="metrics.toolCalls24h ? '过去 24 小时累计审计' : '等待 Agent 产生调用'" stat="24H" tone="blue" />
        <MetricCard label="安全拦截" :value="metrics.blocked" unit="次" :icon="ShieldX" badge="执行前" :caption="metrics.blocked ? '危险操作已在执行前阻止' : '当前未触发拦截'" :stat="metrics.toolCalls24h ? `拦截率 ${percent(blockedRate)}` : '实时空闲'" :progress="blockedRate" :tone="metrics.blocked ? 'red' : 'green'" />
        <MetricCard label="高风险事件" :value="metrics.highRisk" unit="起" :icon="TriangleAlert" :badge="metrics.highRisk ? '需关注' : '运行平稳'" :caption="metrics.highRisk ? '高风险与严重事件' : '当前没有高风险事件'" :stat="metrics.toolCalls24h ? `占比 ${percent(highRiskRate)}` : '实时空闲'" :progress="highRiskRate" :tone="metrics.highRisk ? 'red' : 'green'" />
        <MetricCard label="策略响应" :value="metrics.policyHits" unit="次" :icon="ListChecks" badge="策略引擎" :caption="metrics.policyHits ? '安全规则成功匹配' : '策略已就绪，等待事件'" :stat="metrics.toolCalls24h ? `平均 ${policyAverage.toFixed(1)} 条/调用` : '待命'" tone="blue" />
      </div>
      <RuntimeTabs :model-value="activeRuntimeTab" @update:model-value="setTab" />
      <div class="runtime-view">
        <AuditPathCanvas v-if="activeRuntimeTab==='path'" :nodes="graphNodes" :edges="graphEdges" :selected-node-id="selectedNodeId" @select="selectNode" />
        <TimelinePanel v-else-if="activeRuntimeTab==='timeline'" :events="timeline" @select="store.selectNode" />
        <ToolCallsPanel v-else-if="activeRuntimeTab==='tool-calls'" :calls="activeToolCalls" @select="store.selectNode" />
        <ConversationSummary v-else :messages="conversation" />
      </div>
    </section>
    <template #inspector="{ collapsed, toggle }"><InspectorPanel :collapsed="collapsed" :node="selectedNode" :tool-call="selectedToolCall" :evidence="selectedEvidence" @toggle="toggle" /></template>
    <template #evidence><EvidencePathTable :rows="evidence" :highlighted-step-id="selectedEvidence?.id" @select="store.selectNode" /></template>
  </AuditWorkspaceLayout>
</template>

<style scoped>
.runtime-shell{display:flex;flex-direction:column;gap:8px;height:100%;min-height:0}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(112px,1fr));gap:7px}.runtime-view{flex:1;min-height:0}.error-banner{padding:6px 9px;border:1px solid #f0c9cf;border-radius:8px;color:#9f172b;background:#fff4f3;font-size:8px}
</style>
