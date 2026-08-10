<script setup lang="ts">
import { computed, ref } from "vue";
import { Bell, ChevronDown, Radio, Search, X } from "lucide-vue-next";
import { useRuntimeStore } from "@/stores/runtimeStore";
const store=useRuntimeStore();const showStatus=ref(false);
const pluginStatus=computed(()=>{
  const value=store.status.pluginLastSeen;
  if(value==="event stream pending")return "事件流待连接";
  if(value==="never")return "暂无心跳";
  return value.replace("seconds ago","秒前").replace("minutes ago","分钟前");
});
const streamLabel=computed(()=>store.streamState==="connected"?"已连接":store.streamState==="polling"?"轮询更新":store.streamState==="connecting"?"连接中":"离线");
</script>

<template>
  <header class="topbar">
    <div class="title-block"><strong>TraceShield</strong><span class="divider" /><span>实时审计控制台</span><small>Runtime Audit Console</small></div>
    <div class="status-strip">
      <button class="status-item" @click="showStatus=true"><i class="status-dot" :class="store.status.coreOnline?'online':'offline'" /><span>Core {{store.dataSource==='mock'?'预览':store.status.coreOnline?'在线':'离线'}}</span></button>
      <button class="status-item" @click="showStatus=true"><i class="status-dot" :class="store.status.databaseConnected?'online':'offline'" /><span>PostgreSQL {{store.status.databaseConnected?'已连接':'离线'}}</span></button>
      <button class="status-item" @click="showStatus=true"><Radio :size="13" /><span>插件 · {{pluginStatus}}</span><ChevronDown :size="13" /></button>
      <button class="status-item realtime" @click="showStatus=true"><i class="status-dot" :class="store.streamState==='connected'||store.streamState==='polling'?'online':'offline'"/><span>实时流 {{streamLabel}}</span></button>
    </div>
    <div class="top-actions"><button class="icon-button" aria-label="搜索"><Search :size="17" /></button><button class="icon-button" aria-label="通知"><Bell :size="17" /><b /></button><div class="avatar">TS</div></div>
    <div v-if="showStatus" class="status-backdrop" @click.self="showStatus=false"><section class="status-modal"><header><div><small>系统遥测</small><h2>Core 状态</h2></div><button aria-label="关闭" @click="showStatus=false"><X :size="17"/></button></header><div class="health-hero"><i class="status-dot" :class="store.status.coreOnline?'online':'offline'"/><div><strong>{{store.status.coreOnline?'主要服务运行正常':'Core 需要处理'}}</strong><span>数据源 · {{store.dataSource}}</span></div></div><dl><div><dt>Core</dt><dd>{{store.status.coreOnline?'在线':'离线'}}</dd></div><div><dt>数据库</dt><dd>{{store.status.databaseConnected?'已连接':'未连接'}}</dd></div><div><dt>实时事件流</dt><dd>{{streamLabel}}</dd></div><div><dt>OpenClaw 插件</dt><dd>{{pluginStatus}}</dd></div><div><dt>已接收事件</dt><dd>{{store.status.eventsIngested.toLocaleString()}}</dd></div><div><dt>队列长度</dt><dd>{{store.status.queueSize}}</dd></div><div><dt>Core 版本</dt><dd>{{store.status.coreVersion}}</dd></div><div><dt>策略版本</dt><dd>{{store.status.policyVersion}}</dd></div></dl><footer><router-link to="/core" @click="showStatus=false">打开系统状态页</router-link></footer></section></div>
  </header>
</template>

<style scoped>
.topbar { display: flex; align-items: center; min-width: 0; height: 58px; padding: 0 16px 0 18px; border-bottom: 1px solid var(--trace-border); background: #fff; }
.title-block { display: flex; align-items: baseline; gap: 9px; white-space: nowrap; }.title-block strong { font-size: 16px; letter-spacing: -.02em; }.title-block > span:not(.divider) { font-size: 13px; font-weight: 650; }.title-block small { color: #8993a2; font-size: 10px; letter-spacing: .06em; text-transform: uppercase; }.divider { width: 1px; height: 18px; background: #dce1e7; }
.status-strip { display: flex; align-items: center; gap: 5px; margin-left: auto; }.status-item { display: flex; align-items: center; gap: 6px; padding: 6px 9px; border: 1px solid #e7eaee; border-radius: 999px; color: #596577; background: #fafafa; font-size: 10px; cursor: pointer; }.status-dot { width: 7px; height: 7px; border-radius: 50%; }.status-dot.online { background: #19a77c; box-shadow: 0 0 0 0 rgba(25,167,124,.38); animation: breathe 2.2s infinite; }
.status-dot.offline{background:var(--trace-red)}
.top-actions { display: flex; align-items: center; gap: 6px; margin-left: 10px; }.icon-button { position: relative; display: grid; place-items: center; width: 31px; height: 31px; border: 0; border-radius: 9px; color: #6c7788; background: transparent; cursor: pointer; }.icon-button:hover { background: #f0f2f4; }.icon-button b { position: absolute; right: 7px; top: 6px; width: 5px; height: 5px; border: 1px solid #fff; border-radius: 50%; background: var(--trace-red); }.avatar { display: grid; place-items: center; width: 30px; height: 30px; margin-left: 3px; border-radius: 10px; color: #fff; background: #253041; font-size: 10px; font-weight: 700; }
.realtime{font-family:var(--trace-font-mono)}
@keyframes breathe { 50% { box-shadow: 0 0 0 5px rgba(25,167,124,0); } }
.status-backdrop{position:fixed;inset:0;z-index:80;display:grid;place-items:start center;padding-top:80px;background:rgba(28,35,44,.2);backdrop-filter:blur(3px)}.status-modal{width:430px;border:1px solid #dce1e6;border-radius:17px;background:#fff;box-shadow:0 24px 70px rgba(30,41,59,.23);overflow:hidden}.status-modal>header{display:flex;align-items:center;justify-content:space-between;padding:17px 18px;border-bottom:1px solid #e7eaed}.status-modal header small{color:var(--trace-red);font-size:8px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}.status-modal h2{margin:3px 0 0;font-size:18px}.status-modal header button{display:grid;place-items:center;width:30px;height:30px;border:0;border-radius:8px;background:#f0f2f4;cursor:pointer}.health-hero{display:flex;align-items:center;gap:12px;margin:16px;padding:14px;border:1px solid #dceae5;border-radius:12px;background:#f2fbf8}.health-hero .status-dot{width:10px;height:10px}.health-hero strong,.health-hero span{display:block}.health-hero strong{font-size:11px}.health-hero span{margin-top:3px;color:#788493;font-size:8px}.status-modal dl{margin:0 17px}.status-modal dl div{display:flex;justify-content:space-between;padding:10px 2px;border-bottom:1px solid #edf0f2;font-size:9px}.status-modal dt{color:#7e8998}.status-modal dd{margin:0;font:600 9px var(--trace-font-mono)}.status-modal footer{padding:14px 17px}.status-modal footer a{display:block;padding:9px;border:1px solid var(--trace-red);border-radius:9px;color:#fff;text-align:center;background:var(--trace-red);font-size:9px;font-weight:700}
</style>
