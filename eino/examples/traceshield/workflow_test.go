package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/cloudwego/eino/schema"
)

// testArkRequest 仅为测试解码 Ark 请求体用，字段对齐 arkChatRequest 的 JSON tag。
type testArkRequest struct {
	Model    string `json:"model"`
	Stream   bool   `json:"stream"`
	Messages []struct {
		Role    string `json:"role"`
		Content string `json:"content"`
	} `json:"messages"`
}

func TestAnalysisWorkflowUsesCoreDashboard(t *testing.T) {
	core := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/module4/dashboard" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": map[string]any{
			"summary":          map[string]int{"total_alerts": 2, "critical_count": 1, "high_risk_count": 2},
			"high_risk_events": []map[string]string{{"event_id": "event_test", "risk_level": "critical", "event_title": "敏感文件"}},
		}})
	}))
	defer core.Close()

	// 未配置 ChatModel（nil）→ 走确定性回退，行为与改造前一致。
	workflow, err := NewAnalysisWorkflow(context.Background(), NewCoreClient(core.URL), nil)
	if err != nil {
		t.Fatal(err)
	}
	result, err := workflow.Invoke(context.Background(), AnalysisRequest{Message: "最近有哪些风险？"})
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(result.Answer, "event_test") || result.Mode != "dashboard" {
		t.Fatalf("unexpected result: %+v", result)
	}
}

func TestAnalysisWorkflowWithArkChatModel(t *testing.T) {
	core := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": map[string]any{
			"summary":          map[string]int{"total_alerts": 2, "critical_count": 1, "high_risk_count": 2},
			"high_risk_events": []map[string]string{{"event_id": "event_test", "risk_level": "critical", "event_title": "敏感文件"}},
		}})
	}))
	defer core.Close()

	// 捕获 Ark 收到的请求，供断言。
	var gotReq testArkRequest
	var gotAuth string
	ark := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || !strings.HasSuffix(r.URL.Path, "/chat/completions") {
			t.Fatalf("unexpected ark request: %s %s", r.Method, r.URL.Path)
		}
		gotAuth = r.Header.Get("authorization")
		_ = json.NewDecoder(r.Body).Decode(&gotReq)
		_ = json.NewEncoder(w).Encode(map[string]any{
			"id":    "chatcmpl-test",
			"model": "ep-test",
			"choices": []map[string]any{
				{"index": 0, "message": map[string]string{"role": "assistant", "content": "经分析 event_test 为高危事件（敏感文件），建议立即隔离。"}, "finish_reason": "stop"},
			},
		})
	}))
	defer ark.Close()

	chatModel := NewArkChatModel(ArkConfig{APIKey: "test-key", Model: "ep-test", BaseURL: ark.URL})
	workflow, err := NewAnalysisWorkflow(context.Background(), NewCoreClient(core.URL), chatModel)
	if err != nil {
		t.Fatal(err)
	}

	result, err := workflow.Invoke(context.Background(), AnalysisRequest{Message: "最近有哪些风险？"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if result.Mode != "llm" {
		t.Fatalf("expected mode=llm, got %q (answer=%q)", result.Mode, result.Answer)
	}
	if !strings.Contains(result.Answer, "event_test") {
		t.Fatalf("answer should keep event id verbatim: %q", result.Answer)
	}
	if len(result.EventIDs) == 0 || result.EventIDs[0] != "event_test" {
		t.Fatalf("expected EventIDs=[event_test], got %+v", result.EventIDs)
	}

	// 校验发往 Ark 的请求结构。
	if gotAuth != "Bearer test-key" {
		t.Fatalf("expected Bearer auth, got %q", gotAuth)
	}
	if gotReq.Model != "ep-test" {
		t.Fatalf("expected model=ep-test, got %q", gotReq.Model)
	}
	if gotReq.Stream {
		t.Fatalf("Generate 路径应为非流式，stream=false")
	}
	if len(gotReq.Messages) < 2 || gotReq.Messages[0].Role != "system" || gotReq.Messages[1].Role != "user" {
		t.Fatalf("expected system+user messages, got %+v", gotReq.Messages)
	}
	if !strings.Contains(gotReq.Messages[1].Content, "event_test") || !strings.Contains(gotReq.Messages[1].Content, "最近有哪些风险") {
		t.Fatalf("user message should embed data and question: %q", gotReq.Messages[1].Content)
	}
}

func TestArkChatModelGenerateError(t *testing.T) {
	ark := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		_, _ = w.Write([]byte("internal error"))
	}))
	defer ark.Close()

	chatModel := NewArkChatModel(ArkConfig{APIKey: "test-key", Model: "ep-test", BaseURL: ark.URL})
	_, err := chatModel.Generate(context.Background(), []*schema.Message{{Role: schema.User, Content: "ping"}})
	if err == nil {
		t.Fatal("expected error for HTTP 500")
	}
	if !strings.Contains(err.Error(), "HTTP 500") {
		t.Fatalf("error should mention HTTP 500: %v", err)
	}
	// 错误串不得泄漏 API Key（Key 仅在请求头）。
	if strings.Contains(err.Error(), "test-key") {
		t.Fatalf("error must not leak API key: %v", err)
	}
}

func TestAnalysisWorkflowArkFailureFallback(t *testing.T) {
	core := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]any{"success": true, "data": map[string]any{
			"summary":          map[string]int{"total_alerts": 2, "critical_count": 1, "high_risk_count": 2},
			"high_risk_events": []map[string]string{{"event_id": "event_test", "risk_level": "critical", "event_title": "敏感文件"}},
		}})
	}))
	defer core.Close()

	ark := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer ark.Close()

	chatModel := NewArkChatModel(ArkConfig{APIKey: "test-key", Model: "ep-test", BaseURL: ark.URL})
	workflow, err := NewAnalysisWorkflow(context.Background(), NewCoreClient(core.URL), chatModel)
	if err != nil {
		t.Fatal(err)
	}

	result, err := workflow.Invoke(context.Background(), AnalysisRequest{Message: "最近有哪些风险？"})
	if err != nil {
		t.Fatalf("Ark 失败应回退而非报错: %v", err)
	}
	if result.Mode != "fallback" {
		t.Fatalf("expected mode=fallback, got %q", result.Mode)
	}
	if !strings.Contains(result.Answer, "event_test") {
		t.Fatalf("fallback answer should still reference event_test: %q", result.Answer)
	}
}
