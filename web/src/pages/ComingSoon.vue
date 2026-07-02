<script setup lang="ts">
withDefaults(defineProps<{ title?: string }>(), { title: "Coming Soon" });
</script>

<template>
  <main class="page-shell"><section class="placeholder-card"><p class="text-xs font-semibold uppercase tracking-[0.2em] text-trace-red">TraceShield</p><h1>{{ title }}</h1><p>该区域将在后续版本开放。</p></section></main>
</template>
