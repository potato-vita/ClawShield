<script setup lang="ts">
import { computed, ref } from "vue";
import { ArrowUpRight, ChevronLeft, ChevronRight, Filter, Search } from "lucide-vue-next";
import type { AuditSession } from "@/types/session";
import SessionCard from "./SessionCard.vue";

const props=defineProps<{ collapsed?: boolean; sessions: AuditSession[]; activeId?: string }>();
defineEmits<{ toggle: []; select: [id: string] }>();
const filter = ref<"risk" | "all">("all");
const query=ref("");
const visibleSessions=computed(()=>props.sessions.filter(item=>(filter.value==="all"||item.risk!=="low")&&(item.title+item.subtitle).toLowerCase().includes(query.value.toLowerCase())));
</script>

<template>
  <div class="session-panel" :class="{ collapsed }">
    <template v-if="!collapsed">
      <div class="panel-heading"><div><span>Runtime context</span><strong>Recent sessions</strong></div><router-link to="/sessions" title="Open Sessions page"><ArrowUpRight :size="15" /></router-link></div>
      <div class="filter-row"><div class="segmented"><button :class="{ active: filter === 'risk' }" @click="filter='risk'">Risk</button><button :class="{ active: filter === 'all' }" @click="filter='all'">All</button></div><button class="square"><Filter :size="14" /></button></div>
      <label class="search-box"><Search :size="14" /><input v-model="query" placeholder="Search sessions" /></label>
      <div class="session-list"><p>Today <span>{{ visibleSessions.length }} sessions</span></p><SessionCard v-for="item in visibleSessions" :key="item.id" v-bind="item" :active="activeId === item.id" @select="$emit('select', item.id)" /><div v-if="!visibleSessions.length" class="empty">No matching sessions</div></div>
    </template>
    <span v-else class="vertical-label">Sessions</span>
    <button class="collapse-button" @click="$emit('toggle')"><ChevronLeft v-if="!collapsed" :size="14" /><ChevronRight v-else :size="14" /></button>
  </div>
</template>

<style scoped>
.session-panel { position: relative; height: 100%; padding: 16px 10px 12px; overflow: hidden; border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(30,41,59,.04) }.panel-heading { display: flex; align-items: center; justify-content: space-between; padding: 0 3px 13px; }.panel-heading span,.panel-heading strong { display:block; }.panel-heading span { margin-bottom: 4px; color: #8a94a2; font-size: 8px; letter-spacing:.13em; text-transform:uppercase; }.panel-heading strong { font-size: 14px; }.panel-heading a,.square { display:grid; place-items:center; width:30px; height:30px; border:1px solid #e1e5e9; border-radius:9px; color:#748091;background:#fff; cursor:pointer;transition:color 160ms ease,border-color 160ms ease,transform 180ms cubic-bezier(.2,.8,.2,1) }.panel-heading a:hover{color:var(--trace-red);border-color:#e9bfc6;transform:translate(1px,-1px)}.filter-row { display:flex; align-items:center; gap:7px; margin-bottom:9px; }.segmented { display:grid; grid-template-columns:1fr 1fr; flex:1; padding:3px; border:1px solid #e1e5e9; border-radius:10px; background:#f0f2f3; }.segmented button { padding:6px; border:0; border-radius:7px; color:#7a8595; background:transparent; font-size:10px; cursor:pointer;transition:background-color 160ms ease,color 160ms ease }.segmented button.active { color:var(--trace-ink); background:#fff; box-shadow:0 2px 6px rgba(30,41,59,.08); font-weight:650; }.search-box { display:flex; align-items:center; gap:7px; margin-bottom:15px; padding:8px 10px; border:1px solid #e1e5e9; border-radius:10px; color:#8b96a5; background:#fafbfb;transition:border-color 160ms ease,background-color 160ms ease }.search-box:focus-within{border-color:#c8cfd7;background:#fff}.search-box input { width:100%; border:0; outline:0; color:var(--trace-ink); background:transparent; font-size:10px; }.session-list{height:calc(100% - 132px);overflow:auto;padding-right:2px}.session-list > p { display:flex; justify-content:space-between; margin:0 5px 7px; color:#687486; font-size:10px; font-weight:650; }.session-list > p span { color:#9aa3af; font-weight:500; }.collapse-button { position:absolute; right:-1px; bottom:14px; display:grid; place-items:center; width:25px; height:35px; border:1px solid #dde2e7; border-right:0; border-radius:9px 0 0 9px; color:#6f7a89; background:#fff; cursor:pointer;transition:color 160ms ease,background-color 160ms ease }.collapse-button:hover{color:var(--trace-red);background:#fafafa}.collapsed { display:grid; place-items:center; padding:0; }.vertical-label { color:#7d8795; font-size:9px; font-weight:700; letter-spacing:.15em; text-transform:uppercase; writing-mode:vertical-rl; }
.empty{padding:22px 8px;color:#929ca9;text-align:center;font-size:9px}
</style>
