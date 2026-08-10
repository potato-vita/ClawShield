<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  Circle,
  CircleDot,
  Clock,
  FileSearch,
  Fingerprint,
  History,
  ListChecks,
  Network,
  PanelLeft,
  PanelRight,
  Plus,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Square,
  SquareTerminal,
  UserCheck,
  Workflow,
  Wrench,
} from "lucide-vue-next";
import {
  AssistantStreamError,
  getAssistantHealth,
  streamAssistantChat,
  type AssistantHistoryMessage,
} from "@/api/assistant";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";
import { useUiStore } from "@/stores/uiStore";

type ChatActor = "assistant" | "user";
type MessageStatus = "complete" | "streaming" | "stopped" | "error";
type ConnectionStatus = "checking" | "ready" | "connecting" | "connected" | "error";
type ChatMessage = {
  id: number;
  actor: ChatActor;
  text: string;
  time: string;
  evidence?: string[];
  status?: MessageStatus;
  sendToModel?: boolean;
};

interface FailedRequest {
  message: string;
  history: AssistantHistoryMessage[];
  assistantId: number;
}

type AgentRunState = "idle" | "running" | "complete" | "stopped" | "error";
type InspectorTab = "tasks" | "logs";
type AgentRunLog = {
  id: number;
  time: string;
  label: string;
  detail: string;
  tone?: "success" | "error" | "stopped";
};

type RunLifecycle = {
  request: boolean;
  start: boolean;
  delta: boolean;
  done: boolean;
  state: AgentRunState;
};

const cases = [
  { id: "case-217", title: "可疑凭据访问", meta: "run_8fa2 · 6 分钟前", risk: "critical" },
  { id: "case-216", title: "外发请求复核", meta: "run_39de · 28 分钟前", risk: "medium" },
  { id: "case-213", title: "Shell 命令序列摘要", meta: "run_b812 · 1 小时前", risk: "low" },
  { id: "case-209", title: "未知工具研判", meta: "run_117c · 昨天", risk: "medium" },
] as const;

const riskLabels = { critical: "严重", medium: "中等", low: "低" } as const;

const quickActions = [
  { label: "解释阻止原因", hint: "汇总关键证据", icon: ShieldCheck, prompt: "请解释最近一次工具调用为什么被阻止，并指出决定性证据。" },
  { label: "追踪数据暴露", hint: "跨工具追踪敏感数据", icon: Network, prompt: "请追踪本次运行中可能存在的敏感数据暴露路径。" },
  { label: "复核 Shell 意图", hint: "对照命令与用户意图", icon: SquareTerminal, prompt: "请复核 Shell 命令，并将其与用户原始目标进行对照。" },
  { label: "查找关联事件", hint: "检索相邻时间线", icon: FileSearch, prompt: "请查找与本次凭据访问相关的事件。" },
] as const;

const roadmapCapabilities = [
  { label: "工具调用", detail: "安全工具尚未注册", icon: Wrench },
  { label: "安全技能", detail: "可复用 Skills 尚未接入", icon: Sparkles },
  { label: "人工审批", detail: "HITL 人机协作将在后续接入", icon: UserCheck },
] as const;

const messages = ref<ChatMessage[]>([
  {
    id: 1,
    actor: "assistant",
    text: "选择一个快捷调查，或直接询问当前可见的审计摘要。响应将由 Eino 助手通过 TraceShield Core 实时流式返回。",
    time: timestamp(),
    evidence: ["Agent · CloudWeGo Eino", "模型 · DeepSeek", "上下文 · 仅摘要"],
    status: "complete",
    sendToModel: false,
  },
]);

const activeCaseId = ref<(typeof cases)[number]["id"]>("case-217");
const caseQuery = ref("");
const draft = ref("");
const pending = ref(false);
const thread = ref<HTMLElement | null>(null);
const connectionStatus = ref<ConnectionStatus>("checking");
const modelName = ref("DeepSeek");
const assistantError = ref("");
const lastFailedRequest = ref<FailedRequest | null>(null);
const inspectorTab = ref<InspectorTab>("tasks");
const ui = useUiStore();
const casebookVisible = computed({
  get: () => !ui.assistantSessionsCollapsed,
  set: (visible: boolean) => { ui.assistantSessionsCollapsed = !visible; },
});
const inspectorVisible = computed({
  get: () => !ui.assistantInspectorCollapsed,
  set: (visible: boolean) => { ui.assistantInspectorCollapsed = !visible; },
});
const runLifecycle = ref<RunLifecycle>({ request: false, start: false, delta: false, done: false, state: "idle" });
const runLogs = ref<AgentRunLog[]>([]);
const activeCase = computed(() => cases.find((item) => item.id === activeCaseId.value) ?? cases[0]);
const visibleCases = computed(() => {
  const query = caseQuery.value.trim().toLowerCase();
  if (!query) return cases;
  return cases.filter((item) => `${item.title} ${item.meta} ${item.risk}`.toLowerCase().includes(query));
});
const connectionLabel = computed(() => ({
  checking: "检查中",
  ready: "就绪",
  connecting: "连接中",
  connected: "已连接",
  error: "不可用",
})[connectionStatus.value]);
const assistantIdentity = computed(() => `Eino / ${modelName.value}`);
const runStatusLabel = computed(() => ({
  idle: "暂无运行任务",
  running: "正在流式响应",
  complete: "运行完成",
  stopped: "已停止",
  error: "响应中断",
})[runLifecycle.value.state]);
const runStateBadge = computed(() => ({
  idle: "待命",
  running: "运行中",
  complete: "已完成",
  stopped: "已停止",
  error: "异常",
})[runLifecycle.value.state]);
const lifecycleTasks = computed(() => {
  const definitions = [
    { key: "request" as const, label: "请求已提交", detail: "浏览器请求已通过 TraceShield Core 发出" },
    { key: "start" as const, label: "SSE 流已启动", detail: "已收到 Eino 服务的 start 事件" },
    { key: "delta" as const, label: "正在接收响应", detail: "浏览器已收到真实 delta 数据片段" },
    { key: "done" as const, label: "流式响应完成", detail: "已收到 Eino 服务的 done 事件" },
  ];

  return definitions.map((task, index) => {
    const completed = runLifecycle.value[task.key];
    const previousComplete = definitions.slice(0, index).every((item) => runLifecycle.value[item.key]);
    return {
      ...task,
      status: completed
        ? "complete"
        : runLifecycle.value.state === "running" && previousComplete
          ? "active"
          : "pending",
    };
  });
});
const composerStatus = computed(() => {
  if (pending.value) return `${assistantIdentity.value} 正在生成实时响应`;
  if (connectionStatus.value === "error") return `${assistantIdentity.value} 当前不可用`;
  if (connectionStatus.value === "checking") return "正在通过 TraceShield Core 检查 Eino 助手";
  return `${assistantIdentity.value} · 仅使用审计摘要上下文`;
});

let messageSequence = 10;
let logSequence = 0;
let activeRequest: AbortController | null = null;
let healthRequest: AbortController | null = null;
let requestSerial = 0;

function newMessageId() {
  messageSequence += 1;
  return Date.now() * 100 + messageSequence;
}

function newConversationId(caseId: string) {
  const suffix = typeof crypto.randomUUID === "function" ? crypto.randomUUID() : `${Date.now()}-${messageSequence}`;
  return `traceshield-${caseId}-${suffix}`;
}

const conversationId = ref(newConversationId(activeCaseId.value));

function timestamp() {
  return new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date());
}

function logTimestamp() {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
}

function appendRunLog(label: string, detail: string, tone?: AgentRunLog["tone"]) {
  logSequence += 1;
  runLogs.value.push({ id: logSequence, time: logTimestamp(), label, detail, tone });
}

function resetAgentRun() {
  runLifecycle.value = { request: false, start: false, delta: false, done: false, state: "idle" };
  runLogs.value = [];
  inspectorTab.value = "tasks";
}

function beginAgentRun(message: string) {
  runLifecycle.value = { request: true, start: false, delta: false, done: false, state: "running" };
  runLogs.value = [];
  inspectorTab.value = "tasks";
  appendRunLog("请求已提交", `已通过 TraceShield Core 发送 ${message.length.toLocaleString()} 个字符`);
}

async function scrollToLatest() {
  await nextTick();
  thread.value?.scrollTo({ top: thread.value.scrollHeight, behavior: "smooth" });
}

function conversationHistory(): AssistantHistoryMessage[] {
  const candidates = messages.value
    .filter((message) => message.sendToModel !== false && message.text.trim() && message.status !== "error" && message.status !== "streaming" && message.status !== "stopped")
    .map((message) => ({ role: message.actor, content: message.text }))
    .slice(-40);
  const bounded: AssistantHistoryMessage[] = [];
  let characters = 0;
  for (let index = candidates.length - 1; index >= 0; index -= 1) {
    const item = candidates[index];
    if (!item || characters + item.content.length > 40_000) break;
    bounded.unshift(item);
    characters += item.content.length;
  }
  return bounded;
}

function visibleSecurityContext(): Record<string, unknown> {
  const runReference = activeCase.value.meta.split(" · ")[0];
  return {
    source: "TraceShield AI 安全 Agent 页面",
    investigation: {
      case_id: activeCase.value.id,
      title: activeCase.value.title,
      run_reference: runReference,
      displayed_risk: activeCase.value.risk,
    },
    active_scope: {
      session_id: "ses_84f2",
      runs: 1,
      events: 12,
      evidence_items: 3,
    },
    visible_security_summary: {
      runtime_graph: "当前运行包含 7 个节点",
      policy_decisions: "命中 2 条策略并阻止 1 个操作",
      conversation_intent: "共 6 条消息，仅使用摘要",
    },
    data_handling: "仅附加页面可见摘要，不包含原始秘密信息或 API 凭据。",
  };
}

function errorMessage(error: unknown) {
  if (error instanceof AssistantStreamError) return error.message;
  return error instanceof Error ? error.message : "助手请求失败";
}

async function requestAssistant(message: string, history: AssistantHistoryMessage[]) {
  healthRequest?.abort();
  const previousConnectionStatus = connectionStatus.value;
  const controller = new AbortController();
  activeRequest = controller;
  requestSerial += 1;
  const serial = requestSerial;
  const assistantId = newMessageId();
  messages.value.push({
    id: assistantId,
    actor: "assistant",
    text: "",
    time: timestamp(),
    status: "streaming",
  });
  pending.value = true;
  connectionStatus.value = "connecting";
  assistantError.value = "";
  lastFailedRequest.value = null;
  await scrollToLatest();
  beginAgentRun(message);

  try {
    await streamAssistantChat({
      conversation_id: conversationId.value,
      message,
      history,
      context: visibleSecurityContext(),
    }, {
      onStart(event) {
        if (serial !== requestSerial) return;
        if (event.conversationId) conversationId.value = event.conversationId;
        if (event.model) modelName.value = event.model;
        connectionStatus.value = "connected";
        if (!runLifecycle.value.start) {
          runLifecycle.value.start = true;
          appendRunLog("SSE 流已启动", `${modelName.value} 已确认请求`, "success");
        }
      },
      onDelta(content) {
        if (serial !== requestSerial) return;
        const reply = messages.value.find((item) => item.id === assistantId);
        if (reply) reply.text += content;
        connectionStatus.value = "connected";
        if (!runLifecycle.value.delta) {
          runLifecycle.value.delta = true;
          appendRunLog("收到首个响应片段", "真实 delta 事件已到达对话界面", "success");
        }
        void scrollToLatest();
      },
      onDone(event) {
        if (serial !== requestSerial) return;
        if (event.conversationId) conversationId.value = event.conversationId;
        if (!runLifecycle.value.done) {
          runLifecycle.value.done = true;
          appendRunLog("SSE 流已完成", "Eino 服务已发出 done 事件", "success");
        }
      },
    }, controller.signal);

    if (serial !== requestSerial) return;
    const reply = messages.value.find((item) => item.id === assistantId);
    if (!reply?.text.trim()) {
      throw new AssistantStreamError(200, "EMPTY_RESPONSE", "Eino 已结束请求，但没有返回文本内容");
    }
    reply.status = "complete";
    connectionStatus.value = "connected";
    runLifecycle.value.state = "complete";
  } catch (error) {
    if (serial !== requestSerial) return;
    const reply = messages.value.find((item) => item.id === assistantId);
    if (controller.signal.aborted) {
      if (reply) reply.status = "stopped";
      runLifecycle.value.state = "stopped";
      appendRunLog("生成已停止", "操作人员取消了当前浏览器请求", "stopped");
      if (connectionStatus.value === "connecting") {
        connectionStatus.value = previousConnectionStatus === "error" ? "error" : "ready";
      }
      return;
    }
    if (reply) reply.status = "error";
    connectionStatus.value = "error";
    assistantError.value = `Eino / DeepSeek 请求失败：${errorMessage(error)}`;
    lastFailedRequest.value = { message, history, assistantId };
    runLifecycle.value.state = "error";
    appendRunLog("流式响应中断", errorMessage(error), "error");
  } finally {
    if (serial === requestSerial) {
      pending.value = false;
      activeRequest = null;
      await scrollToLatest();
    }
  }
}

async function sendMessage(text = draft.value) {
  const clean = text.trim();
  if (!clean || pending.value) return;
  const history = conversationHistory();
  messages.value.push({ id: newMessageId(), actor: "user", text: clean, time: timestamp(), status: "complete" });
  draft.value = "";
  await requestAssistant(clean, history);
}

function stopGeneration() {
  activeRequest?.abort();
}

async function retryLastMessage() {
  const failed = lastFailedRequest.value;
  if (!failed || pending.value) {
    if (!pending.value) await probeAssistant();
    return;
  }
  messages.value = messages.value.filter((message) => message.id !== failed.assistantId);
  await requestAssistant(failed.message, failed.history);
}

function cancelConversationRequest() {
  requestSerial += 1;
  activeRequest?.abort();
  activeRequest = null;
  pending.value = false;
}

function startNewInvestigation() {
  cancelConversationRequest();
  resetAgentRun();
  activeCaseId.value = "case-217";
  conversationId.value = newConversationId(activeCaseId.value);
  messages.value = [{
    id: newMessageId(),
    actor: "assistant",
    time: timestamp(),
    text: "新的调查会话已经就绪。你可以选择快捷调查，或询问会话、运行记录、策略决策和证据路径。",
    evidence: ["Agent · CloudWeGo Eino", "模型 · DeepSeek", "上下文 · 仅摘要"],
    status: "complete",
    sendToModel: false,
  }];
  draft.value = "";
  assistantError.value = "";
  lastFailedRequest.value = null;
}

function selectCase(id: (typeof cases)[number]["id"]) {
  cancelConversationRequest();
  resetAgentRun();
  activeCaseId.value = id;
  conversationId.value = newConversationId(id);
  const selected = cases.find((item) => item.id === id) ?? cases[0];
  messages.value = [{
    id: newMessageId(),
    actor: "assistant",
    time: timestamp(),
    text: `“${selected.title}”已经成为当前调查上下文。你希望 Eino 重点分析什么？`,
    evidence: [selected.meta, `风险 · ${selected.risk}`, "上下文 · 已摘要"],
    status: "complete",
    sendToModel: false,
  }];
  draft.value = "";
  assistantError.value = "";
  lastFailedRequest.value = null;
}

async function probeAssistant() {
  if (pending.value) return;
  healthRequest?.abort();
  const controller = new AbortController();
  healthRequest = controller;
  connectionStatus.value = "checking";
  try {
    const health = await getAssistantHealth(controller.signal);
    if (!health.ok) throw new AssistantStreamError(503, "ASSISTANT_UNAVAILABLE", "助手服务报告异常状态");
    if (health.configured === false) throw new AssistantStreamError(503, "ASSISTANT_NOT_CONFIGURED", "DeepSeek 模型尚未配置");
    if (health.model) modelName.value = health.model;
    connectionStatus.value = "ready";
    assistantError.value = "";
  } catch (error) {
    if (controller.signal.aborted) return;
    connectionStatus.value = "error";
    assistantError.value = `Eino / DeepSeek 当前不可用：${errorMessage(error)}`;
  } finally {
    if (healthRequest === controller) healthRequest = null;
  }
}

onMounted(() => { void probeAssistant(); });
onBeforeUnmount(() => {
  cancelConversationRequest();
  healthRequest?.abort();
});
</script>

<template>
  <ProductPageLayout mode="workspace" eyebrow="Agent 工作台" title="TraceShield AI 安全 Agent" description="由 CloudWeGo Eino 驱动的安全调查工作台。">
    <section class="agent-app">
      <header class="agent-command-bar">
        <div class="agent-brand">
          <span class="agent-mark"><Fingerprint :size="21" /></span>
          <div><small>TraceShield 智能分析</small><h1>AI 安全 Agent</h1></div>
          <span class="eino-badge"><Workflow :size="13" /> 由 CloudWeGo Eino 驱动</span>
        </div>
        <div class="runtime-route" aria-label="实时助手链路">
          <span>TraceShield 上下文</span><ChevronRight :size="13" /><span>Eino ChatModel</span><ChevronRight :size="13" /><span>DeepSeek</span><ChevronRight :size="13" /><b>SSE 响应</b>
        </div>
        <div class="agent-actions">
          <span class="top-connection" :class="'status-' + connectionStatus"><CircleDot :size="13" /><b>{{ connectionLabel }}</b><small>{{ modelName }}</small></span>
          <button type="button" class="icon-action" :aria-pressed="casebookVisible" :title="casebookVisible ? '收起 Agent 会话' : '展开 Agent 会话'" @click="casebookVisible=!casebookVisible"><PanelLeft :size="17" /></button>
          <button type="button" class="icon-action" :aria-pressed="inspectorVisible" :title="inspectorVisible ? '收起 Agent 工作区' : '展开 Agent 工作区'" @click="inspectorVisible=!inspectorVisible"><PanelRight :size="17" /></button>
          <button class="new-investigation" type="button" @click="startNewInvestigation"><Plus :size="16" /> 新建会话</button>
        </div>
      </header>

      <div class="agent-main-grid" :class="{ 'casebook-collapsed': !casebookVisible, 'inspector-collapsed': !inspectorVisible }">
        <aside class="agent-sessions" :class="{ 'is-collapsed': !casebookVisible }">
          <template v-if="casebookVisible">
            <header class="section-heading"><span><History :size="16" /><strong>Agent 会话</strong></span><small>{{ cases.length }} 个演示</small></header>
            <div class="session-tools">
              <label class="session-search"><Search :size="15" /><input v-model="caseQuery" aria-label="搜索 Agent 会话" placeholder="搜索会话" /></label>
              <button type="button" @click="startNewInvestigation"><Plus :size="15" /> 新建调查</button>
            </div>
            <div class="session-list">
              <button v-for="item in visibleCases" :key="item.id" type="button" class="session-item" :class="[{ active: activeCaseId === item.id }, 'risk-' + item.risk]" @click="selectCase(item.id)">
                <i /><span><strong>{{ item.title }}</strong><small>{{ item.meta }}</small></span><ChevronRight :size="15" />
              </button>
              <div v-if="!visibleCases.length" class="session-empty">没有匹配的会话</div>
            </div>
            <footer class="demo-scope">
              <div><CircleDot :size="13" /><span><small>演示上下文</small><strong>会话 ses_84f2</strong></span></div><p>1 次运行 · 12 个事件 · 3 项证据</p>
            </footer>
          </template>
          <button v-else class="panel-reopen" type="button" title="展开 Agent 会话" @click="casebookVisible=true"><PanelLeft :size="15" /><span>Agent 会话</span></button>
        </aside>

        <main class="agent-conversation">
          <header class="conversation-header">
            <div class="conversation-title"><small>当前调查 · 演示上下文</small><h2>{{ activeCase.title }}</h2><span>{{ activeCase.meta }} · {{ riskLabels[activeCase.risk] }}风险</span></div>
            <div class="conversation-meta"><span><CheckCircle2 :size="14" /> 已附加上下文</span><code>{{ conversationId.slice(0, 24) }}…</code></div>
          </header>
          <div ref="thread" class="agent-message-thread" aria-live="polite">
            <div class="conversation-intro"><span><Bot :size="20" /></span><div><small>Eino Agent 通道</small><strong>从运行时决策还原完整安全事件。</strong><p>当前已接入实时对话分析；工具调用、Skills 与人工审批卡片将作为下一阶段 Agent 能力。</p></div></div>
            <article v-for="message in messages" :key="message.id" class="agent-message" :class="message.actor">
              <div class="message-avatar"><Bot v-if="message.actor === 'assistant'" :size="16" /><span v-else>你</span></div>
              <div class="agent-message-body">
                <header><strong>{{ message.actor === "assistant" ? "TraceShield Agent" : "你" }}</strong><time>{{ message.time }}</time></header>
                <p v-if="message.text" :class="{ 'streaming-copy': message.status === 'streaming' }">{{ message.text }}</p>
                <div v-if="message.status === 'streaming' && !message.text" class="typing"><i /><i /><i /></div>
                <small v-if="message.status === 'stopped'" class="message-state stopped">生成已停止</small>
                <small v-if="message.status === 'error'" class="message-state failed">流式响应中断</small>
                <div v-if="message.evidence?.length" class="message-chips"><span v-for="item in message.evidence" :key="item">{{ item }}</span></div>
              </div>
            </article>
          </div>
          <footer class="agent-composer">
            <div v-if="assistantError" class="assistant-error" role="alert"><AlertTriangle :size="16" /><span><strong>助手连接异常</strong><small>{{ assistantError }}</small></span><button type="button" :disabled="pending" @click="retryLastMessage"><RotateCcw :size="13" /> 重试</button></div>
            <div class="quick-prompts"><button v-for="action in quickActions" :key="action.label" type="button" :disabled="pending" :title="action.hint" @click="sendMessage(action.prompt)"><component :is="action.icon" :size="13" /> {{ action.label }}</button></div>
            <div class="composer-box"><textarea v-model="draft" rows="1" maxlength="12000" :disabled="pending" placeholder="向 Eino 询问本次运行、决策、风险路径或证据…" @keydown.enter.exact.prevent="sendMessage()" /><button v-if="pending" class="stop-button" type="button" aria-label="停止生成" @click="stopGeneration"><Square :size="15" /></button><button v-else class="send-button" type="button" :disabled="!draft.trim()" aria-label="发送消息" @click="sendMessage()"><Send :size="18" /></button></div>
            <div class="composer-footer"><span><ShieldCheck :size="13" /> 只读分析 · 仅使用摘要上下文</span><small>{{ composerStatus }}</small><kbd>Enter ↵</kbd></div>
          </footer>
        </main>

        <aside class="agent-inspector" :class="{ 'is-collapsed': !inspectorVisible }">
          <template v-if="inspectorVisible">
            <header class="section-heading inspector-heading"><span><Activity :size="16" /><strong>Agent 工作区</strong></span><small>实时事件</small></header>
            <div class="inspector-tabs"><button type="button" :class="{ active: inspectorTab === 'tasks' }" @click="inspectorTab='tasks'"><ListChecks :size="14" /> 任务列表</button><button type="button" :class="{ active: inspectorTab === 'logs' }" @click="inspectorTab='logs'"><SquareTerminal :size="14" /> 运行日志</button></div>
            <div v-if="inspectorTab === 'tasks'" class="inspector-scroll">
              <section class="inspector-section run-section">
                <header><div><small>当前 Agent 运行</small><h3>{{ runStatusLabel }}</h3></div><span :class="'run-' + runLifecycle.state">{{ runStateBadge }}</span></header>
                <div class="lifecycle-list"><article v-for="(task,index) in lifecycleTasks" :key="task.key" :class="'task-' + task.status"><span class="task-icon"><CheckCircle2 v-if="task.status === 'complete'" :size="15" /><Activity v-else-if="task.status === 'active'" :size="15" /><Circle v-else :size="15" /></span><i v-if="index < lifecycleTasks.length - 1" /><div><strong>{{ task.label }}</strong><small>{{ task.detail }}</small></div></article></div>
              </section>
              <section class="inspector-section context-section"><header><div><small>安全上下文</small><h3>已附加证据</h3></div><span class="live-label">3 个来源</span></header><dl><div><dt>运行时图谱</dt><dd>7 个节点</dd></div><div><dt>策略决策</dt><dd>2 次命中 · 1 次阻止</dd></div><div><dt>对话意图</dt><dd>6 条消息</dd></div></dl></section>
              <section class="inspector-section roadmap-section"><header><div><small>未来 Agent 能力层</small><h3>能力路线图</h3></div><span class="roadmap-count">0 项已接入</span></header><article v-for="capability in roadmapCapabilities" :key="capability.label"><span><component :is="capability.icon" :size="15" /></span><div><strong>{{ capability.label }}</strong><small>{{ capability.detail }}</small></div><b>规划中</b></article></section>
            </div>
            <div v-else class="inspector-scroll log-view">
              <div class="log-summary"><Clock :size="15" /><span><small>对话标识</small><code>{{ conversationId }}</code></span></div>
              <div v-if="runLogs.length" class="run-log-list"><article v-for="entry in runLogs" :key="entry.id" :class="entry.tone ? 'log-' + entry.tone : ''"><time>{{ entry.time }}</time><i /><div><strong>{{ entry.label }}</strong><small>{{ entry.detail }}</small></div></article></div>
              <div v-else class="empty-run-log"><SquareTerminal :size="24" /><strong>暂无运行事件</strong><span>发送一条消息，即可在这里观察真实 SSE 生命周期。</span></div>
              <section class="future-slot"><Workflow :size="18" /><div><small>A2UI 兼容展示区</small><strong>工具结果与人工审批卡片</strong><p>这里为下一阶段 Agent 能力保留展示位置。</p></div><span>路线图</span></section>
            </div>
          </template>
          <button v-else class="panel-reopen" type="button" title="展开 Agent 工作区" @click="inspectorVisible=true"><PanelRight :size="15" /><span>Agent 工作区</span></button>
        </aside>
      </div>
    </section>
  </ProductPageLayout>
</template>

<style scoped>
.new-investigation{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid var(--trace-red);border-radius:10px;color:#fff;background:var(--trace-red);font-size:10px;font-weight:700;cursor:pointer;box-shadow:0 7px 16px rgba(201,31,55,.14);transition:transform 180ms ease,box-shadow 180ms ease}.new-investigation:hover{transform:translateY(-1px);box-shadow:0 9px 19px rgba(201,31,55,.2)}
.assistant-workspace{display:grid;grid-template-columns:220px minmax(420px,1fr) 258px;height:calc(100vh - 163px);min-height:570px;overflow:hidden;border:1px solid #202d37;border-radius:17px;color:#e9eef2;background:#101820;box-shadow:0 20px 45px rgba(21,30,40,.14)}
.casebook,.investigation-panel{min-width:0;background:#141e27}.casebook{display:flex;flex-direction:column;padding:14px 11px;border-right:1px solid #26333d}.aside-heading{display:flex;align-items:center;justify-content:space-between;padding:1px 4px 11px}.aside-heading>span{display:flex;align-items:center;gap:7px;font-size:10px;font-weight:750}.aside-heading svg{color:#ef6b7c}.aside-heading small{color:#748492;font:7px var(--trace-font-mono)}.case-search{display:flex;align-items:center;gap:7px;height:34px;padding:0 9px;border:1px solid #2a3741;border-radius:9px;color:#748492;background:#101820}.case-search input{min-width:0;width:100%;border:0;outline:0;color:#dfe7ed;background:transparent;font-size:8px}.case-search input::placeholder{color:#697987}.case-list{display:grid;gap:5px;margin-top:10px}.case-list button{display:grid;grid-template-columns:4px minmax(0,1fr) 15px;align-items:center;gap:9px;width:100%;padding:10px 8px;border:1px solid transparent;border-radius:10px;text-align:left;color:#9eabb6;background:transparent;cursor:pointer;transition:background-color 150ms ease,border-color 150ms ease}.case-list button:hover{border-color:#2a3944;background:#18242e}.case-list button.active{border-color:#45313a;color:#edf1f4;background:#211e25;box-shadow:inset 2px 0 #d83e54}.case-list i{width:3px;height:27px;border-radius:4px;background:#536271}.case-list i.risk-critical{background:#e34b60}.case-list i.risk-medium{background:#d29a3d}.case-list i.risk-low{background:#36a981}.case-list strong,.case-list small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.case-list strong{font-size:8px}.case-list small{margin-top:4px;color:#667684;font:6px var(--trace-font-mono)}.case-list svg{color:#596a78}.scope-card{margin-top:auto;padding:11px;border:1px solid #293741;border-radius:11px;background:#101820}.scope-card>span{display:flex;align-items:center;gap:6px;color:#80909d;font-size:7px;text-transform:uppercase;letter-spacing:.06em}.scope-card>span svg{color:#38ad85}.scope-card strong,.scope-card small{display:block}.scope-card strong{margin-top:9px;font:8px var(--trace-font-mono)}.scope-card small{margin-top:4px;color:#687986;font-size:7px;line-height:1.4}
.conversation-pane{display:flex;min-width:0;min-height:0;flex-direction:column;background:radial-gradient(circle at 50% 12%,rgba(45,65,77,.25),transparent 28%),#0f171e}.conversation-header{display:flex;align-items:center;justify-content:space-between;min-height:55px;padding:0 17px;border-bottom:1px solid #25323c;background:rgba(16,24,32,.76);backdrop-filter:blur(10px)}.conversation-header small,.conversation-header strong{display:block}.conversation-header small{color:#758694;font-size:7px;text-transform:uppercase;letter-spacing:.08em}.conversation-header strong{margin-top:3px;font-size:10px}.header-badges{display:flex;align-items:center;gap:6px}.evidence-status,.connection-status{display:flex;align-items:center;gap:5px;padding:5px 8px;border:1px solid #23443d;border-radius:7px;color:#60c59f;background:#132a25;font-size:7px}.connection-status{border-color:#31414c;color:#9aabb6;background:#17232c}.connection-status small{max-width:104px;overflow:hidden;color:inherit;font:6px var(--trace-font-mono);text-overflow:ellipsis;text-transform:none;letter-spacing:0;white-space:nowrap}.connection-status.status-checking,.connection-status.status-connecting{color:#d8a957;border-color:#59492f;background:#292218}.connection-status.status-connected,.connection-status.status-ready{color:#5bc69d;border-color:#285044;background:#132a25}.connection-status.status-error{color:#ee7786;border-color:#60303a;background:#2a171d}.connection-status.status-checking svg,.connection-status.status-connecting svg{animation:pulse 1.2s infinite}.message-thread{flex:1;min-height:0;overflow:auto;padding:20px 21px}.message-thread::-webkit-scrollbar{width:5px}.message-thread::-webkit-scrollbar-thumb{border-radius:5px;background:#35434e}.message{display:grid;grid-template-columns:28px minmax(0,1fr);gap:9px;max-width:630px;margin:0 auto 15px}.message.user{grid-template-columns:minmax(0,1fr) 28px}.message.user .avatar{grid-column:2}.message.user .message-body{grid-row:1;grid-column:1;border-color:#5c2d3a;background:#281c24}.avatar{display:grid;place-items:center;width:28px;height:28px;border:1px solid #34434e;border-radius:9px;color:#f2a0ab;background:#1c2933}.user .avatar{color:#fff;background:#b91e34;border-color:#cf334a}.avatar span{font-size:7px;font-weight:800}.message-body{padding:11px 12px;border:1px solid #263640;border-radius:4px 12px 12px;background:#17232c;box-shadow:0 8px 19px rgba(0,0,0,.08)}.message-body header{display:flex;align-items:center;justify-content:space-between}.message-body header strong{font-size:8px}.message-body time{color:#667987;font:6px var(--trace-font-mono)}.message-body p{margin:7px 0 0;color:#c0cbd3;font-size:9px;line-height:1.65;white-space:pre-wrap}.streaming-copy::after{display:inline-block;width:4px;height:10px;margin-left:3px;vertical-align:-2px;background:#e65a70;content:"";animation:pulse .8s infinite}.message-state{display:block;margin-top:7px;font:6px var(--trace-font-mono)}.message-state.stopped{color:#9aa8b2}.message-state.failed{color:#ef7888}.evidence-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}.evidence-chips button{display:flex;align-items:center;gap:3px;padding:5px 7px;border:1px solid #33434e;border-radius:7px;color:#91a1ad;background:#111b22;font:6px var(--trace-font-mono);cursor:pointer}.evidence-chips button:hover{color:#fff;border-color:#52636f}.typing{display:flex;gap:4px;padding:8px 2px 2px}.typing i{width:4px;height:4px;border-radius:50%;background:#8495a1;animation:pulse 1s infinite ease-in-out}.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
.composer{flex:0 0 auto;padding:10px 15px 12px;border-top:1px solid #26333d;background:#121c24}.assistant-error{display:grid;grid-template-columns:16px minmax(0,1fr) auto;align-items:center;gap:8px;margin-bottom:8px;padding:8px 9px;border:1px solid #5d3039;border-radius:9px;color:#ef7b8a;background:#2a171d}.assistant-error>span strong,.assistant-error>span small{display:block}.assistant-error>span strong{font-size:7px}.assistant-error>span small{margin-top:3px;color:#bd8990;font-size:6px;line-height:1.35}.assistant-error button{display:flex;align-items:center;gap:4px;padding:5px 7px;border:1px solid #70404a;border-radius:6px;color:#f4a0ab;background:#361d24;font-size:6px;cursor:pointer}.assistant-error button:disabled{opacity:.5;cursor:not-allowed}.suggestions{display:flex;gap:6px;margin-bottom:7px}.suggestions button{display:flex;align-items:center;gap:5px;padding:5px 8px;border:1px solid #30404b;border-radius:7px;color:#8f9fac;background:#17232c;font-size:7px;cursor:pointer}.suggestions button:hover:not(:disabled){color:#e7edf1;border-color:#52626d}.suggestions button:disabled,.quick-list>button:disabled{opacity:.45;cursor:not-allowed}.suggestions svg{color:#e96578}.input-row{display:flex;align-items:flex-end;gap:8px;padding:8px 8px 8px 11px;border:1px solid #3a4954;border-radius:12px;background:#18242d;box-shadow:0 7px 18px rgba(0,0,0,.1)}.input-row:focus-within{border-color:#82606a;box-shadow:0 0 0 3px rgba(201,31,55,.08)}.input-row textarea{flex:1;min-height:23px;max-height:68px;padding:4px 0;border:0;outline:0;resize:none;color:#edf1f4;background:transparent;font-size:9px;line-height:1.5}.input-row textarea:disabled{opacity:.6}.input-row textarea::placeholder{color:#6f808d}.input-row button{display:grid;place-items:center;width:31px;height:31px;border:0;border-radius:9px;color:#fff;background:var(--trace-red);cursor:pointer}.input-row button.stop-button{color:#f7c2c9;background:#5c2430}.input-row button:disabled{color:#667681;background:#2b3943;cursor:not-allowed}.composer>small{display:block;margin-top:6px;color:#596b78;font-size:6px;text-align:center}
.investigation-panel{padding:14px 12px;border-left:1px solid #26333d}.panel-intro{display:flex;align-items:center;gap:9px;padding:1px 3px 12px}.panel-intro>svg{color:#ed6a7b}.panel-intro small,.panel-intro strong{display:block}.panel-intro small{color:#758693;font-size:7px;text-transform:uppercase}.panel-intro strong{margin-top:3px;font-size:10px}.quick-list{display:grid;gap:6px}.quick-list>button{display:grid;grid-template-columns:31px minmax(0,1fr) 15px;align-items:center;gap:8px;width:100%;padding:9px;border:1px solid #293842;border-radius:10px;text-align:left;color:#a7b4bd;background:#101920;cursor:pointer;transition:transform 160ms ease,border-color 160ms ease,background-color 160ms ease}.quick-list>button:hover{transform:translateX(-2px);border-color:#71404b;background:#1b2028}.quick-list>button>span{display:grid;place-items:center;width:31px;height:31px;border-radius:9px;color:#ed7181;background:#2a1c23}.quick-list strong,.quick-list small{display:block}.quick-list strong{color:#d8e0e5;font-size:8px}.quick-list small{margin-top:4px;color:#697a87;font-size:6px;line-height:1.35}.quick-list>button>svg{color:#586a77}.context-stack{margin-top:16px;padding-top:14px;border-top:1px solid #293640}.context-stack header{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;color:#81909c;font-size:7px;text-transform:uppercase}.context-stack header b{padding:3px 5px;border-radius:5px;color:#93a1ac;background:#23303a;font:6px var(--trace-font-mono)}.context-stack>div{display:grid;grid-template-columns:7px 1fr;gap:8px;padding:8px 2px}.context-stack i{width:6px;height:6px;margin-top:2px;border-radius:50%;background:#697985}.context-stack .source-red{background:#e34b60;box-shadow:0 0 0 3px rgba(227,75,96,.1)}.context-stack .source-amber{background:#d29a3d}.context-stack .source-green{background:#36a981}.context-stack strong,.context-stack small{display:block}.context-stack strong{font-size:7px}.context-stack small{margin-top:3px;color:#667784;font-size:6px}.assistant-note{display:flex;align-items:flex-start;gap:6px;margin:15px 0 0;padding:9px;border:1px solid #294139;border-radius:9px;color:#72ad97;background:#13251f;font-size:6px;line-height:1.45}.assistant-note svg{flex:0 0 auto}
@keyframes pulse{0%,70%,100%{opacity:.35;transform:translateY(0)}35%{opacity:1;transform:translateY(-2px)}}
@media (max-width:1250px){.assistant-workspace{grid-template-columns:195px minmax(400px,1fr) 235px}.casebook{padding-left:9px;padding-right:9px}.message-thread{padding-left:14px;padding-right:14px}}

/* Full-bleed Agent workspace. The older selectors above are retained only for
   compatibility with the previous page markup; this layout is the active UI. */
.agent-app {
  display: grid;
  grid-template-rows: 64px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: var(--trace-ink);
  background: #fff;
}

.agent-command-bar {
  display: grid;
  grid-template-columns: minmax(330px, auto) minmax(250px, 1fr) auto;
  align-items: center;
  gap: 18px;
  min-width: 0;
  padding: 0 18px;
  border-bottom: 1px solid #dfe3e8;
  background: #fff;
}

.agent-brand,.agent-actions,.runtime-route,.section-heading>span,.demo-scope>div,.composer-footer>span,.inspector-tabs button,.log-summary { display: flex; align-items: center; }
.agent-brand { min-width: 0; gap: 11px; }
.agent-mark { display: grid; flex: 0 0 auto; place-items: center; width: 38px; height: 38px; border-radius: 11px; color: #fff; background: var(--trace-red); box-shadow: 0 7px 16px rgba(201,31,55,.16); }
.agent-brand small,.agent-brand h1 { display: block; }
.agent-brand small { color: #8a94a2; font-size: 9px; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; }
.agent-brand h1 { margin: 2px 0 0; font-size: 17px; letter-spacing: -.025em; }
.eino-badge { display: flex; align-items: center; gap: 5px; margin-left: 4px; padding: 5px 8px; border: 1px solid #ead7da; border-radius: 999px; color: #9e2638; background: #fff7f7; font-size: 9px; font-weight: 700; white-space: nowrap; }

.runtime-route { justify-self: center; gap: 5px; min-width: 0; color: #8a94a2; font: 9px var(--trace-font-mono); white-space: nowrap; }
.runtime-route svg { color: #b8c0c9; }
.runtime-route b { color: var(--trace-red); font-weight: 750; }
.agent-actions { justify-content: flex-end; gap: 7px; }
.top-connection { display: grid; grid-template-columns: 10px auto; column-gap: 6px; padding: 6px 9px; border: 1px solid #dde3e7; border-radius: 9px; color: #647080; background: #fafbfc; }
.top-connection svg { grid-row: 1 / 3; align-self: center; color: #9ba5b1; }
.top-connection b { font-size: 9px; line-height: 1; }
.top-connection small { margin-top: 3px; color: #909aa7; font: 7px var(--trace-font-mono); line-height: 1; }
.top-connection.status-ready,.top-connection.status-connected { color: #126f55; border-color: #cfe4dc; background: #f3faf7; }
.top-connection.status-ready svg,.top-connection.status-connected svg { color: #19a77c; }
.top-connection.status-checking,.top-connection.status-connecting { color: #9a650c; border-color: #ebddc2; background: #fffaf0; }
.top-connection.status-error { color: var(--trace-red); border-color: #ebcbd0; background: #fff6f6; }
.icon-action { display: grid; place-items: center; width: 34px; height: 34px; padding: 0; border: 1px solid #dfe4e8; border-radius: 9px; color: #6e7988; background: #fff; cursor: pointer; }
.icon-action:hover,.icon-action[aria-pressed="true"] { color: var(--trace-red); border-color: #e8c9ce; background: #fff7f7; }
.new-investigation { display: flex; align-items: center; gap: 7px; min-height: 34px; padding: 0 12px; border: 1px solid var(--trace-red); border-radius: 9px; color: #fff; background: var(--trace-red); box-shadow: none; font-size: 10px; font-weight: 750; cursor: pointer; }
.new-investigation:hover { transform: none; background: var(--trace-red-deep); box-shadow: none; }

.agent-main-grid { display: grid; grid-template-columns: 242px minmax(0, 1fr) 318px; min-width: 0; min-height: 0; overflow: hidden; background: #fff; transition: grid-template-columns 280ms cubic-bezier(.22,1,.36,1); }
.agent-main-grid.casebook-collapsed { grid-template-columns: 48px minmax(0, 1fr) 318px; }
.agent-main-grid.inspector-collapsed { grid-template-columns: 242px minmax(0, 1fr) 48px; }
.agent-main-grid.casebook-collapsed.inspector-collapsed { grid-template-columns: 48px minmax(0, 1fr) 48px; }
.agent-sessions,.agent-conversation,.agent-inspector { min-width: 0; min-height: 0; }

.agent-sessions { display: flex; flex-direction: column; overflow: hidden; border-right: 1px solid #dfe3e8; background: #fafbfc; }
.agent-sessions.is-collapsed,.agent-inspector.is-collapsed { display: grid; place-items: stretch; background: #fafbfc; }
.panel-reopen { display: flex; width: 100%; height: 100%; align-items: center; justify-content: flex-start; flex-direction: column; gap: 10px; padding: 15px 0; border: 0; color: #768291; background: transparent; cursor: pointer; transition: color 160ms ease,background-color 180ms ease; }
.panel-reopen:hover { color: var(--trace-red); background: #fff4f5; }
.panel-reopen span { margin: auto 0; font-size: 9px; font-weight: 750; letter-spacing: .1em; white-space: nowrap; writing-mode: vertical-rl; }
.section-heading { display: flex; flex: 0 0 auto; align-items: center; justify-content: space-between; min-height: 51px; padding: 0 14px; border-bottom: 1px solid #e2e6ea; background: #fff; }
.section-heading>span { gap: 7px; }
.section-heading>span svg { color: var(--trace-red); }
.section-heading strong { font-size: 11px; }
.section-heading small { color: #8c96a3; font: 8px var(--trace-font-mono); text-transform: uppercase; }
.session-tools { display: grid; gap: 8px; padding: 12px; border-bottom: 1px solid #e7eaed; }
.session-search { display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 10px; border: 1px solid #dce1e6; border-radius: 9px; color: #8994a1; background: #fff; }
.session-search:focus-within { border-color: #d9aab2; box-shadow: 0 0 0 3px rgba(201,31,55,.06); }
.session-search input { min-width: 0; width: 100%; border: 0; outline: 0; color: #28313d; background: transparent; font-size: 11px; }
.session-search input::placeholder { color: #a3abb5; }
.session-tools>button { display: flex; align-items: center; justify-content: center; gap: 6px; min-height: 34px; border: 1px solid #e0c4c9; border-radius: 9px; color: var(--trace-red); background: #fff; font-size: 10px; font-weight: 750; cursor: pointer; }
.session-tools>button:hover { background: #fff5f6; }
.session-list { flex: 1; min-height: 0; overflow: auto; padding: 8px; }
.session-list::-webkit-scrollbar,.agent-message-thread::-webkit-scrollbar,.inspector-scroll::-webkit-scrollbar { width: 5px; }
.session-list::-webkit-scrollbar-thumb,.agent-message-thread::-webkit-scrollbar-thumb,.inspector-scroll::-webkit-scrollbar-thumb { border-radius: 6px; background: #d5dbe1; }
.session-item { position: relative; display: grid; grid-template-columns: 4px minmax(0, 1fr) 15px; align-items: center; gap: 9px; width: 100%; min-height: 61px; margin-bottom: 4px; padding: 9px 8px; border: 1px solid transparent; border-radius: 10px; text-align: left; color: #5f6b79; background: transparent; cursor: pointer; }
.session-item:hover { border-color: #e1e5e9; background: #fff; }
.session-item.active { border-color: #eccbd0; color: #202934; background: #fff5f6; box-shadow: 0 4px 12px rgba(30,41,59,.04); }
.session-item>i { width: 3px; height: 35px; border-radius: 5px; background: #9eabb8; }
.session-item.risk-critical>i { background: #d51f3b; }
.session-item.risk-medium>i { background: #d49325; }
.session-item.risk-low>i { background: #24a37c; }
.session-item span { min-width: 0; }
.session-item strong,.session-item small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.session-item strong { font-size: 11px; }
.session-item small { margin-top: 5px; color: #8b96a3; font: 8px var(--trace-font-mono); }
.session-item>svg { color: #a5aeb8; }
.session-empty { padding: 24px 8px; color: #929ca8; text-align: center; font-size: 10px; }
.demo-scope { flex: 0 0 auto; margin: 10px; padding: 11px; border: 1px solid #e0e4e7; border-radius: 10px; background: #fff; }
.demo-scope>div { gap: 8px; }
.demo-scope>div>svg { color: #d49325; }
.demo-scope span small,.demo-scope span strong { display: block; }
.demo-scope span small { color: #959eaa; font-size: 8px; text-transform: uppercase; letter-spacing: .08em; }
.demo-scope span strong { margin-top: 2px; font: 9px var(--trace-font-mono); }
.demo-scope p { margin: 8px 0 0; color: #8994a1; font-size: 9px; }

.agent-conversation { display: flex; flex-direction: column; overflow: hidden; background: #fff; }
.conversation-header { display: flex; flex: 0 0 68px; align-items: center; justify-content: space-between; min-height: 68px; padding: 0 20px; border-bottom: 1px solid #e1e5e9; color: var(--trace-ink); background: #fff; backdrop-filter: none; }
.conversation-title small,.conversation-title h2,.conversation-title span { display: block; }
.conversation-title small { color: var(--trace-red); font-size: 8px; font-weight: 750; letter-spacing: .09em; text-transform: uppercase; }
.conversation-title h2 { margin: 4px 0 2px; font-size: 15px; letter-spacing: -.015em; }
.conversation-title span { color: #84909e; font-size: 9px; text-transform: capitalize; }
.conversation-meta { display: grid; justify-items: end; gap: 5px; }
.conversation-meta span { display: flex; align-items: center; gap: 5px; color: #177b5e; font-size: 9px; font-weight: 700; }
.conversation-meta code { max-width: 220px; overflow: hidden; color: #929ca7; font: 7px var(--trace-font-mono); text-overflow: ellipsis; white-space: nowrap; }
.agent-message-thread { flex: 1; min-height: 0; overflow: auto; padding: 18px clamp(18px,3vw,38px); background: linear-gradient(180deg,#fff 0%,#fcfcfd 100%); }
.conversation-intro { display: grid; grid-template-columns: 38px minmax(0,1fr); gap: 12px; max-width: 780px; margin: 0 auto 20px; padding: 14px 16px; border: 1px solid #efd9dc; border-radius: 12px; background: #fff8f8; }
.conversation-intro>span { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px; color: #fff; background: var(--trace-red); }
.conversation-intro small,.conversation-intro strong { display: block; }
.conversation-intro small { color: var(--trace-red); font-size: 8px; font-weight: 750; letter-spacing: .08em; text-transform: uppercase; }
.conversation-intro strong { margin-top: 4px; font-size: 12px; }
.conversation-intro p { margin: 5px 0 0; color: #747f8c; font-size: 10px; line-height: 1.55; }
.agent-message { display: grid; grid-template-columns: 32px minmax(0,1fr); gap: 10px; max-width: 780px; margin: 0 auto 16px; }
.agent-message.user { grid-template-columns: minmax(0,1fr) 32px; }
.agent-message.user .message-avatar { grid-column: 2; color: #fff; border-color: var(--trace-red); background: var(--trace-red); }
.agent-message.user .agent-message-body { grid-row: 1; grid-column: 1; border-color: #edccd1; background: #fff5f6; }
.message-avatar { display: grid; place-items: center; width: 32px; height: 32px; border: 1px solid #e0e4e8; border-radius: 9px; color: var(--trace-red); background: #fff; }
.message-avatar span { font-size: 8px; font-weight: 800; }
.agent-message-body { min-width: 0; padding: 12px 14px; border: 1px solid #e0e4e8; border-radius: 5px 13px 13px; background: #fff; box-shadow: 0 5px 16px rgba(30,41,59,.04); }
.agent-message-body header { display: flex; align-items: center; justify-content: space-between; }
.agent-message-body header strong { font-size: 10px; }
.agent-message-body time { color: #9ba4af; font: 8px var(--trace-font-mono); }
.agent-message-body p { margin: 8px 0 0; color: #3f4a57; font-size: 12px; line-height: 1.65; white-space: pre-wrap; }
.streaming-copy::after { display: inline-block; width: 4px; height: 13px; margin-left: 4px; vertical-align: -2px; background: var(--trace-red); content: ""; animation: agent-pulse .8s infinite; }
.message-state { display: block; margin-top: 8px; font: 8px var(--trace-font-mono); }
.message-state.stopped { color: #7b8795; }
.message-state.failed { color: var(--trace-red); }
.message-chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
.message-chips span { padding: 4px 7px; border: 1px solid #e1e5e9; border-radius: 6px; color: #778391; background: #fafbfc; font: 7px var(--trace-font-mono); }
.typing { display: flex; gap: 4px; padding: 10px 2px 2px; }
.typing i { width: 5px; height: 5px; border-radius: 50%; background: var(--trace-red); animation: agent-pulse 1s infinite; }
.typing i:nth-child(2) { animation-delay: .15s; }
.typing i:nth-child(3) { animation-delay: .3s; }

.agent-composer { flex: 0 0 auto; padding: 10px 18px 9px; border-top: 1px solid #dfe4e8; background: #fff; }
.assistant-error { display: grid; grid-template-columns: 18px minmax(0,1fr) auto; align-items: center; gap: 9px; margin-bottom: 8px; padding: 8px 10px; border: 1px solid #efc9cf; border-radius: 9px; color: var(--trace-red); background: #fff5f6; }
.assistant-error>span strong,.assistant-error>span small { display: block; }
.assistant-error>span strong { font-size: 9px; }
.assistant-error>span small { margin-top: 2px; color: #9c5964; font-size: 8px; }
.assistant-error button { display: flex; align-items: center; gap: 5px; min-height: 29px; padding: 0 8px; border: 1px solid #ddaab2; border-radius: 7px; color: var(--trace-red); background: #fff; font-size: 8px; cursor: pointer; }
.quick-prompts { display: flex; gap: 6px; margin-bottom: 7px; overflow-x: auto; scrollbar-width: none; }
.quick-prompts::-webkit-scrollbar { display: none; }
.quick-prompts button { display: flex; flex: 0 0 auto; align-items: center; gap: 5px; min-height: 28px; padding: 0 8px; border: 1px solid #e0e4e8; border-radius: 7px; color: #6d7886; background: #fafbfc; font-size: 8px; cursor: pointer; }
.quick-prompts button:hover:not(:disabled) { color: var(--trace-red); border-color: #e3bfc5; background: #fff7f8; }
.quick-prompts button:disabled { opacity: .5; cursor: not-allowed; }
.composer-box { display: grid; grid-template-columns: minmax(0,1fr) 39px; align-items: end; gap: 9px; padding: 8px 8px 8px 12px; border: 1px solid #ccd3da; border-radius: 12px; background: #fff; box-shadow: 0 7px 20px rgba(30,41,59,.06); }
.composer-box:focus-within { border-color: #d58c98; box-shadow: 0 0 0 3px rgba(201,31,55,.07),0 7px 20px rgba(30,41,59,.05); }
.composer-box textarea { width: 100%; min-height: 38px; max-height: 88px; padding: 8px 0; border: 0; outline: 0; resize: none; color: #29333e; background: transparent; font-size: 12px; line-height: 1.45; }
.composer-box textarea::placeholder { color: #a0a8b2; }
.send-button,.stop-button { display: grid; place-items: center; width: 39px; height: 39px; padding: 0; border: 0; border-radius: 10px; color: #fff; background: var(--trace-red); cursor: pointer; }
.send-button:hover,.stop-button:hover { background: var(--trace-red-deep); }
.send-button:disabled { color: #9ba5af; background: #edf0f2; cursor: not-allowed; }
.composer-footer { display: grid; grid-template-columns: auto minmax(0,1fr) auto; align-items: center; gap: 12px; margin-top: 6px; color: #88939f; }
.composer-footer>span { gap: 5px; color: #617e72; font-size: 8px; }
.composer-footer>small { overflow: hidden; font-size: 8px; text-align: center; text-overflow: ellipsis; white-space: nowrap; }
.composer-footer kbd { padding: 2px 5px; border: 1px solid #dde2e6; border-bottom-width: 2px; border-radius: 5px; color: #8a95a2; background: #fafbfc; font: 7px var(--trace-font-mono); }

.agent-inspector { display: flex; flex-direction: column; overflow: hidden; border-left: 1px solid #dfe3e8; background: #fafbfc; }
.inspector-heading { background: #fff; }
.inspector-tabs { display: grid; flex: 0 0 auto; grid-template-columns: 1fr 1fr; padding: 8px 10px 0; border-bottom: 1px solid #e1e5e9; background: #fff; }
.inspector-tabs button { position: relative; justify-content: center; gap: 6px; min-height: 36px; border: 0; color: #87919e; background: transparent; font-size: 9px; font-weight: 700; cursor: pointer; }
.inspector-tabs button::after { position: absolute; right: 9px; bottom: -1px; left: 9px; height: 2px; background: transparent; content: ""; }
.inspector-tabs button.active { color: var(--trace-red); }
.inspector-tabs button.active::after { background: var(--trace-red); }
.inspector-scroll { flex: 1; min-height: 0; overflow: auto; }
.inspector-section { padding: 15px 14px; border-bottom: 1px solid #e3e7ea; }
.inspector-section>header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 13px; }
.inspector-section>header small,.inspector-section>header h3 { display: block; }
.inspector-section>header small { color: #909aa6; font-size: 8px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.inspector-section>header h3 { margin: 3px 0 0; font-size: 12px; }
.inspector-section>header>span { padding: 4px 6px; border-radius: 6px; font: 7px var(--trace-font-mono); text-transform: uppercase; }
.run-idle { color: #74808d; background: #eef1f3; }
.run-running { color: #9a650c; background: #fff1d6; }
.run-complete { color: #147457; background: #e8f6f0; }
.run-stopped { color: #697684; background: #edf0f2; }
.run-error { color: var(--trace-red); background: #fdebed; }
.lifecycle-list article { position: relative; display: grid; grid-template-columns: 22px minmax(0,1fr); gap: 8px; min-height: 49px; }
.lifecycle-list article>i { position: absolute; left: 10px; top: 21px; bottom: -1px; width: 1px; background: #dfe4e8; }
.task-icon { position: relative; z-index: 1; display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; color: #a6afb9; background: #f5f6f7; }
.task-complete .task-icon { color: #178363; background: #eaf7f2; }
.task-active .task-icon { color: var(--trace-red); background: #fdecef; animation: agent-pulse 1.15s infinite; }
.lifecycle-list strong,.lifecycle-list small { display: block; }
.lifecycle-list strong { padding-top: 2px; color: #4a5561; font-size: 9px; }
.lifecycle-list small { margin-top: 3px; color: #919aa5; font-size: 8px; line-height: 1.35; }
.task-complete strong { color: #25303b; }
.task-active strong { color: var(--trace-red); }
.context-section dl { margin: 0; }
.context-section dl div { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; border-top: 1px solid #e7eaed; }
.context-section dt { color: #798491; font-size: 9px; }
.context-section dd { margin: 0; color: #303a45; font: 8px var(--trace-font-mono); }
.live-label { color: #177b5e; background: #eaf7f2; }
.roadmap-count { color: #7e8792; background: #edf0f2; }
.roadmap-section>article { display: grid; grid-template-columns: 31px minmax(0,1fr) auto; align-items: center; gap: 9px; margin-top: 7px; padding: 9px; border: 1px dashed #d8dde2; border-radius: 9px; background: #fff; }
.roadmap-section>article>span { display: grid; place-items: center; width: 31px; height: 31px; border-radius: 8px; color: #9b6270; background: #fff1f3; }
.roadmap-section article strong,.roadmap-section article small { display: block; }
.roadmap-section article strong { font-size: 9px; }
.roadmap-section article small { margin-top: 3px; color: #8e98a4; font-size: 7px; line-height: 1.35; }
.roadmap-section article b { color: #8e98a4; font: 7px var(--trace-font-mono); text-transform: uppercase; }
.log-view { padding: 13px; }
.log-summary { gap: 9px; padding: 10px; border: 1px solid #e0e4e8; border-radius: 9px; background: #fff; }
.log-summary>svg { flex: 0 0 auto; color: var(--trace-red); }
.log-summary span { min-width: 0; }
.log-summary small,.log-summary code { display: block; }
.log-summary small { color: #929ba6; font-size: 7px; text-transform: uppercase; }
.log-summary code { margin-top: 3px; overflow: hidden; color: #626e7c; font: 7px var(--trace-font-mono); text-overflow: ellipsis; white-space: nowrap; }
.run-log-list { margin-top: 13px; }
.run-log-list article { display: grid; grid-template-columns: 49px 8px minmax(0,1fr); gap: 7px; padding: 8px 0; }
.run-log-list time { color: #98a1ac; font: 7px var(--trace-font-mono); }
.run-log-list article>i { width: 7px; height: 7px; margin-top: 2px; border-radius: 50%; background: #aab3bd; }
.run-log-list .log-success>i { background: #1b9a75; }
.run-log-list .log-error>i { background: var(--trace-red); }
.run-log-list .log-stopped>i { background: #8a95a2; }
.run-log-list strong,.run-log-list small { display: block; }
.run-log-list strong { font-size: 9px; }
.run-log-list small { margin-top: 3px; color: #8d97a3; font-size: 8px; line-height: 1.4; }
.empty-run-log { display: grid; justify-items: center; gap: 7px; padding: 48px 20px; color: #9aa4af; text-align: center; }
.empty-run-log strong { color: #697582; font-size: 10px; }
.empty-run-log span { max-width: 190px; font-size: 8px; line-height: 1.5; }
.future-slot { position: relative; display: grid; grid-template-columns: 34px minmax(0,1fr); gap: 10px; margin-top: 14px; padding: 12px; border: 1px dashed #d9c1c5; border-radius: 10px; background: #fff8f8; }
.future-slot>svg { color: var(--trace-red); }
.future-slot small,.future-slot strong { display: block; }
.future-slot small { color: #a36b74; font-size: 7px; text-transform: uppercase; }
.future-slot strong { margin-top: 3px; font-size: 9px; }
.future-slot p { margin: 4px 0 0; color: #8e7780; font-size: 8px; line-height: 1.4; }
.future-slot>span { position: absolute; right: 9px; top: 9px; color: var(--trace-red); font: 7px var(--trace-font-mono); text-transform: uppercase; }

@keyframes agent-pulse { 50% { opacity: .45; } }

@media (max-width: 1380px) {
  .agent-command-bar { grid-template-columns: minmax(310px,1fr) auto; }
  .runtime-route { display: none; }
  .agent-main-grid { grid-template-columns: 220px minmax(0,1fr) 292px; }
  .agent-main-grid.casebook-collapsed { grid-template-columns: 48px minmax(0,1fr) 292px; }
  .agent-main-grid.inspector-collapsed { grid-template-columns: 220px minmax(0,1fr) 48px; }
  .agent-main-grid.casebook-collapsed.inspector-collapsed { grid-template-columns: 48px minmax(0,1fr) 48px; }
  .agent-message-thread { padding-right: 18px; padding-left: 18px; }
}

@media (max-width: 1180px) {
  .eino-badge { display: none; }
  .top-connection small { display: none; }
  .top-connection { display: flex; }
}
</style>
