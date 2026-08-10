<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Activity,
  ArrowUpRight,
  Bot,
  ChevronRight,
  Crosshair,
  Database,
  Eye,
  FileKey2,
  Globe2,
  Radar,
  ShieldAlert,
  ShieldCheck,
  SquareTerminal,
  TrendingUp,
} from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";

type RiskCell = {
  id: string;
  impact: number;
  likelihood: number;
  count: number;
  label: string;
};

const timeRanges = ["24 hours", "7 days", "30 days"];
const activeRange = ref("24 hours");
const likelihoodLabels = ["Rare", "Unlikely", "Possible", "Likely", "Certain"];
const impactLabels = ["Critical", "High", "Moderate", "Low", "Minimal"];
const signalNames = [
  "Credential access",
  "Untrusted network egress",
  "Destructive command",
  "Sensitive file discovery",
  "Prompt injection",
  "Privilege expansion",
  "Unknown tool behavior",
];

const riskCells: RiskCell[] = Array.from({ length: 25 }, (_, index) => {
  const row = Math.floor(index / 5);
  const likelihood = (index % 5) + 1;
  const impact = 5 - row;
  const weight = impact * likelihood;
  const count = weight > 18 ? weight - 13 : weight > 10 ? weight - 7 : weight > 5 ? weight - 4 : 0;
  return {
    id: `${impact}-${likelihood}`,
    impact,
    likelihood,
    count,
    label: signalNames[(impact * 2 + likelihood) % signalNames.length] ?? "Runtime anomaly",
  };
});

const selectedCell = ref<RiskCell>(riskCells.find((cell) => cell.id === "5-4") ?? riskCells[0]!);
const selectedScenario = ref("chain-01");

const matrixSummary = computed(() => {
  const impact = impactLabels[5 - selectedCell.value.impact] ?? "Unknown";
  const likelihood = likelihoodLabels[selectedCell.value.likelihood - 1] ?? "Unknown";
  return `${impact} impact · ${likelihood.toLowerCase()}`;
});

const postureMetrics = [
  { label: "Active signals", value: "18", delta: "+4", icon: Radar },
  { label: "Critical paths", value: "3", delta: "+1", icon: Crosshair },
  { label: "Protected runs", value: "1,284", delta: "98.7%", icon: ShieldCheck },
];

const exposures = [
  { name: "Secrets → external network", detail: "2 correlated runs", value: 91, tone: "critical" },
  { name: "Shell → privileged file", detail: "5 policy intersections", value: 76, tone: "high" },
  { name: "Injected tool observation", detail: "11 suspicious results", value: 58, tone: "medium" },
  { name: "Unknown tool invocation", detail: "7 first-seen tools", value: 34, tone: "low" },
];

const scenarios = [
  { id: "chain-01", label: "Credential exfiltration", score: 94 },
  { id: "chain-02", label: "Destructive workspace", score: 82 },
  { id: "chain-03", label: "Indirect injection", score: 67 },
];

const chainNodes = [
  { step: "01", title: "Prompt received", detail: "Invoice review request", state: "observed", icon: Bot },
  { step: "02", title: "File discovery", detail: "read_file · .env", state: "risk", icon: FileKey2 },
  { step: "03", title: "Secret acquired", detail: "Credential pattern found", state: "critical", icon: Database },
  { step: "04", title: "Egress attempt", detail: "POST · unknown host", state: "critical", icon: Globe2 },
  { step: "05", title: "Execution stopped", detail: "Blocked in 38 ms", state: "safe", icon: ShieldCheck },
];

function cellTone(cell: RiskCell) {
  const score = cell.impact * cell.likelihood;
  if (score >= 20) return "critical";
  if (score >= 12) return "high";
  if (score >= 6) return "medium";
  return "low";
}
</script>

<template>
  <ProductPageLayout
    eyebrow="威胁情报"
    title="风险情报"
    description="定位 Agent 行为中的风险集中区域，并追踪其背后的攻击路径。"
  >
    <template #actions>
      <div class="range-switch" aria-label="Risk intelligence time range">
        <button
          v-for="range in timeRanges"
          :key="range"
          :class="{ active: activeRange === range }"
          @click="activeRange = range"
        >
          {{ range }}
        </button>
      </div>
    </template>

    <section class="posture-deck">
      <div class="posture-score">
        <div class="score-copy">
          <span><Activity :size="14" /> Live posture</span>
          <strong>Elevated</strong>
          <p>Three high-confidence attack paths need attention across two active agents.</p>
        </div>
        <div class="score-orbit" aria-label="Risk score 72 out of 100">
          <div><b>72</b><small>/ 100</small></div>
          <i class="orbit-dot" />
        </div>
      </div>

      <div class="trend-panel">
        <header>
          <div><small>Risk velocity</small><strong>+12.4%</strong></div>
          <span><TrendingUp :size="13" /> since yesterday</span>
        </header>
        <svg viewBox="0 0 420 92" preserveAspectRatio="none" role="img" aria-label="Risk velocity trend">
          <defs>
            <linearGradient id="riskArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stop-color="#e85d6f" stop-opacity=".42" />
              <stop offset="1" stop-color="#e85d6f" stop-opacity="0" />
            </linearGradient>
          </defs>
          <path class="trend-grid" d="M0 18H420M0 46H420M0 74H420" />
          <path class="trend-area" d="M0 76 C30 74 38 53 70 58 S120 69 150 51 S202 33 233 46 S285 65 316 32 S374 25 420 8 V92 H0 Z" />
          <path class="trend-line" d="M0 76 C30 74 38 53 70 58 S120 69 150 51 S202 33 233 46 S285 65 316 32 S374 25 420 8" />
          <circle cx="420" cy="8" r="4" />
        </svg>
        <div class="trend-axis"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>Now</span></div>
      </div>

      <div class="metric-stack">
        <article v-for="metric in postureMetrics" :key="metric.label">
          <span class="metric-icon"><component :is="metric.icon" :size="15" /></span>
          <div><small>{{ metric.label }}</small><strong>{{ metric.value }}</strong></div>
          <em>{{ metric.delta }}</em>
        </article>
      </div>
    </section>

    <section class="intelligence-grid">
      <article class="heatmap-card">
        <header class="section-heading">
          <div><small>Exposure distribution</small><h2>Risk heatmap</h2></div>
          <span><Eye :size="13" /> {{ activeRange }}</span>
        </header>
        <div class="heatmap-layout">
          <div class="impact-title">Impact</div>
          <div class="impact-labels">
            <span v-for="label in impactLabels" :key="label">{{ label }}</span>
          </div>
          <div class="heatmap">
            <button
              v-for="cell in riskCells"
              :key="cell.id"
              :class="[cellTone(cell), { selected: selectedCell.id === cell.id }]"
              :aria-label="`${cell.label}, ${cell.count} signals`"
              @click="selectedCell = cell"
            >
              <strong v-if="cell.count">{{ cell.count }}</strong>
              <span v-else>·</span>
            </button>
          </div>
          <div class="likelihood-labels">
            <span v-for="label in likelihoodLabels" :key="label">{{ label }}</span>
          </div>
          <div class="likelihood-title">Likelihood</div>
        </div>
        <footer class="matrix-detail">
          <span class="detail-indicator" :class="cellTone(selectedCell)" />
          <div><small>Selected cluster · {{ matrixSummary }}</small><strong>{{ selectedCell.label }}</strong></div>
          <b>{{ selectedCell.count }} signals</b>
          <ArrowUpRight :size="15" />
        </footer>
      </article>

      <aside class="exposure-card">
        <header class="section-heading">
          <div><small>Prioritized</small><h2>Top exposures</h2></div>
          <ShieldAlert :size="19" />
        </header>
        <div class="exposure-list">
          <article v-for="(exposure, index) in exposures" :key="exposure.name">
            <span class="rank">0{{ index + 1 }}</span>
            <div class="exposure-copy">
              <strong>{{ exposure.name }}</strong><small>{{ exposure.detail }}</small>
              <div class="risk-bar"><i :class="exposure.tone" :style="{ width: `${exposure.value}%` }" /></div>
            </div>
            <b>{{ exposure.value }}</b>
          </article>
        </div>
        <button class="watch-button"><Crosshair :size="14" /> Open watchlist <ChevronRight :size="14" /></button>
      </aside>
    </section>

    <section class="attack-card">
      <header class="section-heading attack-heading">
        <div><small>Correlated behavior</small><h2>Attack chain reconstruction</h2></div>
        <div class="scenario-tabs">
          <button
            v-for="scenario in scenarios"
            :key="scenario.id"
            :class="{ active: selectedScenario === scenario.id }"
            @click="selectedScenario = scenario.id"
          >
            {{ scenario.label }} <b>{{ scenario.score }}</b>
          </button>
        </div>
      </header>
      <div class="chain-context">
        <span><i /> RUN-7A2F · agent-finance-02</span>
        <span>MITRE mapping · T1552 → T1041</span>
        <strong><ShieldAlert :size="13" /> Critical confidence</strong>
      </div>
      <div class="attack-chain">
        <template v-for="(node, index) in chainNodes" :key="node.step">
          <article :class="node.state">
            <small>{{ node.step }}</small>
            <span><component :is="node.icon" :size="18" /></span>
            <div><strong>{{ node.title }}</strong><p>{{ node.detail }}</p></div>
          </article>
          <div v-if="index < chainNodes.length - 1" class="chain-link"><i /><ChevronRight :size="14" /></div>
        </template>
      </div>
      <footer>
        <div><SquareTerminal :size="14" /><span>Decision evidence</span><code>deny_sensitive_file_pattern + exfiltration_path</code></div>
        <button>Inspect full trace <ArrowUpRight :size="14" /></button>
      </footer>
    </section>
  </ProductPageLayout>
</template>

<style scoped>
.range-switch{display:flex;padding:3px;border:1px solid var(--trace-border);border-radius:11px;background:#fff;box-shadow:0 5px 14px rgba(30,41,59,.04)}.range-switch button{padding:7px 10px;border:0;border-radius:8px;color:#778395;background:transparent;font-size:9px;cursor:pointer;transition:color 150ms ease,background-color 150ms ease}.range-switch button.active{color:#fff;background:var(--trace-ink);box-shadow:0 4px 10px rgba(24,32,43,.18)}
.posture-deck{display:grid;grid-template-columns:minmax(320px,.92fr) minmax(370px,1.2fr) minmax(240px,.72fr);gap:10px;margin-bottom:11px}.posture-score,.trend-panel,.metric-stack{border-radius:16px}.posture-score{position:relative;display:flex;align-items:center;justify-content:space-between;min-height:166px;padding:22px;overflow:hidden;color:#fff;background:linear-gradient(135deg,#171e29 0%,#29212a 58%,#481f29 100%);box-shadow:0 15px 34px rgba(24,32,43,.16)}.posture-score::before{position:absolute;right:-55px;top:-85px;width:245px;height:245px;border:1px solid rgba(255,255,255,.07);border-radius:50%;box-shadow:0 0 0 28px rgba(255,255,255,.025),0 0 0 61px rgba(255,255,255,.018);content:""}.score-copy{position:relative;z-index:1;max-width:190px}.score-copy>span{display:flex;align-items:center;gap:6px;color:#f5a6b1;font-size:8px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}.score-copy>strong{display:block;margin-top:12px;font-size:27px;letter-spacing:-.04em}.score-copy p{margin:7px 0 0;color:#bdc4ce;font-size:9px;line-height:1.6}.score-orbit{position:relative;display:grid;place-items:center;width:112px;height:112px;flex:0 0 112px;border-radius:50%;background:conic-gradient(var(--trace-red-soft) 0 72%,rgba(255,255,255,.09) 72% 100%);box-shadow:0 0 34px rgba(232,93,111,.15)}.score-orbit::before{position:absolute;inset:7px;border-radius:50%;background:#29212a;content:""}.score-orbit div{position:relative;text-align:center}.score-orbit b{display:block;font:700 29px var(--trace-font-mono)}.score-orbit small{color:#aeb7c3;font-size:8px}.orbit-dot{position:absolute;right:15px;bottom:18px;width:8px;height:8px;border:2px solid #29212a;border-radius:50%;background:#fff}
.trend-panel{padding:17px 18px;border:1px solid #343c48;color:#fff;background:#202833;box-shadow:0 12px 28px rgba(30,41,59,.11)}.trend-panel header{display:flex;align-items:flex-start;justify-content:space-between}.trend-panel header small,.trend-panel header strong{display:block}.trend-panel header small{color:#9ea9b8;font-size:8px;text-transform:uppercase;letter-spacing:.08em}.trend-panel header strong{margin-top:4px;font:650 19px var(--trace-font-mono)}.trend-panel header span{display:flex;align-items:center;gap:5px;padding:5px 7px;border-radius:7px;color:#f19ca8;background:rgba(201,31,55,.13);font-size:8px}.trend-panel svg{width:100%;height:73px;margin-top:4px;overflow:visible}.trend-grid{fill:none;stroke:rgba(255,255,255,.06);stroke-width:1}.trend-area{fill:url(#riskArea)}.trend-line{fill:none;stroke:#ef7787;stroke-width:2.2;vector-effect:non-scaling-stroke}.trend-panel circle{fill:#fff;stroke:#ef7787;stroke-width:3}.trend-axis{display:flex;justify-content:space-between;color:#758193;font:7px var(--trace-font-mono)}
.metric-stack{display:grid;gap:1px;overflow:hidden;border:1px solid var(--trace-border);background:var(--trace-border);box-shadow:0 8px 22px rgba(30,41,59,.04)}.metric-stack article{display:grid;grid-template-columns:32px 1fr auto;align-items:center;gap:9px;padding:11px 12px;background:#fff}.metric-icon{display:grid;place-items:center;width:31px;height:31px;border-radius:9px;color:var(--trace-red);background:#fff0f1}.metric-stack small,.metric-stack strong{display:block}.metric-stack small{color:#8994a2;font-size:7px;text-transform:uppercase}.metric-stack strong{margin-top:2px;font:650 14px var(--trace-font-mono)}.metric-stack em{color:#657184;font:normal 7px var(--trace-font-mono)}
.intelligence-grid{display:grid;grid-template-columns:minmax(600px,1.58fr) minmax(310px,.72fr);gap:10px;margin-bottom:11px}.heatmap-card,.exposure-card,.attack-card{border:1px solid var(--trace-border);border-radius:15px;background:#fff;box-shadow:0 8px 22px rgba(30,41,59,.04)}.heatmap-card,.exposure-card{padding:17px}.section-heading{display:flex;align-items:center;justify-content:space-between}.section-heading small{color:var(--trace-red);font-size:7px;font-weight:700;text-transform:uppercase;letter-spacing:.1em}.section-heading h2{margin:4px 0 0;font-size:14px}.section-heading>span{display:flex;align-items:center;gap:5px;color:#8994a1;font-size:8px}.exposure-card>.section-heading>svg{color:#a8b1bc}
.heatmap-layout{display:grid;grid-template-columns:16px 60px minmax(0,1fr);grid-template-rows:1fr 22px 14px;gap:0 8px;margin-top:15px}.impact-title{display:grid;place-items:center;grid-row:1;grid-column:1;color:#9aa4b0;font-size:7px;text-transform:uppercase;letter-spacing:.12em;writing-mode:vertical-rl;transform:rotate(180deg)}.impact-labels{display:grid;grid-row:1;grid-column:2;grid-template-rows:repeat(5,1fr);align-items:center;color:#788596;font-size:7px}.heatmap{display:grid;grid-row:1;grid-column:3;grid-template-columns:repeat(5,1fr);gap:5px}.heatmap button{position:relative;min-height:34px;border:1px solid transparent;border-radius:7px;color:#607083;cursor:pointer;transition:transform 150ms ease,box-shadow 150ms ease,border-color 150ms ease}.heatmap button:hover{z-index:1;transform:scale(1.04)}.heatmap button.low{background:#edf3f1}.heatmap button.medium{color:#8e620f;background:#f8e9bd}.heatmap button.high{color:#9c3e35;background:#f4b9ae}.heatmap button.critical{color:#fff;background:linear-gradient(145deg,#d94b5f,#ad172e);box-shadow:inset 0 0 0 1px rgba(255,255,255,.13)}.heatmap button.selected{border-color:#17202b;box-shadow:0 0 0 2px #fff,0 0 0 3px #17202b}.heatmap button strong{font:650 9px var(--trace-font-mono)}.likelihood-labels{display:grid;grid-row:2;grid-column:3;grid-template-columns:repeat(5,1fr);align-items:end;color:#788596;font-size:7px;text-align:center}.likelihood-title{grid-row:3;grid-column:3;color:#9aa4b0;font-size:7px;text-align:center;text-transform:uppercase;letter-spacing:.12em}.matrix-detail{display:grid;grid-template-columns:8px 1fr auto 16px;align-items:center;gap:9px;margin-top:12px;padding:10px 11px;border:1px solid #e7eaed;border-radius:10px;background:#fafbfb}.detail-indicator{width:5px;height:31px;border-radius:5px;background:#8fa09c}.detail-indicator.medium{background:#d9ad4a}.detail-indicator.high{background:#e47f70}.detail-indicator.critical{background:var(--trace-red)}.matrix-detail small,.matrix-detail strong{display:block}.matrix-detail small{color:#8b96a4;font-size:7px}.matrix-detail strong{margin-top:3px;font-size:9px}.matrix-detail>b{font:650 8px var(--trace-font-mono)}.matrix-detail>svg{color:#9da7b2}
.exposure-list{display:grid;margin-top:9px}.exposure-list article{display:grid;grid-template-columns:22px 1fr 25px;gap:8px;padding:11px 0;border-bottom:1px solid #edf0f2}.rank{color:#adb5bf;font:7px var(--trace-font-mono)}.exposure-copy strong,.exposure-copy small{display:block}.exposure-copy strong{font-size:9px}.exposure-copy small{margin-top:3px;color:#8792a0;font-size:7px}.risk-bar{height:3px;margin-top:8px;overflow:hidden;border-radius:3px;background:#edf0f2}.risk-bar i{display:block;height:100%;border-radius:3px;background:#8da99f}.risk-bar i.medium{background:#d7aa45}.risk-bar i.high{background:#e27569}.risk-bar i.critical{background:var(--trace-red)}.exposure-list article>b{align-self:center;color:#657184;font:650 9px var(--trace-font-mono)}.watch-button{display:flex;align-items:center;justify-content:center;gap:7px;width:100%;margin-top:11px;padding:8px;border:1px solid #dee3e7;border-radius:9px;background:#fff;font-size:8px;cursor:pointer}.watch-button svg:last-child{margin-left:auto}
.attack-card{overflow:hidden}.attack-heading{padding:16px 17px 12px}.scenario-tabs{display:flex;gap:4px}.scenario-tabs button{padding:6px 8px;border:1px solid #e3e7ea;border-radius:8px;color:#748092;background:#fff;font-size:7px;cursor:pointer}.scenario-tabs button b{margin-left:5px;font:700 7px var(--trace-font-mono)}.scenario-tabs button.active{border-color:#dfb6bc;color:var(--trace-red-deep);background:#fff5f4}.chain-context{display:flex;gap:22px;padding:8px 17px;color:#7a8797;background:#f5f6f7;font:7px var(--trace-font-mono)}.chain-context span:first-child{display:flex;align-items:center}.chain-context span:first-child i{width:6px;height:6px;margin-right:6px;border-radius:50%;background:var(--trace-success);box-shadow:0 0 0 3px rgba(21,132,102,.1)}.chain-context strong{display:flex;align-items:center;gap:5px;margin-left:auto;color:var(--trace-red);font:650 7px var(--trace-font-sans)}.attack-chain{display:flex;align-items:center;padding:19px 17px}.attack-chain article{display:grid;grid-template-columns:34px 1fr;grid-template-rows:auto auto;align-items:center;min-width:150px;flex:1}.attack-chain article>small{grid-column:1/3;margin-bottom:7px;color:#a1aab5;font:7px var(--trace-font-mono)}.attack-chain article>span{display:grid;place-items:center;width:31px;height:31px;border:1px solid #dce2e5;border-radius:9px;color:#6e7c8d;background:#f6f8f8}.attack-chain article.risk>span{border-color:#ead7b4;color:#a46d0b;background:#fff7e9}.attack-chain article.critical>span{border-color:#efc2c8;color:var(--trace-red);background:#fff0f1}.attack-chain article.safe>span{border-color:#cce6de;color:var(--trace-success);background:#ecf8f4}.attack-chain article strong{font-size:9px}.attack-chain article p{margin:3px 0 0;color:#8792a0;font-size:7px;white-space:nowrap}.chain-link{display:flex;align-items:center;width:32px;flex:0 0 32px;margin:16px 4px 0;color:#a8b1bc}.chain-link i{height:1px;flex:1;background:#d9dfe3}.attack-card>footer{display:flex;align-items:center;justify-content:space-between;padding:10px 17px;border-top:1px solid #e9ecef;background:#fafbfb}.attack-card>footer div{display:flex;align-items:center;gap:7px;color:#7f8b9a;font-size:8px}.attack-card>footer code{color:#697688;font-size:7px}.attack-card>footer button{display:flex;align-items:center;gap:6px;border:0;color:var(--trace-red);background:transparent;font-size:8px;font-weight:700;cursor:pointer}
@media (max-width:1280px){.posture-deck{grid-template-columns:1fr 1fr}.metric-stack{grid-column:1/3;grid-template-columns:repeat(3,1fr)}.intelligence-grid{grid-template-columns:1fr}.exposure-list{grid-template-columns:repeat(2,1fr);column-gap:20px}.attack-chain article{min-width:130px}.scenario-tabs button{font-size:6px}}
</style>
