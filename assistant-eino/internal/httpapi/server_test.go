package httpapi

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"traceshield/assistant-eino/internal/chat"
)

type fakeModel struct {
	mu       sync.Mutex
	name     string
	stream   chat.Stream
	err      error
	messages []chat.Message
	calls    int
}

type streamStartResult struct {
	stream chat.Stream
	err    error
}

type scriptedStartModel struct {
	mu      sync.Mutex
	name    string
	results []streamStartResult
	calls   int
}

func (m *scriptedStartModel) Name() string { return m.name }

func (m *scriptedStartModel) Stream(_ context.Context, _ []chat.Message) (chat.Stream, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	resultIndex := m.calls
	m.calls++
	if resultIndex >= len(m.results) {
		resultIndex = len(m.results) - 1
	}
	return m.results[resultIndex].stream, m.results[resultIndex].err
}

func (m *scriptedStartModel) callCount() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.calls
}

func (m *fakeModel) Name() string { return m.name }

func (m *fakeModel) Stream(_ context.Context, messages []chat.Message) (chat.Stream, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.calls++
	m.messages = append([]chat.Message(nil), messages...)
	return m.stream, m.err
}

type fakeStream struct {
	mu     sync.Mutex
	chunks []chat.Chunk
	index  int
	endErr error
	closed bool
}

func (s *fakeStream) Recv() (chat.Chunk, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.index < len(s.chunks) {
		chunk := s.chunks[s.index]
		s.index++
		return chunk, nil
	}
	if s.endErr != nil {
		return chat.Chunk{}, s.endErr
	}
	return chat.Chunk{}, io.EOF
}

func (s *fakeStream) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.closed = true
}

type timeoutModel struct {
	mu    sync.Mutex
	calls int
}

func (*timeoutModel) Name() string { return "deepseek-v4-flash" }

func (m *timeoutModel) Stream(ctx context.Context, _ []chat.Message) (chat.Stream, error) {
	m.mu.Lock()
	m.calls++
	m.mu.Unlock()
	<-ctx.Done()
	return nil, ctx.Err()
}

func (m *timeoutModel) callCount() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.calls
}

type cancelingStartModel struct {
	mu     sync.Mutex
	calls  int
	cancel context.CancelFunc
}

func (*cancelingStartModel) Name() string { return "deepseek-v4-flash" }

func (m *cancelingStartModel) Stream(_ context.Context, _ []chat.Message) (chat.Stream, error) {
	m.mu.Lock()
	m.calls++
	m.mu.Unlock()
	m.cancel()
	return nil, errors.New("transport stopped after caller cancellation")
}

func (m *cancelingStartModel) callCount() int {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.calls
}

func testConfig() Config {
	return Config{
		ModelName:       "deepseek-v4-flash",
		Configured:      true,
		RequestTimeout:  time.Second,
		MaxBodyBytes:    64 * 1024,
		MaxMessageRunes: 1_000,
		MaxHistoryItems: 10,
		MaxHistoryRunes: 5_000,
		MaxContextBytes: 8 * 1024,
		AllowedOrigins:  []string{"http://localhost:5173"},
	}
}

func newTestHandler(cfg Config, model chat.Model, output *bytes.Buffer) http.Handler {
	if output == nil {
		output = &bytes.Buffer{}
	}
	logger := slog.New(slog.NewJSONHandler(output, nil))
	return New(cfg, model, logger).Handler()
}

func TestHealthIdentifiesEinoAndDeepSeek(t *testing.T) {
	model := &fakeModel{name: "deepseek-v4-flash", stream: &fakeStream{}}
	recorder := httptest.NewRecorder()
	newTestHandler(testConfig(), model, nil).ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/health", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d", recorder.Code)
	}
	var response healthResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatal(err)
	}
	if !response.OK || !response.Configured || response.Framework != "cloudwego-eino" || response.Provider != "deepseek" || response.Model != "deepseek-v4-flash" {
		t.Fatalf("unexpected health response: %+v", response)
	}
}

func TestHealthReportsUnconfiguredWithoutExposingConfiguration(t *testing.T) {
	cfg := testConfig()
	cfg.Configured = false
	recorder := httptest.NewRecorder()
	newTestHandler(cfg, nil, nil).ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/health", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d", recorder.Code)
	}
	if strings.Contains(recorder.Body.String(), "base_url") || strings.Contains(recorder.Body.String(), "api_key") {
		t.Fatalf("health contains private configuration: %s", recorder.Body.String())
	}
	if !strings.Contains(recorder.Body.String(), `"configured":false`) || !strings.Contains(recorder.Body.String(), `"ok":false`) {
		t.Fatalf("unexpected health response: %s", recorder.Body.String())
	}
}

func TestChatStreamContractAndPromptConstruction(t *testing.T) {
	stream := &fakeStream{chunks: []chat.Chunk{
		{Content: "hello "},
		{Content: "world", FinishReason: "stop"},
	}}
	model := &fakeModel{name: "deepseek-v4-flash", stream: stream}
	body := `{"conversation_id":"demo-1","message":"What happened?","history":[{"role":"user","content":"Earlier"},{"role":"assistant","content":"Summary"}],"context":{"decision":"BLOCK","risk":8}}`
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(body))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(testConfig(), model, nil).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK {
		t.Fatalf("status = %d body=%s", recorder.Code, recorder.Body.String())
	}
	if contentType := recorder.Header().Get("Content-Type"); !strings.HasPrefix(contentType, "text/event-stream") {
		t.Fatalf("Content-Type = %q", contentType)
	}
	wantParts := []string{
		"event: start\n",
		`data: {"conversation_id":"demo-1","model":"deepseek-v4-flash"}`,
		"event: delta\n",
		`data: {"content":"hello "}`,
		`data: {"content":"world"}`,
		"event: done\n",
		`data: {"conversation_id":"demo-1","finish_reason":"stop"}`,
	}
	for _, want := range wantParts {
		if !strings.Contains(recorder.Body.String(), want) {
			t.Fatalf("SSE response missing %q:\n%s", want, recorder.Body.String())
		}
	}

	model.mu.Lock()
	messages := append([]chat.Message(nil), model.messages...)
	model.mu.Unlock()
	if len(messages) != 5 {
		t.Fatalf("model received %d messages: %+v", len(messages), messages)
	}
	if messages[0].Role != chat.RoleSystem || !strings.Contains(messages[0].Content, "read-only") {
		t.Fatalf("missing read-only system prompt: %+v", messages[0])
	}
	if messages[1].Role != chat.RoleSystem || !strings.Contains(messages[1].Content, `"decision":"BLOCK"`) || !strings.Contains(messages[1].Content, "untrusted evidence") {
		t.Fatalf("context was not isolated as untrusted evidence: %+v", messages[1])
	}
	if messages[4] != (chat.Message{Role: chat.RoleUser, Content: "What happened?"}) {
		t.Fatalf("unexpected final user message: %+v", messages[4])
	}
	stream.mu.Lock()
	closed := stream.closed
	stream.mu.Unlock()
	if !closed {
		t.Fatal("model stream was not closed")
	}
}

func TestChatStreamGeneratesConversationID(t *testing.T) {
	model := &fakeModel{name: "deepseek-v4-flash", stream: &fakeStream{}}
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(`{"message":"hello"}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(testConfig(), model, nil).ServeHTTP(recorder, request)
	if recorder.Code != http.StatusOK || !strings.Contains(recorder.Body.String(), `"conversation_id":"conv_`) {
		t.Fatalf("unexpected response: status=%d body=%s", recorder.Code, recorder.Body.String())
	}
}

func TestChatValidationReturnsSSEErrorsWithoutCallingModel(t *testing.T) {
	tests := []struct {
		name string
		body string
		code string
	}{
		{name: "missing message", body: `{}`, code: "message_required"},
		{name: "unknown field", body: `{"message":"hello","extra":true}`, code: "invalid_request"},
		{name: "invalid role", body: `{"message":"hello","history":[{"role":"system","content":"bad"}]}`, code: "invalid_history"},
		{name: "invalid id", body: `{"conversation_id":"bad id","message":"hello"}`, code: "invalid_conversation_id"},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			model := &fakeModel{name: "deepseek-v4-flash", stream: &fakeStream{}}
			request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(test.body))
			request.Header.Set("Content-Type", "application/json")
			recorder := httptest.NewRecorder()
			newTestHandler(testConfig(), model, nil).ServeHTTP(recorder, request)

			if recorder.Code != http.StatusBadRequest {
				t.Fatalf("status = %d body=%s", recorder.Code, recorder.Body.String())
			}
			if !strings.Contains(recorder.Body.String(), "event: error") || !strings.Contains(recorder.Body.String(), `"code":"`+test.code+`"`) {
				t.Fatalf("unexpected SSE error: %s", recorder.Body.String())
			}
			model.mu.Lock()
			calls := model.calls
			model.mu.Unlock()
			if calls != 0 {
				t.Fatalf("model called %d times", calls)
			}
		})
	}
}

func TestChatProviderErrorAndLogsAreSanitized(t *testing.T) {
	privateText := "private user payload and provider secret"
	model := &fakeModel{name: "deepseek-v4-flash", err: errors.New(privateText)}
	var logs bytes.Buffer
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(`{"message":"`+privateText+`"}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(testConfig(), model, &logs).ServeHTTP(recorder, request)
	if recorder.Code != http.StatusBadGateway || !strings.Contains(recorder.Body.String(), `"code":"upstream_error"`) {
		t.Fatalf("unexpected response: status=%d body=%s", recorder.Code, recorder.Body.String())
	}
	if strings.Contains(recorder.Body.String(), privateText) || strings.Contains(logs.String(), privateText) {
		t.Fatalf("private text leaked: response=%s logs=%s", recorder.Body.String(), logs.String())
	}
}

func TestChatRetriesTransientStreamStartBeforeWritingSSE(t *testing.T) {
	stream := &fakeStream{chunks: []chat.Chunk{{Content: "recovered", FinishReason: "stop"}}}
	model := &scriptedStartModel{
		name: "deepseek-v4-flash",
		results: []streamStartResult{
			{err: errors.New("temporary upstream failure")},
			{stream: stream},
		},
	}
	var logs bytes.Buffer
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(`{"message":"hello"}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(testConfig(), model, &logs).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK || !strings.Contains(recorder.Body.String(), `{"content":"recovered"}`) {
		t.Fatalf("unexpected response: status=%d body=%s", recorder.Code, recorder.Body.String())
	}
	if calls := model.callCount(); calls != 2 {
		t.Fatalf("model called %d times, want 2", calls)
	}
	if !strings.Contains(logs.String(), "assistant model stream start failed; retrying") || strings.Contains(logs.String(), "temporary upstream failure") {
		t.Fatalf("retry log missing or leaked provider error: %s", logs.String())
	}
}

func TestChatDoesNotRetryAfterSSEStreamStarts(t *testing.T) {
	stream := &fakeStream{
		chunks: []chat.Chunk{{Content: "partial"}},
		endErr: errors.New("stream ended unexpectedly"),
	}
	model := &fakeModel{name: "deepseek-v4-flash", stream: stream}
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(`{"message":"hello"}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(testConfig(), model, nil).ServeHTTP(recorder, request)

	if recorder.Code != http.StatusOK || !strings.Contains(recorder.Body.String(), `event: start`) || !strings.Contains(recorder.Body.String(), `event: error`) {
		t.Fatalf("unexpected response: status=%d body=%s", recorder.Code, recorder.Body.String())
	}
	model.mu.Lock()
	calls := model.calls
	model.mu.Unlock()
	if calls != 1 {
		t.Fatalf("model called %d times after SSE started, want 1", calls)
	}
}

func TestChatDoesNotRetryAfterCallerCancellation(t *testing.T) {
	requestContext, cancel := context.WithCancel(context.Background())
	model := &cancelingStartModel{cancel: cancel}
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(`{"message":"hello"}`)).WithContext(requestContext)
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(testConfig(), model, nil).ServeHTTP(recorder, request)

	if calls := model.callCount(); calls != 1 {
		t.Fatalf("model called %d times after caller cancellation, want 1", calls)
	}
}

func TestChatTimeoutReturnsStableError(t *testing.T) {
	cfg := testConfig()
	cfg.RequestTimeout = 5 * time.Millisecond
	model := &timeoutModel{}
	request := httptest.NewRequest(http.MethodPost, "/v1/chat/stream", strings.NewReader(`{"message":"hello"}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()

	newTestHandler(cfg, model, nil).ServeHTTP(recorder, request)
	if recorder.Code != http.StatusGatewayTimeout || !strings.Contains(recorder.Body.String(), `"code":"upstream_timeout"`) {
		t.Fatalf("unexpected timeout response: status=%d body=%s", recorder.Code, recorder.Body.String())
	}
	if calls := model.callCount(); calls != 1 {
		t.Fatalf("model called %d times after deadline, want 1", calls)
	}
}

func TestCORSAllowsConfiguredOriginAndRejectsOthers(t *testing.T) {
	model := &fakeModel{name: "deepseek-v4-flash", stream: &fakeStream{}}
	handler := newTestHandler(testConfig(), model, nil)

	allowed := httptest.NewRecorder()
	allowedRequest := httptest.NewRequest(http.MethodGet, "/health", nil)
	allowedRequest.Header.Set("Origin", "http://localhost:5173")
	handler.ServeHTTP(allowed, allowedRequest)
	if allowed.Header().Get("Access-Control-Allow-Origin") != "http://localhost:5173" {
		t.Fatalf("allowed origin header = %q", allowed.Header().Get("Access-Control-Allow-Origin"))
	}

	rejected := httptest.NewRecorder()
	rejectedRequest := httptest.NewRequest(http.MethodGet, "/health", nil)
	rejectedRequest.Header.Set("Origin", "https://not-allowed.example")
	handler.ServeHTTP(rejected, rejectedRequest)
	if rejected.Code != http.StatusForbidden {
		t.Fatalf("rejected status = %d", rejected.Code)
	}
}
