<script setup lang="ts">
import { Activity, Bot, Braces, ChevronsUp, Database, Network, ScrollText, Settings, ShieldCheck } from "lucide-vue-next";

const auditItems = [
  { label: "Sessions", to: "/sessions", icon: Network },
  { label: "Tool Calls", to: "/tool-calls", icon: Braces },
  { label: "Policies", to: "/policies", icon: ScrollText },
  { label: "Core", to: "/core", icon: Database },
];
</script>

<template>
  <nav class="rail" aria-label="Primary navigation">
    <router-link class="logo" to="/runtime" title="TraceShield"><ShieldCheck :size="25" :stroke-width="2.1" /></router-link>
    <div class="rail-items">
      <router-link to="/runtime" class="rail-link runtime-link" exact-active-class="is-active" title="Runtime"><Activity :size="20" /><span>Runtime</span></router-link>
      <span class="rail-separator" />
      <router-link v-for="item in auditItems" :key="item.label" :to="item.to" class="rail-link" exact-active-class="is-active" :title="item.label">
        <component :is="item.icon" :size="20" /><span>{{ item.label }}</span>
      </router-link>
      <span class="rail-separator" />
      <router-link to="/assistant" class="rail-link" exact-active-class="is-active" title="Assistant"><Bot :size="20" /><span>Assistant</span></router-link>
    </div>
    <div class="rail-bottom">
      <button class="rail-link" title="Scroll to newest"><ChevronsUp :size="20" /><span>Newest</span></button>
      <router-link to="/settings" class="rail-link" exact-active-class="is-active" title="Settings"><Settings :size="20" /><span>Settings</span></router-link>
    </div>
  </nav>
</template>

<style scoped>
.rail { display: flex; flex-direction: column; align-items: center; padding: 10px 7px; border-right: 1px solid #dde2e7; background: #f4f5f6; }
.logo { display: grid; place-items: center; width: 42px; height: 42px; margin-bottom: 13px; border-radius: 13px; color: #fff; background: var(--trace-red); box-shadow: 0 7px 16px rgba(201, 31, 55, 0.18); transition: transform 180ms cubic-bezier(.2,.8,.2,1), box-shadow 180ms ease; }
.logo:hover{transform:translateY(-1px);box-shadow:0 9px 20px rgba(201,31,55,.22)}
.rail-items, .rail-bottom { display: flex; width: 100%; flex-direction: column; gap: 4px; }
.rail-bottom { margin-top: auto; }
.rail-separator{width:30px;height:1px;margin:4px auto;background:#d9dee4}
.rail-link { position: relative; display: flex; flex-direction: column; align-items: center; gap: 4px; width: 100%; padding: 8px 2px 7px; border: 1px solid transparent; border-radius: 10px; color: #778395; background: transparent; cursor: pointer; transition: color 160ms ease, background-color 160ms ease, border-color 160ms ease, transform 180ms cubic-bezier(.2,.8,.2,1); }
.rail-link span { font-size: 9px; font-weight: 650; line-height: 1; }
.rail-link:hover { color: var(--trace-ink); border-color:#e0e4e8; background: #fff; transform: translateY(-1px); }
.rail-link.is-active { color: var(--trace-red); border-color:#efd4d8; background: #fff; box-shadow:0 4px 11px rgba(30,41,59,.05) }
.rail-link.is-active::before { position: absolute; left: -8px; top: 11px; width: 3px; height: 23px; border-radius: 0 4px 4px 0; background: var(--trace-red); content: ""; }
</style>
