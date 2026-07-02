<script setup lang="ts">
import { Ban, Bot, FileKey, Network, ShieldAlert, Terminal, UserRound } from "lucide-vue-next";
import type { GraphNode } from "@/types/graph";

const props = defineProps<{ node: GraphNode; selected?: boolean }>();
defineEmits<{ select: [node: GraphNode] }>();

const icons = {
  user_intent: UserRound,
  tool_call: Terminal,
  sensitive_object: FileKey,
  network_sink: Network,
  policy_decision: ShieldAlert,
  blocked: Ban,
};
</script>

<template>
  <button class="path-node" :class="[`type-${node.type}`, `risk-${node.risk}`, { selected }]" @click="$emit('select', props.node)">
    <span class="node-icon"><component :is="icons[node.type] ?? Bot" :size="17" /></span>
    <span class="node-copy"><small>{{ node.type.replace('_', ' ') }}</small><strong>{{ node.label }}</strong><code>{{ node.detail }}</code></span>
    <span v-if="node.decision" class="decision">{{ node.decision }}</span>
  </button>
</template>

<style scoped>
.path-node{position:relative;display:flex;align-items:center;gap:9px;width:100%;min-width:0;padding:10px;border:1px solid #dfe4e9;border-radius:11px;text-align:left;background:#fff;box-shadow:0 5px 14px rgba(30,41,59,.045);cursor:pointer;transition:border-color 170ms ease,box-shadow 190ms ease,transform 200ms cubic-bezier(.2,.8,.2,1)}.path-node:hover{border-color:#bdc6d0;box-shadow:0 9px 20px rgba(30,41,59,.075);transform:translateY(-2px)}.path-node.selected{border-color:var(--trace-red);box-shadow:0 0 0 3px rgba(201,31,55,.08),0 9px 20px rgba(30,41,59,.07)}.node-icon{display:grid;place-items:center;flex:0 0 31px;width:31px;height:31px;border-radius:9px;color:#627083;background:#eef1f4}.node-copy{min-width:0}.node-copy small,.node-copy strong,.node-copy code{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.node-copy small{color:#99a2ae;font-size:7px;letter-spacing:.08em;text-transform:uppercase}.node-copy strong{margin:2px 0;font-size:10px}.node-copy code{color:#748091;font-size:7px}.risk-high .node-icon,.risk-critical .node-icon{color:var(--trace-red);background:#fff0f0}.type-blocked{border-color:#b91b31;color:#fff;background:var(--trace-red);animation:block-pulse 2.4s infinite}.type-blocked .node-icon{color:#fff;background:rgba(255,255,255,.16)}.type-blocked .node-copy small,.type-blocked .node-copy code{color:rgba(255,255,255,.72)}.type-blocked.selected{border-color:#8d1023;box-shadow:0 0 0 3px rgba(201,31,55,.14),0 9px 20px rgba(201,31,55,.18)}.decision{position:absolute;right:7px;top:6px;padding:2px 4px;border-radius:4px;color:var(--trace-red);background:#fff1f1;font-size:6px;font-weight:800;text-transform:uppercase}.type-blocked .decision{display:none}@keyframes block-pulse{50%{box-shadow:0 0 0 5px rgba(201,31,55,0),0 9px 20px rgba(201,31,55,.16)}}
</style>
