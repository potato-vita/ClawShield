package main

import (
	"context"
	"log"
	"net/http"
	"os"
)

func main() {
	coreURL := envOr("TRACESHIELD_CORE_URL", "http://127.0.0.1:8000")
	port := envOr("TRACESHIELD_EINO_PORT", "8080")
	server, err := NewServer(context.Background(), coreURL)
	if err != nil {
		log.Fatal(err)
	}
	address := listenAddress(port)
	log.Printf("TraceShield Eino frontend listening on http://%s (Core %s)", address, coreURL)
	if err := http.ListenAndServe(address, server.Handler()); err != nil {
		log.Fatal(err)
	}
}

func envOr(name, fallback string) string {
	if value := os.Getenv(name); value != "" {
		return value
	}
	return fallback
}
