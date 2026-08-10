<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Archive,
  BadgeCheck,
  Check,
  ChevronRight,
  Clock3,
  Copy,
  Download,
  FileCheck2,
  Fingerprint,
  Link2,
  LockKeyhole,
  Search,
  ShieldCheck,
} from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";

type EvidenceStatus = "sealed" | "verified" | "pending";
interface CaseFile { id:string; title:string; session:string; decision:string; risk:string; items:number; status:EvidenceStatus; created:string; hash:string; owner:string }

const query = ref("");
const filter = ref<"all" | EvidenceStatus>("all");
const copied = ref(false);
const selected = ref<CaseFile | null>(null);
const cases: CaseFile[] = [
  { id:"EV-2026-0841",title:"Payroll data exfiltration attempt",session:"payroll-leak-demo",decision:"BLOCK",risk:"critical",items:14,status:"sealed",created:"08 Aug 2026 · 10:42",hash:"sha256:8cb7b2f1…97d2a4",owner:"Runtime Core" },
  { id:"EV-2026-0839",title:"Destructive workspace cleanup",session:"workspace-cleanup",decision:"ASK",risk:"high",items:9,status:"verified",created:"08 Aug 2026 · 10:38",hash:"sha256:92e440ab…d163ce",owner:"Policy Engine" },
  { id:"EV-2026-0834",title:"Remote content prompt injection",session:"research-agent",decision:"WARN",risk:"medium",items:11,status:"verified",created:"08 Aug 2026 · 10:31",hash:"sha256:1a0d62c9…45bf90",owner:"Method Engine" },
  { id:"EV-2026-0828",title:"Unregistered plugin capability",session:"plugin-bootstrap",decision:"ASK",risk:"medium",items:7,status:"pending",created:"08 Aug 2026 · 09:58",hash:"sha256:f8c32511…08c774",owner:"OpenClaw Gateway" },
  { id:"EV-2026-0821",title:"Source repository review",session:"source-review",decision:"ALLOW",risk:"low",items:18,status:"sealed",created:"08 Aug 2026 · 09:26",hash:"sha256:40ad93bb…a9fc10",owner:"Runtime Core" },
];
const visible = computed(() => cases.filter(item => (filter.value === "all" || item.status === filter.value) && `${item.id} ${item.title} ${item.session}`.toLowerCase().includes(query.value.toLowerCase())));
const statusFilters: Array<"all" | EvidenceStatus> = ["all", "sealed", "verified", "pending"];
const timeline = [
  { icon:Archive,title:"Evidence bundle opened",detail:"Run context and intent frame recorded",time:"10:42:17.114" },
  { icon:Fingerprint,title:"Tool parameters fingerprinted",detail:"Original payload excluded by retention policy",time:"10:42:17.128" },
  { icon:ShieldCheck,title:"Policy decision attached",detail:"deny_sensitive_external_chain · BLOCK",time:"10:42:17.146" },
  { icon:Link2,title:"Risk path materialized",detail:"source → propagation → sink",time:"10:42:17.184" },
  { icon:LockKeyhole,title:"Bundle sealed",detail:"Integrity digest committed",time:"10:42:17.219" },
];
function openCase(item:CaseFile){selected.value=item;copied.value=false}
function setFilter(value:"all"|EvidenceStatus){filter.value=value}
async function copyHash(){if(!selected.value)return;await navigator.clipboard?.writeText(selected.value.hash);copied.value=true;window.setTimeout(()=>copied.value=false,1600)}
</script>

<template>
  <ProductPageLayout eyebrow="证据保全链" title="证据仓库" description="查看不可篡改的审计证据包，并还原每一次运行时决策。">
    <template #actions><button class="export"><Download :size="14"/> Export manifest</button></template>
    <section class="vault-banner">
      <div class="vault-icon"><LockKeyhole :size="27"/></div>
      <div><small>Evidence integrity</small><h2>All sealed bundles verified</h2><p>Last ledger verification completed 48 seconds ago. No missing sequence or digest mismatch detected.</p></div>
      <dl><div><dt>Bundles</dt><dd>1,284</dd></div><div><dt>Sealed today</dt><dd>47</dd></div><div><dt>Retention</dt><dd>180 days</dd></div></dl>
      <BadgeCheck class="watermark" :size="150" :stroke-width=".8"/>
    </section>
    <section class="vault-layout">
      <article class="case-list">
        <header>
          <label><Search :size="14"/><input v-model="query" placeholder="Search evidence or session"/></label>
          <div class="filters"><button v-for="item in statusFilters" :key="item" :class="{active:filter===item}" @click="setFilter(item)">{{item}}</button></div>
        </header>
        <div class="list-heading"><span>Evidence bundle</span><span>Decision</span><span>Artifacts</span><span>Integrity</span><span>Created</span><span/></div>
        <button v-for="item in visible" :key="item.id" class="case-row" @click="openCase(item)">
          <span class="case-title"><FileCheck2 :size="17"/><span><strong>{{item.title}}</strong><small>{{item.id}} · {{item.session}}</small></span></span>
          <b :class="`decision-${item.decision.toLowerCase()}`">{{item.decision}}</b>
          <span class="artifacts">{{item.items}} items</span>
          <span class="integrity" :class="item.status"><i/><span>{{item.status}}</span></span>
          <time>{{item.created}}</time>
          <ChevronRight :size="14"/>
        </button>
        <div v-if="!visible.length" class="empty">No evidence bundle matches this filter.</div>
      </article>
      <aside class="ledger-card">
        <header><div><small>Custody ledger</small><h3>Latest commitments</h3></div><span>append-only</span></header>
        <div class="ledger-line" v-for="(entry,index) in ['block #18,442','block #18,441','block #18,440','block #18,439']" :key="entry">
          <i><Check :size="10"/></i><div><strong>{{entry}}</strong><small>{{47-index*3}} evidence digests</small></div><code>{{10-index}}:{{String(46-index*7).padStart(2,'0')}}:08</code>
        </div>
        <footer><Clock3 :size="13"/><span>Next verification in</span><strong>00:42</strong></footer>
      </aside>
    </section>
    <div v-if="selected" class="drawer-backdrop" @click.self="selected=null">
      <aside class="evidence-drawer">
        <header><div><small>{{selected.id}}</small><h2>{{selected.title}}</h2></div><button @click="selected=null">×</button></header>
        <div class="seal"><ShieldCheck :size="22"/><div><strong>Evidence {{selected.status}}</strong><span>Integrity verification passed</span></div><b>{{selected.decision}}</b></div>
        <dl><div><dt>Session</dt><dd>{{selected.session}}</dd></div><div><dt>Owner</dt><dd>{{selected.owner}}</dd></div><div><dt>Artifacts</dt><dd>{{selected.items}}</dd></div><div><dt>Created</dt><dd>{{selected.created}}</dd></div></dl>
        <section class="digest"><small>Bundle digest</small><div><code>{{selected.hash}}</code><button @click="copyHash"><component :is="copied?Check:Copy" :size="13"/>{{copied?'Copied':'Copy'}}</button></div></section>
        <section class="custody"><small>Chain of custody</small><article v-for="entry in timeline" :key="entry.time"><i><component :is="entry.icon" :size="13"/></i><div><strong>{{entry.title}}</strong><span>{{entry.detail}}</span></div><time>{{entry.time}}</time></article></section>
        <footer><button><Download :size="14"/> Download signed bundle</button></footer>
      </aside>
    </div>
  </ProductPageLayout>
</template>

<style scoped>
.export{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid #293444;border-radius:9px;color:#fff;background:#293444;font-size:9px;font-weight:700;cursor:pointer}.vault-banner{position:relative;display:grid;grid-template-columns:46px 1fr auto;align-items:center;gap:13px;min-height:110px;padding:18px 21px;overflow:hidden;border:1px solid #dce9e5;border-radius:16px;background:linear-gradient(100deg,#f2fbf8,#fff 72%);box-shadow:0 8px 24px rgba(30,41,59,.035)}.vault-icon{display:grid;place-items:center;width:44px;height:44px;border-radius:13px;color:#fff;background:var(--trace-success);box-shadow:0 7px 16px rgba(21,132,102,.18)}.vault-banner small{color:var(--trace-success);font-size:7px;font-weight:700;text-transform:uppercase;letter-spacing:.09em}.vault-banner h2{margin:3px 0 4px;font-size:15px}.vault-banner p{margin:0;color:#6f7d8c;font-size:8px}.vault-banner dl{z-index:1;display:flex;gap:30px;margin:0 15px 0 25px}.vault-banner dl div{display:flex;flex-direction:column}.vault-banner dt{color:#83909d;font-size:7px;text-transform:uppercase}.vault-banner dd{margin:4px 0 0;font:650 13px var(--trace-font-mono)}.watermark{position:absolute;right:-25px;color:rgba(21,132,102,.055)}
.vault-layout{display:grid;grid-template-columns:minmax(760px,1fr) 270px;gap:12px;margin-top:12px}.case-list,.ledger-card{overflow:hidden;border:1px solid var(--trace-border);border-radius:15px;background:#fff;box-shadow:0 8px 24px rgba(30,41,59,.04)}.case-list>header{display:flex;align-items:center;justify-content:space-between;padding:11px 13px;border-bottom:1px solid #e8ecef}.case-list label{display:flex;align-items:center;gap:7px;width:310px;padding:8px 9px;border:1px solid #e2e6ea;border-radius:8px;color:#929ca8;background:#fafafa}.case-list input{width:100%;border:0;outline:0;background:transparent;font-size:8px}.filters{display:flex;gap:3px;padding:3px;border-radius:8px;background:#f1f3f4}.filters button{padding:5px 8px;border:0;border-radius:6px;color:#7b8795;background:transparent;font-size:7px;text-transform:capitalize;cursor:pointer}.filters button.active{color:var(--trace-ink);background:#fff;box-shadow:0 2px 6px rgba(30,41,59,.08)}.list-heading,.case-row{display:grid;grid-template-columns:minmax(280px,1.7fr) 70px 65px 85px 120px 15px;align-items:center;gap:10px;padding:0 13px}.list-heading{height:30px;color:#929ca8;background:#f6f7f7;font-size:7px;font-weight:700;text-transform:uppercase}.case-row{width:100%;min-height:63px;border:0;border-top:1px solid #edf0f2;text-align:left;background:#fff;cursor:pointer}.case-row:hover{background:#fbfbfb;box-shadow:inset 3px 0 var(--trace-success)}.case-title{display:flex;align-items:center;gap:9px;min-width:0}.case-title>svg{flex:none;color:#758293}.case-title span,.case-title strong,.case-title small{display:block;min-width:0}.case-title strong,.case-title small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.case-title strong{font-size:9px}.case-title small{margin-top:4px;color:#939da9;font:7px var(--trace-font-mono)}.case-row>b{justify-self:start;padding:4px 6px;border-radius:5px;color:#657184;background:#eef1f3;font-size:7px}.case-row .decision-block{color:var(--trace-red);background:#fff0f0}.case-row .decision-ask,.case-row .decision-warn{color:#a36600;background:#fff6e7}.case-row .decision-allow{color:var(--trace-success);background:#eaf8f3}.artifacts,.case-row time{color:#748191;font:7px var(--trace-font-mono)}.integrity{display:flex;align-items:center;gap:5px;color:#667587;font-size:7px;text-transform:capitalize}.integrity i{width:6px;height:6px;border-radius:50%;background:var(--trace-warning)}.integrity.sealed i,.integrity.verified i{background:var(--trace-success)}.case-row>svg{color:#a0aab5}.empty{padding:60px;text-align:center;color:#8b96a3;font-size:9px}
.ledger-card>header{display:flex;align-items:center;justify-content:space-between;padding:14px;border-bottom:1px solid #e9ecef}.ledger-card header small{color:#929ca8;font-size:7px;text-transform:uppercase}.ledger-card h3{margin:3px 0 0;font-size:11px}.ledger-card header>span{padding:4px 6px;border-radius:5px;color:#6f7c8b;background:#eef1f3;font:6px var(--trace-font-mono);text-transform:uppercase}.ledger-line{position:relative;display:grid;grid-template-columns:25px 1fr auto;align-items:center;gap:7px;padding:12px 13px}.ledger-line:not(:last-of-type):after{position:absolute;left:25px;bottom:-7px;width:1px;height:14px;background:#dbe1e5;content:""}.ledger-line>i{display:grid;place-items:center;width:23px;height:23px;border:1px solid #cfe5dd;border-radius:50%;color:var(--trace-success);background:#eff9f6}.ledger-line strong,.ledger-line small{display:block}.ledger-line strong{font:600 8px var(--trace-font-mono)}.ledger-line small{margin-top:3px;color:#8b96a4;font-size:7px}.ledger-line code{color:#929ca8;font-size:6px}.ledger-card>footer{display:flex;align-items:center;gap:7px;margin:8px 13px 13px;padding:9px;border-radius:8px;color:#778493;background:#f4f6f6;font-size:7px}.ledger-card footer strong{margin-left:auto;font:650 8px var(--trace-font-mono)}
.drawer-backdrop{position:fixed;inset:0;z-index:90;background:rgba(25,32,43,.25);backdrop-filter:blur(2px)}.evidence-drawer{position:absolute;right:0;top:0;width:475px;height:100%;overflow:auto;border-left:1px solid #dce1e6;background:#fff;box-shadow:-20px 0 60px rgba(30,41,59,.18);animation:drawer-in .22s cubic-bezier(.2,.8,.2,1)}.evidence-drawer>header{display:flex;align-items:flex-start;justify-content:space-between;padding:20px;border-bottom:1px solid #e6eaed}.evidence-drawer header small{color:var(--trace-red);font:7px var(--trace-font-mono)}.evidence-drawer h2{margin:5px 0 0;font-size:16px}.evidence-drawer header button{width:29px;height:29px;border:0;border-radius:8px;background:#eff1f3;cursor:pointer}.seal{display:flex;align-items:center;gap:10px;margin:16px;padding:13px;border:1px solid #d4e7e0;border-radius:11px;color:var(--trace-success);background:#eff9f6}.seal strong,.seal span{display:block}.seal strong{font-size:9px}.seal span{margin-top:3px;color:#75878a;font-size:7px}.seal b{margin-left:auto;padding:5px 7px;border-radius:6px;color:#fff;background:var(--trace-success);font-size:7px}.evidence-drawer>dl{display:grid;grid-template-columns:1fr 1fr;margin:0 16px;border:1px solid #e5e9ec;border-radius:10px;overflow:hidden}.evidence-drawer dl div{padding:10px;border-bottom:1px solid #edf0f2;background:#fafbfb}.evidence-drawer dt{color:#8a95a3;font-size:7px}.evidence-drawer dd{margin:4px 0 0;font:600 8px var(--trace-font-mono)}.digest,.custody{margin:17px 16px}.digest>small,.custody>small{color:#7b8795;font-size:7px;font-weight:700;text-transform:uppercase}.digest>div{display:flex;align-items:center;justify-content:space-between;margin-top:7px;padding:10px;border:1px solid #e2e6e9;border-radius:9px;background:#f8f9f9}.digest code{font-size:8px}.digest button{display:flex;align-items:center;gap:5px;border:0;color:var(--trace-red);background:transparent;font-size:7px;cursor:pointer}.custody article{position:relative;display:grid;grid-template-columns:30px 1fr auto;align-items:center;gap:9px;padding:10px 0}.custody article:not(:last-child):after{position:absolute;left:14px;bottom:-7px;width:1px;height:14px;background:#dce2e6;content:""}.custody article>i{display:grid;place-items:center;width:29px;height:29px;border:1px solid #e1e5e8;border-radius:9px;color:#657486;background:#f8f9f9}.custody strong,.custody span{display:block}.custody strong{font-size:8px}.custody span{margin-top:3px;color:#8994a2;font-size:7px}.custody time{color:#909aa7;font:6px var(--trace-font-mono)}.evidence-drawer>footer{padding:16px;border-top:1px solid #e5e9ec}.evidence-drawer footer button{display:flex;align-items:center;justify-content:center;gap:7px;width:100%;padding:10px;border:1px solid #263141;border-radius:9px;color:#fff;background:#263141;font-size:8px;font-weight:700;cursor:pointer}@keyframes drawer-in{from{transform:translateX(30px);opacity:0}}
@media(max-width:1250px){.vault-layout{grid-template-columns:1fr}.ledger-card{display:none}}
</style>
