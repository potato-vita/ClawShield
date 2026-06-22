package main

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"io/fs"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/cloudwego/eino/components/model"
)

//go:embed web/*
var webFiles embed.FS

type Server struct {
	workflow         *AnalysisWorkflow
	core             *CoreClient
	proxy            *httputil.ReverseProxy
	chatModelEnabled bool
}

func NewServer(ctx context.Context, coreURL string) (*Server, error) {
	client := NewCoreClient(coreURL)

	// 从环境变量加载 Ark ChatModel 配置；未配置时使用确定性回退。
	cfg, ok := LoadArkConfig(os.Getenv)
	var chatModel model.BaseChatModel
	if ok {
		chatModel = NewArkChatModel(cfg)
		log.Printf("ChatModel: enabled (model=%s base=%s)", cfg.Model, cfg.BaseURL)
	} else {
		log.Printf("ChatModel: disabled (ARK_API_KEY/ARK_CHAT_MODEL not set), using deterministic fallback")
	}

	workflow, err := NewAnalysisWorkflow(ctx, client, chatModel)
	if err != nil {
		return nil, err
	}
	target, err := url.Parse(coreURL)
	if err != nil {
		return nil, err
	}
	return &Server{workflow: workflow, core: client, proxy: httputil.NewSingleHostReverseProxy(target), chatModelEnabled: ok}, nil
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/analysis", requireMethod(http.MethodPost, s.analysis))
	mux.HandleFunc("/api/health", requireMethod(http.MethodGet, s.health))
	mux.HandleFunc("/core/", s.proxyCore)
	assets, _ := fs.Sub(webFiles, "web")
	mux.Handle("/", http.FileServer(http.FS(assets)))
	return requestLog(mux)
}

func requireMethod(method string, handler http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != method {
			w.Header().Set("allow", method)
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handler(w, r)
	}
}

func (s *Server) analysis(w http.ResponseWriter, r *http.Request) {
	var request AnalysisRequest
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&request); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid request"})
		return
	}
	request.Message = strings.TrimSpace(request.Message)
	if request.Message == "" {
		writeJSON(w, http.StatusUnprocessableEntity, map[string]string{"error": "message is required"})
		return
	}
	if request.SessionID != "" {
		if err := s.core.AppendMessage(r.Context(), request.SessionID, "user", request.Message, ""); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
	}
	response, err := s.workflow.Invoke(r.Context(), request)
	if err != nil {
		writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
		return
	}
	if request.SessionID != "" {
		eventID := ""
		if len(response.EventIDs) > 0 {
			eventID = response.EventIDs[0]
		}
		if err := s.core.AppendMessage(r.Context(), request.SessionID, "assistant", response.Answer, eventID); err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{"error": err.Error()})
			return
		}
	}
	writeJSON(w, http.StatusOK, response)
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.core.Health(ctx); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{"success": false, "core": "error", "error": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "service": "traceshield-eino", "core": "ok", "chat_model": chatModelStatus(s.chatModelEnabled), "eino_commit": "e8832e2"})
}

func (s *Server) proxyCore(w http.ResponseWriter, r *http.Request) {
	r.URL.Path = strings.TrimPrefix(r.URL.Path, "/core")
	s.proxy.ServeHTTP(w, r)
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("content-type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func chatModelStatus(enabled bool) string {
	if enabled {
		return "enabled"
	}
	return "disabled"
}

func requestLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		started := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(started).Round(time.Millisecond))
	})
}

func listenAddress(port string) string {
	return fmt.Sprintf("0.0.0.0:%s", port)
}
