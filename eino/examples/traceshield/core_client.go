package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type CoreClient struct {
	baseURL string
	http    *http.Client
}

type Dashboard struct {
	Summary struct {
		TotalAlerts   int `json:"total_alerts"`
		CriticalCount int `json:"critical_count"`
		HighRiskCount int `json:"high_risk_count"`
		QueryCount    int `json:"query_count"`
	} `json:"summary"`
	HighRiskEvents []DashboardEvent `json:"high_risk_events"`
}

type DashboardEvent struct {
	EventID        string `json:"event_id"`
	RiskLevel      string `json:"risk_level"`
	EventTitle     string `json:"event_title"`
	Username       string `json:"username"`
	DepartmentName string `json:"department_name"`
	Timestamp      string `json:"timestamp"`
}

type EventDetail struct {
	Event struct {
		EventID        string  `json:"event_id"`
		RiskLevel      string  `json:"risk_level"`
		RiskScore      float64 `json:"risk_score"`
		EventStatus    string  `json:"event_status"`
		EventTitle     string  `json:"event_title"`
		Username       string  `json:"username"`
		DepartmentName string  `json:"department_name"`
		Target         string  `json:"target"`
		TargetType     string  `json:"target_type"`
		Timestamp      string  `json:"timestamp"`
	} `json:"event"`
	RiskExplanation    string           `json:"risk_explanation"`
	RecommendedActions []string         `json:"recommended_actions"`
	Evidence           []map[string]any `json:"evidence"`
	RiskGraph          []map[string]any `json:"risk_graph"`
}

func NewCoreClient(baseURL string) *CoreClient {
	return &CoreClient{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: 5 * time.Second},
	}
}

func (c *CoreClient) Dashboard(ctx context.Context) (*Dashboard, error) {
	var envelope struct {
		Success bool      `json:"success"`
		Data    Dashboard `json:"data"`
	}
	if err := c.getJSON(ctx, "/api/module4/dashboard?time_range=7d", &envelope); err != nil {
		return nil, err
	}
	return &envelope.Data, nil
}

func (c *CoreClient) Event(ctx context.Context, eventID string) (*EventDetail, error) {
	var detail EventDetail
	if err := c.getJSON(ctx, "/api/module4/events/"+eventID, &detail); err != nil {
		return nil, err
	}
	return &detail, nil
}

func (c *CoreClient) AppendMessage(ctx context.Context, sessionID, role, content, eventID string) error {
	payload := map[string]string{"role": role, "content": content}
	if eventID != "" {
		payload["related_event_id"] = eventID
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/sessions/"+sessionID+"/messages", bytes.NewReader(body))
	if err != nil {
		return err
	}
	req.Header.Set("content-type", "application/json")
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("append message: Core returned HTTP %d", resp.StatusCode)
	}
	return nil
}

func (c *CoreClient) Health(ctx context.Context) error {
	var result struct {
		Success bool `json:"success"`
	}
	if err := c.getJSON(ctx, "/api/module4/health", &result); err != nil {
		return err
	}
	if !result.Success {
		return fmt.Errorf("Core health reported failure")
	}
	return nil
}

func (c *CoreClient) getJSON(ctx context.Context, path string, target any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+path, nil)
	if err != nil {
		return err
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 300 {
		return fmt.Errorf("Core GET %s returned HTTP %d", path, resp.StatusCode)
	}
	return json.NewDecoder(resp.Body).Decode(target)
}
