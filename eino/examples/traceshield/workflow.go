package main

import (
	"context"
	"fmt"
	"log"
	"regexp"
	"strings"

	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino/compose"
	"github.com/cloudwego/eino/schema"
)

var eventIDPattern = regexp.MustCompile(`event_[A-Za-z0-9]+`)

// arkSystemPrompt 约束 Ark 只做基于真实事件数据的只读安全分析。
// 关键约束：不得编造、必须原样保留 event_xxx、禁止命令执行。
const arkSystemPrompt = `你是 TraceShield 的安全分析助手。你的职责是基于下方「事件数据」中真实存在的 TraceShield 安全事件，用简体中文给出简洁、专业、可操作的风险分析。

严格规则：
1. 只能基于「事件数据」里真实存在的事实作答；数据中没有的信息一律不得编造。
2. 必须原样保留并在回答中引用相关的事件 ID（形如 event_xxx），不得改写、缩写或省略这些 ID。
3. 不得输出任何工具调用、shell 命令、代码执行建议或对外部系统的写操作；只产出只读的分析文本。
4. 回答控制在 200 字以内，先给结论（风险等级/状态），再给 2-3 条简短建议。
5. 如果「事件数据」为空或与问题无关，直接回复「未找到相关事件」并简述原因。`

type AnalysisRequest struct {
	SessionID string `json:"session_id"`
	Message   string `json:"message"`
	EventID   string `json:"event_id,omitempty"`
}

type AnalysisResponse struct {
	Answer   string   `json:"answer"`
	EventIDs []string `json:"event_ids"`
	Mode     string   `json:"mode"`
}

type analysisContext struct {
	Request   AnalysisRequest
	Dashboard *Dashboard
	Detail    *EventDetail
}

type AnalysisWorkflow struct {
	runnable compose.Runnable[AnalysisRequest, AnalysisResponse]
}

// NewAnalysisWorkflow 构建分析工作流。
// chatModel 为 nil（未配置 Ark）或调用失败时，自动回退到确定性答案。
func NewAnalysisWorkflow(ctx context.Context, client *CoreClient, chatModel model.BaseChatModel) (*AnalysisWorkflow, error) {
	chain := compose.NewChain[AnalysisRequest, AnalysisResponse]().
		AppendLambda(compose.InvokableLambda(func(ctx context.Context, input AnalysisRequest) (analysisContext, error) {
			eventID := input.EventID
			if eventID == "" {
				eventID = eventIDPattern.FindString(input.Message)
			}
			if eventID != "" {
				detail, err := client.Event(ctx, eventID)
				if err != nil {
					return analysisContext{}, err
				}
				return analysisContext{Request: input, Detail: detail}, nil
			}
			dashboard, err := client.Dashboard(ctx)
			if err != nil {
				return analysisContext{}, err
			}
			return analysisContext{Request: input, Dashboard: dashboard}, nil
		})).
		AppendLambda(compose.InvokableLambda(func(ctx context.Context, input analysisContext) (AnalysisResponse, error) {
			// 已配置 ChatModel：优先用 LLM 生成；调用失败则回退到确定性答案（Mode=fallback）。
			if chatModel != nil {
				msg, err := chatModel.Generate(ctx, buildMessages(input))
				if err == nil {
					return assembleLLMAnswer(msg, input), nil
				}
				log.Printf("ChatModel generate failed, falling back: %v", err)
				return buildFallbackAnswerWithMode(input, "fallback"), nil
			}
			// 未配置 ChatModel：维持原有确定性行为。
			return buildFallbackAnswer(input), nil
		}))

	runnable, err := chain.Compile(ctx)
	if err != nil {
		return nil, err
	}
	return &AnalysisWorkflow{runnable: runnable}, nil
}

func (w *AnalysisWorkflow) Invoke(ctx context.Context, request AnalysisRequest) (AnalysisResponse, error) {
	return w.runnable.Invoke(ctx, request)
}

// buildFallbackAnswer 是未配置 ChatModel 时的确定性答案，Mode 取自然值（dashboard/event_detail）。
func buildFallbackAnswer(input analysisContext) AnalysisResponse {
	return buildFallbackAnswerWithMode(input, naturalMode(input))
}

// buildFallbackAnswerWithMode 复用同一套确定性拼装逻辑，Mode 由调用方决定
// （ChatModel 调用失败回退时传 "fallback"）。
func buildFallbackAnswerWithMode(input analysisContext, mode string) AnalysisResponse {
	if input.Detail != nil {
		event := input.Detail.Event
		actions := strings.Join(input.Detail.RecommendedActions, "；")
		answer := fmt.Sprintf(
			"事件 %s 为 %s（%.0f 分），状态 %s。\n%s\n目标：%s（%s）\n建议：%s",
			event.EventID, strings.ToUpper(event.RiskLevel), event.RiskScore,
			event.EventStatus, input.Detail.RiskExplanation, event.Target,
			event.TargetType, actions,
		)
		return AnalysisResponse{Answer: answer, EventIDs: []string{event.EventID}, Mode: mode}
	}
	dashboard := input.Dashboard
	if dashboard == nil || len(dashboard.HighRiskEvents) == 0 {
		return AnalysisResponse{Answer: "当前数据库中没有高危事件。", Mode: mode}
	}
	lines := []string{fmt.Sprintf(
		"最近 7 天共 %d 条告警，其中高危 %d 条、Critical %d 条。",
		dashboard.Summary.TotalAlerts, dashboard.Summary.HighRiskCount, dashboard.Summary.CriticalCount,
	)}
	ids := make([]string, 0, len(dashboard.HighRiskEvents))
	for _, event := range dashboard.HighRiskEvents {
		lines = append(lines, fmt.Sprintf("- %s｜%s｜%s", event.EventID, strings.ToUpper(event.RiskLevel), event.EventTitle))
		ids = append(ids, event.EventID)
	}
	return AnalysisResponse{Answer: strings.Join(lines, "\n"), EventIDs: ids, Mode: mode}
}

// naturalMode 是未配置 ChatModel 时给确定性答案打的模式标记。
func naturalMode(input analysisContext) string {
	if input.Detail != nil {
		return "event_detail"
	}
	return "dashboard"
}

// assembleLLMAnswer 把 Ark 返回的 Message 组装成 AnalysisResponse。
// 不完全信任模型一定原样输出 event_id：若回答里抽不到，用真实事件 ID 兜底并补在末尾。
func assembleLLMAnswer(msg *schema.Message, input analysisContext) AnalysisResponse {
	answer := strings.TrimSpace(msg.Content)
	// 模型可能在回答里多次提及同一事件 ID，去重以保持 EventIDs 干净。
	ids := dedupeStrings(eventIDPattern.FindAllString(answer, -1))
	if len(ids) == 0 {
		ids = realEventIDs(input)
		if len(ids) > 0 {
			answer = answer + "\n（相关事件：" + strings.Join(ids, "、") + "）"
		}
	}
	return AnalysisResponse{Answer: answer, EventIDs: ids, Mode: "llm"}
}

// dedupeStrings 按首次出现顺序去重（go 1.18 无 slices，手写）。
func dedupeStrings(in []string) []string {
	seen := make(map[string]struct{}, len(in))
	out := make([]string, 0, len(in))
	for _, s := range in {
		if _, ok := seen[s]; ok {
			continue
		}
		seen[s] = struct{}{}
		out = append(out, s)
	}
	return out
}

// realEventIDs 从 Core 数据里取出真实事件 ID，作为模型漏写时的兜底。
func realEventIDs(input analysisContext) []string {
	if input.Detail != nil {
		if id := input.Detail.Event.EventID; id != "" {
			return []string{id}
		}
		return nil
	}
	if input.Dashboard == nil {
		return nil
	}
	ids := make([]string, 0, len(input.Dashboard.HighRiskEvents))
	for _, e := range input.Dashboard.HighRiskEvents {
		if e.EventID != "" {
			ids = append(ids, e.EventID)
		}
	}
	return ids
}

// buildMessages 把 Core 上下文 + 用户问题组装成 Ark 的 system+user 消息。
func buildMessages(input analysisContext) []*schema.Message {
	var dataText string
	if input.Detail != nil {
		dataText = eventDetailContextText(input.Detail)
	} else {
		dataText = dashboardContextText(input.Dashboard)
	}
	user := dataText + "\n\n【用户问题】\n" + input.Request.Message
	return []*schema.Message{
		{Role: schema.System, Content: arkSystemPrompt},
		{Role: schema.User, Content: user},
	}
}

// dashboardContextText 把仪表盘数据序列化成纯文本（非 JSON dump，避免 event_id 被转义）。
func dashboardContextText(d *Dashboard) string {
	if d == nil {
		return "【TraceShield 事件数据 - 仪表盘视图】\n当前没有可用的仪表盘数据。"
	}
	var b strings.Builder
	b.WriteString("【TraceShield 事件数据 - 仪表盘视图】\n")
	fmt.Fprintf(&b, "统计：最近 7 天共 %d 条告警，其中高危 %d 条、Critical %d 条。\n",
		d.Summary.TotalAlerts, d.Summary.HighRiskCount, d.Summary.CriticalCount)
	if len(d.HighRiskEvents) == 0 {
		b.WriteString("高危事件列表：（暂无）")
		return b.String()
	}
	b.WriteString("高危事件列表：")
	for _, e := range d.HighRiskEvents {
		fmt.Fprintf(&b, "\n- %s｜%s｜%s", e.EventID, strings.ToUpper(e.RiskLevel), e.EventTitle)
	}
	return b.String()
}

// eventDetailContextText 把单个事件详情序列化成纯文本。
// Evidence / RiskGraph 本轮不喂模型，避免敏感信息外泄与巨型 payload。
func eventDetailContextText(d *EventDetail) string {
	if d == nil {
		return "【TraceShield 事件数据 - 事件详情】\n当前没有可用的事件详情。"
	}
	e := d.Event
	var b strings.Builder
	b.WriteString("【TraceShield 事件数据 - 事件详情】\n")
	fmt.Fprintf(&b, "事件 ID：%s\n", e.EventID)
	fmt.Fprintf(&b, "风险等级：%s（%.0f 分）｜状态：%s\n", strings.ToUpper(e.RiskLevel), e.RiskScore, e.EventStatus)
	if e.EventTitle != "" {
		fmt.Fprintf(&b, "标题：%s\n", e.EventTitle)
	}
	fmt.Fprintf(&b, "用户：%s（%s）｜目标：%s（%s）\n", e.Username, e.DepartmentName, e.Target, e.TargetType)
	if e.Timestamp != "" {
		fmt.Fprintf(&b, "时间：%s\n", e.Timestamp)
	}
	if d.RiskExplanation != "" {
		fmt.Fprintf(&b, "风险说明：%s\n", d.RiskExplanation)
	}
	if len(d.RecommendedActions) > 0 {
		b.WriteString("建议处置：")
		for _, a := range d.RecommendedActions {
			fmt.Fprintf(&b, "\n- %s", a)
		}
	}
	return b.String()
}
