from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/ui")


def _shell(title: str, content: str, script: str) -> str:
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg-top: #f2f7ef;
      --bg-mid: #fffdf7;
      --bg-bottom: #fff4e6;
      --ink: #1f2a1f;
      --muted: #5f6a5f;
      --card: rgba(255, 255, 255, 0.92);
      --line: #d7e1d2;
      --brand: #1f8a6a;
      --brand-soft: #e4f6ef;
      --brand-deep: #0f5f48;
      --danger: #d35a2b;
      --warn: #f0a93a;
      --ok: #2f7d5f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "IBM Plex Sans", "Noto Sans SC", "Source Han Sans SC", sans-serif;
      background:
        radial-gradient(circle at 10% 10%, rgba(31, 138, 106, 0.18), transparent 42%),
        radial-gradient(circle at 90% 20%, rgba(240, 169, 58, 0.2), transparent 32%),
        linear-gradient(180deg, var(--bg-top), var(--bg-mid) 45%, var(--bg-bottom));
      min-height: 100vh;
      animation: fadeIn 0.45s ease-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    header {{
      padding: 22px 24px 14px;
      border-bottom: 1px solid rgba(31, 138, 106, 0.2);
      background: rgba(255, 255, 255, 0.68);
      backdrop-filter: blur(4px);
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    header h1 {{ margin: 0; font-size: 1.24rem; letter-spacing: 0.01em; }}
    header p {{ margin: 6px 0 0; color: var(--muted); font-size: 0.95rem; }}
    nav {{ margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; }}
    nav a,
    .btn {{
      text-decoration: none;
      color: var(--brand);
      background: var(--brand-soft);
      border: 1px solid rgba(31, 138, 106, 0.25);
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 0.88rem;
      transition: transform 0.14s ease, filter 0.14s ease;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    nav a:hover, .btn:hover {{ transform: translateY(-1px); }}
    .btn.primary {{
      background: linear-gradient(120deg, #e6f8f0, #f1f8ea);
      color: var(--brand-deep);
      border-color: #9ecdb8;
    }}
    .btn:disabled {{
      opacity: 0.65;
      cursor: not-allowed;
      transform: none;
      filter: grayscale(0.2);
    }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 18px 16px 28px; }}
    .grid {{ display: grid; gap: 14px; }}
    .cards {{ grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }}
    .split {{ grid-template-columns: 1fr 1fr; }}
    .triple {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      box-shadow: 0 7px 22px rgba(31, 35, 31, 0.05);
    }}
    .kpi {{ font-size: 1.7rem; font-weight: 700; margin-top: 10px; }}
    .muted {{ color: var(--muted); }}
    .badge {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 0.8rem;
      border: 1px solid #c5d6c2;
      background: #f5faf3;
    }}
    .badge.high, .badge.critical {{ background: #ffe9e0; border-color: #f2b39c; color: #8f2f0a; }}
    .badge.medium, .badge.warn {{ background: #fff3df; border-color: #f1c77e; color: #8f5b00; }}
    .badge.deny {{ background: #ffe7df; border-color: #f2b3a4; color: #8c2f16; }}
    .badge.error {{ background: #ffe7df; border-color: #f2b3a4; color: #8c2f16; }}
    .badge.allow {{ background: #e8f6ef; border-color: #9fcfba; color: #11573f; }}
    .badge.category-chat {{ background: #edf8ff; border-color: #b7dfff; color: #0a4f79; }}
    .badge.category-tool {{ background: #f1f4ff; border-color: #c3d0ff; color: #24418a; }}
    .badge.category-alignment {{ background: #fff3e9; border-color: #ffd0ab; color: #8a3f08; }}
    .badge.category-resource {{ background: #eef9ef; border-color: #b8e4bd; color: #1f6a29; }}
    .badge.category-system {{ background: #f1f1f1; border-color: #d1d1d1; color: #555; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    th, td {{ border-bottom: 1px solid #e2eadf; padding: 8px 6px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li + li {{ margin-top: 8px; }}
    .timeline {{ border-left: 2px solid #c9dbca; margin-left: 6px; padding-left: 14px; }}
    .timeline-item {{ position: relative; padding-bottom: 10px; }}
    .timeline-item::before {{
      content: "";
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--brand);
      position: absolute;
      left: -20px;
      top: 4px;
    }}
    .risk-node {{ color: #9c3a12; font-weight: 700; }}
    .hero {{
      background: linear-gradient(125deg, rgba(31, 138, 106, 0.12), rgba(240, 169, 58, 0.14));
      border: 1px solid rgba(31, 138, 106, 0.24);
      border-radius: 18px;
      padding: 14px;
      margin-bottom: 14px;
    }}
    .hero h2 {{ margin: 0; font-size: 1.06rem; }}
    .hero p {{ margin: 8px 0 0; color: var(--muted); }}
    .hero .highlight {{
      margin-top: 10px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .hero .highlight .cell {{
      background: rgba(255, 255, 255, 0.7);
      border: 1px solid rgba(31, 138, 106, 0.15);
      border-radius: 12px;
      padding: 10px;
    }}
    .hero .highlight .label {{
      color: var(--muted);
      font-size: 0.8rem;
    }}
    .hero .highlight .value {{
      margin-top: 4px;
      font-weight: 700;
    }}
    .mono {{ font-family: "IBM Plex Mono", "Cascadia Mono", monospace; font-size: 0.87rem; }}
    .hidden {{ display: none; }}
    .scenario-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }}
    .scenario-item {{
      border: 1px solid #d8e5d5;
      border-radius: 13px;
      padding: 10px;
      background: #fbfef9;
    }}
    .scenario-item .head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }}
    .scenario-item .actions {{
      margin-top: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .flash {{
      margin-top: 8px;
      font-size: 0.88rem;
      color: var(--muted);
    }}
    .flash strong {{ color: var(--ink); }}
    .list-block {{
      border: 1px solid #e2eadf;
      border-radius: 12px;
      padding: 10px;
      background: #fbfef9;
    }}
    .list-block h4 {{
      margin: 0 0 8px;
      font-size: 0.9rem;
    }}
    .list-block ul {{
      margin: 0;
      padding-left: 16px;
    }}
    .focus-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .focus-grid .focus-card {{
      border: 1px solid #dce8d8;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.85);
      padding: 10px;
    }}
    .focus-card .label {{
      color: var(--muted);
      font-size: 0.8rem;
    }}
    .focus-card .value {{
      margin-top: 6px;
      font-size: 1rem;
      font-weight: 700;
      word-break: break-word;
    }}
    .insight {{
      border: 1px solid #d7e5d2;
      border-radius: 13px;
      background: #f8fcf6;
      padding: 10px;
    }}
    .insight + .insight {{ margin-top: 8px; }}
    .toolbar {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
    .event-explain {{ max-width: 520px; line-height: 1.45; }}
    .event-text {{ max-width: 520px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }}
    .pager {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
    .soft {{ font-size: 0.85rem; color: var(--muted); }}
    @media (max-width: 860px) {{
      .split {{ grid-template-columns: 1fr; }}
      .triple {{ grid-template-columns: 1fr; }}
      .focus-grid {{ grid-template-columns: 1fr 1fr; }}
      .hero .highlight {{ grid-template-columns: 1fr; }}
      header {{ position: static; }}
      .event-explain {{ max-width: none; }}
      .event-text {{ max-width: none; }}
    }}
  </style>
</head>
<body>
  {content}
  <script>
  const EVENT_EXPLANATION_LIBRARY = {{
    chat_message_received: {{
      label: '聊天消息',
      category: 'chat',
      explain: '记录用户或助手的一条对话消息。',
    }},
    tool_call_requested: {{
      label: '工具调用请求',
      category: 'tool',
      explain: 'AI 请求执行工具，系统会据此进行放行、告警或阻断判断。',
    }},
    tool_result_received: {{
      label: '工具执行结果',
      category: 'tool',
      explain: '工具执行后回传结果，系统会继续评估后续风险。',
    }},
    resource_access_requested: {{
      label: '资源访问',
      category: 'resource',
      explain: 'AI 尝试访问文件、环境变量或网络资源，是风险判定的重要依据。',
    }},
    goal_contract_created: {{
      label: '目标契约建立',
      category: 'system',
      explain: '系统把用户目标结构化为可审计契约，后续动作需要对齐该目标。',
    }},
    task_step_created: {{
      label: '任务步骤创建',
      category: 'system',
      explain: '系统创建步骤节点，用于追踪当前运行阶段。',
    }},
    task_step_transitioned: {{
      label: '步骤状态变化',
      category: 'system',
      explain: '任务从一个阶段进入下一阶段，保证流程状态合法。',
    }},
    semantic_check_completed: {{
      label: '语义检查',
      category: 'alignment',
      explain: '系统对当前动作进行语义判断，确认是否偏离任务语义。',
    }},
    alignment_evaluation_completed: {{
      label: '一致性评分',
      category: 'alignment',
      explain: '系统计算本次动作的一致性分数，并给出 allow/review/deny 结论。',
    }},
    alignment_blocked: {{
      label: '一致性阻断',
      category: 'alignment',
      explain: '动作与用户目标不一致，系统提前阻断以避免风险继续。',
    }},
  }};

  function eventDisplay(eventType) {{
    const entry = EVENT_EXPLANATION_LIBRARY[eventType] || {{
      label: eventType || 'unknown_event',
      category: 'system',
      explain: '系统记录了一条行为事件。',
    }};
    return entry;
  }}
  {script}
  </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page() -> HTMLResponse:
    content = """
<header>
  <h1>ClawShield Demo Console</h1>
  <p>面向答辩演示：状态、标准案例一键运行、最近风险审计结果。</p>
  <p id="live-meta" class="muted">live refresh: waiting...</p>
  <p class="muted">
    <button type="button" class="btn" id="dashboard-refresh-now">refresh now</button>
    <button type="button" class="btn" id="dashboard-refresh-toggle">auto refresh: off</button>
  </p>
  <nav>
    <a href="/api/v1/ui/dashboard">Dashboard</a>
    <a href="/docs">API Docs</a>
    <a href="/api/v1/rules/summary">Rule Summary</a>
  </nav>
</header>
<main>
  <section class="hero">
    <h2>一句话定位</h2>
    <p>ClawShield 通过语义守卫 + 统一安全网关 + run 级证据链，解释 AI 工具调用“为什么危险、如何处置、证据在哪里”。</p>
    <div class="highlight">
      <div class="cell">
        <div class="label">ClawShield</div>
        <div id="status-clawshield" class="value">-</div>
      </div>
      <div class="cell">
        <div class="label">OpenClaw</div>
        <div id="status-openclaw" class="value">-</div>
      </div>
      <div class="cell">
        <div class="label">Guardrails</div>
        <div id="status-guardrails" class="value">-</div>
        <div id="status-guardrails-detail" class="muted"></div>
      </div>
    </div>
  </section>

  <section class="grid cards">
    <article class="card"><div class="muted">最近 Runs</div><div id="kpi-runs" class="kpi">-</div><div class="muted">用于展示任务连续性</div></article>
    <article class="card"><div class="muted">高风险 Runs</div><div id="kpi-risk" class="kpi">-</div><div class="muted">high / critical / severe</div></article>
    <article class="card"><div class="muted">阻断次数</div><div id="kpi-blocked" class="kpi">-</div><div class="muted">deny / block</div></article>
  </section>

  <section class="grid split" style="margin-top:14px;">
    <article class="card">
      <h3>标准案例一键入口</h3>
      <div id="scenario-list" class="scenario-list"></div>
      <div id="scenario-feedback" class="flash"></div>
    </article>

    <article class="card">
      <h3>最近 Runs</h3>
      <table>
        <thead>
          <tr><th>run_id</th><th>task</th><th>risk</th><th>view</th></tr>
        </thead>
        <tbody id="run-table"></tbody>
      </table>
    </article>
  </section>

  <section class="grid split" style="margin-top:14px;">
    <article class="card">
      <h3>自由输入兜底：安全任务</h3>
      <div class="list-block">
        <h4>建议现场优先选择</h4>
        <ul id="safe-task-list"></ul>
      </div>
    </article>
    <article class="card">
      <h3>自由输入兜底：风险任务</h3>
      <div class="list-block">
        <h4>用于展示风险判定链</h4>
        <ul id="risk-task-list"></ul>
      </div>
    </article>
  </section>

  <section class="card" style="margin-top:14px;">
    <h3>实时审计流（OpenClaw 对话与工具）</h3>
    <table>
      <thead>
        <tr><th>time</th><th>run_id</th><th>event</th><th>tool</th><th>status</th></tr>
      </thead>
      <tbody id="live-event-table"></tbody>
    </table>
  </section>
</main>
"""

    script = """
let overviewLoading = false;
let dashboardTimer = null;
let dashboardErrorCount = 0;
let dashboardLastLiveEventTs = null;
const DASHBOARD_REFRESH_KEY = 'clawshield_ui_dashboard_auto_refresh_enabled';
const LEGACY_REFRESH_KEY = 'clawshield_ui_auto_refresh_enabled';
const dashboardStoredRefresh = window.localStorage.getItem(DASHBOARD_REFRESH_KEY);
let dashboardAutoRefreshEnabled = (
  dashboardStoredRefresh === null
    ? window.localStorage.getItem(LEGACY_REFRESH_KEY) === '1'
    : dashboardStoredRefresh === '1'
);
const DASHBOARD_LIVE_EVENT_MAX_ROWS = 20;
const DASHBOARD_REFRESH_ACTIVE_MS = 5000;
const DASHBOARD_REFRESH_HIDDEN_MS = 20000;
const DASHBOARD_REFRESH_MAX_BACKOFF_MS = 60000;

function nextDashboardDelayMs() {
  const base = document.hidden ? DASHBOARD_REFRESH_HIDDEN_MS : DASHBOARD_REFRESH_ACTIVE_MS;
  const multiplier = Math.pow(2, Math.min(dashboardErrorCount, 4));
  return Math.min(base * multiplier, DASHBOARD_REFRESH_MAX_BACKOFF_MS);
}

function scheduleDashboardRefresh() {
  if (dashboardTimer) {
    window.clearTimeout(dashboardTimer);
  }
  if (!dashboardAutoRefreshEnabled) {
    return;
  }
  dashboardTimer = window.setTimeout(loadOverview, nextDashboardDelayMs());
}

function renderDashboardRefreshState(lastStamp = null) {
  const toggle = document.getElementById('dashboard-refresh-toggle');
  toggle.textContent = dashboardAutoRefreshEnabled ? 'auto refresh: on' : 'auto refresh: off';
  const meta = document.getElementById('live-meta');
  if (!dashboardAutoRefreshEnabled) {
    meta.textContent = lastStamp
      ? `live refresh: off, last update ${lastStamp}`
      : 'live refresh: off';
    return;
  }
  const nextSeconds = Math.round(nextDashboardDelayMs() / 1000);
  meta.textContent = lastStamp
    ? `live refresh: ~${nextSeconds}s, last update ${lastStamp}`
    : `live refresh: ~${nextSeconds}s`;
}

function setDashboardAutoRefresh(enabled) {
  dashboardAutoRefreshEnabled = Boolean(enabled);
  window.localStorage.setItem(DASHBOARD_REFRESH_KEY, dashboardAutoRefreshEnabled ? '1' : '0');
  if (!dashboardAutoRefreshEnabled && dashboardTimer) {
    window.clearTimeout(dashboardTimer);
    dashboardTimer = null;
  }
  renderDashboardRefreshState();
  if (dashboardAutoRefreshEnabled) {
    scheduleDashboardRefresh();
  }
}

function renderTaskExamples(containerId, items) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';
  for (const text of items || []) {
    const li = document.createElement('li');
    li.textContent = text;
    container.appendChild(li);
  }
}

function appendLiveEventRow(table, ev) {
  const row = document.createElement('tr');
  row.innerHTML = `
    <td>${ev.ts}</td>
    <td class="mono">${ev.run_id}</td>
    <td>${ev.event_type}</td>
    <td>${ev.tool_id || '-'}</td>
    <td><span class="badge ${ev.status || ''}">${ev.status || '-'}</span></td>
  `;
  table.appendChild(row);
}

function trimLiveRows(table, maxRows) {
  while (table.rows.length > maxRows) {
    table.deleteRow(0);
  }
}

async function runScenario(button, scenarioId) {
  const feedback = document.getElementById('scenario-feedback');
  button.disabled = true;
  const prevText = button.textContent;
  button.textContent = 'running...';

  try {
    const response = await fetch(`/api/v1/dashboard/scenarios/${scenarioId}/run`, {
      method: 'POST'
    });
    const payload = await response.json();
    if (!payload.success) {
      feedback.innerHTML = `<span class="badge error">error</span> ${payload.message}`;
      return;
    }

    const data = payload.data;
    feedback.innerHTML = `
      <strong>latest run:</strong>
      <span class="mono">${data.run_id}</span>
      <span class="badge ${data.final_risk_level || ''}">${data.final_risk_level || 'none'}</span>
      <a class="btn" href="${data.report_url}">open report</a>
    `;
    window.setTimeout(() => {
      window.location.href = data.report_url;
    }, 350);
  } catch (error) {
    feedback.innerHTML = `<span class="badge error">error</span> scenario run failed: ${error}`;
  } finally {
    button.disabled = false;
    button.textContent = prevText;
  }
}

async function loadOverview() {
  if (overviewLoading) return;
  overviewLoading = true;
  let succeeded = false;

  try {
    const statusResp = await fetch('/api/v1/system/status');
    const statusPayload = await statusResp.json();
    if (statusPayload.success) {
      const status = statusPayload.data;
      document.getElementById('status-clawshield').innerHTML = `<span class="badge allow">${status.system_status}</span>`;
      document.getElementById('status-openclaw').innerHTML = `<span class="badge ${status.opencaw_status}">${status.opencaw_status}</span>`;
      document.getElementById('status-guardrails').innerHTML = `<span class="badge ${status.guardrails_status}">${status.guardrails_status}</span>`;
      document.getElementById('status-guardrails-detail').textContent = status.guardrails_detail || '';
    }

    const resp = await fetch('/api/v1/dashboard/overview');
    const payload = await resp.json();
    if (!payload.success) return;

    const data = payload.data;
    const recent = data.recent_runs || [];
    document.getElementById('kpi-runs').textContent = recent.length;
    document.getElementById('kpi-risk').textContent = data.high_risk_count;
    document.getElementById('kpi-blocked').textContent = data.blocked_count;

    const scenarioList = document.getElementById('scenario-list');
    scenarioList.innerHTML = '';
    for (const item of data.standard_scenarios || []) {
      const block = document.createElement('article');
      block.className = 'scenario-item';
      block.innerHTML = `
        <div class="head">
          <strong>${item.name}</strong>
          <span class="badge">${item.expected_chain}</span>
        </div>
        <div class="muted">${item.prompt}</div>
        <div class="actions">
          <button type="button" class="btn primary" data-scenario-id="${item.scenario_id}">run scenario</button>
          <span class="mono">${item.scenario_id}</span>
        </div>
      `;
      scenarioList.appendChild(block);
    }

    for (const button of document.querySelectorAll('[data-scenario-id]')) {
      const scenarioId = button.getAttribute('data-scenario-id');
      button.addEventListener('click', () => runScenario(button, scenarioId));
    }

    const table = document.getElementById('run-table');
    table.innerHTML = '';
    for (const run of recent) {
      const risk = run.final_risk_level || 'none';
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${run.run_id}</td>
        <td>${run.task_summary || '-'}</td>
        <td><span class="badge ${risk}">${risk}</span></td>
        <td>
          <a href="/api/v1/ui/runs/${run.run_id}">detail</a> |
          <a href="/api/v1/ui/runs/${run.run_id}/report">report</a>
        </td>
      `;
      table.appendChild(row);
    }

    renderTaskExamples('safe-task-list', data.free_input_examples?.safe_tasks || []);
    renderTaskExamples('risk-task-list', data.free_input_examples?.risk_tasks || []);

    const tracked = new Set(['chat_message_received', 'tool_call_requested', 'tool_result_received']);
    const hasCursor = Boolean(dashboardLastLiveEventTs);
    const queryParams = new URLSearchParams({
      limit: hasCursor ? '200' : '60',
      order: hasCursor ? 'asc' : 'desc',
      event_types: 'chat_message_received,tool_call_requested,tool_result_received',
    });
    if (hasCursor) {
      queryParams.set('since_ts', dashboardLastLiveEventTs);
    }

    const evResp = await fetch(`/api/v1/events?${queryParams.toString()}`);
    const evPayload = await evResp.json();
    const liveTable = document.getElementById('live-event-table');

    if (!hasCursor) {
      liveTable.innerHTML = '';
    }
    if (evPayload.success) {
      const sourceEvents = evPayload.data.events || [];
      if (sourceEvents.length > 0) {
        dashboardLastLiveEventTs = hasCursor
          ? sourceEvents[sourceEvents.length - 1].ts
          : sourceEvents[0].ts;
      }

      const trackedEvents = sourceEvents.filter(ev => tracked.has(ev.event_type));
      if (!hasCursor) {
        for (const ev of trackedEvents.slice(0, DASHBOARD_LIVE_EVENT_MAX_ROWS).reverse()) {
          appendLiveEventRow(liveTable, ev);
        }
      } else {
        for (const ev of trackedEvents) {
          appendLiveEventRow(liveTable, ev);
        }
      }

      trimLiveRows(liveTable, DASHBOARD_LIVE_EVENT_MAX_ROWS);
    }

    const stamp = new Date().toLocaleTimeString();
    renderDashboardRefreshState(stamp);
    succeeded = true;
  } catch (error) {
    console.error('dashboard load failed', error);
  } finally {
    if (succeeded) {
      dashboardErrorCount = 0;
    } else {
      dashboardErrorCount = Math.min(dashboardErrorCount + 1, 6);
    }
    overviewLoading = false;
    scheduleDashboardRefresh();
  }
}

document.addEventListener('visibilitychange', scheduleDashboardRefresh);
document.getElementById('dashboard-refresh-now').addEventListener('click', () => loadOverview());
document.getElementById('dashboard-refresh-toggle').addEventListener('click', () => {
  setDashboardAutoRefresh(!dashboardAutoRefreshEnabled);
});
renderDashboardRefreshState();
loadOverview();
"""

    return HTMLResponse(content=_shell("ClawShield Dashboard", content, script))


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail_page(run_id: str) -> HTMLResponse:
    content = f"""
<header>
  <h1>Run Detail</h1>
  <p>run_id: <strong>{run_id}</strong></p>
  <p class="muted">
    <button type="button" class="btn" id="run-refresh-now">refresh now</button>
    <button type="button" class="btn" id="run-refresh-toggle">auto refresh: off</button>
  </p>
  <nav>
    <a href="/api/v1/ui/dashboard">Dashboard</a>
    <a href="/api/v1/ui/runs/{run_id}/report">Audit Report</a>
    <a href="/api/v1/ui/runs/{run_id}/events">All Events</a>
  </nav>
</header>
<main>
  <section class="grid split">
    <article class="card">
      <h3>基础信息</h3>
      <div id="run-meta" class="muted">loading...</div>
    </article>
    <article class="card">
      <h3>状态概览</h3>
      <div id="run-status" class="muted">loading...</div>
    </article>
  </section>

  <section class="card" style="margin-top:14px;">
    <div class="toolbar">
      <h3 style="margin:0;">最近事件（降序，最新在前）</h3>
      <a class="btn" href="/api/v1/ui/runs/{run_id}/events">查看全部事件</a>
    </div>
    <div class="soft" id="event-meta">loading...</div>
    <table>
      <thead>
        <tr><th>time</th><th>标注</th><th>事件</th><th>tool/resource</th><th>risk</th><th>disposition</th></tr>
      </thead>
      <tbody id="event-table"></tbody>
    </table>
  </section>
</main>
"""

    script_template = """
let runLoading = false;
let runTimer = null;
let runErrorCount = 0;
let runIdleCycles = 0;
const RUN_REFRESH_KEY = 'clawshield_ui_run_auto_refresh_enabled';
const RUN_LEGACY_REFRESH_KEY = 'clawshield_ui_auto_refresh_enabled';
const runStoredRefresh = window.localStorage.getItem(RUN_REFRESH_KEY);
let runAutoRefreshEnabled = (
  runStoredRefresh === null
    ? window.localStorage.getItem(RUN_LEGACY_REFRESH_KEY) === '1'
    : runStoredRefresh === '1'
);
const RUN_REFRESH_ACTIVE_MS = 3000;
const RUN_REFRESH_IDLE_MS = 12000;
const RUN_REFRESH_HIDDEN_MS = 25000;
const RUN_REFRESH_MAX_BACKOFF_MS = 60000;
const RUN_IDLE_CYCLES_THRESHOLD = 3;
const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled', 'stopped', 'done']);

function isRunTerminal(status) {
  return TERMINAL_STATUSES.has((status || '').toLowerCase());
}

function nextRunDelayMs() {
  const base = document.hidden
    ? RUN_REFRESH_HIDDEN_MS
    : (runIdleCycles >= RUN_IDLE_CYCLES_THRESHOLD ? RUN_REFRESH_IDLE_MS : RUN_REFRESH_ACTIVE_MS);
  const multiplier = Math.pow(2, Math.min(runErrorCount, 4));
  return Math.min(base * multiplier, RUN_REFRESH_MAX_BACKOFF_MS);
}

function scheduleRunRefresh() {
  if (runTimer) {
    window.clearTimeout(runTimer);
  }
  if (!runAutoRefreshEnabled) {
    return;
  }
  runTimer = window.setTimeout(loadRun, nextRunDelayMs());
}

function renderRunRefreshState() {
  const toggle = document.getElementById('run-refresh-toggle');
  toggle.textContent = runAutoRefreshEnabled ? 'auto refresh: on' : 'auto refresh: off';
}

function setRunAutoRefresh(enabled) {
  runAutoRefreshEnabled = Boolean(enabled);
  window.localStorage.setItem(RUN_REFRESH_KEY, runAutoRefreshEnabled ? '1' : '0');
  if (!runAutoRefreshEnabled && runTimer) {
    window.clearTimeout(runTimer);
    runTimer = null;
  }
  renderRunRefreshState();
  if (runAutoRefreshEnabled) {
    scheduleRunRefresh();
  }
}

function renderEventRow(ev) {
  const display = eventDisplay(ev.event_type);
  const resource = ev.resource_type ? '/' + ev.resource_type + ':' + (ev.resource_id || '') : '';
  const message = ev.input_summary || '';
  return `
    <tr>
      <td>${ev.ts}</td>
      <td><span class="badge category-${display.category}">${display.label}</span></td>
      <td>
        <div><strong>${ev.event_type}</strong></div>
        <div class="soft event-explain">${display.explain}</div>
        ${message ? `<div class="soft event-text"><strong>input:</strong> ${message}</div>` : ''}
      </td>
      <td>${ev.tool_id || ''} ${resource}</td>
      <td><span class="badge ${ev.risk_level || ''}">${ev.risk_level || '-'}</span></td>
      <td><span class="badge ${ev.disposition || ''}">${ev.disposition || '-'}</span></td>
    </tr>
  `;
}

async function loadRun() {
  if (runLoading) return;
  runLoading = true;
  let succeeded = false;
  let runIsTerminal = false;

  try {
    const runResp = await fetch('/api/v1/runs/__RUN_ID__');
    const runPayload = await runResp.json();
    if (runPayload.success) {
      const run = runPayload.data;
      runIsTerminal = isRunTerminal(run.status);
      document.getElementById('run-meta').innerHTML = `
        <div>task: ${run.task_summary || '-'}</div>
        <div>task_type: <span class="badge">${run.task_type}</span></div>
        <div>created_at: ${run.created_at}</div>
      `;
      document.getElementById('run-status').innerHTML = `
        <div>status: <span class="badge">${run.status}</span></div>
        <div>risk: <span class="badge ${run.final_risk_level || ''}">${run.final_risk_level || 'none'}</span></div>
        <div>disposition: <span class="badge ${run.disposition || ''}">${run.disposition || 'unknown'}</span></div>
      `;
    }

    const limit = 20;
    const params = new URLSearchParams({
      run_id: '__RUN_ID__',
      order: 'desc',
      limit: String(limit),
      offset: '0',
    });
    const evResp = await fetch(`/api/v1/events?${params.toString()}`);
    const evPayload = await evResp.json();
    const table = document.getElementById('event-table');
    table.innerHTML = '';
    if (!evPayload.success) return;

    const events = evPayload.data.events || [];
    const pagination = evPayload.data.pagination || {};
    for (const ev of events) {
      table.insertAdjacentHTML('beforeend', renderEventRow(ev));
    }

    const total = Number(pagination.total_count || events.length);
    const hasMore = Boolean(pagination.has_more);
    document.getElementById('event-meta').innerHTML = `当前显示最近 <strong>${events.length}</strong> 条 / 共 <strong>${total}</strong> 条${hasMore ? '，可点击“查看全部事件”浏览完整记录。' : '。'}`;

    if (events.length > 0) {
      runIdleCycles = 0;
    } else {
      runIdleCycles += 1;
      if (!runIsTerminal) {
        runIdleCycles = Math.min(runIdleCycles, RUN_IDLE_CYCLES_THRESHOLD);
      }
    }
    succeeded = true;
  } catch (error) {
    console.error('run detail refresh failed', error);
  } finally {
    if (succeeded) {
      runErrorCount = 0;
    } else {
      runErrorCount = Math.min(runErrorCount + 1, 6);
    }
    runLoading = false;
    scheduleRunRefresh();
  }
}

document.addEventListener('visibilitychange', scheduleRunRefresh);
document.getElementById('run-refresh-now').addEventListener('click', () => loadRun());
document.getElementById('run-refresh-toggle').addEventListener('click', () => {
  setRunAutoRefresh(!runAutoRefreshEnabled);
});
renderRunRefreshState();
loadRun();
"""
    script = script_template.replace("__RUN_ID__", run_id)

    return HTMLResponse(content=_shell(f"Run Detail {run_id}", content, script))


@router.get("/runs/{run_id}/events", response_class=HTMLResponse)
def run_events_page(run_id: str) -> HTMLResponse:
    content = f"""
<header>
  <h1>Run All Events</h1>
  <p>run_id: <strong>{run_id}</strong></p>
  <nav>
    <a href="/api/v1/ui/dashboard">Dashboard</a>
    <a href="/api/v1/ui/runs/{run_id}">Run Detail</a>
    <a href="/api/v1/ui/runs/{run_id}/report">Audit Report</a>
  </nav>
</header>
<main>
  <section class="card">
    <div class="toolbar">
      <h3 style="margin:0;">完整事件记录（降序）</h3>
      <span class="soft" id="events-meta">loading...</span>
    </div>

    <table>
      <thead>
        <tr><th>time</th><th>标注</th><th>事件</th><th>tool/resource</th><th>risk</th><th>disposition</th></tr>
      </thead>
      <tbody id="events-table"></tbody>
    </table>

    <div class="pager" style="margin-top:12px;">
      <button class="btn" id="prev-btn">上一页</button>
      <button class="btn" id="next-btn">下一页</button>
      <span class="soft" id="page-meta"></span>
    </div>
  </section>
</main>
"""

    script_template = """
const PAGE_SIZE = 100;
let pageOffset = 0;
let totalCount = 0;

function renderEventRow(ev) {
  const display = eventDisplay(ev.event_type);
  const resource = ev.resource_type ? '/' + ev.resource_type + ':' + (ev.resource_id || '') : '';
  const message = ev.input_summary || '';
  return `
    <tr>
      <td>${ev.ts}</td>
      <td><span class="badge category-${display.category}">${display.label}</span></td>
      <td>
        <div><strong>${ev.event_type}</strong></div>
        <div class="soft event-explain">${display.explain}</div>
        ${message ? `<div class="soft event-text"><strong>input:</strong> ${message}</div>` : ''}
      </td>
      <td>${ev.tool_id || ''} ${resource}</td>
      <td><span class="badge ${ev.risk_level || ''}">${ev.risk_level || '-'}</span></td>
      <td><span class="badge ${ev.disposition || ''}">${ev.disposition || '-'}</span></td>
    </tr>
  `;
}

async function loadEvents() {
  const params = new URLSearchParams({
    run_id: '__RUN_ID__',
    order: 'desc',
    limit: String(PAGE_SIZE),
    offset: String(pageOffset),
  });
  const resp = await fetch(`/api/v1/events?${params.toString()}`);
  const payload = await resp.json();
  if (!payload.success) return;

  const table = document.getElementById('events-table');
  table.innerHTML = '';
  const events = payload.data.events || [];
  const pagination = payload.data.pagination || {};
  totalCount = Number(pagination.total_count || events.length);

  for (const ev of events) {
    table.insertAdjacentHTML('beforeend', renderEventRow(ev));
  }

  const currentPage = Math.floor(pageOffset / PAGE_SIZE) + 1;
  const totalPage = Math.max(Math.ceil(totalCount / PAGE_SIZE), 1);
  document.getElementById('events-meta').textContent = `共 ${totalCount} 条事件，按时间降序（最新在前）`;
  document.getElementById('page-meta').textContent = `第 ${currentPage} / ${totalPage} 页`;

  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  prevBtn.disabled = pageOffset === 0;
  nextBtn.disabled = !Boolean(pagination.has_more);
}

function bindPager() {
  document.getElementById('prev-btn').addEventListener('click', async () => {
    pageOffset = Math.max(pageOffset - PAGE_SIZE, 0);
    await loadEvents();
  });
  document.getElementById('next-btn').addEventListener('click', async () => {
    pageOffset += PAGE_SIZE;
    await loadEvents();
  });
}

bindPager();
loadEvents();
"""
    script = script_template.replace("__RUN_ID__", run_id)

    return HTMLResponse(content=_shell(f"Run Events {run_id}", content, script))


@router.get("/runs/{run_id}/report", response_class=HTMLResponse)
def run_report_page(run_id: str) -> HTMLResponse:
    content = f"""
<header>
  <h1>Audit Report</h1>
  <p>run_id: <strong>{run_id}</strong></p>
  <p class="muted">
    <button type="button" class="btn" id="report-refresh-now">refresh now</button>
    <button type="button" class="btn" id="report-refresh-toggle">auto refresh: off</button>
  </p>
  <nav>
    <a href="/api/v1/ui/dashboard">Dashboard</a>
    <a href="/api/v1/ui/runs/{run_id}">Run Detail</a>
  </nav>
</header>
<main>
  <section class="hero">
    <h2>审计结论总览</h2>
    <p id="report-hero">loading...</p>
    <div class="focus-grid" style="margin-top:10px;">
      <div class="focus-card">
        <div class="label">当前任务</div>
        <div id="focus-task" class="value mono">-</div>
      </div>
      <div class="focus-card">
        <div class="label">风险等级</div>
        <div id="focus-risk" class="value">-</div>
      </div>
      <div class="focus-card">
        <div class="label">最终处置</div>
        <div id="focus-disposition" class="value">-</div>
      </div>
      <div class="focus-card">
        <div class="label">链式命中数</div>
        <div id="focus-findings" class="value">-</div>
      </div>
    </div>
  </section>

  <section class="grid split">
    <article class="card">
      <h3>关键 Tool Calls（按风险解读）</h3>
      <div id="tool-call-spotlight" class="insight muted">loading...</div>
      <ul id="tool-call-list" style="margin-top:10px;"></ul>
    </article>
    <article class="card">
      <h3>访问资源</h3>
      <ul id="resource-list"></ul>
    </article>
  </section>

  <section class="grid split">
    <article class="card">
      <h3>左侧时间线</h3>
      <div id="timeline" class="timeline"></div>
      <div id="timeline-hint" class="flash"></div>
    </article>
    <article class="card">
      <h3>右侧链图摘要</h3>
      <div id="graph-summary" class="muted">loading...</div>
      <ul id="graph-highlight" style="margin-top:10px;"></ul>
    </article>
  </section>

  <section class="grid split" style="margin-top:14px;">
    <article class="card">
      <h3>风险命中区域</h3>
      <ul id="risk-hit-list"></ul>
    </article>
    <article class="card">
      <h3>最终结论区域</h3>
      <div id="conclusion" class="muted">loading...</div>
    </article>
  </section>
</main>
"""

    script_template = """
let reportLoading = false;
let reportTimer = null;
let reportErrorCount = 0;
let reportStableCycles = 0;
const REPORT_REFRESH_KEY = 'clawshield_ui_report_auto_refresh_enabled';
const REPORT_LEGACY_REFRESH_KEY = 'clawshield_ui_auto_refresh_enabled';
const reportStoredRefresh = window.localStorage.getItem(REPORT_REFRESH_KEY);
let reportAutoRefreshEnabled = (
  reportStoredRefresh === null
    ? window.localStorage.getItem(REPORT_LEGACY_REFRESH_KEY) === '1'
    : reportStoredRefresh === '1'
);
const REPORT_REFRESH_ACTIVE_MS = 5000;
const REPORT_REFRESH_STABLE_MS = 15000;
const REPORT_REFRESH_HIDDEN_MS = 30000;
const REPORT_REFRESH_MAX_BACKOFF_MS = 90000;

function hasFinalDisposition(report) {
  const disposition = (report.final_disposition || '').toLowerCase();
  return Boolean(disposition) && disposition !== 'unknown';
}

function nextReportDelayMs() {
  const base = document.hidden
    ? REPORT_REFRESH_HIDDEN_MS
    : (reportStableCycles >= 2 ? REPORT_REFRESH_STABLE_MS : REPORT_REFRESH_ACTIVE_MS);
  const multiplier = Math.pow(2, Math.min(reportErrorCount, 4));
  return Math.min(base * multiplier, REPORT_REFRESH_MAX_BACKOFF_MS);
}

function scheduleReportRefresh() {
  if (reportTimer) {
    window.clearTimeout(reportTimer);
  }
  if (!reportAutoRefreshEnabled) {
    return;
  }
  reportTimer = window.setTimeout(loadReport, nextReportDelayMs());
}

function renderReportRefreshState() {
  const toggle = document.getElementById('report-refresh-toggle');
  toggle.textContent = reportAutoRefreshEnabled ? 'auto refresh: on' : 'auto refresh: off';
}

function setReportAutoRefresh(enabled) {
  reportAutoRefreshEnabled = Boolean(enabled);
  window.localStorage.setItem(REPORT_REFRESH_KEY, reportAutoRefreshEnabled ? '1' : '0');
  if (!reportAutoRefreshEnabled && reportTimer) {
    window.clearTimeout(reportTimer);
    reportTimer = null;
  }
  renderReportRefreshState();
  if (reportAutoRefreshEnabled) {
    scheduleReportRefresh();
  }
}

async function loadReport() {
  if (reportLoading) return;
  reportLoading = true;
  let succeeded = false;
  try {
    const resp = await fetch('/api/v1/runs/__RUN_ID__/report');
    const payload = await resp.json();
    if (!payload.success) return;
    const report = payload.data;
    const findings = report.risk_hits || [];
    const highlightedPaths = report.graph?.highlighted_paths || [];

    document.getElementById('report-hero').innerHTML = `<span class="muted">run-level semantic summary:</span> ${report.semantic_summary || '-'}`;
    document.getElementById('focus-task').textContent = report.task_summary || '-';
    document.getElementById('focus-risk').innerHTML = `<span class="badge ${report.final_risk_level || ''}">${report.final_risk_level || 'none'}</span>`;
    document.getElementById('focus-disposition').innerHTML = `<span class="badge ${report.final_disposition || ''}">${report.final_disposition || 'unknown'}</span>`;
    document.getElementById('focus-findings').textContent = String(findings.length);

    const toolCallList = document.getElementById('tool-call-list');
    toolCallList.innerHTML = '';
    const toolCalls = report.tool_calls || [];
    for (const item of toolCalls) {
      const li = document.createElement('li');
      li.innerHTML = `<span class="mono">${item.tool_id}</span> <span class="badge ${item.risk_level || ''}">${item.risk_level || '-'}</span> <span class="badge ${item.disposition || ''}">${item.disposition || '-'}</span>`;
      toolCallList.appendChild(li);
    }
    const spotlight = document.getElementById('tool-call-spotlight');
    const riskyCall = toolCalls.find(item => ['high', 'critical', 'severe', 'medium'].includes((item.risk_level || '').toLowerCase()));
    if (!riskyCall) {
      spotlight.innerHTML = `<strong>spotlight:</strong> no explicit risky tool-call found.`;
    } else {
      spotlight.innerHTML = `
        <strong>spotlight:</strong>
        <span class="mono">${riskyCall.tool_id}</span>
        <span class="badge ${riskyCall.risk_level || ''}">${riskyCall.risk_level || '-'}</span>
        <span class="badge ${riskyCall.disposition || ''}">${riskyCall.disposition || '-'}</span>
      `;
    }

    const resourceList = document.getElementById('resource-list');
    resourceList.innerHTML = '';
    for (const item of report.resources || []) {
      const li = document.createElement('li');
      li.innerHTML = `<span class="mono">${item.resource_type}:${item.resource_id}</span> x${item.access_count} <span class="badge ${item.max_risk_level || ''}">${item.max_risk_level || '-'}</span>`;
      resourceList.appendChild(li);
    }

    const timelineBox = document.getElementById('timeline');
    timelineBox.innerHTML = '';
    const timelineItems = report.timeline || [];
    for (const item of timelineItems.slice(0, 14)) {
      const div = document.createElement('div');
      div.className = 'timeline-item';
      div.innerHTML = `<strong>${item.title}</strong><div class="muted">${item.ts}</div><div>${item.summary}</div>`;
      timelineBox.appendChild(div);
    }
    const timelineHint = document.getElementById('timeline-hint');
    if (timelineItems.length > 14) {
      timelineHint.innerHTML = `<span class="muted">仅展示前 14 条关键事件，完整事件请看 Run Detail 页面。</span>`;
    } else {
      timelineHint.innerHTML = '';
    }

    const graphSummary = report.graph?.summary || {};
    document.getElementById('graph-summary').innerHTML = `
      <div>finding_count: <span class="badge">${graphSummary.finding_count ?? 0}</span></div>
      <div>final_risk: <span class="badge ${graphSummary.final_risk_level || ''}">${graphSummary.final_risk_level || 'none'}</span></div>
      <div>nodes: ${(report.graph?.nodes || []).length} | edges: ${(report.graph?.edges || []).length}</div>
    `;

    const highlight = document.getElementById('graph-highlight');
    highlight.innerHTML = '';
    for (const path of highlightedPaths) {
      const li = document.createElement('li');
      const rendered = path.map(n => n.includes('risk:') ? `<span class="risk-node">${n}</span>` : n).join(' -> ');
      li.innerHTML = rendered;
      highlight.appendChild(li);
    }

    const riskHitList = document.getElementById('risk-hit-list');
    riskHitList.innerHTML = '';
    for (const hit of findings) {
      const li = document.createElement('li');
      li.innerHTML = `<span class="badge ${hit.risk_level}">${hit.risk_level}</span> <strong>${hit.chain_id}</strong><br><span class="muted">${hit.explanation || ''}</span>`;
      riskHitList.appendChild(li);
    }

    document.getElementById('conclusion').innerHTML = `
      <div>task: <strong>${report.task_summary || '-'}</strong></div>
      <div>semantic: ${report.semantic_summary || '-'}</div>
      <div>disposition: <span class="badge ${report.final_disposition || ''}">${report.final_disposition || 'unknown'}</span></div>
      <div>disposition summary: ${report.disposition_summary || '-'}</div>
      <div style="margin-top:8px;">${report.conclusion}</div>
    `;

    if (hasFinalDisposition(report)) {
      reportStableCycles = Math.min(reportStableCycles + 1, 4);
    } else {
      reportStableCycles = 0;
    }
    succeeded = true;
  } catch (error) {
    console.error('report refresh failed', error);
  } finally {
    if (succeeded) {
      reportErrorCount = 0;
    } else {
      reportErrorCount = Math.min(reportErrorCount + 1, 6);
    }
    reportLoading = false;
    scheduleReportRefresh();
  }
}

document.addEventListener('visibilitychange', scheduleReportRefresh);
document.getElementById('report-refresh-now').addEventListener('click', () => loadReport());
document.getElementById('report-refresh-toggle').addEventListener('click', () => {
  setReportAutoRefresh(!reportAutoRefreshEnabled);
});
renderReportRefreshState();
loadReport();
"""
    script = script_template.replace("__RUN_ID__", run_id)

    return HTMLResponse(content=_shell(f"Audit Report {run_id}", content, script))
