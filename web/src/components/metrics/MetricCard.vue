<script setup lang="ts">
import { computed, type Component } from "vue";

const props = withDefaults(defineProps<{
  label: string;
  value: string | number;
  unit?: string;
  caption: string;
  badge?: string;
  stat?: string;
  progress?: number;
  icon?: Component;
  tone?: "red" | "blue" | "green" | "neutral";
}>(), {
  unit: "",
  badge: "",
  stat: "",
  icon: undefined,
  tone: "neutral",
});

const normalizedProgress = computed(() => Math.min(100, Math.max(0, props.progress ?? 0)));
</script>

<template>
  <article class="metric-card" :class="`tone-${tone}`">
    <header>
      <span v-if="icon" class="metric-icon"><component :is="icon" :size="13" /></span>
      <strong>{{ label }}</strong>
      <em v-if="badge">{{ badge }}</em>
    </header>
    <div class="metric-value"><b>{{ value }}</b><span v-if="unit">{{ unit }}</span></div>
    <footer><span>{{ caption }}</span><b v-if="stat">{{ stat }}</b></footer>
    <div v-if="progress !== undefined" class="metric-progress" aria-hidden="true"><i :style="{ width: `${normalizedProgress}%` }" /></div>
  </article>
</template>

<style scoped>
.metric-card{position:relative;min-width:0;padding:10px 12px 9px;overflow:hidden;border:1px solid #e2e6ea;border-radius:12px;background:#fff;box-shadow:0 4px 13px rgba(30,41,59,.035);transition:border-color 160ms ease,box-shadow 180ms ease,transform 180ms cubic-bezier(.2,.8,.2,1)}
.metric-card:hover{border-color:#d4dbe2;box-shadow:0 7px 17px rgba(30,41,59,.06);transform:translateY(-1px)}
.metric-card header{display:flex;align-items:center;gap:6px;min-width:0}
.metric-card header>strong{overflow:hidden;color:#667384;font-size:9px;font-weight:750;letter-spacing:.02em;text-overflow:ellipsis;white-space:nowrap}
.metric-card header>em{margin-left:auto;padding:2px 5px;border-radius:5px;color:#768393;background:#f1f3f5;font-size:7px;font-style:normal;white-space:nowrap}
.metric-icon{display:grid;place-items:center;width:22px;height:22px;flex:0 0 auto;border-radius:7px;color:#667384;background:#f2f4f6}
.metric-value{display:flex;align-items:baseline;gap:4px;margin-top:5px}
.metric-value>b{color:#17202b;font:700 22px/1 var(--trace-font-mono);letter-spacing:-.04em}
.metric-value>span{color:#8b96a3;font-size:8px;font-weight:650}
.metric-card footer{display:flex;align-items:center;gap:6px;min-width:0;margin-top:6px;color:#8a95a2;font-size:7px}
.metric-card footer>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.metric-card footer>b{margin-left:auto;color:#647183;font:650 7px var(--trace-font-mono);white-space:nowrap}
.metric-progress{height:2px;margin-top:6px;overflow:hidden;border-radius:3px;background:#edf0f2}
.metric-progress>i{display:block;height:100%;border-radius:inherit;background:#7f8b98;transition:width 420ms cubic-bezier(.22,1,.36,1)}
.tone-red{border-color:#efd8dc;background:linear-gradient(145deg,#fffafa,#fff)}
.tone-red .metric-icon{color:var(--trace-red);background:#fff0f1}
.tone-red .metric-value>b,.tone-red footer>b{color:var(--trace-red)}
.tone-red .metric-progress>i{background:var(--trace-red)}
.tone-blue .metric-icon{color:var(--trace-blue);background:#eef4ff}
.tone-blue .metric-value>b,.tone-blue footer>b{color:var(--trace-blue)}
.tone-blue .metric-progress>i{background:var(--trace-blue)}
.tone-green .metric-icon{color:var(--trace-success);background:#edf8f4}
.tone-green .metric-value>b,.tone-green footer>b{color:var(--trace-success)}
.tone-green .metric-progress>i{background:var(--trace-success)}
</style>
