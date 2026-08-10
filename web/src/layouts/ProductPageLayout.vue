<script setup lang="ts">
import SideRail from "@/components/nav/SideRail.vue";
import TopStatusBar from "@/components/nav/TopStatusBar.vue";
import { useUiStore } from "@/stores/uiStore";

const ui = useUiStore();

withDefaults(defineProps<{
  eyebrow: string;
  title: string;
  description: string;
  mode?: "page" | "workspace";
  immersive?: boolean;
}>(), {
  mode: "page",
  immersive: false,
});
</script>

<template>
  <div class="product-layout" :class="{ 'is-workspace': mode === 'workspace' || immersive, 'nav-collapsed': ui.navigationCollapsed }">
    <TopStatusBar class="top" />
    <SideRail class="rail" />
    <main>
      <header v-if="mode !== 'workspace' && !immersive" class="page-header">
        <div>
          <small>{{ eyebrow }}</small>
          <h1>{{ title }}</h1>
          <p>{{ description }}</p>
        </div>
        <slot name="actions" />
      </header>
      <div class="page-content"><slot /></div>
    </main>
  </div>
</template>

<style scoped>
.product-layout {
  display: grid;
  grid-template-columns: 188px minmax(0, 1fr);
  grid-template-rows: 58px minmax(0, 1fr);
  grid-template-areas:
    "top top"
    "rail main";
  min-width: 1000px;
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
  background: var(--trace-canvas);
  transition: grid-template-columns 280ms cubic-bezier(.22,1,.36,1);
}

.product-layout.nav-collapsed { grid-template-columns: 68px minmax(0, 1fr); }

.top { grid-area: top; }
.rail { grid-area: rail; }

main {
  grid-area: main;
  min-width: 0;
  min-height: 0;
  padding: 26px 30px;
  overflow: auto;
  scroll-behavior: smooth;
}

.page-header,
.page-content {
  max-width: 1560px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.page-header small {
  color: var(--trace-red);
  font-size: 9px;
  font-weight: 750;
  letter-spacing: .12em;
  text-transform: uppercase;
}

.page-header h1 {
  margin: 5px 0 4px;
  font-size: 24px;
  letter-spacing: -.03em;
}

.page-header p {
  margin: 0;
  color: #748091;
  font-size: 11px;
}

.product-layout.is-workspace main {
  padding: 0;
  overflow: hidden;
}

.product-layout.is-workspace .page-content {
  width: 100%;
  max-width: none;
  height: 100%;
  min-height: 0;
  margin: 0;
}

@media (min-width: 1680px) {
  main { padding: 32px 40px; }
  .page-header { margin-bottom: 22px; }
  .product-layout.is-workspace main { padding: 0; }
}
</style>
