<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import {
  ArrowUpRight,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FileWarning,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Waypoints,
} from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";
import { useRuntimeStore } from "@/stores/runtimeStore";

const store = useRuntimeStore();
const router = useRouter();
const range = ref<"24h" | "7d" | "30d">("24h");
const ranges = ["24h", "7d", "30d"] as const;
const rangeLabels: Record<(typeof ranges)[number], string> = {
  "24h": "24 小时",
  "7d": "7 天",
  "30d": "30 天",
};

const multiplier = computed(() => (range.value === "24h" ? 1 : range.value === "7d" ? 6.4 : 24.8));
const guardedCalls = computed(() => Math.max(1284, Math.round(store.metrics.toolCalls24h * multiplier.value)));
const blockedCalls = computed(() => Math.max(23, Math.round(store.metrics.blocked * multiplier.value)));
const protectionRate = computed(() => `${(99.72 - (range.value === "30d" ? 0.08 : 0)).toFixed(2)}%`);

const threatMix = [
  { label: "敏感凭据访问", value: 84, count: 31, tone: "critical" },
  { label: "外部数据传输", value: 61, count: 22, tone: "high" },
  { label: "高危 Shell 命令", value: 43, count: 16, tone: "medium" },
  { label: "意图偏移", value: 29, count: 9, tone: "low" },
];

const activity = [
  { time: "10:42:18", title: "凭据外传链路已阻断", detail: "read_file → http_post · 薪资泄露演示", risk: "critical" },
  { time: "10:38:04", title: "破坏性命令已转入审批", detail: "shell_exec · 工作区清理", risk: "high" },
  { time: "10:31:47", title: "已关联提示词注入信号", detail: "web_fetch 返回 · 研究 Agent", risk: "medium" },
  { time: "10:25:11", title: "只读工作流已完成", detail: "4 次工具调用 · 来源审查", risk: "safe" },
];

const openRisk = () => router.push("/risk-intelligence");
</script>

<template>
  <ProductPageLayout
    eyebrow="执行指挥中心"
    title="安全总览"
    description="集中展示防护覆盖、活跃威胁与控制平面健康状态。"
  >
    <template #actions>
      <div class="range-switch" aria-label="仪表盘时间范围">
        <button v-for="item in ranges" :key="item" :class="{ active: range === item }" @click="range = item">{{ rangeLabels[item] }}</button>
      </div>
    </template>

    <section class="hero-grid">
      <article class="posture-hero">
        <div class="hero-gridlines" />
        <header>
          <span class="live"><Radio :size="13" /> 实时防护</span>
          <span class="period">{{ rangeLabels[range] }}时间窗</span>
        </header>
        <div class="posture-copy">
          <small>运行时安全态势</small>
          <h2>防护正常</h2>
          <p>所有执行门控均按当前安全基线生效，暂无未处置的严重事件绕过控制。</p>
        </div>
        <div class="hero-stats">
          <div><strong>{{ guardedCalls.toLocaleString() }}</strong><span>已防护调用</span></div>
          <div><strong>{{ blockedCalls }}</strong><span>已阻断操作</span></div>
          <div><strong>18 ms</strong><span>审计中位耗时</span></div>
        </div>
        <ShieldCheck class="hero-shield" :size="190" :stroke-width="0.7" />
      </article>

      <article class="coverage-card">
        <header><span>控制覆盖率</span><Sparkles :size="17" /></header>
        <div class="coverage-ring" :style="{ '--coverage': protectionRate }">
          <div><strong>{{ protectionRate }}</strong><span>已评估</span></div>
        </div>
        <ul>
          <li><i class="ok" /><span>执行前门控</span><b>在线</b></li>
          <li><i class="ok" /><span>证据管线</span><b>健康</b></li>
          <li><i class="warn" /><span>审批队列</span><b>2 项待处理</b></li>
        </ul>
      </article>
    </section>

    <section class="signal-row">
      <article><ShieldAlert :size="18" /><div><small>严重风险信号</small><strong>3</strong></div><span class="down">−18%</span></article>
      <article><Waypoints :size="18" /><div><small>风险路径</small><strong>12</strong></div><span>4 条多步骤</span></article>
      <article><Clock3 :size="18" /><div><small>待审批</small><strong>2</strong></div><span>最久 4 分钟</span></article>
      <article><CheckCircle2 :size="18" /><div><small>策略覆盖率</small><strong>96%</strong></div><span>28 项生效</span></article>
    </section>

    <section class="lower-grid">
      <article class="threat-card">
        <header>
          <div><small>行为观测</small><h3>威胁构成</h3></div>
          <button @click="openRisk">查看风险情报 <ArrowUpRight :size="13" /></button>
        </header>
        <div class="threat-content">
          <div class="bars">
            <div v-for="threat in threatMix" :key="threat.label" class="bar-row">
              <span>{{ threat.label }}</span>
              <div><i :class="threat.tone" :style="{ width: `${threat.value}%` }" /></div>
              <b>{{ threat.count }}</b>
            </div>
          </div>
          <div class="insight">
            <FileWarning :size="19" />
            <small>重点发现</small>
            <strong>敏感文件访问后出现外部网络传输意图</strong>
            <p>已在 4 次 Agent 运行中关联发现 7 条风险路径。</p>
          </div>
        </div>
      </article>

      <article class="activity-card">
        <header><div><small>最新决策</small><h3>实时防护动态</h3></div><span><i /> 实时更新</span></header>
        <button v-for="item in activity" :key="item.time" @click="router.push('/runtime')">
          <time>{{ item.time }}</time>
          <i :class="`event-${item.risk}`" />
          <span><strong>{{ item.title }}</strong><small>{{ item.detail }}</small></span>
          <ChevronRight :size="14" />
        </button>
      </article>
    </section>
  </ProductPageLayout>
</template>

<style scoped>
.range-switch{display:flex;padding:3px;border:1px solid var(--trace-border);border-radius:10px;background:#fff}.range-switch button{padding:7px 11px;border:0;border-radius:7px;color:#7a8695;background:transparent;font-size:9px;cursor:pointer}.range-switch button.active{color:#fff;background:#263141;box-shadow:0 3px 9px rgba(30,41,59,.17)}
.hero-grid{display:grid;grid-template-columns:minmax(600px,2fr) minmax(270px,.72fr);gap:12px}.posture-hero{position:relative;min-height:263px;padding:21px 24px;overflow:hidden;border-radius:19px;color:#fff;background:radial-gradient(circle at 82% 8%,rgba(232,93,111,.29),transparent 31%),linear-gradient(130deg,#151d29 0%,#242d3b 60%,#321d26 100%);box-shadow:0 18px 42px rgba(25,31,42,.17)}.hero-gridlines{position:absolute;inset:0;opacity:.1;background-image:linear-gradient(rgba(255,255,255,.15) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.15) 1px,transparent 1px);background-size:36px 36px;mask-image:linear-gradient(90deg,#000,transparent 80%)}.posture-hero header{position:relative;z-index:1;display:flex;justify-content:space-between}.live,.period{display:flex;align-items:center;gap:6px;font:8px var(--trace-font-mono);letter-spacing:.06em;text-transform:uppercase}.live{padding:6px 8px;border:1px solid rgba(255,255,255,.15);border-radius:999px;color:#b9f5df;background:rgba(21,132,102,.17)}.period{color:#aab4c1}.posture-copy{position:relative;z-index:1;width:59%;margin-top:28px}.posture-copy small{color:#aab4c1;font-size:8px;letter-spacing:.1em;text-transform:uppercase}.posture-copy h2{margin:5px 0 8px;font-size:39px;letter-spacing:-.05em}.posture-copy p{margin:0;color:#b4bdc9;font-size:9px;line-height:1.65}.hero-stats{position:absolute;z-index:2;right:23px;bottom:21px;left:24px;display:flex;gap:35px}.hero-stats div{display:flex;flex-direction:column}.hero-stats strong{font:650 16px var(--trace-font-mono)}.hero-stats span{margin-top:3px;color:#99a5b4;font-size:7px;text-transform:uppercase}.hero-shield{position:absolute;right:20px;top:38px;color:rgba(255,255,255,.1);filter:drop-shadow(0 0 28px rgba(232,93,111,.18))}
.coverage-card{padding:17px;border:1px solid var(--trace-border);border-radius:19px;background:#fff;box-shadow:var(--trace-shadow)}.coverage-card>header{display:flex;justify-content:space-between;color:#697587;font-size:9px;font-weight:700}.coverage-card header svg{color:var(--trace-red)}.coverage-ring{position:relative;isolation:isolate;display:grid;place-items:center;width:128px;height:128px;margin:14px auto 13px;border-radius:50%;background:conic-gradient(var(--trace-red) 0 var(--coverage),#edf0f2 var(--coverage) 100%);box-shadow:inset 0 0 0 1px rgba(201,31,55,.04)}.coverage-ring:before{position:absolute;inset:13px;border-radius:50%;background:#fff;content:"";pointer-events:none}.coverage-ring div{position:relative;z-index:1;text-align:center}.coverage-ring strong,.coverage-ring span{display:block}.coverage-ring strong{font:700 18px var(--trace-font-mono)}.coverage-ring span{margin-top:3px;color:#8b96a4;font-size:7px;text-transform:uppercase}.coverage-card ul{padding:0;margin:0;list-style:none}.coverage-card li{display:grid;grid-template-columns:8px 1fr auto;align-items:center;gap:7px;padding:7px 2px;border-top:1px solid #edf0f2;font-size:8px}.coverage-card li i{width:6px;height:6px;border-radius:50%}.coverage-card li .ok{background:var(--trace-success)}.coverage-card li .warn{background:var(--trace-warning)}.coverage-card li span{color:#6f7b8b}.coverage-card li b{font:600 7px var(--trace-font-mono)}
.signal-row{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:12px 0}.signal-row article{display:grid;grid-template-columns:30px 1fr auto;align-items:center;gap:9px;padding:12px 14px;border:1px solid var(--trace-border);border-radius:12px;background:#fff}.signal-row svg{color:#7c8796}.signal-row small,.signal-row strong{display:block}.signal-row small{color:#8c96a3;font-size:7px;text-transform:uppercase}.signal-row strong{margin-top:2px;font:650 15px var(--trace-font-mono)}.signal-row article>span{align-self:end;color:#8b95a2;font-size:7px}.signal-row article>span.down{color:var(--trace-success)}
.lower-grid{display:grid;grid-template-columns:minmax(570px,1.35fr) minmax(390px,1fr);gap:12px}.threat-card,.activity-card{overflow:hidden;border:1px solid var(--trace-border);border-radius:15px;background:#fff;box-shadow:0 8px 24px rgba(30,41,59,.04)}.threat-card>header,.activity-card>header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #e9ecef}.threat-card header small,.activity-card header small{color:#929ca9;font-size:7px;text-transform:uppercase}.threat-card h3,.activity-card h3{margin:3px 0 0;font-size:12px}.threat-card header button{display:flex;align-items:center;gap:5px;border:0;color:var(--trace-red);background:none;font-size:8px;font-weight:700;cursor:pointer}.threat-content{display:grid;grid-template-columns:1fr 190px;gap:20px;padding:18px 16px}.bars{display:grid;gap:12px}.bar-row{display:grid;grid-template-columns:95px 1fr 20px;align-items:center;gap:9px}.bar-row>span{color:#687587;font-size:8px}.bar-row>div{height:7px;border-radius:6px;background:#edf0f2;overflow:hidden}.bar-row i{display:block;height:100%;border-radius:6px;background:#8491a1}.bar-row i.critical{background:var(--trace-red)}.bar-row i.high{background:#e76a58}.bar-row i.medium{background:#d79a32}.bar-row b{font:600 8px var(--trace-font-mono)}.insight{padding:13px;border:1px solid #f0d9dc;border-radius:11px;background:#fff8f7}.insight svg{color:var(--trace-red)}.insight small,.insight strong{display:block}.insight small{margin-top:8px;color:var(--trace-red);font-size:7px;text-transform:uppercase}.insight strong{margin-top:4px;font-size:9px;line-height:1.4}.insight p{margin:6px 0 0;color:#7e8998;font-size:7px;line-height:1.5}.activity-card>header>span{display:flex;align-items:center;gap:6px;color:#718091;font:7px var(--trace-font-mono)}.activity-card>header>span i{width:6px;height:6px;border-radius:50%;background:var(--trace-success);animation:pulse 2s infinite}.activity-card>button{display:grid;grid-template-columns:55px 6px 1fr 14px;align-items:center;gap:9px;width:100%;padding:10px 14px;border:0;border-bottom:1px solid #edf0f2;text-align:left;background:#fff;cursor:pointer}.activity-card>button:hover{background:#fafafa}.activity-card time{color:#919ba8;font:7px var(--trace-font-mono)}.activity-card button>i{width:6px;height:6px;border-radius:50%;background:#8fa0ad}.activity-card .event-critical,.activity-card .event-high{background:var(--trace-red)}.activity-card .event-medium{background:var(--trace-warning)}.activity-card .event-safe{background:var(--trace-success)}.activity-card button span{min-width:0}.activity-card button strong,.activity-card button small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.activity-card button strong{font-size:8px}.activity-card button small{margin-top:4px;color:#8994a2;font-size:7px}.activity-card button svg{color:#a1aab4}@keyframes pulse{50%{box-shadow:0 0 0 5px rgba(21,132,102,0)}}
@media(max-width:1250px){.hero-grid{grid-template-columns:1fr 275px}.lower-grid{grid-template-columns:1fr}.threat-content{grid-template-columns:1fr 210px}}
</style>
