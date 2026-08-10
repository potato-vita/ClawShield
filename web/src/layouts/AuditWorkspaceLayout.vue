<script setup lang="ts">
import SideRail from "@/components/nav/SideRail.vue";
import TopStatusBar from "@/components/nav/TopStatusBar.vue";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();
</script>

<template>
  <div
    class="audit-workspace"
    :class="{
      'nav-collapsed': ui.navigationCollapsed,
      'session-collapsed': ui.runtimeSessionsCollapsed,
      'inspector-collapsed': ui.runtimeInspectorCollapsed,
    }"
  >
    <TopStatusBar class="workspace-top" />
    <SideRail class="workspace-rail" />
    <aside class="workspace-sessions">
      <slot name="sessions" :collapsed="ui.runtimeSessionsCollapsed" :toggle="() => (ui.runtimeSessionsCollapsed = !ui.runtimeSessionsCollapsed)" />
    </aside>
    <main class="workspace-main"><slot /></main>
    <aside class="workspace-inspector">
      <slot name="inspector" :collapsed="ui.runtimeInspectorCollapsed" :toggle="() => (ui.runtimeInspectorCollapsed = !ui.runtimeInspectorCollapsed)" />
    </aside>
    <section class="workspace-evidence"><slot name="evidence" /></section>
  </div>
</template>

<style scoped>
.audit-workspace {
  --nav-track: 188px;
  --session-track: 276px;
  --inspector-track: 356px;
  --main-min: 540px;
  display: grid;
  grid-template-columns: var(--nav-track) var(--session-track) minmax(var(--main-min), 1fr) var(--inspector-track);
  grid-template-rows: 58px minmax(400px, 1fr) 220px;
  grid-template-areas:
    "top top top top"
    "rail sessions main inspector"
    "rail sessions evidence inspector";
  min-width: 1180px;
  min-height: 680px;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: var(--trace-canvas);
  transition: grid-template-columns 280ms cubic-bezier(.22,1,.36,1);
}
.audit-workspace.nav-collapsed { --nav-track: 68px; }
.audit-workspace.session-collapsed { --session-track: 54px; }
.audit-workspace.inspector-collapsed { --inspector-track: 54px; }
.workspace-top { grid-area: top; }
.workspace-rail { grid-area: rail; }
.workspace-sessions { grid-area: sessions; min-width: 0; padding:12px 0 12px 12px; }
.workspace-main { grid-area: main; min-width: 0; overflow: hidden; padding: 12px 12px 8px; }
.workspace-inspector { grid-area: inspector; min-width: 0; padding:12px 12px 12px 0; }
.workspace-evidence { grid-area: evidence; min-width: 0; padding: 0 12px 12px; overflow: hidden; }
@media (max-width: 1380px) {
  .audit-workspace { --session-track: 248px; --inspector-track: 316px; --main-min: 500px; }
  .audit-workspace.session-collapsed { --session-track: 54px; }
  .audit-workspace.inspector-collapsed { --inspector-track: 54px; }
}
@media (max-width: 1250px) {
  .audit-workspace { --session-track: 220px; --inspector-track: 290px; --main-min: 480px; }
  .audit-workspace.session-collapsed { --session-track: 54px; }
  .audit-workspace.inspector-collapsed { --inspector-track: 54px; }
}
@media (min-width: 1680px) {
  .audit-workspace { --session-track: 292px; --inspector-track: 380px; --main-min: 760px; grid-template-rows:58px minmax(460px,1fr) 230px; }
  .audit-workspace.session-collapsed { --session-track: 54px; }
  .audit-workspace.inspector-collapsed { --inspector-track: 54px; }
}
</style>
