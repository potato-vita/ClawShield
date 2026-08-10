<script setup lang="ts">
import { ref } from "vue";
import { ChevronLeft, MoreHorizontal, X } from "lucide-vue-next";
import AssistantTab from "./AssistantTab.vue";
import DecisionTab from "./DecisionTab.vue";
import EvidenceTab from "./EvidenceTab.vue";
import type { EvidenceStep } from "@/types/evidence";
import type { GraphNode } from "@/types/graph";
import type { ToolCall } from "@/types/toolCall";
defineProps<{collapsed?:boolean;node?:GraphNode;toolCall?:ToolCall;evidence?:EvidenceStep}>();
defineEmits<{toggle:[]}>();
const active = ref<"decision" | "evidence" | "assistant">("decision");
const notice=ref("");
const act=(label:string)=>{notice.value=`已记录演示操作：${label}`;window.setTimeout(()=>notice.value="",2200)};
const tabs = ["decision", "evidence", "assistant"] as const;
const tabLabels = { decision: "决策", evidence: "证据", assistant: "助手" } as const;
</script>
<template>
  <section class="inspector" :class="{ collapsed }">
    <template v-if="!collapsed">
      <header><div><small>审计检查器</small><strong>{{node?.label ?? '尚未选择节点'}}</strong></div><div><button aria-label="更多操作"><MoreHorizontal :size="16" /></button><button aria-label="收起检查器" title="收起检查器" @click="$emit('toggle')"><X :size="15" /></button></div></header>
      <div class="tab-list"><button v-for="tab in tabs" :key="tab" :class="{active:active===tab}" @click="active=tab">{{ tabLabels[tab] }}</button></div>
      <div class="tab-body"><DecisionTab v-if="active==='decision'" :node="node" :tool-call="toolCall" /><EvidenceTab v-else-if="active==='evidence'" :evidence="evidence" /><AssistantTab v-else :node="node" /></div>
      <div v-if="notice" class="action-notice">{{notice}}</div>
      <footer><button class="secondary" @click="act('保持阻止')">保持阻止</button><button class="secondary" @click="act('仅本次批准')">仅本次批准</button><button class="primary" @click="act('创建策略')">创建策略</button><button class="secondary" @click="act('加入允许名单')">加入允许名单</button></footer>
    </template>
    <button v-else class="collapsed-reopen" type="button" title="展开审计检查器" @click="$emit('toggle')"><ChevronLeft :size="15" /><span>审计详情</span></button>
  </section>
</template>
<style scoped>
.inspector{display:flex;flex-direction:column;height:100%;overflow:hidden;border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(30,41,59,.04);transition:border-color 180ms ease,box-shadow 220ms ease}.inspector header{display:flex;align-items:center;justify-content:space-between;padding:16px 15px 13px;border-bottom:1px solid var(--trace-border);animation:panel-reveal 180ms ease}header small,header strong{display:block}header small{margin-bottom:3px;color:#8d97a4;font-size:9px;text-transform:uppercase;letter-spacing:.13em}header strong{font:650 13px var(--trace-font-mono)}header>div:last-child{display:flex;gap:3px}header button{display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:8px;color:#7c8796;background:transparent;cursor:pointer;transition:background-color 160ms ease,color 160ms ease}header button:hover{color:var(--trace-ink);background:#f1f3f5}.tab-list{display:grid;grid-template-columns:repeat(3,1fr);padding:8px 12px 0;border-bottom:1px solid var(--trace-border)}.tab-list button{padding:9px 3px 10px;border:0;border-bottom:2px solid transparent;color:#8993a1;background:transparent;font-size:10px;cursor:pointer;transition:color 160ms ease,border-color 160ms ease}.tab-list button.active{border-color:var(--trace-red);color:var(--trace-ink);font-weight:700}.tab-body{flex:1;padding:18px 16px;overflow:auto}.action-notice{margin:0 13px 6px;padding:7px;border:1px solid #f0cdd2;border-radius:7px;color:#9f172b;background:#fff5f4;text-align:center;font-size:8px}.inspector footer{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:10px 12px;border-top:1px solid var(--trace-border)}footer button{padding:7px 4px;border-radius:8px;font-size:8px;font-weight:650;cursor:pointer;transition:transform 160ms cubic-bezier(.2,.8,.2,1),box-shadow 160ms ease}footer button:hover{transform:translateY(-1px);box-shadow:0 4px 10px rgba(30,41,59,.07)}.secondary{border:1px solid #dfe4e9;background:#fff}.primary{border:1px solid var(--trace-red);color:#fff;background:var(--trace-red)}
.inspector.collapsed{display:grid;place-items:center;padding:0;box-shadow:none}.collapsed-reopen{display:flex;width:100%;height:100%;align-items:center;justify-content:center;gap:9px;padding:9px 0;border:0;color:#748091;background:#fff;cursor:pointer;transition:color 160ms ease,background-color 160ms ease}.collapsed-reopen:hover{color:var(--trace-red);background:#fff7f7}.collapsed-reopen span{font-size:9px;font-weight:700;letter-spacing:.12em;white-space:nowrap;writing-mode:vertical-rl}.collapsed-reopen svg{flex:0 0 auto}
@keyframes panel-reveal{from{opacity:0;transform:translateX(5px)}}
</style>
