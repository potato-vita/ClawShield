<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import {
  Bell,
  Check,
  CheckCircle2,
  ChevronRight,
  Database,
  Eye,
  EyeOff,
  Globe2,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  PanelLeftClose,
  PanelLeftOpen,
  RotateCcw,
  Save,
  Server,
  Settings2,
  ShieldCheck,
} from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";
import { useUiStore } from "@/stores/uiStore";

type SectionId = "general" | "connection" | "privacy" | "notifications";
type ConnectionState = "idle" | "testing" | "connected";

const sections = [
  { id: "general", label: "常规设置", description: "工作台显示与交互", icon: Settings2 },
  { id: "connection", label: "服务连接", description: "Core 与插件配置", icon: Database },
  { id: "privacy", label: "隐私保护", description: "留存与脱敏策略", icon: LockKeyhole },
  { id: "notifications", label: "通知提醒", description: "告警与消息投递", icon: Bell },
] as const;

const defaults = {
  language: "简体中文",
  timezone: "Asia/Shanghai (UTC+08:00)",
  defaultLanding: "Runtime Audit",
  compactTables: true,
  animations: true,
  coreUrl: "http://127.0.0.1:8787",
  apiToken: "ts_demo_6B3W9Z2R8K",
  requestTimeout: "1200",
  saveRawPayloads: false,
  hashSensitiveValues: true,
  redactPreview: true,
  retentionDays: "30",
  criticalAlerts: true,
  reviewAlerts: true,
  systemAlerts: false,
  emailDigest: "Daily at 09:00",
  alertEmail: "security@acme.dev",
};

const settings = reactive({ ...defaults });
const ui = useUiStore();
const activeSection = ref<SectionId>("general");
const dirty = ref(false);
const showToken = ref(false);
const toast = ref("");
const connectionState = ref<ConnectionState>("idle");
const activeMeta = computed(() => sections.find((section) => section.id === activeSection.value) ?? sections[0]);

function markDirty() {
  dirty.value = true;
  connectionState.value = "idle";
}

function toggle<K extends keyof typeof settings>(key: K) {
  if (typeof settings[key] !== "boolean") return;
  (settings[key] as boolean) = !settings[key];
  markDirty();
}

function showToast(message: string) {
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) toast.value = "";
  }, 2500);
}

function saveSettings() {
  dirty.value = false;
  showToast("设置已保存到当前演示工作台。 ");
}

function restoreDefaults() {
  Object.assign(settings, defaults);
  dirty.value = true;
  connectionState.value = "idle";
  showToast("已恢复默认值，请保存以保留本次修改。 ");
}

function testConnection() {
  if (connectionState.value === "testing") return;
  connectionState.value = "testing";
  window.setTimeout(() => {
    connectionState.value = "connected";
    showToast("Core 连接验证成功，耗时 38 ms。 ");
  }, 760);
}
</script>

<template>
  <ProductPageLayout eyebrow="工作台偏好" title="系统设置" description="配置控制台体验、服务连接与本地数据处理方式。">
    <template #actions>
      <div class="page-actions">
        <span v-if="dirty" class="unsaved-dot"><i /> 有未保存的修改</span>
        <button class="restore-button" type="button" @click="restoreDefaults"><RotateCcw :size="14" /> 恢复默认</button>
        <button class="save-button" type="button" @click="saveSettings"><Save :size="14" /> 保存修改</button>
      </div>
    </template>

    <div v-if="toast" class="settings-toast"><CheckCircle2 :size="16" /> {{ toast }}</div>

    <section class="settings-shell" :class="{ 'nav-collapsed': ui.settingsNavigationCollapsed }">
      <aside class="settings-nav" :class="{ collapsed: ui.settingsNavigationCollapsed }">
        <header v-if="!ui.settingsNavigationCollapsed"><div><span>控制台设置</span><small>演示工作台</small></div><button class="settings-nav-toggle" type="button" title="收起设置导航" @click="ui.settingsNavigationCollapsed = true"><PanelLeftClose :size="16" /></button></header>
        <button v-else class="settings-nav-toggle collapsed-toggle" type="button" title="展开设置导航" @click="ui.settingsNavigationCollapsed = false"><PanelLeftOpen :size="16" /></button>
        <nav aria-label="设置分类">
          <button v-for="section in sections" :key="section.id" type="button" :class="{ active: activeSection === section.id }" @click="activeSection = section.id">
            <span><component :is="section.icon" :size="16" /></span>
            <div v-if="!ui.settingsNavigationCollapsed"><strong>{{ section.label }}</strong><small>{{ section.description }}</small></div>
            <ChevronRight v-if="!ui.settingsNavigationCollapsed" :size="14" />
          </button>
        </nav>
        <div v-if="!ui.settingsNavigationCollapsed" class="config-version"><ShieldCheck :size="15" /><span><strong>配置状态正常</strong><small>4 分钟前保存</small></span></div>
      </aside>

      <div class="settings-content" @input="markDirty" @change="markDirty">
        <header class="section-heading">
          <div><span><component :is="activeMeta.icon" :size="17" /></span><div><small>设置分类</small><h2>{{ activeMeta.label }}</h2></div></div>
          <p>{{ activeMeta.description }}</p>
        </header>

        <template v-if="activeSection === 'general'">
          <section class="setting-card preference-card">
            <header><div><Globe2 :size="16" /><span><strong>语言与显示</strong><small>选择数据在当前浏览器中的呈现方式。</small></span></div></header>
            <div class="field-grid">
              <label><span>界面语言</span><select v-model="settings.language"><option value="English (US)">英语（美国）</option><option value="简体中文">简体中文</option><option value="Japanese">日语</option></select></label>
              <label><span>时区</span><select v-model="settings.timezone"><option value="Asia/Shanghai (UTC+08:00)">上海（UTC+08:00）</option><option value="UTC">UTC</option><option value="America/Los_Angeles (UTC-08:00)">洛杉矶（UTC-08:00）</option></select></label>
              <label class="wide-field"><span>默认首页</span><select v-model="settings.defaultLanding"><option value="Runtime Audit">运行时审计</option><option value="Sessions">会话</option><option value="Security Assistant">安全助手</option></select></label>
            </div>
          </section>
          <section class="setting-card">
            <header><div><Settings2 :size="16" /><span><strong>界面行为</strong><small>调整演示时的信息密度与动态效果。</small></span></div></header>
            <div class="setting-rows">
              <div><span><strong>紧凑型审计表格</strong><small>减少滚动，在同一屏中展示更多工具调用与事件。</small></span><button class="switch" :class="{ enabled: settings.compactTables }" type="button" :aria-pressed="settings.compactTables" @click="toggle('compactTables')"><i /></button></div>
              <div><span><strong>界面动画</strong><small>切换面板和状态时使用轻量、流畅的过渡效果。</small></span><button class="switch" :class="{ enabled: settings.animations }" type="button" :aria-pressed="settings.animations" @click="toggle('animations')"><i /></button></div>
            </div>
          </section>
        </template>

        <template v-else-if="activeSection === 'connection'">
          <section class="connection-hero">
            <div class="connection-icon"><Server :size="24" /></div>
            <div><small>TraceShield Core</small><h3>{{ connectionState === "connected" ? "连接验证成功" : "主要审计端点" }}</h3><p>{{ connectionState === "connected" ? "Core API 已成功响应，耗时 38 ms。" : "用于实时审计查询、事件流传输与运行状态检查。" }}</p></div>
            <span :class="connectionState"><i /> {{ connectionState === "connected" ? "已连接" : connectionState === "testing" ? "正在测试" : "尚未测试" }}</span>
          </section>
          <section class="setting-card connection-form">
            <header><div><Database :size="16" /><span><strong>Core API 连接</strong><small>配置变更仅保留在当前演示环境中。</small></span></div></header>
            <div class="field-grid">
              <label class="wide-field"><span>Core 基础 URL</span><div class="input-with-icon"><Globe2 :size="14" /><input v-model="settings.coreUrl" spellcheck="false" /></div></label>
              <label class="wide-field"><span>API 令牌</span><div class="input-with-icon"><KeyRound :size="14" /><input v-model="settings.apiToken" :type="showToken ? 'text' : 'password'" spellcheck="false" /><button type="button" :aria-label="showToken ? '隐藏 API 令牌' : '显示 API 令牌'" @click="showToken = !showToken"><EyeOff v-if="showToken" :size="14" /><Eye v-else :size="14" /></button></div></label>
              <label><span>请求超时</span><div class="unit-input"><input v-model="settings.requestTimeout" inputmode="numeric" /><b>ms</b></div></label>
              <div class="test-field"><span>连通性</span><button type="button" :disabled="connectionState === 'testing'" @click="testConnection"><LoaderCircle v-if="connectionState === 'testing'" class="spin" :size="14" /><Check v-else-if="connectionState === 'connected'" :size="14" /><Server v-else :size="14" />{{ connectionState === "testing" ? "测试中…" : connectionState === "connected" ? "再次测试" : "测试连接" }}</button></div>
            </div>
          </section>
          <section class="plugin-strip"><div><span class="plugin-mark"><ShieldCheck :size="18" /></span><span><small>OpenClaw 插件</small><strong>最近一次心跳在 12 秒前</strong></span></div><dl><div><dt>版本</dt><dd>0.4.2</dd></div><div><dt>队列</dt><dd>0 个事件</dd></div><div><dt>模式</dt><dd>影子模式</dd></div></dl></section>
        </template>

        <template v-else-if="activeSection === 'privacy'">
          <section class="privacy-banner"><LockKeyhole :size="22" /><div><small>隐私策略</small><h3>默认最小化采集</h3><p>除非明确启用原始数据采集，否则 TraceShield 仅保存哈希值与安全预览。</p></div><span>A</span></section>
          <section class="setting-card">
            <header><div><ShieldCheck :size="16" /><span><strong>采集控制</strong><small>决定审计证据中需要保留哪些数据。</small></span></div></header>
            <div class="setting-rows">
              <div><span><strong>保存原始事件载荷</strong><small>存储完整的事件内容，不建议在共享演示环境中启用。</small></span><button class="switch" :class="{ enabled: settings.saveRawPayloads }" type="button" :aria-pressed="settings.saveRawPayloads" @click="toggle('saveRawPayloads')"><i /></button></div>
              <div><span><strong>对敏感值进行哈希处理</strong><small>将匹配到的敏感信息替换为稳定且可搜索的指纹。</small></span><button class="switch" :class="{ enabled: settings.hashSensitiveValues }" type="button" :aria-pressed="settings.hashSensitiveValues" @click="toggle('hashSensitiveValues')"><i /></button></div>
              <div><span><strong>内容预览脱敏</strong><small>遮盖邮箱、令牌、密钥和授权请求头。</small></span><button class="switch" :class="{ enabled: settings.redactPreview }" type="button" :aria-pressed="settings.redactPreview" @click="toggle('redactPreview')"><i /></button></div>
            </div>
          </section>
          <section class="privacy-grid">
            <article><label><span>审计数据保留期限</span><select v-model="settings.retentionDays"><option value="7">7 天</option><option value="30">30 天</option><option value="90">90 天</option></select></label><p>过期证据将在下一个维护周期中从控制台移除。</p></article>
            <article class="redaction-preview"><small>脱敏预览</small><code>Authorization: Bearer ••••••••</code><code>user: al•••@acme.dev</code><span><CheckCircle2 :size="13" /> 已遮盖 2 项敏感值</span></article>
          </section>
        </template>

        <template v-else>
          <section class="notification-summary"><span><Bell :size="21" /></span><div><small>告警路由</small><h3>只推送需要处理的信号</h3><p>仅在 TraceShield 需要关注时通知团队，避免日常审计流量造成消息轰炸。</p></div><b>2 项已启用</b></section>
          <section class="setting-card">
            <header><div><Bell :size="16" /><span><strong>运行时告警</strong><small>选择哪些事件需要生成通知。</small></span></div></header>
            <div class="setting-rows alert-rows">
              <div><i class="critical-marker" /><span><strong>高危拦截</strong><small>高置信度的不安全操作被阻止时立即告警。</small></span><button class="switch" :class="{ enabled: settings.criticalAlerts }" type="button" :aria-pressed="settings.criticalAlerts" @click="toggle('criticalAlerts')"><i /></button></div>
              <div><i class="review-marker" /><span><strong>需要审批</strong><small>操作人员必须审核工具调用时发送通知。</small></span><button class="switch" :class="{ enabled: settings.reviewAlerts }" type="button" :aria-pressed="settings.reviewAlerts" @click="toggle('reviewAlerts')"><i /></button></div>
              <div><i class="system-marker" /><span><strong>系统健康状态</strong><small>监测 Core 断连、队列压力和插件心跳超时。</small></span><button class="switch" :class="{ enabled: settings.systemAlerts }" type="button" :aria-pressed="settings.systemAlerts" @click="toggle('systemAlerts')"><i /></button></div>
            </div>
          </section>
          <section class="setting-card delivery-card">
            <header><div><Globe2 :size="16" /><span><strong>邮件投递</strong><small>配置演示摘要的接收位置。</small></span></div></header>
            <div class="field-grid"><label><span>摘要发送频率</span><select v-model="settings.emailDigest"><option value="Daily at 09:00">每天 09:00</option><option value="Weekly on Monday">每周一</option><option value="Never">从不发送</option></select></label><label><span>接收地址</span><input v-model="settings.alertEmail" type="email" /></label></div>
          </section>
        </template>

        <footer class="settings-footer"><span>所有修改仅保存在当前演示界面中。</span><button type="button" @click="saveSettings"><Save :size="13" /> 保存{{ activeMeta.label }}</button></footer>
      </div>
    </section>
  </ProductPageLayout>
</template>

<style scoped>
.page-actions{display:flex;align-items:center;gap:8px}.page-actions button{display:flex;align-items:center;gap:6px;padding:8px 11px;border-radius:9px;font-size:9px;font-weight:700;cursor:pointer}.restore-button{border:1px solid var(--trace-border);color:#697586;background:#fff}.save-button{border:1px solid var(--trace-red);color:#fff;background:var(--trace-red);box-shadow:0 6px 14px rgba(201,31,55,.14)}.unsaved-dot{display:flex;align-items:center;gap:6px;margin-right:3px;color:#a56a00;font-size:8px}.unsaved-dot i{width:6px;height:6px;border-radius:50%;background:#d5962e;box-shadow:0 0 0 3px #fff4df}.settings-toast{position:fixed;z-index:40;top:70px;right:24px;display:flex;align-items:center;gap:8px;padding:10px 13px;border:1px solid #cfe6dd;border-radius:10px;color:#166f57;background:#f5fffb;box-shadow:0 14px 35px rgba(30,41,59,.13);font-size:9px;animation:toast-in .2s ease}.settings-shell{display:grid;grid-template-columns:232px minmax(0,1fr);min-height:610px;overflow:hidden;border:1px solid var(--trace-border);border-radius:16px;background:#fff;box-shadow:0 13px 34px rgba(30,41,59,.055);transition:grid-template-columns 280ms cubic-bezier(.22,1,.36,1)}.settings-shell.nav-collapsed{grid-template-columns:58px minmax(0,1fr)}
.settings-nav{display:flex;flex-direction:column;padding:17px 11px;border-right:1px solid #e2e6ea;background:#f4f5f6;transition:padding 260ms cubic-bezier(.22,1,.36,1)}.settings-nav>header{display:flex;align-items:center;justify-content:space-between;gap:7px;padding:1px 0 12px 7px}.settings-nav>header span,.settings-nav>header small{display:block}.settings-nav>header span{font-size:10px;font-weight:750}.settings-nav>header small{margin-top:4px;color:#8994a1;font-size:7px}.settings-nav nav{display:grid;gap:5px}.settings-nav nav button{display:grid;grid-template-columns:31px minmax(0,1fr) 15px;align-items:center;gap:8px;width:100%;padding:9px 8px;border:1px solid transparent;border-radius:10px;text-align:left;color:#758191;background:transparent;cursor:pointer;transition:background-color 160ms ease,border-color 160ms ease,transform 160ms ease,padding 240ms ease}.settings-nav nav button:hover{transform:translateX(2px);border-color:#dfe3e7;background:#fff}.settings-nav nav button.active{border-color:#e8d2d6;color:var(--trace-ink);background:#fff;box-shadow:inset 3px 0 var(--trace-red),0 5px 13px rgba(30,41,59,.045)}.settings-nav nav button>span{display:grid;place-items:center;width:31px;height:31px;border-radius:9px;color:#7d8997;background:#e9ecef}.settings-nav nav button.active>span{color:var(--trace-red);background:#fff1f1}.settings-nav nav strong,.settings-nav nav small{display:block}.settings-nav nav strong{font-size:9px}.settings-nav nav small{margin-top:3px;color:#939ca7;font-size:7px}.settings-nav nav>button>svg{color:#a0a8b1}.config-version{display:flex;align-items:center;gap:8px;margin-top:auto;padding:11px;border:1px solid #dfe7e3;border-radius:10px;color:#197458;background:#f8fcfa}.config-version strong,.config-version small{display:block}.config-version strong{font-size:8px}.config-version small{margin-top:3px;color:#79a091;font-size:6px}.settings-nav-toggle{display:flex;flex:0 0 31px;align-items:center;justify-content:center;width:31px;min-height:31px;margin:0;padding:0;border:1px solid #dce1e6;border-radius:9px;color:#6d7988;background:#fff;cursor:pointer;transition:color 160ms ease,border-color 160ms ease}.settings-nav-toggle:hover{color:var(--trace-red);border-color:#e4b9c0}.settings-nav.collapsed{padding-right:7px;padding-left:7px}.settings-nav.collapsed nav button{grid-template-columns:1fr;justify-items:center;padding-right:4px;padding-left:4px}.settings-nav.collapsed nav button:hover{transform:translateY(-1px)}.settings-nav.collapsed .settings-nav-toggle{width:100%;margin:0 0 9px;padding:0}
.settings-content{display:flex;min-width:0;flex-direction:column;padding:21px 24px;background:linear-gradient(135deg,#fff 0%,#fff 70%,#fcfcfb 100%)}.section-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:15px;padding-bottom:14px;border-bottom:1px solid #e9ecef}.section-heading>div{display:flex;align-items:center;gap:10px}.section-heading>div>span{display:grid;place-items:center;width:37px;height:37px;border-radius:11px;color:var(--trace-red);background:#fff0f0}.section-heading small{color:#949da8;font-size:7px;text-transform:uppercase;letter-spacing:.07em}.section-heading h2{margin:3px 0 0;font-size:16px}.section-heading p{margin:0;color:#8a95a2;font-size:8px}.setting-card{margin-bottom:12px;border:1px solid #e1e5e9;border-radius:13px;background:#fff;box-shadow:0 6px 16px rgba(30,41,59,.035)}.setting-card>header{display:flex;align-items:center;justify-content:space-between;padding:13px 15px;border-bottom:1px solid #edf0f2}.setting-card>header>div{display:flex;align-items:center;gap:9px}.setting-card>header svg{color:#7d8997}.setting-card>header strong,.setting-card>header small{display:block}.setting-card>header strong{font-size:10px}.setting-card>header small{margin-top:3px;color:#8b96a3;font-size:7px}.field-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:15px}.field-grid label>span,.test-field>span{display:block;margin-bottom:6px;color:#697586;font-size:8px;font-weight:650}.field-grid select,.field-grid>label>input,.input-with-icon,.unit-input{width:100%;height:35px;border:1px solid #dfe4e8;border-radius:9px;outline:0;color:#344052;background:#fafbfb;font-size:9px}.field-grid select,.field-grid>label>input{padding:0 10px}.field-grid select:focus,.field-grid>label>input:focus,.input-with-icon:focus-within,.unit-input:focus-within{border-color:#d5a0a8;box-shadow:0 0 0 3px #fff3f3}.wide-field{grid-column:1/-1}.setting-rows>div{display:flex;align-items:center;gap:10px;min-height:58px;padding:11px 15px;border-top:1px solid #edf0f2}.setting-rows>div:first-child{border-top:0}.setting-rows>div>span{flex:1}.setting-rows strong,.setting-rows small{display:block}.setting-rows strong{font-size:9px}.setting-rows small{margin-top:4px;color:#8994a1;font-size:7px;line-height:1.45}.switch{flex:0 0 auto;width:36px;height:21px;padding:2px;border:0;border-radius:12px;background:#cbd2d9;cursor:pointer;transition:background-color 160ms ease}.switch>i{display:block;width:17px;height:17px;border-radius:50%;background:#fff;box-shadow:0 2px 5px rgba(30,41,59,.2);transition:transform 180ms cubic-bezier(.2,.8,.2,1)}.switch.enabled{background:var(--trace-red)}.switch.enabled>i{transform:translateX(15px)}
.connection-hero{display:grid;grid-template-columns:46px minmax(0,1fr) auto;align-items:center;gap:12px;margin-bottom:12px;padding:14px 16px;border:1px solid #dbe7e2;border-radius:13px;background:linear-gradient(105deg,#f5fbf8,#fff)}.connection-icon{display:grid;place-items:center;width:46px;height:46px;border-radius:13px;color:#168062;background:#e4f5ee}.connection-hero small{color:#6d8e82;font-size:7px;text-transform:uppercase}.connection-hero h3{margin:3px 0;font-size:13px}.connection-hero p{margin:0;color:#7c8a94;font-size:7px}.connection-hero>span{display:flex;align-items:center;gap:6px;padding:6px 8px;border:1px solid #dde3e6;border-radius:8px;color:#788491;background:#fff;font-size:7px}.connection-hero>span i{width:6px;height:6px;border-radius:50%;background:#aeb6bd}.connection-hero>span.connected{color:#14775a;border-color:#cfe7dd;background:#f5fffb}.connection-hero>span.connected i{background:#20a279;box-shadow:0 0 0 3px rgba(32,162,121,.1)}.connection-hero>span.testing i{background:#d29a30}.input-with-icon{display:flex;align-items:center;gap:8px;padding:0 9px}.input-with-icon>svg{color:#8d97a3}.input-with-icon input{flex:1;min-width:0;border:0;outline:0;background:transparent;font:8px var(--trace-font-mono)}.input-with-icon button{display:grid;place-items:center;padding:2px;border:0;color:#8a95a2;background:transparent;cursor:pointer}.unit-input{display:flex;align-items:center;padding:0 9px}.unit-input input{min-width:0;flex:1;border:0;outline:0;background:transparent;font:8px var(--trace-font-mono)}.unit-input b{color:#9aa3ad;font-size:7px}.test-field button{display:flex;align-items:center;justify-content:center;gap:6px;width:100%;height:35px;border:1px solid #d4dbe0;border-radius:9px;color:#556374;background:#fff;font-size:8px;font-weight:700;cursor:pointer}.test-field button:hover{border-color:#b9c3ca}.test-field button:disabled{cursor:wait}.spin{animation:spin .8s linear infinite}.plugin-strip{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border:1px solid #e1e5e9;border-radius:13px;background:#fafbfb}.plugin-strip>div{display:flex;align-items:center;gap:9px}.plugin-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:10px;color:#fff;background:#293440}.plugin-strip small,.plugin-strip strong{display:block}.plugin-strip small{color:#8b96a3;font-size:7px}.plugin-strip strong{margin-top:3px;font-size:9px}.plugin-strip dl{display:flex;gap:25px;margin:0}.plugin-strip dl div{min-width:62px}.plugin-strip dt{color:#929ca7;font-size:6px;text-transform:uppercase}.plugin-strip dd{margin:3px 0 0;font:8px var(--trace-font-mono)}
.privacy-banner{display:grid;grid-template-columns:42px minmax(0,1fr) 38px;align-items:center;gap:12px;margin-bottom:12px;padding:14px 16px;border:1px solid #dce5e9;border-radius:13px;color:#eaf2f5;background:linear-gradient(112deg,#1b2933,#273a43)}.privacy-banner>svg{color:#79d4b1}.privacy-banner small{color:#96adb7;font-size:7px;text-transform:uppercase}.privacy-banner h3{margin:3px 0;font-size:13px}.privacy-banner p{margin:0;color:#9eb0b9;font-size:7px}.privacy-banner>span{display:grid;place-items:center;width:34px;height:34px;border:1px solid #45606a;border-radius:50%;color:#7cdbb7;font:800 13px var(--trace-font-mono)}.privacy-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:12px}.privacy-grid article{padding:14px;border:1px solid #e1e5e9;border-radius:12px;background:#fff}.privacy-grid label>span{display:block;margin-bottom:6px;font-size:8px;font-weight:700}.privacy-grid select{width:100%;height:34px;padding:0 9px;border:1px solid #dfe4e8;border-radius:8px;background:#fafbfb;font-size:8px}.privacy-grid p{margin:8px 0 0;color:#8b95a2;font-size:7px;line-height:1.5}.redaction-preview{display:flex;flex-direction:column;gap:7px;color:#dbe6ea;background:#1b2831!important}.redaction-preview>small{color:#8fa2ac;font-size:7px;text-transform:uppercase}.redaction-preview code{padding:7px 8px;border:1px solid #34444e;border-radius:7px;color:#b6c5cc;background:#142029;font-size:7px}.redaction-preview span{display:flex;align-items:center;gap:5px;color:#66caa4;font-size:7px}
.notification-summary{display:grid;grid-template-columns:43px minmax(0,1fr) auto;align-items:center;gap:11px;margin-bottom:12px;padding:13px 15px;border:1px solid #ebdcd7;border-radius:13px;background:linear-gradient(105deg,#fff7f5,#fff)}.notification-summary>span{display:grid;place-items:center;width:43px;height:43px;border-radius:12px;color:var(--trace-red);background:#ffe9e7}.notification-summary small{color:#a28c88;font-size:7px;text-transform:uppercase}.notification-summary h3{margin:3px 0;font-size:13px}.notification-summary p{margin:0;color:#8e8a8a;font-size:7px}.notification-summary>b{padding:5px 8px;border-radius:7px;color:var(--trace-red);background:#fff0ef;font-size:7px}.alert-rows>div>i{width:7px;height:28px;border-radius:4px;background:#9ca7b2}.alert-rows>div>i.critical-marker{background:var(--trace-red)}.alert-rows>div>i.review-marker{background:#d0952d}.alert-rows>div>i.system-marker{background:#6687a4}.delivery-card{margin-bottom:0}
.settings-footer{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:13px;border-top:1px solid #edf0f2}.settings-footer span{color:#929ca7;font-size:7px}.settings-footer button{display:flex;align-items:center;gap:6px;padding:8px 10px;border:1px solid #dfe3e7;border-radius:8px;color:#5f6d7d;background:#fff;font-size:8px;font-weight:700;cursor:pointer}.settings-footer button:hover{border-color:#e3b3ba;color:var(--trace-red)}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes toast-in{from{opacity:0;transform:translateY(-7px)}}
</style>
