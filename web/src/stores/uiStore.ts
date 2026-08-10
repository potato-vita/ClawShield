import { defineStore } from "pinia";
import { ref, watch } from "vue";

type PreferenceKey =
  | "navigation-collapsed"
  | "runtime-sessions-collapsed"
  | "runtime-inspector-collapsed"
  | "assistant-sessions-collapsed"
  | "assistant-inspector-collapsed"
  | "settings-navigation-collapsed";

function readPreference(key: PreferenceKey, fallback = false) {
  try {
    const value = window.localStorage.getItem(`traceshield.ui.${key}`);
    return value === null ? fallback : value === "true";
  } catch {
    return fallback;
  }
}

function persistPreference(key: PreferenceKey, value: boolean) {
  try {
    window.localStorage.setItem(`traceshield.ui.${key}`, String(value));
  } catch {
    // The interface remains usable when storage is unavailable.
  }
}

export const useUiStore = defineStore("ui", () => {
  const navigationCollapsed = ref(readPreference("navigation-collapsed"));
  const runtimeSessionsCollapsed = ref(readPreference("runtime-sessions-collapsed"));
  const runtimeInspectorCollapsed = ref(readPreference("runtime-inspector-collapsed"));
  const assistantSessionsCollapsed = ref(readPreference("assistant-sessions-collapsed"));
  const assistantInspectorCollapsed = ref(readPreference("assistant-inspector-collapsed"));
  const settingsNavigationCollapsed = ref(readPreference("settings-navigation-collapsed"));

  const preferences = [
    ["navigation-collapsed", navigationCollapsed],
    ["runtime-sessions-collapsed", runtimeSessionsCollapsed],
    ["runtime-inspector-collapsed", runtimeInspectorCollapsed],
    ["assistant-sessions-collapsed", assistantSessionsCollapsed],
    ["assistant-inspector-collapsed", assistantInspectorCollapsed],
    ["settings-navigation-collapsed", settingsNavigationCollapsed],
  ] as const;

  for (const [key, preference] of preferences) {
    watch(preference, (value) => persistPreference(key, value));
  }

  function toggleNavigation() {
    navigationCollapsed.value = !navigationCollapsed.value;
  }

  return {
    navigationCollapsed,
    runtimeSessionsCollapsed,
    runtimeInspectorCollapsed,
    assistantSessionsCollapsed,
    assistantInspectorCollapsed,
    settingsNavigationCollapsed,
    toggleNavigation,
  };
});
