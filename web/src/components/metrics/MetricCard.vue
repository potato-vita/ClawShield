<script setup lang="ts">
defineProps<{ label: string; value: string | number; trend?: string; tone?: "red" | "blue" | "green" | "neutral" }>();
</script>
<template><article class="metric-card" :class="`tone-${tone ?? 'neutral'}`"><span>{{ label }}</span><div><strong>{{ value }}</strong><small v-if="trend">{{ trend }}</small></div></article></template>
<style scoped>
.metric-card { min-width:0; padding:11px 13px; border:1px solid #e4e7eb; border-radius:12px; background:#fff; box-shadow:0 4px 13px rgba(30,41,59,.035);transition:border-color 160ms ease,box-shadow 180ms ease,transform 180ms cubic-bezier(.2,.8,.2,1) }.metric-card:hover{border-color:#d7dde3;box-shadow:0 7px 17px rgba(30,41,59,.055);transform:translateY(-1px)}.metric-card > span { color:#7f8a99; font-size:9px; letter-spacing:.05em; text-transform:uppercase; }.metric-card div { display:flex; align-items:baseline; gap:7px; margin-top:4px; }.metric-card strong { font-family:var(--trace-font-mono); font-size:19px; }.metric-card small { color:#8893a1; font-size:9px; }.tone-red { border-color:#f0d4d8; background:#fffafa; }.tone-red strong { color:var(--trace-red); }.tone-blue strong { color:var(--trace-blue); }.tone-green strong { color:var(--trace-success); }
</style>
