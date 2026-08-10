package httpapi

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"regexp"
	"runtime/debug"
	"strings"
	"time"
	"unicode/utf8"

	"traceshield/assistant-eino/internal/chat"
)

const (
	serviceName            = "traceshield-assistant-eino"
	framework              = "cloudwego-eino"
	provider               = "deepseek"
	maxStreamStartAttempts = 2
)

var safeIDPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`)

type Config struct {
	ModelName       string
	Configured      bool
	RequestTimeout  time.Duration
	MaxBodyBytes    int64
	MaxMessageRunes int
	MaxHistoryItems int
	MaxHistoryRunes int
	MaxContextBytes int
	AllowedOrigins  []string
}

type Server struct {
	cfg            Config
	model          chat.Model
	logger         *slog.Logger
	allowedOrigins map[string]struct{}
	allowAnyOrigin bool
}

func New(cfg Config, model chat.Model, logger *slog.Logger) *Server {
	if logger == nil {
		logger = slog.Default()
	}
	server := &Server{
		cfg:            cfg,
		model:          model,
		logger:         logger,
		allowedOrigins: make(map[string]struct{}, len(cfg.AllowedOrigins)),
	}
	for _, origin := range cfg.AllowedOrigins {
		if origin == "*" {
			server.allowAnyOrigin = true
			continue
		}
		server.allowedOrigins[origin] = struct{}{}
	}
	return server
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /v1/chat/stream", s.handleChatStream)
	mux.HandleFunc("OPTIONS /", s.handleOptions)

	var handler http.Handler = mux
	handler = s.withCORS(handler)
	handler = s.withRecovery(handler)
	handler = s.withLogging(handler)
	handler = s.withRequestID(handler)
	return handler
}

type healthResponse struct {
	OK         bool   `json:"ok"`
	Service    string `json:"service"`
	Framework  string `json:"framework"`
	Provider   string `json:"provider"`
	Model      string `json:"model"`
	Configured bool   `json:"configured"`
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	configured := s.cfg.Configured && s.model != nil
	writeJSON(w, http.StatusOK, healthResponse{
		OK:         configured,
		Service:    serviceName,
		Framework:  framework,
		Provider:   provider,
		Model:      s.cfg.ModelName,
		Configured: configured,
	})
}

type historyMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type chatRequest struct {
	ConversationID string           `json:"conversation_id,omitempty"`
	Message        string           `json:"message"`
	History        []historyMessage `json:"history,omitempty"`
	Context        map[string]any   `json:"context,omitempty"`
}

type startEvent struct {
	ConversationID string `json:"conversation_id"`
	Model          string `json:"model"`
}

type deltaEvent struct {
	Content string `json:"content"`
}

type doneEvent struct {
	ConversationID string `json:"conversation_id"`
	FinishReason   string `json:"finish_reason,omitempty"`
}

type errorEvent struct {
	Code    string `json:"code"`
	Message string `json:"message"`
}

func (s *Server) handleChatStream(w http.ResponseWriter, r *http.Request) {
	if mediaType := strings.ToLower(strings.TrimSpace(strings.Split(r.Header.Get("Content-Type"), ";")[0])); mediaType != "" && mediaType != "application/json" {
		writeSSEError(w, http.StatusUnsupportedMediaType, "unsupported_media_type", "content type must be application/json")
		return
	}

	request, contextJSON, validationErr := s.decodeAndValidate(w, r)
	if validationErr != nil {
		writeSSEError(w, validationErr.status, validationErr.code, validationErr.message)
		return
	}
	conversationID := request.ConversationID
	if conversationID == "" {
		var err error
		conversationID, err = randomID("conv_")
		if err != nil {
			writeSSEError(w, http.StatusInternalServerError, "internal_error", "could not create conversation")
			return
		}
	}
	if !s.cfg.Configured || s.model == nil {
		writeSSEError(w, http.StatusServiceUnavailable, "service_unavailable", "assistant model is not configured")
		return
	}

	messages := buildMessages(request, contextJSON)
	ctx, cancel := context.WithTimeout(r.Context(), s.cfg.RequestTimeout)
	defer cancel()
	stream, err := s.startModelStream(ctx, messages)
	if err != nil {
		status, code, message := upstreamError(ctx, "assistant model request failed")
		writeSSEError(w, status, code, message)
		return
	}
	if stream == nil {
		writeSSEError(w, http.StatusBadGateway, "upstream_error", "assistant model request failed")
		return
	}
	defer stream.Close()

	prepareSSE(w, http.StatusOK)
	if err := writeSSE(w, "start", startEvent{ConversationID: conversationID, Model: s.model.Name()}); err != nil {
		return
	}

	finishReason := ""
	for {
		chunk, recvErr := stream.Recv()
		if errors.Is(recvErr, io.EOF) {
			_ = writeSSE(w, "done", doneEvent{ConversationID: conversationID, FinishReason: finishReason})
			return
		}
		if recvErr != nil {
			if r.Context().Err() != nil {
				return
			}
			_, code, message := upstreamError(ctx, "assistant model stream failed")
			_ = writeSSE(w, "error", errorEvent{Code: code, Message: message})
			return
		}
		if chunk.FinishReason != "" {
			finishReason = safeFinishReason(chunk.FinishReason)
		}
		if chunk.Content != "" {
			if err := writeSSE(w, "delta", deltaEvent{Content: chunk.Content}); err != nil {
				return
			}
		}
	}
}

// startModelStream retries once only while stream establishment is still
// invisible to the downstream caller. Once this returns a stream,
// handleChatStream writes the SSE start event and no later error is retried.
func (s *Server) startModelStream(ctx context.Context, messages []chat.Message) (chat.Stream, error) {
	var lastErr error
	for attempt := 1; attempt <= maxStreamStartAttempts; attempt++ {
		if err := ctx.Err(); err != nil {
			return nil, err
		}

		stream, err := s.model.Stream(ctx, messages)
		if err == nil {
			return stream, nil
		}
		if stream != nil {
			stream.Close()
		}
		lastErr = err

		if attempt == maxStreamStartAttempts || ctx.Err() != nil || !chat.IsRetryableStreamStartError(err) {
			break
		}
		s.logger.Warn("assistant model stream start failed; retrying", "attempt", attempt)
	}
	return nil, lastErr
}

type requestError struct {
	status  int
	code    string
	message string
}

func (s *Server) decodeAndValidate(w http.ResponseWriter, r *http.Request) (chatRequest, []byte, *requestError) {
	defer r.Body.Close()
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, s.cfg.MaxBodyBytes))
	decoder.DisallowUnknownFields()
	var request chatRequest
	if err := decoder.Decode(&request); err != nil {
		var maxBytesErr *http.MaxBytesError
		if errors.As(err, &maxBytesErr) {
			return chatRequest{}, nil, &requestError{http.StatusRequestEntityTooLarge, "request_too_large", "request body is too large"}
		}
		return chatRequest{}, nil, &requestError{http.StatusBadRequest, "invalid_request", "request body is invalid"}
	}
	if err := ensureJSONEOF(decoder); err != nil {
		return chatRequest{}, nil, &requestError{http.StatusBadRequest, "invalid_request", "request body is invalid"}
	}
	if request.ConversationID != "" && !safeIDPattern.MatchString(request.ConversationID) {
		return chatRequest{}, nil, &requestError{http.StatusBadRequest, "invalid_conversation_id", "conversation_id has an invalid format"}
	}
	if strings.TrimSpace(request.Message) == "" {
		return chatRequest{}, nil, &requestError{http.StatusBadRequest, "message_required", "message is required"}
	}
	if !utf8.ValidString(request.Message) || utf8.RuneCountInString(request.Message) > s.cfg.MaxMessageRunes {
		return chatRequest{}, nil, &requestError{http.StatusBadRequest, "message_too_long", "message exceeds the configured limit"}
	}
	if len(request.History) > s.cfg.MaxHistoryItems {
		return chatRequest{}, nil, &requestError{http.StatusBadRequest, "history_too_long", "history exceeds the configured limit"}
	}
	historyRunes := 0
	for _, item := range request.History {
		if item.Role != string(chat.RoleUser) && item.Role != string(chat.RoleAssistant) {
			return chatRequest{}, nil, &requestError{http.StatusBadRequest, "invalid_history", "history roles must be user or assistant"}
		}
		if strings.TrimSpace(item.Content) == "" || !utf8.ValidString(item.Content) {
			return chatRequest{}, nil, &requestError{http.StatusBadRequest, "invalid_history", "history content must be valid non-empty text"}
		}
		historyRunes += utf8.RuneCountInString(item.Content)
		if historyRunes > s.cfg.MaxHistoryRunes {
			return chatRequest{}, nil, &requestError{http.StatusBadRequest, "history_too_long", "history exceeds the configured limit"}
		}
	}

	var contextJSON []byte
	if len(request.Context) > 0 {
		var err error
		contextJSON, err = json.Marshal(request.Context)
		if err != nil || len(contextJSON) > s.cfg.MaxContextBytes {
			return chatRequest{}, nil, &requestError{http.StatusBadRequest, "context_too_large", "context exceeds the configured limit"}
		}
	}
	return request, contextJSON, nil
}

func buildMessages(request chatRequest, contextJSON []byte) []chat.Message {
	messages := make([]chat.Message, 0, len(request.History)+3)
	messages = append(messages, chat.Message{Role: chat.RoleSystem, Content: chat.SystemPrompt})
	if len(contextJSON) > 0 {
		messages = append(messages, chat.Message{
			Role:    chat.RoleSystem,
			Content: chat.ContextPreamble + string(contextJSON) + chat.ContextSuffix,
		})
	}
	for _, item := range request.History {
		messages = append(messages, chat.Message{Role: chat.Role(item.Role), Content: item.Content})
	}
	messages = append(messages, chat.Message{Role: chat.RoleUser, Content: request.Message})
	return messages
}

func ensureJSONEOF(decoder *json.Decoder) error {
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		if err == nil {
			return errors.New("multiple JSON values")
		}
		return err
	}
	return nil
}

func upstreamError(ctx context.Context, fallback string) (int, string, string) {
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		return http.StatusGatewayTimeout, "upstream_timeout", "assistant model request timed out"
	}
	return http.StatusBadGateway, "upstream_error", fallback
}

func safeFinishReason(value string) string {
	if len(value) > 64 || strings.ContainsAny(value, "\r\n") {
		return ""
	}
	return value
}

func prepareSSE(w http.ResponseWriter, status int) {
	header := w.Header()
	header.Set("Content-Type", "text/event-stream; charset=utf-8")
	header.Set("Cache-Control", "no-cache, no-transform")
	header.Set("Connection", "keep-alive")
	header.Set("X-Accel-Buffering", "no")
	header.Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
}

func writeSSEError(w http.ResponseWriter, status int, code, message string) {
	prepareSSE(w, status)
	_ = writeSSE(w, "error", errorEvent{Code: code, Message: message})
}

func writeSSE(w http.ResponseWriter, event string, data any) error {
	payload, err := json.Marshal(data)
	if err != nil {
		return err
	}
	if _, err = fmt.Fprintf(w, "event: %s\ndata: %s\n\n", event, payload); err != nil {
		return err
	}
	if flusher, ok := w.(http.Flusher); ok {
		flusher.Flush()
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func randomID(prefix string) (string, error) {
	buffer := make([]byte, 12)
	if _, err := rand.Read(buffer); err != nil {
		return "", err
	}
	return prefix + hex.EncodeToString(buffer), nil
}

func (s *Server) handleOptions(w http.ResponseWriter, _ *http.Request) {
	w.WriteHeader(http.StatusNoContent)
}

type contextKey string

const requestIDContextKey contextKey = "request_id"

func (s *Server) withRequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-ID")
		if !safeIDPattern.MatchString(requestID) {
			generated, err := randomID("req_")
			if err != nil {
				generated = "req_unavailable"
			}
			requestID = generated
		}
		w.Header().Set("X-Request-ID", requestID)
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), requestIDContextKey, requestID)))
	})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (w *statusRecorder) WriteHeader(status int) {
	if w.status != 0 {
		return
	}
	w.status = status
	w.ResponseWriter.WriteHeader(status)
}

func (w *statusRecorder) Write(body []byte) (int, error) {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}
	return w.ResponseWriter.Write(body)
}

func (w *statusRecorder) Flush() {
	if w.status == 0 {
		w.WriteHeader(http.StatusOK)
	}
	if flusher, ok := w.ResponseWriter.(http.Flusher); ok {
		flusher.Flush()
	}
}

func (s *Server) withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		recorder := &statusRecorder{ResponseWriter: w}
		next.ServeHTTP(recorder, r)
		status := recorder.status
		if status == 0 {
			status = http.StatusOK
		}
		s.logger.Info("http request completed",
			"request_id", requestIDFromContext(r.Context()),
			"method", r.Method,
			"path", r.URL.Path,
			"status", status,
			"duration_ms", time.Since(started).Milliseconds(),
		)
	})
}

func (s *Server) withRecovery(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if recover() == nil {
				return
			}
			// Do not log the panic value: provider errors or future handler values
			// could contain prompts. A stack is sufficient to locate the defect.
			s.logger.Error("http handler panic",
				"request_id", requestIDFromContext(r.Context()),
				"path", r.URL.Path,
				"stack", string(debug.Stack()),
			)
			writeJSON(w, http.StatusInternalServerError, errorEvent{Code: "internal_error", Message: "internal server error"})
		}()
		next.ServeHTTP(w, r)
	})
}

func requestIDFromContext(ctx context.Context) string {
	value, _ := ctx.Value(requestIDContextKey).(string)
	return value
}

func (s *Server) withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if origin != "" {
			if !s.allowAnyOrigin {
				if _, allowed := s.allowedOrigins[origin]; !allowed {
					writeJSON(w, http.StatusForbidden, errorEvent{Code: "origin_not_allowed", Message: "origin is not allowed"})
					return
				}
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Add("Vary", "Origin")
			} else {
				w.Header().Set("Access-Control-Allow-Origin", "*")
			}
		}
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
		next.ServeHTTP(w, r)
	})
}
