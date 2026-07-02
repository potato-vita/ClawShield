<script setup lang="ts">
import { ref } from "vue";
import SideRail from "@/components/nav/SideRail.vue";
import TopStatusBar from "@/components/nav/TopStatusBar.vue";

const sessionCollapsed = ref(false);
</script>

<template>
  <div class="audit-workspace" :class="{ 'session-collapsed': sessionCollapsed }">
    <TopStatusBar class="workspace-top" />
    <SideRail class="workspace-rail" />
    <aside class="workspace-sessions">
      <slot name="sessions" :collapsed="sessionCollapsed" :toggle="() => (sessionCollapsed = !sessionCollapsed)" />
    </aside>
    <main class="workspace-main"><slot /></main>
    <aside class="workspace-inspector"><slot name="inspector" /></aside>
    <section class="workspace-evidence"><slot name="evidence" /></section>
  </div>
</template>

<style scoped>
.audit-workspace {
  display: grid;
  grid-template-columns: 68px 276px minmax(540px, 1fr) 356px;
  grid-template-rows: 58px minmax(400px, 1fr) 220px;
  grid-template-areas:
    "top top top top"
    "rail sessions main inspector"
    "rail sessions evidence inspector";
  min-width: 1200px;
  min-height: 680px;
  height: 100vh;
  overflow: hidden;
  background: var(--trace-canvas);
  transition: grid-template-columns 240ms cubic-bezier(.2,.8,.2,1);
}
.audit-workspace.session-collapsed { grid-template-columns: 68px 54px minmax(650px, 1fr) 356px; }
.workspace-top { grid-area: top; }
.workspace-rail { grid-area: rail; }
.workspace-sessions { grid-area: sessions; min-width: 0; padding:12px 0 12px 12px; }
.workspace-main { grid-area: main; min-width: 0; overflow: hidden; padding: 12px 12px 8px; }
.workspace-inspector { grid-area: inspector; min-width: 0; padding:12px 12px 12px 0; }
.workspace-evidence { grid-area: evidence; min-width: 0; padding: 0 12px 12px; overflow: hidden; }
@media (min-width: 1680px) { .audit-workspace { grid-template-columns: 72px 292px minmax(760px, 1fr) 380px; grid-template-rows:58px minmax(460px,1fr) 230px } }
</style>
