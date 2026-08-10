package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"log/slog"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"traceshield/assistant-eino/internal/chat"
	"traceshield/assistant-eino/internal/config"
	"traceshield/assistant-eino/internal/httpapi"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	if err := run(logger); err != nil {
		logger.Error("assistant service stopped", "error", err)
		os.Exit(1)
	}
}

func run(logger *slog.Logger) error {
	cfg, err := config.Load()
	if err != nil {
		return fmt.Errorf("invalid assistant configuration: %w", err)
	}

	var assistantModel chat.Model
	configured := cfg.APIKey != ""
	if configured {
		model, modelErr := chat.NewEinoDeepSeekModel(context.Background(), chat.DeepSeekConfig{
			APIKey:          cfg.APIKey,
			BaseURL:         cfg.BaseURL,
			Model:           cfg.Model,
			Timeout:         cfg.RequestTimeout,
			MaxOutputTokens: cfg.MaxOutputTokens,
			Temperature:     cfg.Temperature,
			ThinkingEnabled: cfg.ThinkingEnabled,
		})
		if modelErr != nil {
			// Do not wrap the provider error: third-party errors are not guaranteed
			// to exclude credentials or request details.
			return errors.New("could not initialize CloudWeGo Eino chat model")
		}
		assistantModel = model
	}

	api := httpapi.New(httpapi.Config{
		ModelName:       cfg.Model,
		Configured:      configured,
		RequestTimeout:  cfg.RequestTimeout,
		MaxBodyBytes:    cfg.MaxBodyBytes,
		MaxMessageRunes: cfg.MaxMessageRunes,
		MaxHistoryItems: cfg.MaxHistoryItems,
		MaxHistoryRunes: cfg.MaxHistoryRunes,
		MaxContextBytes: cfg.MaxContextBytes,
		AllowedOrigins:  cfg.AllowedOrigins,
	}, assistantModel, logger)

	address := net.JoinHostPort(cfg.Host, strconv.Itoa(cfg.Port))
	server := &http.Server{
		Addr:              address,
		Handler:           api.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		IdleTimeout:       60 * time.Second,
		// Streaming requests are bounded by RequestTimeout in the handler.
		WriteTimeout: 0,
		ErrorLog:     log.New(os.Stderr, "assistant-http: ", log.LstdFlags),
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	serverErrors := make(chan error, 1)
	go func() {
		logger.Info("assistant service listening",
			"address", address,
			"framework", "cloudwego-eino",
			"provider", "deepseek",
			"model", cfg.Model,
			"configured", configured,
			"thinking_enabled", cfg.ThinkingEnabled,
		)
		serverErrors <- server.ListenAndServe()
	}()

	select {
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			return errors.New("assistant service shutdown timed out")
		}
		logger.Info("assistant service stopped gracefully")
		return nil
	case err := <-serverErrors:
		if errors.Is(err, http.ErrServerClosed) {
			return nil
		}
		return fmt.Errorf("assistant HTTP server failed: %w", err)
	}
}
