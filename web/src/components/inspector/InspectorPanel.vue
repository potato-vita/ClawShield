<script setup lang="ts">
import { ref } from "vue";
import { MoreHorizontal, X } from "lucide-vue-next";
import AssistantTab from "./AssistantTab.vue";
import DecisionTab from "./DecisionTab.vue";
import EvidenceTab from "./EvidenceTab.vue";
import type { EvidenceStep } from "@/types/evidence";
import type { GraphNode } from "@/types/graph";
import type { ToolCall } from "@/types/toolCall";
defineProps<{node?:GraphNode;toolCall?:ToolCall;evidence?:EvidenceStep}>();
const active = ref<"decision" | "evidence" | "assistant">("decision");
const notice=ref("");
const act=(label:string)=>{notice.value=`${label}: preview action recorded`;window.setTimeout(()=>notice.value="",2200)};
const tabs = ["decision", "evidence", "assistant"] as const;
</script>
<template><section class="inspector"><header><div><small>Inspector</small><strong>{{node?.label ?? 'Nothing selected'}}</strong></div><div><button><MoreHorizontal :size="16" /></button><button><X :size="15" /></button></div></header><div class="tab-list"><button v-for="tab in tabs" :key="tab" :class="{active:active===tab}" @click="active=tab">{{ tab }}</button></div><div class="tab-body"><DecisionTab v-if="active==='decision'" :node="node" :tool-call="toolCall" /><EvidenceTab v-else-if="active==='evidence'" :evidence="evidence" /><AssistantTab v-else :node="node" /></div><div v-if="notice" class="action-notice">{{notice}}</div><footer><button class="secondary" @click="act('Keep Blocked')">Keep Blocked</button><button class="secondary" @click="act('Approve Once')">Approve Once</button><button class="primary" @click="act('Create Policy')">Create Policy</button><button class="secondary" @click="act('Add to Allowlist')">Add to Allowlist</button></footer></section></template>
<style scoped>
.inspector{display:flex;flex-direction:column;height:100%;overflow:hidden;border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(30,41,59,.04)}.inspector header{display:flex;align-items:center;justify-content:space-between;padding:16px 15px 13px;border-bottom:1px solid var(--trace-border)}header small,header strong{display:block}header small{margin-bottom:3px;color:#8d97a4;font-size:9px;text-transform:uppercase;letter-spacing:.13em}header strong{font:650 13px var(--trace-font-mono)}header>div:last-child{display:flex;gap:3px}header button{display:grid;place-items:center;width:28px;height:28px;border:0;border-radius:8px;color:#7c8796;background:transparent;cursor:pointer;transition:background-color 160ms ease,color 160ms ease}header button:hover{color:var(--trace-ink);background:#f1f3f5}.tab-list{display:grid;grid-template-columns:repeat(3,1fr);padding:8px 12px 0;border-bottom:1px solid var(--trace-border)}.tab-list button{padding:9px 3px 10px;border:0;border-bottom:2px solid transparent;color:#8993a1;background:transparent;font-size:10px;text-transform:capitalize;cursor:pointer;transition:color 160ms ease,border-color 160ms ease}.tab-list button.active{border-color:var(--trace-red);color:var(--trace-ink);font-weight:700}.tab-body{flex:1;padding:18px 16px;overflow:auto}.action-notice{margin:0 13px 6px;padding:7px;border:1px solid #f0cdd2;border-radius:7px;color:#9f172b;background:#fff5f4;text-align:center;font-size:8px}.inspector footer{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:10px 12px;border-top:1px solid var(--trace-border)}footer button{padding:7px 4px;border-radius:8px;font-size:8px;font-weight:650;cursor:pointer;transition:transform 160ms cubic-bezier(.2,.8,.2,1),box-shadow 160ms ease}footer button:hover{transform:translateY(-1px);box-shadow:0 4px 10px rgba(30,41,59,.07)}.secondary{border:1px solid #dfe4e9;background:#fff}.primary{border:1px solid var(--trace-red);color:#fff;background:var(--trace-red)}
</style>
