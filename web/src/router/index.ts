import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/overview" },
    {
      path: "/overview",
      name: "overview",
      component: () => import("@/pages/ExecutiveOverview.vue"),
    },
    { path: "/runtime", name: "runtime", component: () => import("@/pages/RuntimeAudit.vue") },
    { path: "/sessions", name: "sessions", component: () => import("@/pages/Sessions.vue") },
    { path: "/tool-calls", name: "tool-calls", component: () => import("@/pages/ToolCalls.vue") },
    { path: "/policies", name: "policies", component: () => import("@/pages/PolicyCenter.vue") },
    {
      path: "/risk-intelligence",
      name: "risk-intelligence",
      component: () => import("@/pages/RiskIntelligence.vue"),
    },
    {
      path: "/evidence",
      name: "evidence",
      component: () => import("@/pages/EvidenceVault.vue"),
    },
    {
      path: "/reports",
      name: "reports",
      component: () => import("@/pages/ComplianceReports.vue"),
    },
    { path: "/core", name: "core", component: () => import("@/pages/CoreStatus.vue") },
    {
      path: "/assistant",
      name: "assistant",
      component: () => import("@/pages/SecurityAssistant.vue"),
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/pages/Settings.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/overview" },
  ],
});

export default router;
