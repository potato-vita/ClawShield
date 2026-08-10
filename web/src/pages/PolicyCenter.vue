<script setup lang="ts">
import { ref } from "vue";
import { NMessageProvider } from "naive-ui";
import { Plus, ShieldCheck, X } from "lucide-vue-next";
import ProductPageLayout from "@/layouts/ProductPageLayout.vue";
import { useRuntimeStore } from "@/stores/runtimeStore";
import { createPolicy, updatePolicy } from "@/api/policies";
import { useMockData } from "@/api/client";
import {
  loadPolicyDemoState,
  mergePoliciesWithDemoState,
  rememberCreatedPolicy,
  savePolicyDemoState,
} from "@/utils/policyDemoStorage";
import type { Policy } from "@/types/policy";
import type { RiskLevel } from "@/types/session";

const templates = [
  {
    name: "禁止读取某类文件",
    ruleId: "deny_sensitive_file_pattern",
    severity: "high",
    action: "BLOCK",
    description: "拦截对已配置敏感文件类型的读取操作。",
  },
  {
    name: "禁止危险 shell 命令",
    ruleId: "deny_dangerous_shell",
    severity: "critical",
    action: "BLOCK",
    description: "在执行前拦截破坏性 Shell 命令。",
  },
  {
    name: "外部网络请求需要审批",
    ruleId: "review_external_network",
    severity: "medium",
    action: "REVIEW",
    description: "访问外部域名前必须经过审批。",
  },
  {
    name: "未知工具调用告警",
    ruleId: "alert_unknown_tool",
    severity: "low",
    action: "ALERT",
    description: "调用未注册工具时发出告警。",
  },
] as const;

const store = useRuntimeStore();
const showCreate = ref(false);
const selectedTemplate = ref(0);
const notice = ref("");
const demoState = loadPolicyDemoState();

const severityLabels: Record<RiskLevel, string> = {
  critical: "严重",
  high: "高风险",
  medium: "中风险",
  low: "低风险",
};
const actionLabels: Record<Policy["action"], string> = {
  BLOCK: "拦截",
  REVIEW: "审核",
  ALERT: "告警",
};
const policyNameLabels: Record<string, string> = {
  "Sensitive data exfiltration guard": "敏感数据外泄防护",
  "Dangerous shell command guard": "危险 Shell 命令防护",
  "External request approval": "外部请求审批",
  "Unknown tool observer": "未知工具监测",
};
const policyDescriptionLabels: Record<string, string> = {
  "Blocks sensitive derivatives from reaching untrusted destinations.": "防止敏感数据及其派生内容流向不可信目标。",
  "Blocks destructive or privilege-escalating shell commands.": "拦截破坏性或尝试提升权限的 Shell 命令。",
  "Requires review before tools contact unknown domains.": "工具访问未知域名前需要审核。",
  "Raises an alert for tools missing from the registry.": "调用未登记在注册表中的工具时发出告警。",
};
const policyName = (policy: Policy) => policyNameLabels[policy.name] ?? policy.name;
const policyDescription = (policy: Policy) =>
  policyDescriptionLabels[policy.description] ?? policy.description;
const lastHitLabel = (value: string) => {
  if (value === "Never") return "从未命中";
  if (value === "just now") return "刚刚";
  const relative = value.match(/^(\d+)([mhd]) ago$/);
  if (!relative) return value;
  const units: Record<string, string> = { m: "分钟", h: "小时", d: "天" };
  return `${relative[1]} ${units[relative[2] ?? ""] ?? ""}前`;
};

store.policies = mergePoliciesWithDemoState(store.policies, demoState);

const notify = (message: string) => {
  notice.value = message;
  window.setTimeout(() => {
    if (notice.value === message) notice.value = "";
  }, 3200);
};

const localPolicyId = () =>
  `policy-local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const toggle = async (policy: Policy) => {
  policy.enabled = !policy.enabled;
  demoState.enabledByPolicyId[policy.id] = policy.enabled;
  const savedLocally = savePolicyDemoState(demoState);
  const stateLabel = policy.enabled ? "已启用" : "已停用";

  if (useMockData) {
    notify(
      savedLocally
        ? `${policyName(policy)} ${stateLabel}，已保存到本地演示数据。`
        : `${policyName(policy)} ${stateLabel}，但浏览器未允许持久化。`,
    );
    return;
  }

  try {
    await updatePolicy(policy.id, { enabled: policy.enabled });
    notify(`${policyName(policy)} ${stateLabel}，已同步至 Core。`);
  } catch {
    notify(
      savedLocally
        ? `${policyName(policy)} ${stateLabel}；已本地保存，Core 暂不可用，待同步。`
        : `${policyName(policy)} ${stateLabel}；Core 暂不可用，且浏览器未允许持久化。`,
    );
  }
};

const addPolicy = async () => {
  const template = templates[selectedTemplate.value] ?? templates[0];
  const policy: Policy = {
    id: localPolicyId(),
    name: template.name,
    ruleId: template.ruleId,
    severity: template.severity,
    action: template.action,
    enabled: true,
    hitCount: 0,
    lastHitTime: "Never",
    description: template.description,
  };

  store.policies.unshift(policy);
  rememberCreatedPolicy(demoState, policy);
  let savedLocally = savePolicyDemoState(demoState);
  showCreate.value = false;

  if (useMockData) {
    notify(
      savedLocally
        ? `${policyName(policy)} 已创建并保存到本地演示数据。`
        : `${policyName(policy)} 已创建，但浏览器未允许持久化。`,
    );
    return;
  }

  const localId = policy.id;
  let remotePolicy: Policy;
  try {
    remotePolicy = await createPolicy({
      name: policy.name,
      ruleId: policy.ruleId,
      severity: policy.severity,
      action: policy.action,
      enabled: policy.enabled,
      description: policy.description,
    });
  } catch {
    notify(
      savedLocally
        ? `${policyName(policy)} 已本地保存，Core 暂不可用，待同步。`
        : `${policyName(policy)} 已在当前页创建，但 Core 和本地持久化均不可用。`,
    );
    return;
  }

  const latestEnabled = policy.enabled;
  Object.assign(policy, remotePolicy, { enabled: latestEnabled });
  rememberCreatedPolicy(demoState, policy, localId);
  savedLocally = savePolicyDemoState(demoState);

  if (remotePolicy.enabled !== latestEnabled) {
    try {
      await updatePolicy(policy.id, { enabled: latestEnabled });
    } catch {
      notify(
        savedLocally
          ? `${policyName(policy)} 已本地保存，最新开关状态待同步。`
          : `${policyName(policy)} 已创建，但最新开关状态未能持久化。`,
      );
      return;
    }
  }

  notify(`${policyName(policy)} 已创建并同步至 Core。`);
};
</script>
<template><NMessageProvider><ProductPageLayout eyebrow="策略引擎" title="策略中心" description="无需编辑 JSON，即可管理直观易懂的安全防护规则。"><template #actions><button type="button" class="create-button" @click="showCreate=true"><Plus :size="15"/> 从模板新建</button></template><div v-if="notice" class="toast" role="status" aria-live="polite">{{notice}}</div><section class="policy-grid"><article v-for="policy in store.policies" :key="policy.id" class="policy-card" :class="{disabled:!policy.enabled}"><header><span class="shield" :class="`severity-${policy.severity}`"><ShieldCheck :size="18"/></span><div><small>{{policy.ruleId}} · {{policy.enabled?'已启用':'已停用'}}</small><h2>{{policyName(policy)}}</h2></div><button type="button" class="switch" :class="{enabled:policy.enabled}" :aria-label="`${policy.enabled?'停用':'启用'}${policyName(policy)}`" :aria-pressed="policy.enabled" @click="toggle(policy)"><i/></button></header><p>{{policyDescription(policy)}}</p><dl><div><dt>风险等级</dt><dd :class="`severity-${policy.severity}`">{{severityLabels[policy.severity]}}</dd></div><div><dt>执行动作</dt><dd>{{actionLabels[policy.action]}}</dd></div><div><dt>命中次数</dt><dd>{{policy.hitCount}}</dd></div><div><dt>最近命中</dt><dd>{{lastHitLabel(policy.lastHitTime)}}</dd></div></dl></article></section><div v-if="showCreate" class="modal-backdrop" @click.self="showCreate=false"><section class="create-modal"><header><div><small>策略模板</small><h2>创建安全防护规则</h2></div><button type="button" aria-label="关闭创建策略窗口" @click="showCreate=false"><X :size="17"/></button></header><p>选择符合安全意图的模板，TraceShield 将使用安全默认值创建规则。</p><div class="template-list"><button v-for="(template,index) in templates" :key="template.ruleId" type="button" :class="{active:selectedTemplate===index}" @click="selectedTemplate=index"><strong>{{template.name}}</strong><span>{{template.description}}</span><code>{{actionLabels[template.action]}} · {{severityLabels[template.severity]}}</code></button></div><footer><button type="button" class="cancel" @click="showCreate=false">取消</button><button type="button" class="confirm" @click="addPolicy">创建策略</button></footer></section></div></ProductPageLayout></NMessageProvider></template>
<style scoped>.create-button{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid var(--trace-red);border-radius:10px;color:#fff;background:var(--trace-red);font-size:10px;font-weight:700;cursor:pointer}.toast{position:fixed;right:22px;top:70px;z-index:20;padding:10px 13px;border:1px solid #dfe4e9;border-radius:10px;color:#4f5d6f;background:#fff;box-shadow:0 14px 36px rgba(30,41,59,.16);font-size:10px;animation:toast-in .2s ease}.policy-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}.policy-card{padding:17px;border:1px solid var(--trace-border);border-radius:14px;background:#fff;box-shadow:0 6px 18px rgba(30,41,59,.04);transition:border-color 160ms ease,box-shadow 180ms ease,transform 190ms cubic-bezier(.2,.8,.2,1)}.policy-card:hover{border-color:#d7dce2;box-shadow:0 10px 23px rgba(30,41,59,.07);transform:translateY(-2px)}.policy-card header{display:grid;grid-template-columns:38px minmax(0,1fr) auto;align-items:center;gap:10px}.shield{display:grid;place-items:center;width:36px;height:36px;border-radius:10px;color:#637083;background:#eef1f4}.shield.severity-critical,.shield.severity-high{color:var(--trace-red);background:#fff0f0}.policy-card header small{color:#929ca8;font:7px var(--trace-font-mono)}.policy-card h2{margin:3px 0 0;font-size:12px}.policy-card>p{min-height:34px;margin:14px 0;color:#6d7988;font-size:9px;line-height:1.65}.switch{width:34px;height:20px;padding:2px;border:0;border-radius:12px;background:#cbd2d9;cursor:pointer;transition:background-color 160ms ease}.switch i{display:block;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 2px 5px rgba(30,41,59,.2);transition:transform 180ms cubic-bezier(.2,.8,.2,1)}.switch.enabled{background:var(--trace-red)}.switch.enabled i{transform:translateX(14px)}dl{display:grid;grid-template-columns:1fr 1fr;gap:1px;margin:0;border:1px solid #eaedf0;border-radius:9px;overflow:hidden}dl div{display:flex;justify-content:space-between;padding:8px;background:#fafbfb;font-size:8px}dt{color:#8b95a2}dd{margin:0;font:700 8px var(--trace-font-mono);text-transform:uppercase}dd.severity-critical,dd.severity-high{color:var(--trace-red)}.modal-backdrop{position:fixed;inset:0;z-index:30;display:grid;place-items:center;background:rgba(27,34,44,.24);backdrop-filter:blur(3px)}.create-modal{width:500px;padding:19px;border:1px solid #dce1e6;border-radius:17px;background:#fff;box-shadow:0 24px 60px rgba(30,41,59,.2)}.create-modal header{display:flex;justify-content:space-between}.create-modal header small{color:var(--trace-red);font-size:8px;text-transform:uppercase}.create-modal h2{margin:4px 0;font-size:18px}.create-modal header button{display:grid;place-items:center;width:30px;height:30px;border:0;border-radius:8px;background:#f1f3f4;cursor:pointer}.create-modal>p{color:#738091;font-size:9px}.template-list{display:grid;gap:7px;margin:15px 0}.template-list button{position:relative;padding:11px 90px 11px 12px;border:1px solid #e1e5e9;border-radius:10px;text-align:left;background:#fff;cursor:pointer;transition:border-color 160ms ease,background-color 160ms ease}.template-list button.active{border-color:var(--trace-red);background:#fff8f7;box-shadow:inset 3px 0 var(--trace-red)}.template-list strong,.template-list span{display:block}.template-list strong{font-size:10px}.template-list span{margin-top:3px;color:#788493;font-size:8px}.template-list code{position:absolute;right:10px;top:50%;color:#8b95a2;font-size:7px;transform:translateY(-50%)}.create-modal footer{display:flex;justify-content:flex-end;gap:8px}.create-modal footer button{padding:8px 12px;border-radius:9px;font-size:9px;cursor:pointer}.cancel{border:1px solid #dfe3e7;background:#fff}.confirm{border:1px solid var(--trace-red);color:#fff;background:var(--trace-red)}@keyframes toast-in{from{opacity:0;transform:translateY(-7px)}}</style>
