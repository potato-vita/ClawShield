<script setup lang="ts">
defineProps<{ title: string; subtitle: string; risk: string; time: string; active?: boolean; unread?: boolean }>();
defineEmits<{ select: [] }>();
</script>

<template>
  <button class="session-card" :class="[{ active, unread }, `risk-${risk}`]" @click="$emit('select')"><span class="risk-mark" /><span class="session-copy"><strong>{{ title }}</strong><small>{{ subtitle }}</small></span><span class="session-meta"><b>{{ risk }}</b><small>{{ time }}</small></span></button>
</template>

<style scoped>
.session-card { position: relative; display: grid; grid-template-columns: 5px minmax(0,1fr) auto; gap: 9px; width: 100%; padding: 12px 11px; border: 1px solid transparent; border-radius: 11px; text-align: left; background: transparent; cursor: pointer; transition: border-color 160ms ease,background-color 160ms ease,box-shadow 180ms ease,transform 190ms cubic-bezier(.2,.8,.2,1); }.session-card:hover { border-color: #e1e5ea; background: #fafafa; box-shadow: 0 6px 15px rgba(30,41,59,.05); transform: translateY(-1px); }.session-card.active { border-color: #efcbd1; background: #fff4f4; box-shadow: 0 6px 16px rgba(201,31,55,.07); }.risk-mark { width: 4px; height: 32px; margin-top: 2px; border-radius: 5px; background: #a5b0bd; }.risk-critical .risk-mark, .risk-high .risk-mark { background: var(--trace-red); }.risk-medium .risk-mark { background: #d58b18; }.session-copy { min-width: 0; }.session-copy strong, .session-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.session-copy strong { margin-bottom: 5px; font-size: 12px; }.session-copy small { color: #808b9b; font-size: 10px; }.session-meta { display: flex; align-items: flex-end; flex-direction: column; gap: 7px; }.session-meta b { color: var(--trace-red); font-size: 9px; text-transform: uppercase; }.risk-low .session-meta b { color: #168363; }.risk-medium .session-meta b { color: #b46f00; }.session-meta small { color: #9aa3af; font-size: 9px; }
.session-card.unread:not(:hover){animation:new-event 1.5s ease 1}@keyframes new-event{40%{background:#fff0ef;box-shadow:0 0 0 4px rgba(201,31,55,.08)}}
</style>
