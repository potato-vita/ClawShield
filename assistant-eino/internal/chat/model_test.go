package chat

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	openai "github.com/cloudwego/eino-ext/components/model/openai"
)

func TestEinoDeepSeekModelUsesOpenAICompatibleStreaming(t *testing.T) {
	requestBody := make(chan map[string]any, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/chat/completions" {
			t.Errorf("path = %q", r.URL.Path)
		}
		if r.Header.Get("Authorization") != "Bearer test-key" {
			t.Errorf("Authorization = %q", r.Header.Get("Authorization"))
		}
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Errorf("decode request: %v", err)
			return
		}
		requestBody <- body

		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "event: message\n")
		_, _ = io.WriteString(w, `data: {"id":"1","object":"chat.completion.chunk","created":1,"model":"deepseek-v4-flash","choices":[{"index":0,"delta":{"role":"assistant","content":"Eino "},"finish_reason":""}]}`+"\n\n")
		_, _ = io.WriteString(w, "event: message\n")
		_, _ = io.WriteString(w, `data: {"id":"2","object":"chat.completion.chunk","created":2,"model":"deepseek-v4-flash","choices":[{"index":0,"delta":{"content":"works"},"finish_reason":"stop"}]}`+"\n\n")
		_, _ = io.WriteString(w, "event: done\ndata: [DONE]\n\n")
	}))
	defer upstream.Close()

	model, err := NewEinoDeepSeekModel(context.Background(), DeepSeekConfig{
		APIKey:          "test-key",
		BaseURL:         upstream.URL,
		Model:           "deepseek-v4-flash",
		Timeout:         time.Second,
		MaxOutputTokens: 1_200,
		Temperature:     0.2,
		ThinkingEnabled: false,
	})
	if err != nil {
		t.Fatalf("NewEinoDeepSeekModel() error = %v", err)
	}
	stream, err := model.Stream(context.Background(), []Message{
		{Role: RoleSystem, Content: "read only"},
		{Role: RoleUser, Content: "hello"},
	})
	if err != nil {
		t.Fatalf("Stream() error = %v", err)
	}
	defer stream.Close()

	first, err := stream.Recv()
	if err != nil || first.Content != "Eino " {
		t.Fatalf("first chunk = %+v, error = %v", first, err)
	}
	second, err := stream.Recv()
	if err != nil || second.Content != "works" || second.FinishReason != "stop" {
		t.Fatalf("second chunk = %+v, error = %v", second, err)
	}
	if _, err = stream.Recv(); err != io.EOF {
		t.Fatalf("final error = %v, want io.EOF", err)
	}

	body := <-requestBody
	if body["model"] != "deepseek-v4-flash" || body["stream"] != true || body["max_tokens"] != float64(1_200) {
		t.Fatalf("unexpected provider request: %#v", body)
	}
	thinking, ok := body["thinking"].(map[string]any)
	if !ok || thinking["type"] != "disabled" {
		t.Fatalf("thinking toggle was not forwarded: %#v", body["thinking"])
	}
	if _, exists := body["tools"]; exists {
		t.Fatalf("tools must not be registered: %#v", body["tools"])
	}
	messages, ok := body["messages"].([]any)
	if !ok || len(messages) != 2 {
		t.Fatalf("unexpected messages: %#v", body["messages"])
	}
}

func TestIsRetryableStreamStartError(t *testing.T) {
	tests := []struct {
		name string
		err  error
		want bool
	}{
		{name: "provider bad request", err: &openai.APIError{HTTPStatusCode: http.StatusBadRequest}, want: false},
		{name: "provider unauthorized", err: &openai.APIError{HTTPStatusCode: http.StatusUnauthorized}, want: false},
		{name: "provider rate limit", err: &openai.APIError{HTTPStatusCode: http.StatusTooManyRequests}, want: true},
		{name: "provider bad gateway", err: &openai.APIError{HTTPStatusCode: http.StatusBadGateway}, want: true},
		{name: "deadline", err: context.DeadlineExceeded, want: false},
		{name: "canceled", err: context.Canceled, want: false},
		{name: "wrapped cancellation", err: errors.Join(errors.New("provider"), context.Canceled), want: false},
		{name: "unknown adapter error", err: errors.New("adapter failed"), want: true},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			if got := IsRetryableStreamStartError(test.err); got != test.want {
				t.Fatalf("IsRetryableStreamStartError() = %v, want %v", got, test.want)
			}
		})
	}
}
