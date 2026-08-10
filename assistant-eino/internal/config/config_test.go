package config

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

var configEnvNames = []string{
	"TRACESHIELD_ASSISTANT_HOST",
	"TRACESHIELD_ASSISTANT_PORT",
	"TRACESHIELD_ASSISTANT_API_KEY",
	"TRACESHIELD_ASSISTANT_API_KEY_FILE",
	"TRACESHIELD_ASSISTANT_BASE_URL",
	"TRACESHIELD_ASSISTANT_MODEL",
	"TRACESHIELD_ASSISTANT_TIMEOUT_MS",
	"TRACESHIELD_ASSISTANT_MAX_BODY_BYTES",
	"TRACESHIELD_ASSISTANT_MAX_MESSAGE_RUNES",
	"TRACESHIELD_ASSISTANT_MAX_HISTORY_ITEMS",
	"TRACESHIELD_ASSISTANT_MAX_HISTORY_RUNES",
	"TRACESHIELD_ASSISTANT_MAX_CONTEXT_BYTES",
	"TRACESHIELD_ASSISTANT_MAX_TOKENS",
	"TRACESHIELD_ASSISTANT_TEMPERATURE",
	"TRACESHIELD_ASSISTANT_THINKING_ENABLED",
	"TRACESHIELD_ASSISTANT_ALLOWED_ORIGINS",
	"DEEPSEEK_API_KEY",
	"DEEPSEEK_BASE_URL",
	"DEEPSEEK_MODEL",
}

func clearConfigEnv(t *testing.T) {
	t.Helper()
	for _, name := range configEnvNames {
		t.Setenv(name, "")
	}
}

func TestLoadDefaults(t *testing.T) {
	clearConfigEnv(t)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.Host != "127.0.0.1" || cfg.Port != 8790 {
		t.Fatalf("unexpected listen address: %s:%d", cfg.Host, cfg.Port)
	}
	if cfg.BaseURL != "https://api.deepseek.com" || cfg.Model != "deepseek-v4-flash" {
		t.Fatalf("unexpected provider defaults: base=%q model=%q", cfg.BaseURL, cfg.Model)
	}
	if cfg.RequestTimeout != 60*time.Second {
		t.Fatalf("RequestTimeout = %s", cfg.RequestTimeout)
	}
	if cfg.APIKey != "" {
		t.Fatal("APIKey should be empty by default")
	}
}

func TestLoadAPIKeyFromFile(t *testing.T) {
	clearConfigEnv(t)
	keyPath := filepath.Join(t.TempDir(), "api-key")
	if err := os.WriteFile(keyPath, []byte("  test-file-key\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("TRACESHIELD_ASSISTANT_API_KEY_FILE", keyPath)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.APIKey != "test-file-key" {
		t.Fatalf("APIKey = %q", cfg.APIKey)
	}
}

func TestLoadEnvironmentKeyTakesPriorityOverFile(t *testing.T) {
	clearConfigEnv(t)
	t.Setenv("TRACESHIELD_ASSISTANT_API_KEY", "environment-key")
	t.Setenv("TRACESHIELD_ASSISTANT_API_KEY_FILE", filepath.Join(t.TempDir(), "does-not-exist"))

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.APIKey != "environment-key" {
		t.Fatalf("APIKey = %q", cfg.APIKey)
	}
}

func TestLoadTraceShieldNamesTakePriorityOverAliases(t *testing.T) {
	clearConfigEnv(t)
	t.Setenv("TRACESHIELD_ASSISTANT_API_KEY", "primary-key")
	t.Setenv("DEEPSEEK_API_KEY", "alias-key")
	t.Setenv("TRACESHIELD_ASSISTANT_BASE_URL", "https://primary.example/v1")
	t.Setenv("DEEPSEEK_BASE_URL", "https://alias.example/v1")
	t.Setenv("TRACESHIELD_ASSISTANT_MODEL", "primary-model")
	t.Setenv("DEEPSEEK_MODEL", "alias-model")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.APIKey != "primary-key" || cfg.BaseURL != "https://primary.example/v1" || cfg.Model != "primary-model" {
		t.Fatalf("priority was not applied: key=%q base=%q model=%q", cfg.APIKey, cfg.BaseURL, cfg.Model)
	}
}

func TestLoadRejectsInvalidValues(t *testing.T) {
	clearConfigEnv(t)
	t.Setenv("TRACESHIELD_ASSISTANT_PORT", "70000")
	if _, err := Load(); err == nil {
		t.Fatal("Load() expected an invalid port error")
	}

	clearConfigEnv(t)
	t.Setenv("TRACESHIELD_ASSISTANT_BASE_URL", "file:///tmp/provider")
	if _, err := Load(); err == nil {
		t.Fatal("Load() expected an invalid base URL error")
	}
}
