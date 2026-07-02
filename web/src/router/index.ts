import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/runtime" },
    { path: "/runtime", name: "runtime", component: () => import("@/pages/RuntimeAudit.vue") },
    { path: "/sessions", name: "sessions", component: () => import("@/pages/Sessions.vue") },
    { path: "/tool-calls", name: "tool-calls", component: () => import("@/pages/ToolCalls.vue") },
    { path: "/policies", name: "policies", component: () => import("@/pages/PolicyCenter.vue") },
    { path: "/core", name: "core", component: () => import("@/pages/CoreStatus.vue") },
    {
      path: "/assistant",
      name: "assistant",
      component: () => import("@/pages/ComingSoon.vue"),
      props: { title: "Assistant" },
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/pages/ComingSoon.vue"),
      props: { title: "Settings" },
    },
    { path: "/:pathMatch(.*)*", redirect: "/runtime" },
  ],
});

export default router;
