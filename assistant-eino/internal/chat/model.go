package chat

import (
	"context"
	"errors"
	"io"
	"net"
	"time"

	openai "github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
)

// Role is deliberately narrower than the provider role set: the public API
// accepts only user/assistant history and this service never exposes tools.
type Role string

const (
	RoleSystem    Role = "system"
	RoleUser      Role = "user"
	RoleAssistant Role = "assistant"
)

type Message struct {
	Role    Role
	Content string
}

type Chunk struct {
	Content      string
	FinishReason string
}

type Stream interface {
	Recv() (Chunk, error)
	Close()
}

// Model is the small boundary used by HTTP handlers. Production uses the Eino
// adapter below; tests can use deterministic fakes without making API calls.
type Model interface {
	Name() string
	Stream(ctx context.Context, messages []Message) (Stream, error)
}

// DeepSeekConfig avoids exposing provider configuration beyond this package.
type DeepSeekConfig struct {
	APIKey          string
	BaseURL         string
	Model           string
	Timeout         time.Duration
	MaxOutputTokens int
	Temperature     float32
	ThinkingEnabled bool
}

type EinoModel struct {
	name  string
	model model.BaseChatModel
}

func NewEinoDeepSeekModel(ctx context.Context, cfg DeepSeekConfig) (*EinoModel, error) {
	maxTokens := cfg.MaxOutputTokens
	providerConfig := &openai.ChatModelConfig{
		APIKey:      cfg.APIKey,
		BaseURL:     cfg.BaseURL,
		Model:       cfg.Model,
		Timeout:     cfg.Timeout,
		MaxTokens:   &maxTokens,
		ExtraFields: map[string]any{"thinking": map[string]string{"type": thinkingMode(cfg.ThinkingEnabled)}},
	}
	if !cfg.ThinkingEnabled {
		providerConfig.Temperature = &cfg.Temperature
	}

	chatModel, err := openai.NewChatModel(ctx, providerConfig)
	if err != nil {
		return nil, err
	}
	return &EinoModel{name: cfg.Model, model: chatModel}, nil
}

func (m *EinoModel) Name() string {
	return m.name
}

func (m *EinoModel) Stream(ctx context.Context, messages []Message) (Stream, error) {
	input := make([]*schema.Message, 0, len(messages))
	for _, message := range messages {
		input = append(input, toEinoMessage(message))
	}
	reader, err := m.model.Stream(ctx, input)
	if err != nil {
		return nil, err
	}
	return &einoStream{reader: reader}, nil
}

// IsRetryableStreamStartError reports whether a model error is safe to retry
// before the HTTP handler has exposed an SSE stream to its caller. Provider
// 4xx responses are normally permanent; timeouts, rate limits, server errors,
// and transport failures may be transient.
func IsRetryableStreamStartError(err error) bool {
	if err == nil || errors.Is(err, context.Canceled) || errors.Is(err, context.DeadlineExceeded) {
		return false
	}

	var apiErr *openai.APIError
	if errors.As(err, &apiErr) {
		switch apiErr.HTTPStatusCode {
		case httpStatusRequestTimeout, httpStatusConflict, httpStatusTooEarly, httpStatusTooManyRequests:
			return true
		default:
			return apiErr.HTTPStatusCode == 0 || apiErr.HTTPStatusCode >= 500
		}
	}

	var networkErr net.Error
	if errors.As(err, &networkErr) {
		return true
	}

	// Eino extensions can wrap provider and transport failures in types that do
	// not expose an HTTP status. A single bounded retry remains safe here because
	// callers use this only before the response stream has started.
	return true
}

const (
	httpStatusRequestTimeout  = 408
	httpStatusConflict        = 409
	httpStatusTooEarly        = 425
	httpStatusTooManyRequests = 429
)

type einoStream struct {
	reader *schema.StreamReader[*schema.Message]
}

func (s *einoStream) Recv() (Chunk, error) {
	message, err := s.reader.Recv()
	if err != nil {
		if err == io.EOF {
			return Chunk{}, io.EOF
		}
		return Chunk{}, err
	}
	chunk := Chunk{Content: message.Content}
	if message.ResponseMeta != nil {
		chunk.FinishReason = message.ResponseMeta.FinishReason
	}
	return chunk, nil
}

func (s *einoStream) Close() {
	s.reader.Close()
}

func toEinoMessage(message Message) *schema.Message {
	switch message.Role {
	case RoleSystem:
		return schema.SystemMessage(message.Content)
	case RoleAssistant:
		return schema.AssistantMessage(message.Content, nil)
	default:
		return schema.UserMessage(message.Content)
	}
}

func thinkingMode(enabled bool) string {
	if enabled {
		return "enabled"
	}
	return "disabled"
}
