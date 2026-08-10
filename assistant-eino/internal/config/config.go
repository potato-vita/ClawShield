package config

import (
	"errors"
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	defaultHost              = "127.0.0.1"
	defaultPort              = 8790
	defaultBaseURL           = "https://api.deepseek.com"
	defaultModel             = "deepseek-v4-flash"
	defaultTimeout           = 60 * time.Second
	defaultMaxBodyBytes      = int64(256 * 1024)
	defaultMaxMessageRunes   = 12_000
	defaultMaxHistoryItems   = 40
	defaultMaxHistoryRunes   = 48_000
	defaultMaxContextBytes   = 32 * 1024
	defaultMaxOutputTokens   = 1_200
	defaultTemperature       = float32(0.2)
	defaultAllowedOriginsCSV = "http://localhost:5173,http://127.0.0.1:5173"
)

// Config contains the complete process configuration. APIKey must never be
// logged or included in HTTP responses.
type Config struct {
	Host            string
	Port            int
	APIKey          string
	BaseURL         string
	Model           string
	RequestTimeout  time.Duration
	MaxBodyBytes    int64
	MaxMessageRunes int
	MaxHistoryItems int
	MaxHistoryRunes int
	MaxContextBytes int
	MaxOutputTokens int
	Temperature     float32
	ThinkingEnabled bool
	AllowedOrigins  []string
}

// Load reads configuration from environment variables. The TraceShield names
// take precedence over their shorter DeepSeek aliases.
func Load() (Config, error) {
	cfg := Config{
		Host:            envOrDefault("TRACESHIELD_ASSISTANT_HOST", defaultHost),
		BaseURL:         firstNonBlank(os.Getenv("TRACESHIELD_ASSISTANT_BASE_URL"), os.Getenv("DEEPSEEK_BASE_URL"), defaultBaseURL),
		Model:           firstNonBlank(os.Getenv("TRACESHIELD_ASSISTANT_MODEL"), os.Getenv("DEEPSEEK_MODEL"), defaultModel),
		RequestTimeout:  defaultTimeout,
		MaxBodyBytes:    defaultMaxBodyBytes,
		MaxMessageRunes: defaultMaxMessageRunes,
		MaxHistoryItems: defaultMaxHistoryItems,
		MaxHistoryRunes: defaultMaxHistoryRunes,
		MaxContextBytes: defaultMaxContextBytes,
		MaxOutputTokens: defaultMaxOutputTokens,
		Temperature:     defaultTemperature,
		ThinkingEnabled: false,
		AllowedOrigins:  splitCSV(envOrDefault("TRACESHIELD_ASSISTANT_ALLOWED_ORIGINS", defaultAllowedOriginsCSV)),
	}

	var err error
	if cfg.Port, err = envInt("TRACESHIELD_ASSISTANT_PORT", defaultPort, 1, 65_535); err != nil {
		return Config{}, err
	}
	timeoutMS, err := envInt("TRACESHIELD_ASSISTANT_TIMEOUT_MS", int(defaultTimeout/time.Millisecond), 1_000, 300_000)
	if err != nil {
		return Config{}, err
	}
	cfg.RequestTimeout = time.Duration(timeoutMS) * time.Millisecond
	if cfg.MaxBodyBytes, err = envInt64("TRACESHIELD_ASSISTANT_MAX_BODY_BYTES", defaultMaxBodyBytes, 1_024, 4*1024*1024); err != nil {
		return Config{}, err
	}
	if cfg.MaxMessageRunes, err = envInt("TRACESHIELD_ASSISTANT_MAX_MESSAGE_RUNES", defaultMaxMessageRunes, 1, 100_000); err != nil {
		return Config{}, err
	}
	if cfg.MaxHistoryItems, err = envInt("TRACESHIELD_ASSISTANT_MAX_HISTORY_ITEMS", defaultMaxHistoryItems, 0, 200); err != nil {
		return Config{}, err
	}
	if cfg.MaxHistoryRunes, err = envInt("TRACESHIELD_ASSISTANT_MAX_HISTORY_RUNES", defaultMaxHistoryRunes, 0, 500_000); err != nil {
		return Config{}, err
	}
	if cfg.MaxContextBytes, err = envInt("TRACESHIELD_ASSISTANT_MAX_CONTEXT_BYTES", defaultMaxContextBytes, 0, 512*1024); err != nil {
		return Config{}, err
	}
	if cfg.MaxOutputTokens, err = envInt("TRACESHIELD_ASSISTANT_MAX_TOKENS", defaultMaxOutputTokens, 1, 32_768); err != nil {
		return Config{}, err
	}
	if cfg.Temperature, err = envFloat32("TRACESHIELD_ASSISTANT_TEMPERATURE", defaultTemperature, 0, 2); err != nil {
		return Config{}, err
	}
	if cfg.ThinkingEnabled, err = envBool("TRACESHIELD_ASSISTANT_THINKING_ENABLED", false); err != nil {
		return Config{}, err
	}

	cfg.APIKey = firstNonBlank(os.Getenv("TRACESHIELD_ASSISTANT_API_KEY"), os.Getenv("DEEPSEEK_API_KEY"))
	if cfg.APIKey == "" {
		keyFile := strings.TrimSpace(os.Getenv("TRACESHIELD_ASSISTANT_API_KEY_FILE"))
		if keyFile != "" {
			contents, readErr := os.ReadFile(keyFile)
			if readErr != nil {
				return Config{}, fmt.Errorf("read TRACESHIELD_ASSISTANT_API_KEY_FILE: %w", readErr)
			}
			cfg.APIKey = strings.TrimSpace(string(contents))
			if cfg.APIKey == "" {
				return Config{}, errors.New("TRACESHIELD_ASSISTANT_API_KEY_FILE is empty")
			}
		}
	}

	if err := validate(cfg); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func validate(cfg Config) error {
	if strings.TrimSpace(cfg.Host) == "" {
		return errors.New("TRACESHIELD_ASSISTANT_HOST must not be empty")
	}
	parsed, err := url.Parse(cfg.BaseURL)
	if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" {
		return errors.New("TRACESHIELD_ASSISTANT_BASE_URL must be an absolute http(s) URL")
	}
	if strings.TrimSpace(cfg.Model) == "" {
		return errors.New("TRACESHIELD_ASSISTANT_MODEL must not be empty")
	}
	for _, origin := range cfg.AllowedOrigins {
		if origin == "*" {
			continue
		}
		u, parseErr := url.Parse(origin)
		if parseErr != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" || u.Path != "" {
			return fmt.Errorf("invalid allowed origin %q", origin)
		}
	}
	return nil
}

func envOrDefault(name, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(name)); value != "" {
		return value
	}
	return fallback
}

func firstNonBlank(values ...string) string {
	for _, value := range values {
		if value = strings.TrimSpace(value); value != "" {
			return value
		}
	}
	return ""
}

func splitCSV(value string) []string {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		if part = strings.TrimSpace(part); part != "" {
			result = append(result, part)
		}
	}
	return result
}

func envInt(name string, fallback, minValue, maxValue int) (int, error) {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback, nil
	}
	parsed, err := strconv.Atoi(value)
	if err != nil || parsed < minValue || parsed > maxValue {
		return 0, fmt.Errorf("%s must be an integer from %d to %d", name, minValue, maxValue)
	}
	return parsed, nil
}

func envInt64(name string, fallback, minValue, maxValue int64) (int64, error) {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback, nil
	}
	parsed, err := strconv.ParseInt(value, 10, 64)
	if err != nil || parsed < minValue || parsed > maxValue {
		return 0, fmt.Errorf("%s must be an integer from %d to %d", name, minValue, maxValue)
	}
	return parsed, nil
}

func envFloat32(name string, fallback, minValue, maxValue float32) (float32, error) {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback, nil
	}
	parsed, err := strconv.ParseFloat(value, 32)
	if err != nil || float32(parsed) < minValue || float32(parsed) > maxValue {
		return 0, fmt.Errorf("%s must be a number from %.1f to %.1f", name, minValue, maxValue)
	}
	return float32(parsed), nil
}

func envBool(name string, fallback bool) (bool, error) {
	value := strings.TrimSpace(os.Getenv(name))
	if value == "" {
		return fallback, nil
	}
	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return false, fmt.Errorf("%s must be true or false", name)
	}
	return parsed, nil
}
