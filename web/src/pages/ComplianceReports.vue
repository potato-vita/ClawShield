<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Archive,
  ArrowUpRight,
  BookOpenCheck,
  CalendarDays,
  Check,
  CircleCheckBig,
  ClipboardCheck,
  Clock3,
  Download,
  FileDown,
  FileText,
  Fingerprint,
  LockKeyhole,
  RefreshCw,
  ShieldCheck,
  Users,
} from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";

type FrameworkKey = "SOC 2" | "ISO 27001" | "NIST AI RMF";

type ExportRecord = {
  id: string;
  name: string;
  format: string;
  scope: string;
  generated: string;
  owner: string;
  size: string;
};

const frameworks: FrameworkKey[] = ["SOC 2", "ISO 27001", "NIST AI RMF"];
const activeFramework = ref<FrameworkKey>("SOC 2");
const generating = ref(false);
const notice = ref("");

const frameworkData: Record<FrameworkKey, { score: number; controls: number; evidence: number; period: string }> = {
  "SOC 2": { score: 92, controls: 48, evidence: 1264, period: "Q3 2026" },
  "ISO 27001": { score: 87, controls: 39, evidence: 948, period: "2026 annual" },
  "NIST AI RMF": { score: 84, controls: 32, evidence: 817, period: "H2 2026" },
};

const selectedData = computed(() => frameworkData[activeFramework.value]);

const coverage = [
  { family: "Access control", code: "CC6", covered: 12, total: 12, evidence: 364, owner: "Security", icon: LockKeyhole },
  { family: "System operations", code: "CC7", covered: 9, total: 10, evidence: 281, owner: "Platform", icon: RefreshCw },
  { family: "Change management", code: "CC8", covered: 7, total: 8, evidence: 196, owner: "Engineering", icon: ClipboardCheck },
  { family: "Risk mitigation", code: "CC9", covered: 8, total: 9, evidence: 247, owner: "GRC", icon: ShieldCheck },
  { family: "Confidentiality", code: "C1", covered: 6, total: 6, evidence: 176, owner: "Security", icon: Fingerprint },
];

const reportSections = [
  { id: "01", title: "Executive summary", status: "complete", pages: "2 pages" },
  { id: "02", title: "Control coverage", status: "complete", pages: "8 pages" },
  { id: "03", title: "Runtime evidence", status: "complete", pages: "24 pages" },
  { id: "04", title: "Exceptions & remediation", status: "review", pages: "4 pages" },
];

const attestations = [
  { date: "12", month: "AUG", title: "Quarterly access review", owner: "Lin Chen", state: "Due in 4 days" },
  { date: "18", month: "AUG", title: "Evidence owner sign-off", owner: "Maya Rao", state: "Due in 10 days" },
  { date: "02", month: "SEP", title: "External auditor handoff", owner: "Audit team", state: "Scheduled" },
];

const exports = ref<ExportRecord[]>([
  { id: "EXP-0482", name: "SOC 2 readiness package", format: "PDF + CSV", scope: "Full organization", generated: "Today, 09:42", owner: "Maya Rao", size: "8.4 MB" },
  { id: "EXP-0479", name: "Runtime evidence archive", format: "JSONL", scope: "Finance agents", generated: "Yesterday, 16:18", owner: "Lin Chen", size: "24.1 MB" },
  { id: "EXP-0474", name: "Control exceptions", format: "CSV", scope: "Open findings", generated: "Aug 05, 11:08", owner: "Sam Lee", size: "164 KB" },
  { id: "EXP-0468", name: "ISO 27001 evidence index", format: "PDF", scope: "Annual review", generated: "Aug 01, 14:23", owner: "Maya Rao", size: "5.7 MB" },
]);

function showNotice(message: string) {
  notice.value = message;
  window.setTimeout(() => {
    if (notice.value === message) notice.value = "";
  }, 2400);
}

function generateReport() {
  if (generating.value) return;
  generating.value = true;
  window.setTimeout(() => {
    exports.value.unshift({
      id: `EXP-${String(483 + exports.value.length).padStart(4, "0")}`,
      name: `${activeFramework.value} evidence package`,
      format: "PDF + CSV",
      scope: selectedData.value.period,
      generated: "Just now",
      owner: "Demo user",
      size: "Preparing",
    });
    generating.value = false;
    showNotice(`${activeFramework.value} report generated for the demo`);
  }, 650);
}
</script>

<template>
  <ProductPageLayout
    eyebrow="审计保障工作台"
    title="合规报告"
    description="将运行时审计证据整理为面向审计人员的控制说明与导出材料。"
  >
    <template #actions>
      <div class="report-actions">
        <label>
          <span>Framework</span>
          <select v-model="activeFramework">
            <option v-for="framework in frameworks" :key="framework">{{ framework }}</option>
          </select>
        </label>
        <button @click="generateReport"><RefreshCw v-if="generating" class="spin" :size="14" /><FileDown v-else :size="14" />{{ generating ? "Generating…" : "Generate report" }}</button>
      </div>
    </template>

    <div v-if="notice" class="toast"><CircleCheckBig :size="15" />{{ notice }}</div>

    <section class="assurance-banner">
      <div class="assurance-copy">
        <span class="status-pill"><ShieldCheck :size="13" /> Audit ready</span>
        <h2>{{ activeFramework }} evidence book</h2>
        <p>{{ selectedData.period }} reporting period · Evidence refreshed 6 minutes ago</p>
        <div class="framework-tabs">
          <button v-for="framework in frameworks" :key="framework" :class="{ active: activeFramework === framework }" @click="activeFramework = framework">{{ framework }}</button>
        </div>
      </div>
      <div class="readiness-score" :style="{ '--score': `${selectedData.score * 3.6}deg` }">
        <div><strong>{{ selectedData.score }}%</strong><small>readiness</small></div>
      </div>
      <dl>
        <div><dt>Mapped controls</dt><dd>{{ selectedData.controls }}</dd></div>
        <div><dt>Evidence items</dt><dd>{{ selectedData.evidence.toLocaleString() }}</dd></div>
        <div><dt>Open exceptions</dt><dd class="warning">4</dd></div>
        <div><dt>Evidence freshness</dt><dd>99.2%</dd></div>
      </dl>
    </section>

    <section class="report-workspace">
      <article class="report-paper">
        <div class="paper-topline">
          <span>TRACESHIELD / ASSURANCE</span><code>REPORT TS-SOC2-Q3-026</code>
        </div>
        <header>
          <div class="document-mark"><BookOpenCheck :size="21" /></div>
          <div><small>Draft for management review</small><h2>Runtime Security &amp;<br />Controls Report</h2><p>{{ activeFramework }} · {{ selectedData.period }}</p></div>
          <span class="confidential">Confidential</span>
        </header>
        <div class="paper-rule" />
        <section class="executive-note">
          <span>01</span>
          <div><small>EXECUTIVE CONCLUSION</small><p>TraceShield's runtime controls operated effectively throughout the review window. No material exceptions were identified in protected agent execution paths.</p></div>
          <strong><Check :size="15" /> Effective</strong>
        </section>
        <div class="document-sections">
          <article v-for="section in reportSections" :key="section.id">
            <span>{{ section.id }}</span>
            <div><strong>{{ section.title }}</strong><small>{{ section.pages }}</small></div>
            <b :class="section.status"><Check v-if="section.status === 'complete'" :size="11" />{{ section.status === "complete" ? "Complete" : "Needs review" }}</b>
          </article>
        </div>
        <footer>
          <div class="signature"><span>Prepared by</span><strong>TraceShield Assurance</strong><small>Automated evidence compilation</small></div>
          <div class="signature"><span>Review owner</span><strong>Maya Rao</strong><small>Head of Security &amp; Trust</small></div>
          <div class="page-number">01 <i /> 38</div>
        </footer>
      </article>

      <aside class="review-sidebar">
        <section class="review-card">
          <header><div><small>Review queue</small><h2>Upcoming attestations</h2></div><CalendarDays :size="18" /></header>
          <div class="attestation-list">
            <article v-for="item in attestations" :key="item.title">
              <time><strong>{{ item.date }}</strong><small>{{ item.month }}</small></time>
              <div><strong>{{ item.title }}</strong><small>{{ item.owner }} · {{ item.state }}</small></div>
              <ArrowUpRight :size="14" />
            </article>
          </div>
          <button>View audit calendar <ArrowUpRight :size="13" /></button>
        </section>
        <section class="evidence-snapshot">
          <header><small>Evidence health</small><strong>1,264 items</strong></header>
          <div class="snapshot-chart">
            <span v-for="height in [45, 62, 51, 74, 69, 82, 78, 91, 85, 96, 88, 94]" :key="`${height}`" :style="{ height: `${height}%` }" />
          </div>
          <dl>
            <div><dt><i class="fresh" />Fresh</dt><dd>1,183</dd></div>
            <div><dt><i class="aging" />Aging</dt><dd>69</dd></div>
            <div><dt><i class="expired" />Expired</dt><dd>12</dd></div>
          </dl>
        </section>
      </aside>
    </section>

    <section class="coverage-card">
      <header class="section-title">
        <div><small>Control mapping</small><h2>Coverage by control family</h2></div>
        <span><ClipboardCheck :size="13" /> {{ selectedData.controls }} controls in scope</span>
      </header>
      <div class="coverage-head"><span>Control family</span><span>Coverage</span><span>Evidence</span><span>Owner</span><span>Status</span></div>
      <article v-for="item in coverage" :key="item.code" class="coverage-row">
        <div class="control-name"><span><component :is="item.icon" :size="15" /></span><div><strong>{{ item.family }}</strong><code>{{ activeFramework }} · {{ item.code }}</code></div></div>
        <div class="coverage-progress"><div><i :style="{ width: `${(item.covered / item.total) * 100}%` }" /></div><span>{{ item.covered }} / {{ item.total }}</span></div>
        <strong class="evidence-count">{{ item.evidence }}</strong>
        <span class="owner"><Users :size="12" />{{ item.owner }}</span>
        <b :class="{ partial: item.covered < item.total }">{{ item.covered === item.total ? "Covered" : "Partial" }}</b>
      </article>
    </section>

    <section class="exports-card">
      <header class="section-title">
        <div><small>Deliverables</small><h2>Export history</h2></div>
        <span><Archive :size="13" /> Retained for 365 days</span>
      </header>
      <div class="exports-table">
        <div class="exports-head"><span>Export</span><span>Format</span><span>Scope</span><span>Generated</span><span>Owner</span><span>Size</span><span /></div>
        <article v-for="item in exports" :key="item.id">
          <div><span class="file-icon"><FileText :size="15" /></span><span><strong>{{ item.name }}</strong><code>{{ item.id }}</code></span></div>
          <b>{{ item.format }}</b><span>{{ item.scope }}</span><time><Clock3 :size="11" />{{ item.generated }}</time><span>{{ item.owner }}</span><code>{{ item.size }}</code>
          <button title="Download demo export" @click="showNotice(`${item.name} queued for download`)"><Download :size="14" /></button>
        </article>
      </div>
    </section>
  </ProductPageLayout>
</template>

<style scoped>
.report-actions{display:flex;align-items:stretch;gap:8px}.report-actions label{display:flex;align-items:center;gap:8px;padding:0 10px;border:1px solid var(--trace-border);border-radius:10px;background:#fff}.report-actions label span{color:#8b96a4;font-size:8px}.report-actions select{border:0;outline:0;color:var(--trace-ink);background:transparent;font-size:9px;font-weight:650}.report-actions>button{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid var(--trace-red);border-radius:10px;color:#fff;background:var(--trace-red);font-size:9px;font-weight:700;cursor:pointer;box-shadow:0 6px 14px rgba(201,31,55,.16)}.spin{animation:spin .8s linear infinite}.toast{position:fixed;right:22px;top:70px;z-index:20;display:flex;align-items:center;gap:8px;padding:10px 13px;border:1px solid #cfe5de;border-radius:10px;color:#15775c;background:#f7fffc;box-shadow:0 14px 36px rgba(30,41,59,.16);font-size:9px;animation:toast-in .2s ease}
.assurance-banner{display:grid;grid-template-columns:minmax(310px,1.1fr) 135px minmax(360px,.95fr);align-items:center;gap:24px;margin-bottom:11px;padding:20px 24px;border:1px solid #d8e4df;border-radius:17px;background:linear-gradient(120deg,#fbfdfc 0%,#f1f8f5 55%,#edf5f2 100%);box-shadow:0 9px 24px rgba(30,41,59,.045)}.status-pill{display:inline-flex;align-items:center;gap:5px;padding:5px 8px;border-radius:8px;color:#15775c;background:#dff2eb;font-size:7px;font-weight:750;text-transform:uppercase;letter-spacing:.08em}.assurance-copy h2{margin:9px 0 4px;font-size:19px;letter-spacing:-.025em}.assurance-copy p{margin:0;color:#748293;font-size:8px}.framework-tabs{display:flex;gap:5px;margin-top:14px}.framework-tabs button{padding:5px 8px;border:1px solid #d8e2de;border-radius:7px;color:#718073;background:rgba(255,255,255,.65);font-size:7px;cursor:pointer}.framework-tabs button.active{border-color:#187d61;color:#fff;background:#187d61}.readiness-score{display:grid;place-items:center;width:112px;height:112px;border-radius:50%;background:conic-gradient(var(--trace-success) var(--score),#dce8e3 0)}.readiness-score::before{grid-area:1/1;width:88px;height:88px;border-radius:50%;background:#f7fbf9;box-shadow:inset 0 0 0 1px rgba(21,132,102,.08);content:""}.readiness-score>div{z-index:1;grid-area:1/1;text-align:center}.readiness-score strong,.readiness-score small{display:block}.readiness-score strong{font:700 21px var(--trace-font-mono)}.readiness-score small{margin-top:3px;color:#788797;font-size:7px;text-transform:uppercase}.assurance-banner>dl{display:grid;grid-template-columns:1fr 1fr;gap:1px;margin:0;overflow:hidden;border:1px solid #dce6e2;border-radius:11px;background:#dce6e2}.assurance-banner>dl div{padding:10px 12px;background:rgba(255,255,255,.75)}.assurance-banner dt,.assurance-banner dd{display:block}.assurance-banner dt{color:#7d8b98;font-size:7px}.assurance-banner dd{margin:4px 0 0;font:650 13px var(--trace-font-mono)}.assurance-banner dd.warning{color:var(--trace-warning)}
.report-workspace{display:grid;grid-template-columns:minmax(620px,1.45fr) minmax(300px,.62fr);gap:11px;margin-bottom:11px}.report-paper{position:relative;min-height:428px;padding:24px 28px 19px;overflow:hidden;border:1px solid #dfe3e5;border-radius:3px;background:#fff;box-shadow:0 12px 30px rgba(30,41,59,.08)}.report-paper::after{position:absolute;right:-40px;top:-55px;width:180px;height:180px;border:34px solid rgba(21,132,102,.025);border-radius:50%;content:""}.paper-topline{display:flex;justify-content:space-between;color:#9aa4ae;font:6px var(--trace-font-mono);letter-spacing:.09em}.report-paper>header{position:relative;display:grid;grid-template-columns:42px 1fr auto;align-items:start;gap:13px;margin-top:21px}.document-mark{display:grid;place-items:center;width:40px;height:40px;border:1px solid #d8e5e0;border-radius:4px;color:var(--trace-success);background:#eef7f3}.report-paper header small{color:var(--trace-success);font-size:7px;text-transform:uppercase;letter-spacing:.08em}.report-paper header h2{margin:5px 0 4px;font-family:Georgia,"Times New Roman",serif;font-size:24px;font-weight:500;line-height:1.05;letter-spacing:-.025em}.report-paper header p{margin:0;color:#778494;font-size:8px}.confidential{position:relative;z-index:1;padding:5px 7px;border:1px solid #e1cfd2;border-radius:4px;color:#a23c4b;font:650 6px var(--trace-font-mono);text-transform:uppercase;letter-spacing:.08em}.paper-rule{height:3px;margin:18px 0 15px;background:linear-gradient(90deg,var(--trace-success) 0 24%,#e5e9e7 24% 100%)}.executive-note{display:grid;grid-template-columns:25px 1fr auto;gap:10px;padding:12px;border:1px solid #e2e7e5;background:#fafcfb}.executive-note>span{color:#a0aaa6;font:7px var(--trace-font-mono)}.executive-note small{color:#72807b;font-size:6px;font-weight:750;letter-spacing:.1em}.executive-note p{max-width:580px;margin:5px 0 0;color:#58666f;font-family:Georgia,"Times New Roman",serif;font-size:9px;line-height:1.55}.executive-note>strong{display:flex;align-items:center;gap:5px;align-self:center;color:var(--trace-success);font-size:8px}.document-sections{display:grid;grid-template-columns:1fr 1fr;margin-top:14px;border-top:1px solid #e4e8e6;border-left:1px solid #e4e8e6}.document-sections article{display:grid;grid-template-columns:23px 1fr auto;gap:8px;padding:11px;border-right:1px solid #e4e8e6;border-bottom:1px solid #e4e8e6}.document-sections article>span{color:#a0aaa7;font:7px var(--trace-font-mono)}.document-sections strong,.document-sections small{display:block}.document-sections strong{font-family:Georgia,"Times New Roman",serif;font-size:9px}.document-sections small{margin-top:3px;color:#929caa;font-size:6px}.document-sections b{display:flex;align-items:center;gap:4px;align-self:center;color:#188064;font-size:6px;text-transform:uppercase}.document-sections b.review{color:var(--trace-warning)}.report-paper>footer{display:grid;grid-template-columns:1fr 1fr auto;align-items:end;gap:15px;margin-top:18px}.signature{padding-top:7px;border-top:1px solid #dfe4e2}.signature span,.signature strong,.signature small{display:block}.signature span{color:#99a3ad;font-size:6px;text-transform:uppercase}.signature strong{margin-top:4px;font-family:Georgia,"Times New Roman",serif;font-size:9px}.signature small{margin-top:2px;color:#8c97a4;font-size:6px}.page-number{display:flex;align-items:center;gap:6px;color:#8d989f;font:7px var(--trace-font-mono)}.page-number i{display:block;width:24px;height:1px;background:#cfd6d3}
.review-sidebar{display:grid;grid-template-rows:1fr auto;gap:10px}.review-card,.evidence-snapshot{border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 8px 22px rgba(30,41,59,.04)}.review-card{padding:16px}.review-card>header{display:flex;justify-content:space-between}.review-card header small,.section-title small,.evidence-snapshot header small{color:var(--trace-success);font-size:7px;font-weight:700;text-transform:uppercase;letter-spacing:.09em}.review-card h2,.section-title h2{margin:4px 0 0;font-size:13px}.review-card header svg{color:#a1abb4}.attestation-list{display:grid;margin-top:8px}.attestation-list article{display:grid;grid-template-columns:36px 1fr 15px;align-items:center;gap:9px;padding:10px 0;border-bottom:1px solid #edf0ef}.attestation-list time{display:grid;place-items:center;height:34px;border:1px solid #dfe5e2;border-radius:7px;background:#f8faf9}.attestation-list time strong,.attestation-list time small{display:block}.attestation-list time strong{font:650 11px var(--trace-font-mono)}.attestation-list time small{color:#89958f;font-size:5px}.attestation-list article>div strong,.attestation-list article>div small{display:block}.attestation-list article>div strong{font-size:8px}.attestation-list article>div small{margin-top:4px;color:#8994a2;font-size:6px}.attestation-list article>svg{color:#a5aeb7}.review-card>button{display:flex;align-items:center;justify-content:center;gap:6px;width:100%;margin-top:11px;padding:7px;border:1px solid #dfe4e2;border-radius:8px;background:#fff;font-size:7px;cursor:pointer}.evidence-snapshot{padding:14px 16px}.evidence-snapshot>header{display:flex;align-items:end;justify-content:space-between}.evidence-snapshot header strong{font:650 12px var(--trace-font-mono)}.snapshot-chart{display:flex;align-items:flex-end;gap:4px;height:46px;margin:13px 0 10px;border-bottom:1px solid #e5eae8}.snapshot-chart span{flex:1;border-radius:3px 3px 0 0;background:linear-gradient(180deg,#36a483,#8bcdb9)}.evidence-snapshot dl{display:grid;grid-template-columns:repeat(3,1fr);margin:0}.evidence-snapshot dl div{text-align:center}.evidence-snapshot dt{display:flex;align-items:center;justify-content:center;gap:4px;color:#87938f;font-size:6px}.evidence-snapshot dt i{width:5px;height:5px;border-radius:50%;background:var(--trace-success)}.evidence-snapshot dt i.aging{background:#d8aa48}.evidence-snapshot dt i.expired{background:var(--trace-red)}.evidence-snapshot dd{margin:3px 0 0;font:650 8px var(--trace-font-mono)}
.coverage-card,.exports-card{margin-bottom:11px;overflow:hidden;border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 8px 22px rgba(30,41,59,.04)}.section-title{display:flex;align-items:center;justify-content:space-between;padding:15px 16px}.section-title>span{display:flex;align-items:center;gap:5px;color:#84908f;font-size:7px}.coverage-head,.coverage-row{display:grid;grid-template-columns:minmax(230px,1.25fr) minmax(210px,1fr) 90px 130px 70px;align-items:center;gap:12px;padding:0 16px}.coverage-head{height:28px;color:#8f999e;background:#f5f7f6;font-size:6px;font-weight:750;text-transform:uppercase;letter-spacing:.08em}.coverage-row{min-height:48px;border-top:1px solid #edf0ef}.control-name{display:flex;align-items:center;gap:9px}.control-name>span{display:grid;place-items:center;width:29px;height:29px;border-radius:8px;color:#177d60;background:#eaf6f1}.control-name strong,.control-name code{display:block}.control-name strong{font-size:8px}.control-name code{margin-top:3px;color:#919ba5;font-size:6px}.coverage-progress{display:flex;align-items:center;gap:9px}.coverage-progress>div{height:5px;flex:1;overflow:hidden;border-radius:5px;background:#e8eeeb}.coverage-progress i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#187f62,#47ab8c)}.coverage-progress span,.evidence-count{font:650 7px var(--trace-font-mono)}.evidence-count{color:#63716e}.owner{display:flex;align-items:center;gap:5px;color:#75827f;font-size:7px}.coverage-row>b{justify-self:start;padding:4px 6px;border-radius:6px;color:#16795e;background:#e8f6f1;font-size:6px;text-transform:uppercase}.coverage-row>b.partial{color:#9a6505;background:#fff5df}
.exports-card{margin-bottom:0}.exports-table{overflow-x:auto}.exports-head,.exports-table article{display:grid;grid-template-columns:minmax(260px,1.5fr) 90px minmax(130px,.8fr) 130px 100px 70px 28px;align-items:center;gap:11px;padding:0 16px}.exports-head{height:28px;color:#8f999e;background:#f5f7f6;font-size:6px;font-weight:750;text-transform:uppercase;letter-spacing:.08em}.exports-table article{min-height:51px;border-top:1px solid #edf0ef}.exports-table article>div{display:flex;align-items:center;gap:9px}.file-icon{display:grid;place-items:center;width:29px;height:29px;border:1px solid #dfe6e3;border-radius:7px;color:#27856a;background:#f7faf9}.exports-table article div span:last-child strong,.exports-table article div span:last-child code{display:block}.exports-table article strong{font-size:8px}.exports-table article div span:last-child code{margin-top:3px;color:#929ca6;font-size:6px}.exports-table article>b{justify-self:start;padding:4px 6px;border-radius:5px;color:#657571;background:#eef3f1;font-size:6px}.exports-table article>span,.exports-table article>code,.exports-table article>time{overflow:hidden;color:#74817e;text-overflow:ellipsis;white-space:nowrap;font-size:7px}.exports-table article>time{display:flex;align-items:center;gap:5px}.exports-table article>code{font-family:var(--trace-font-mono)}.exports-table article>button{display:grid;place-items:center;width:27px;height:27px;border:1px solid #dfe4e2;border-radius:7px;color:#75827f;background:#fff;cursor:pointer;transition:color 150ms ease,border-color 150ms ease}.exports-table article>button:hover{border-color:#90b8aa;color:var(--trace-success)}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes toast-in{from{opacity:0;transform:translateY(-7px)}}
@media (max-width:1280px){.assurance-banner{grid-template-columns:1fr 120px}.assurance-banner>dl{grid-column:1/3}.report-workspace{grid-template-columns:minmax(590px,1.3fr) 300px}.report-paper{padding-left:20px;padding-right:20px}.coverage-head,.coverage-row{grid-template-columns:minmax(200px,1fr) minmax(170px,.8fr) 70px 105px 65px}}
</style>
