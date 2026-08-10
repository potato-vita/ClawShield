<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { ArrowRight, Filter, MessageSquareText, Search, ShieldAlert, Wrench } from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";
import { useRuntimeStore } from "@/stores/runtimeStore";
import type { AuditSession, RiskLevel } from "@/types/session";

const store=useRuntimeStore();
const router=useRouter();
const query=ref("");
const risk=ref<RiskLevel|"all">("all");
const visible=computed(()=>store.sessions.filter(session=>(risk.value==="all"||session.risk===risk.value)&&(session.title+session.subtitle).toLowerCase().includes(query.value.toLowerCase())));
const riskSessions=computed(()=>store.sessions.filter(session=>session.risk==="critical"||session.risk==="high").length);
const conversationOnly=computed(()=>store.sessions.filter(session=>session.subtitle.includes("message")&&!session.subtitle.includes("tool calls")).length);
async function openSession(session:AuditSession){await store.selectSession(session.id);await router.push("/runtime");}
</script>

<template>
  <ProductPageLayout eyebrow="审计记录" title="会话" description="独立浏览对话与已审计运行，并可随时进入实时审计工作台。">
    <template #actions><div class="live-state"><i :class="{online:store.streamState==='connected'||store.streamState==='polling'}"/>{{store.streamState==='connected'?'实时更新':store.streamState==='polling'?'定时更新':'实时流离线'}}</div></template>
    <section class="session-metrics">
      <article><MessageSquareText :size="18"/><span><small>全部会话</small><strong>{{store.sessions.length}}</strong></span></article>
      <article><ShieldAlert :size="18"/><span><small>高风险</small><strong>{{riskSessions}}</strong></span></article>
      <article><Wrench :size="18"/><span><small>工具调用</small><strong>{{store.toolCalls.length}}</strong></span></article>
      <article><MessageSquareText :size="18"/><span><small>纯对话</small><strong>{{conversationOnly}}</strong></span></article>
    </section>
    <section class="session-toolbar">
      <label class="search"><Search :size="15"/><input v-model="query" placeholder="搜索会话 ID 或活动"/></label>
      <label class="risk-filter"><Filter :size="14"/><select v-model="risk"><option value="all">全部风险等级</option><option value="critical">严重</option><option value="high">高</option><option value="medium">中</option><option value="low">低</option></select></label>
      <span>{{visible.length}} 条记录</span>
    </section>
    <section class="session-table">
      <header><span>会话</span><span>最近活动</span><span>风险</span><span>运行次数</span><span>更新时间</span><span/></header>
      <button v-for="session in visible" :key="session.id" @click="openSession(session)">
        <span class="identity"><i :class="`risk-${session.risk}`"/><strong>{{session.title}}</strong><code>{{session.id}}</code></span>
        <span class="activity">{{session.subtitle}}</span>
        <b :class="`risk-${session.risk}`">{{session.risk}}</b>
        <span>{{session.runIds.length}}</span>
        <time>{{session.time}}</time>
        <ArrowRight :size="15"/>
      </button>
      <div v-if="!visible.length" class="empty"><strong>没有找到会话</strong><span>请尝试其他搜索词或风险筛选条件。</span></div>
    </section>
  </ProductPageLayout>
</template>

<style scoped>
.live-state{display:flex;align-items:center;gap:7px;padding:8px 11px;border:1px solid var(--trace-border);border-radius:10px;color:#667285;background:#fff;font-size:10px}.live-state i{width:7px;height:7px;border-radius:50%;background:#a8b1bc}.live-state i.online{background:var(--trace-success);box-shadow:0 0 0 3px rgba(21,132,102,.1)}.session-metrics{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:10px;margin-bottom:12px}.session-metrics article{display:flex;align-items:center;gap:11px;padding:14px 15px;border:1px solid var(--trace-border);border-radius:13px;background:#fff;box-shadow:0 5px 14px rgba(30,41,59,.035)}.session-metrics svg{color:#7b8796}.session-metrics small,.session-metrics strong{display:block}.session-metrics small{color:#8993a1;font-size:8px;text-transform:uppercase;letter-spacing:.06em}.session-metrics strong{margin-top:3px;font:650 18px var(--trace-font-mono)}.session-toolbar{display:flex;align-items:center;gap:9px;margin-bottom:10px;padding:9px;border:1px solid var(--trace-border);border-radius:12px;background:#fff}.session-toolbar label{display:flex;align-items:center;gap:8px;height:34px;padding:0 10px;border:1px solid #e1e5e9;border-radius:9px;color:#8993a1;background:#fafbfb}.search{flex:1;max-width:520px}.search input,.risk-filter select{width:100%;border:0;outline:0;background:transparent;color:var(--trace-ink);font-size:10px}.risk-filter{width:190px}.session-toolbar>span{margin-left:auto;padding-right:5px;color:#8b95a2;font:9px var(--trace-font-mono)}.session-table{overflow:hidden;border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 8px 22px rgba(30,41,59,.045)}.session-table>header,.session-table>button{display:grid;grid-template-columns:minmax(240px,1.4fr) minmax(190px,1fr) 85px 70px 90px 28px;align-items:center;gap:12px;padding:0 15px}.session-table>header{height:34px;color:#8a95a3;background:#f4f5f6;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}.session-table>button{width:100%;min-height:62px;border:0;border-top:1px solid #edf0f2;text-align:left;background:#fff;cursor:pointer;transition:background-color 160ms ease,box-shadow 160ms ease}.session-table>button:hover{background:#fafafa;box-shadow:inset 3px 0 var(--trace-red)}.identity{position:relative;min-width:0;padding-left:13px}.identity>i{position:absolute;left:0;top:2px;width:4px;height:30px;border-radius:4px;background:#9ca7b3}.identity>i.risk-critical,.identity>i.risk-high{background:var(--trace-red)}.identity>i.risk-medium{background:var(--trace-warning)}.identity strong,.identity code{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.identity strong{font-size:10px}.identity code{margin-top:4px;color:#929ca9;font-size:7px}.activity{overflow:hidden;color:#697688;text-overflow:ellipsis;white-space:nowrap;font-size:9px}.session-table b{justify-self:start;padding:4px 7px;border-radius:6px;color:#168363;background:#eaf8f3;font-size:7px;text-transform:uppercase}.session-table b.risk-critical,.session-table b.risk-high{color:var(--trace-red);background:#fff0f0}.session-table b.risk-medium{color:#a36600;background:#fff6e7}.session-table>button>span:not(.identity):not(.activity),.session-table time{color:#768292;font:9px var(--trace-font-mono)}.session-table svg{color:#9aa4af;transition:transform 180ms cubic-bezier(.2,.8,.2,1)}.session-table button:hover svg{transform:translateX(3px);color:var(--trace-red)}.empty{display:grid;place-items:center;padding:65px;color:#8b96a3}.empty strong{font-size:12px}.empty span{margin-top:5px;font-size:9px}
</style>
