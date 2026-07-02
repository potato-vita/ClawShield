<script setup lang="ts">
import { computed } from "vue";
import { ArrowDown, ArrowLeft, ArrowRight, Link2 } from "lucide-vue-next";
import type { GraphEdge, GraphNode } from "@/types/graph";
import PathLegend from "./PathLegend.vue";
import PathNode from "./PathNode.vue";

const props = defineProps<{ nodes: GraphNode[]; edges: GraphEdge[]; selectedNodeId?: string }>();
defineEmits<{ select: [node: GraphNode] }>();

const node = (id: string) => props.nodes.find((item) => item.id === id);
const isDemoGraph=computed(()=>Boolean(node("intent")&&node("blocked")));
</script>

<template>
  <section class="path-canvas">
    <header><div><small>Active risk graph</small><strong>Payroll exfiltration · run-payroll-001</strong></div><PathLegend /></header>
    <div v-if="nodes.length && isDemoGraph" class="path-grid">
      <div class="slot n1"><PathNode v-if="node('intent')" :node="node('intent')!" :selected="selectedNodeId==='intent'" @select="$emit('select',$event)" /></div><ArrowRight class="arrow a1" :size="17" />
      <div class="slot n2"><PathNode v-if="node('shell')" :node="node('shell')!" :selected="selectedNodeId==='shell'" @select="$emit('select',$event)" /></div><ArrowRight class="arrow a2" :size="17" />
      <div class="slot n3"><PathNode v-if="node('read')" :node="node('read')!" :selected="selectedNodeId==='read'" @select="$emit('select',$event)" /><button v-if="node('object')" class="branch" @click="$emit('select',node('object')!)"><Link2 :size="10" /> Sensitive: payroll.xlsx</button></div>
      <ArrowDown class="arrow a3" :size="17" />
      <div class="slot n4"><PathNode v-if="node('process')" :node="node('process')!" :selected="selectedNodeId==='process'" @select="$emit('select',$event)" /></div><ArrowLeft class="arrow a4" :size="17" />
      <div class="slot n5"><PathNode v-if="node('send')" :node="node('send')!" :selected="selectedNodeId==='send'" @select="$emit('select',$event)" /><button v-if="node('sink')" class="branch danger" @click="$emit('select',node('sink')!)"><Link2 :size="10" /> Untrusted: suspicious-exfil.com</button></div><ArrowLeft class="arrow a5" :size="17" />
      <div class="slot n6"><PathNode v-if="node('blocked')" :node="node('blocked')!" :selected="selectedNodeId==='blocked'" @select="$emit('select',$event)" /></div>
    </div>
    <div v-else-if="nodes.length" class="generic-path"><template v-for="(item,index) in nodes" :key="item.id"><PathNode :node="item" :selected="selectedNodeId===item.id" @select="$emit('select',$event)" /><ArrowRight v-if="index<nodes.length-1" class="arrow" :size="17" /></template></div>
    <div v-else class="empty">No graph is available for this run.</div>
  </section>
</template>

<style scoped>
.path-canvas{height:100%;min-height:0;padding:14px 16px;border:1px solid var(--trace-border);border-radius:13px;background:#fff;box-shadow:0 6px 18px rgba(30,41,59,.04);overflow:auto;scroll-behavior:smooth}.path-canvas header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:11px}.path-canvas header small,.path-canvas header strong{display:block}.path-canvas header small{margin-bottom:2px;color:var(--trace-red);font-size:7px;font-weight:750;letter-spacing:.12em;text-transform:uppercase}.path-canvas header strong{font-size:10px}.path-grid{display:grid;grid-template-columns:minmax(125px,1fr) 22px minmax(125px,1fr) 22px minmax(125px,1fr);grid-template-rows:minmax(68px,1fr) 20px minmax(68px,1fr);grid-template-areas:"n1 a1 n2 a2 n3" ". . . . a3" "n6 a5 n5 a4 n4";align-items:center;gap:3px;height:calc(100% - 36px);min-height:195px}.slot{min-width:0}.n1{grid-area:n1}.n2{grid-area:n2}.n3{grid-area:n3}.n4{grid-area:n4}.n5{grid-area:n5}.n6{grid-area:n6}.arrow{justify-self:center;color:#a5afba}.a1{grid-area:a1}.a2{grid-area:a2}.a3{grid-area:a3;align-self:center}.a4{grid-area:a4}.a5{grid-area:a5}.branch{display:flex;align-items:center;gap:4px;max-width:100%;margin:4px 0 0 auto;padding:3px 6px;border:1px dashed #d7a04a;border-radius:6px;color:#99640f;background:#fffaf0;font-size:6px;cursor:pointer;transition:transform 160ms ease,border-color 160ms ease}.branch:hover{transform:translateY(-1px);border-style:solid}.branch.danger{border-color:#df9aa5;color:var(--trace-red);background:#fff5f5}.empty{display:grid;place-items:center;height:calc(100% - 40px);color:#8792a0;font-size:10px}
.generic-path{display:flex;align-items:center;gap:7px;min-width:max-content;min-height:190px;padding:15px}.generic-path :deep(.path-node){width:150px}
</style>
