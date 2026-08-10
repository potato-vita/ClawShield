<script setup lang="ts">
import {
  Activity,
  Bot,
  Braces,
  ChevronsUp,
  Database,
  FileCheck2,
  LayoutDashboard,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Radar,
  ScrollText,
  Settings,
  ShieldCheck,
} from "lucide-vue-next";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();

const auditItems = [
  { label: "审计会话", shortLabel: "会话", to: "/sessions", icon: Network },
  { label: "工具调用", shortLabel: "工具", to: "/tool-calls", icon: Braces },
  { label: "策略中心", shortLabel: "策略", to: "/policies", icon: ScrollText },
  { label: "风险情报", shortLabel: "风险", to: "/risk-intelligence", icon: Radar },
  { label: "证据仓库", shortLabel: "证据", to: "/evidence", icon: FileCheck2 },
  { label: "合规报告", shortLabel: "报告", to: "/reports", icon: ScrollText },
  { label: "核心状态", shortLabel: "核心", to: "/core", icon: Database },
];
</script>

<template>
  <nav class="rail" :class="{ collapsed: ui.navigationCollapsed }" aria-label="主导航">
    <div class="rail-brand">
      <router-link class="logo" to="/overview" title="TraceShield"><ShieldCheck :size="25" :stroke-width="2.1" /></router-link>
      <span class="brand-copy"><small>TraceShield</small><strong>安全审计</strong></span>
    </div>
    <div class="rail-items">
      <router-link to="/overview" class="rail-link" exact-active-class="is-active" title="安全总览"><LayoutDashboard :size="19" /><span>{{ ui.navigationCollapsed ? "总览" : "安全总览" }}</span></router-link>
      <router-link to="/runtime" class="rail-link runtime-link" exact-active-class="is-active" title="实时审计"><Activity :size="20" /><span>{{ ui.navigationCollapsed ? "运行" : "实时审计" }}</span></router-link>
      <span class="rail-separator" />
      <router-link v-for="item in auditItems" :key="item.label" :to="item.to" class="rail-link" exact-active-class="is-active" :title="item.label">
        <component :is="item.icon" :size="20" /><span>{{ ui.navigationCollapsed ? item.shortLabel : item.label }}</span>
      </router-link>
      <span class="rail-separator" />
      <router-link to="/assistant" class="rail-link" exact-active-class="is-active" title="安全智能体"><Bot :size="20" /><span>{{ ui.navigationCollapsed ? "智能体" : "安全智能体" }}</span></router-link>
    </div>
    <div class="rail-bottom">
      <button class="rail-link" title="跳转到最新事件"><ChevronsUp :size="20" /><span>{{ ui.navigationCollapsed ? "最新" : "最新事件" }}</span></button>
      <router-link to="/settings" class="rail-link" exact-active-class="is-active" title="系统设置"><Settings :size="20" /><span>{{ ui.navigationCollapsed ? "设置" : "系统设置" }}</span></router-link>
      <button class="rail-toggle" type="button" :aria-expanded="!ui.navigationCollapsed" :title="ui.navigationCollapsed ? '展开主导航' : '收起主导航'" @click="ui.toggleNavigation">
        <PanelLeftOpen v-if="ui.navigationCollapsed" :size="19" />
        <PanelLeftClose v-else :size="19" />
        <span>{{ ui.navigationCollapsed ? "展开" : "收起导航" }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.rail { display: flex; min-width: 0; flex-direction: column; padding: 8px; border-right: 1px solid #dde2e7; background: #f4f5f6; overflow: hidden; transition: padding 280ms cubic-bezier(.22,1,.36,1); }
.rail-brand { display: flex; flex: none; align-items: center; gap: 10px; min-height: 42px; margin-bottom: 7px; overflow: hidden; }.logo { flex:none;display: grid; place-items: center; width: 40px; height: 40px; border-radius: 12px; color: #fff; background: var(--trace-red); box-shadow: 0 7px 16px rgba(201, 31, 55, 0.18); transition: transform 180ms cubic-bezier(.2,.8,.2,1), box-shadow 180ms ease; }
.logo:hover{transform:translateY(-1px);box-shadow:0 9px 20px rgba(201,31,55,.22)}
.brand-copy { min-width: 0; opacity: 1; transform: translateX(0); transition: opacity 160ms ease 80ms, transform 260ms cubic-bezier(.22,1,.36,1); }.brand-copy small,.brand-copy strong { display: block; white-space: nowrap; }.brand-copy small { color: #929ca8; font: 7px var(--trace-font-mono); letter-spacing: .08em; text-transform: uppercase; }.brand-copy strong { margin-top: 3px; font-size: 12px; }
.rail-items, .rail-bottom { display: flex; width: 100%; flex-direction: column; gap: 2px; }
.rail-items { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: none; }
.rail-items::-webkit-scrollbar { display: none; }
.rail-bottom { flex: 0 0 auto; margin-top: 4px; }
.rail-separator{width:calc(100% - 18px);height:1px;margin:3px auto;background:#d9dee4;transition:width 260ms ease}
.rail-link { position: relative; flex:none;display: flex; align-items: center; gap: 11px; width: 100%; min-height: 39px; padding: 7px 10px; border: 1px solid transparent; border-radius: 9px; color: #778395; background: transparent; cursor: pointer; transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, transform 180ms cubic-bezier(.2,.8,.2,1), padding 260ms cubic-bezier(.22,1,.36,1), gap 260ms ease; }
.rail-link svg { flex: 0 0 auto; }
.rail-link span { overflow: hidden; font-size: 10px; font-weight: 650; line-height: 1.2; text-overflow: ellipsis; white-space:nowrap }
.rail-link:hover { color: var(--trace-ink); border-color:#e0e4e8; background: #fff; transform: translateX(2px); }
.rail-link.is-active { color: var(--trace-red); border-color:#efd4d8; background: #fff; box-shadow:0 4px 11px rgba(30,41,59,.05) }
.rail-link.is-active::before { position: absolute; left: -9px; top: 8px; width: 3px; height: 21px; border-radius: 0 4px 4px 0; background: var(--trace-red); content: ""; }
.rail-toggle { display: flex; align-items: center; gap: 11px; width: 100%; min-height: 38px; padding: 7px 10px; overflow: hidden; border: 1px solid #dce1e6; border-radius: 9px; color: #647183; background: rgba(255,255,255,.72); cursor: pointer; transition: color 160ms ease, border-color 160ms ease, background-color 160ms ease, padding 260ms cubic-bezier(.22,1,.36,1), gap 260ms ease; }.rail-toggle:hover { color: var(--trace-red); border-color: #e7c1c7; background: #fff; }.rail-toggle svg { flex: 0 0 auto; }.rail-toggle span { overflow: hidden; font-size: 9px; font-weight: 700; white-space: nowrap; }

.rail.collapsed { align-items: center; padding-right: 6px; padding-left: 6px; }
.rail.collapsed .rail-brand { justify-content: center; width: 100%; }
.rail.collapsed .brand-copy { width: 0; opacity: 0; transform: translateX(-8px); transition-delay: 0ms; }
.rail.collapsed .rail-link { flex-direction: column; justify-content: center; gap: 2px; min-height: 38px; padding: 3px 2px 2px; }
.rail.collapsed .rail-link span { font-size: 8px; }
.rail.collapsed .rail-link:hover { transform: translateY(-1px); }
.rail.collapsed .rail-link.is-active::before { left: -7px; }
.rail.collapsed .rail-separator { width: 30px; }
.rail.collapsed .rail-toggle { flex-direction: column; justify-content: center; gap: 2px; min-height: 39px; padding: 3px 2px; }
.rail.collapsed .rail-toggle span { font-size: 8px; }
</style>
