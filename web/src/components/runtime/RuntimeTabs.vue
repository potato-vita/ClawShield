<script setup lang="ts">
export type RuntimeTab = "path" | "timeline" | "tool-calls" | "conversation";
defineProps<{ modelValue: RuntimeTab }>();
defineEmits<{ "update:modelValue": [tab: RuntimeTab] }>();
const tabs: { id: RuntimeTab; label: string }[] = [{ id: "path", label: "Path" }, { id: "timeline", label: "Timeline" }, { id: "tool-calls", label: "Tool Calls" }, { id: "conversation", label: "Conversation" }];
</script>
<template><nav class="runtime-tabs"><button v-for="tab in tabs" :key="tab.id" :class="{active:modelValue===tab.id}" @click="$emit('update:modelValue',tab.id)">{{tab.label}}</button><span>Pre-execution audit</span></nav></template>
<style scoped>.runtime-tabs{display:flex;align-items:center;gap:3px;padding:3px;border:1px solid var(--trace-border);border-radius:10px;background:#f0f2f3}.runtime-tabs button{padding:6px 12px;border:0;border-radius:7px;color:#788493;background:transparent;font-size:9px;cursor:pointer}.runtime-tabs button.active{color:var(--trace-ink);background:#fff;box-shadow:0 2px 7px rgba(30,41,59,.09);font-weight:700}.runtime-tabs span{margin-left:auto;padding-right:8px;color:#99a2ae;font:7px var(--trace-font-mono);text-transform:uppercase;letter-spacing:.08em}</style>
