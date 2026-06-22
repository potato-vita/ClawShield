/*
TraceShield Ark ChatModel

实现一个满足 Eino model.BaseChatModel 接口的火山云方舟 Ark 客户端。
Ark 暴露的是 OpenAI 兼容协议：POST {ARK_BASE_URL}/chat/completions。

设计要点：
  - 零外部依赖：仅用 net/http + encoding/json，保持 vendored 自包含、go 1.18 兼容。
  - 只读分析用途：请求体绝不携带 tools / tool_choice（见 arkChatRequest），system prompt 侧也禁止命令执行。
  - 凭证全部来自环境变量，源码内不硬编码。
  - Stream 退化为单块流（本服务只走 Invoke→Generate 路径），仍满足 BaseChatModel 接口要求。
*/
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/schema"
)

const arkDefaultBaseURL = "https://ark.cn-beijing.volces.com/api/v3"

// ArkConfig 保存 Ark ChatModel 的运行时配置，全部来自环境变量。
type ArkConfig struct {
	APIKey         string // ARK_API_KEY
	Model          string // ARK_CHAT_MODEL（endpoint id，形如 ep-...）
	EmbeddingModel string // ARK_EMBEDDING_MODEL（本轮不使用，仅加载记录）
	BaseURL        string // ARK_BASE_URL，缺省 arkDefaultBaseURL
}

// LoadArkConfig 从环境变量读取 Ark 配置。
// 当且仅当 APIKey 与 Model 同时非空时认为已启用（ok=true）。
// getenv 默认绑定到 os.Getenv，便于测试注入。
func LoadArkConfig(getenv func(string) string) (cfg ArkConfig, ok bool) {
	cfg = ArkConfig{
		APIKey:         strings.TrimSpace(getenv("ARK_API_KEY")),
		Model:          strings.TrimSpace(getenv("ARK_CHAT_MODEL")),
		EmbeddingModel: strings.TrimSpace(getenv("ARK_EMBEDDING_MODEL")),
		BaseURL:        strings.TrimSpace(getenv("ARK_BASE_URL")),
	}
	if cfg.BaseURL == "" {
		cfg.BaseURL = arkDefaultBaseURL
	}
	ok = cfg.APIKey != "" && cfg.Model != ""
	return cfg, ok
}

// NewArkChatModel 构造一个实现 model.BaseChatModel 的 Ark 客户端。
// 调用前 cfg 应已通过 LoadArkConfig 校验（ok=true）。
func NewArkChatModel(cfg ArkConfig) model.BaseChatModel {
	return &arkChatModel{
		cfg:  cfg,
		http: &http.Client{Timeout: 30 * time.Second},
	}
}

type arkChatModel struct {
	cfg  ArkConfig
	http *http.Client
}

// Generate 调用一次 Ark chat/completions（非流式），返回完整回答。
func (m *arkChatModel) Generate(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.Message, error) {
	// 默认低温，倾向稳定、可复现的安全分析；调用方可通过 model.WithTemperature 覆盖。
	options := model.GetCommonOptions(&model.Options{
		Temperature: ptrOf(float32(0.2)),
	}, opts...)

	body, err := json.Marshal(m.buildRequest(input, options, false))
	if err != nil {
		return nil, fmt.Errorf("ark chatmodel: marshal request: %w", err)
	}

	endpoint := strings.TrimRight(m.cfg.BaseURL, "/") + "/chat/completions"
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("ark chatmodel: build request: %w", err)
	}
	req.Header.Set("content-type", "application/json")
	req.Header.Set("authorization", "Bearer "+m.cfg.APIKey)

	resp, err := m.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ark chatmodel: http: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		snippet := readLimited(resp.Body, 512)
		return nil, fmt.Errorf("ark chatmodel: HTTP %d: %s", resp.StatusCode, snippet)
	}

	var parsed arkChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&parsed); err != nil {
		return nil, fmt.Errorf("ark chatmodel: decode response: %w", err)
	}
	if len(parsed.Choices) == 0 {
		return nil, fmt.Errorf("ark chatmodel: empty choices in response")
	}
	return &schema.Message{
		Role:    schema.Assistant,
		Content: parsed.Choices[0].Message.Content,
	}, nil
}

// Stream 退化为单块流：调用一次 Generate 后包成单元素 StreamReader。
// 本服务的 /api/analysis 只走 Invoke→Generate，无需真正的逐 token 流式。
func (m *arkChatModel) Stream(ctx context.Context, input []*schema.Message, opts ...model.Option) (*schema.StreamReader[*schema.Message], error) {
	msg, err := m.Generate(ctx, input, opts...)
	if err != nil {
		return nil, err
	}
	return schema.StreamReaderFromArray([]*schema.Message{msg}), nil
}

// ---- OpenAI 兼容协议的 JSON 类型（仅取 TraceShield 用得到的字段子集）----

type arkChatReqMsg struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type arkChatRequest struct {
	Model       string          `json:"model"`        // endpoint id
	Messages    []arkChatReqMsg `json:"messages"`
	Temperature *float32        `json:"temperature,omitempty"`
	MaxTokens   *int            `json:"max_tokens,omitempty"`
	Stream      bool            `json:"stream"`
	// 注意：刻意不携带 tools / tool_choice —— TraceShield 是只读分析产品，禁止模型发 tool call。
}

type arkChatResponse struct {
	ID      string          `json:"id"`
	Model   string          `json:"model"`
	Choices []arkChatChoice `json:"choices"`
}

type arkChatChoice struct {
	Index        int           `json:"index"`
	Message      arkChatReqMsg `json:"message"`
	FinishReason string        `json:"finish_reason"`
}

// buildRequest 把 schema.Message 列表映射成 Ark 请求体。
// 多模态 / ToolCalls 不映射：TraceShield 只发文本 system+user 消息。
func (m *arkChatModel) buildRequest(input []*schema.Message, opts *model.Options, stream bool) arkChatRequest {
	messages := make([]arkChatReqMsg, 0, len(input))
	for _, msg := range input {
		if msg == nil {
			continue
		}
		messages = append(messages, arkChatReqMsg{
			Role:    string(msg.Role),
			Content: msg.Content,
		})
	}
	return arkChatRequest{
		Model:       m.cfg.Model,
		Messages:    messages,
		Temperature: opts.Temperature,
		MaxTokens:   opts.MaxTokens,
		Stream:      stream,
	}
}

// ---- 辅助 ----

// ptrOf 是 go 1.18 泛型辅助，用于取标量指针。
func ptrOf[T any](v T) *T {
	return &v
}

// readLimited 最多读 n 字节，避免错误响应体撑爆内存。
func readLimited(r io.Reader, n int) string {
	limited := io.LimitReader(r, int64(n))
	data, _ := io.ReadAll(limited)
	return strings.TrimSpace(string(data))
}
