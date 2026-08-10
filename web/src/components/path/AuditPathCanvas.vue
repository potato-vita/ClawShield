<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import {
  Handle,
  MarkerType,
  Position,
  VueFlow,
  useVueFlow,
  type Edge as VueFlowEdge,
  type Node as VueFlowNode,
  type ViewportTransform,
} from "@vue-flow/core";
import { Focus, Maximize2, Minus, Plus } from "lucide-vue-next";
import type { GraphEdge, GraphNode } from "@/types/graph";
import PathLegend from "./PathLegend.vue";
import PathNode from "./PathNode.vue";

const props = defineProps<{ nodes: GraphNode[]; edges: GraphEdge[]; selectedNodeId?: string }>();
defineEmits<{ select: [node: GraphNode] }>();

const FLOW_ID = "runtime-audit-path";
const NODE_WIDTH = 174;
const NODE_HEIGHT = 58;
const CHAIN_COLUMNS = 6;
const CHAIN_X_GAP = 232;
const CHAIN_Y_GAP = 178;
const LAYER_X_GAP = 226;
const LAYER_Y_GAP = 98;

interface AuditNodeData {
  auditNode: GraphNode;
  hasIncoming: boolean;
  hasOutgoing: boolean;
}

interface LayoutNode {
  position: { x: number; y: number };
  sourcePosition: Position;
  targetPosition: Position;
}

const { fitView, getViewport, setCenter, zoomIn, zoomOut, zoomTo } = useVueFlow({ id: FLOW_ID });
const flowReady = ref(false);
const zoomLevel = ref(1);

const validEdges = computed(() => {
  const ids = new Set(props.nodes.map((item) => item.id));
  return props.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));
});

const graphOrder = computed(() => {
  const nodeIndex = new Map(props.nodes.map((item, index) => [item.id, index]));
  const indegree = new Map(props.nodes.map((item) => [item.id, 0]));
  const outgoing = new Map(props.nodes.map((item) => [item.id, [] as string[]]));

  for (const edge of validEdges.value) {
    indegree.set(edge.target, (indegree.get(edge.target) ?? 0) + 1);
    outgoing.get(edge.source)?.push(edge.target);
  }

  const queue = props.nodes
    .filter((item) => (indegree.get(item.id) ?? 0) === 0)
    .map((item) => item.id)
    .sort((a, b) => (nodeIndex.get(a) ?? 0) - (nodeIndex.get(b) ?? 0));
  const ordered: string[] = [];
  const depth = new Map(props.nodes.map((item) => [item.id, 0]));

  while (queue.length) {
    const current = queue.shift()!;
    ordered.push(current);
    for (const target of outgoing.get(current) ?? []) {
      depth.set(target, Math.max(depth.get(target) ?? 0, (depth.get(current) ?? 0) + 1));
      const remaining = (indegree.get(target) ?? 1) - 1;
      indegree.set(target, remaining);
      if (remaining === 0) {
        queue.push(target);
        queue.sort((a, b) => (nodeIndex.get(a) ?? 0) - (nodeIndex.get(b) ?? 0));
      }
    }
  }

  // Method snapshots should be acyclic. Keeping cyclic or isolated leftovers visible is
  // still more useful than silently dropping them from the investigation canvas.
  for (const item of props.nodes) {
    if (!ordered.includes(item.id)) ordered.push(item.id);
  }

  return { ordered, depth };
});

const isLinearChain = computed(() => {
  if (props.nodes.length <= 1) return true;
  if (validEdges.value.length !== props.nodes.length - 1) return false;
  const incoming = new Map(props.nodes.map((item) => [item.id, 0]));
  const outgoing = new Map(props.nodes.map((item) => [item.id, 0]));
  for (const edge of validEdges.value) {
    incoming.set(edge.target, (incoming.get(edge.target) ?? 0) + 1);
    outgoing.set(edge.source, (outgoing.get(edge.source) ?? 0) + 1);
  }
  return (
    props.nodes.filter((item) => (incoming.get(item.id) ?? 0) === 0).length === 1 &&
    props.nodes.every((item) => (incoming.get(item.id) ?? 0) <= 1 && (outgoing.get(item.id) ?? 0) <= 1)
  );
});

const layout = computed(() => {
  const result = new Map<string, LayoutNode>();
  const order = graphOrder.value.ordered;

  if (isLinearChain.value) {
    order.forEach((id, index) => {
      const row = Math.floor(index / CHAIN_COLUMNS);
      const indexInRow = index % CHAIN_COLUMNS;
      const column = row % 2 === 0 ? indexInRow : CHAIN_COLUMNS - 1 - indexInRow;
      const beginsNewRow = indexInRow === 0 && row > 0;
      const endsRow = indexInRow === CHAIN_COLUMNS - 1 && index < order.length - 1;
      result.set(id, {
        position: { x: column * CHAIN_X_GAP, y: row * CHAIN_Y_GAP },
        targetPosition: beginsNewRow ? Position.Top : row % 2 === 0 ? Position.Left : Position.Right,
        sourcePosition: endsRow ? Position.Bottom : row % 2 === 0 ? Position.Right : Position.Left,
      });
    });
    return result;
  }

  const layers = new Map<number, string[]>();
  for (const id of order) {
    const depth = graphOrder.value.depth.get(id) ?? 0;
    const layer = layers.get(depth) ?? [];
    layer.push(id);
    layers.set(depth, layer);
  }
  const tallestLayer = Math.max(1, ...Array.from(layers.values(), (items) => items.length));
  for (const [depth, ids] of layers) {
    const offset = ((tallestLayer - ids.length) * LAYER_Y_GAP) / 2;
    ids.forEach((id, index) => {
      result.set(id, {
        position: { x: depth * LAYER_X_GAP, y: offset + index * LAYER_Y_GAP },
        targetPosition: Position.Left,
        sourcePosition: Position.Right,
      });
    });
  }
  return result;
});

const incomingIds = computed(() => new Set(validEdges.value.map((edge) => edge.target)));
const outgoingIds = computed(() => new Set(validEdges.value.map((edge) => edge.source)));

const flowNodes = computed<VueFlowNode<AuditNodeData>[]>(() =>
  props.nodes.map((item) => {
    const placed = layout.value.get(item.id) ?? {
      position: { x: 0, y: 0 },
      targetPosition: Position.Left,
      sourcePosition: Position.Right,
    };
    return {
      id: item.id,
      type: "audit",
      position: placed.position,
      targetPosition: placed.targetPosition,
      sourcePosition: placed.sourcePosition,
      draggable: false,
      selectable: false,
      connectable: false,
      focusable: true,
      ariaLabel: `${item.label}，风险等级 ${item.risk}`,
      data: {
        auditNode: item,
        hasIncoming: incomingIds.value.has(item.id),
        hasOutgoing: outgoingIds.value.has(item.id),
      },
    };
  }),
);

const edgeLabel = (value?: string) => {
  if (!value || value === "flow") return undefined;
  const labels: Record<string, string> = {
    "pre-execution": "执行前审计",
    classified: "已分类",
    untrusted: "不可信",
    dependency: "依赖",
  };
  return labels[value] ?? value.replaceAll("_", " ");
};

const flowEdges = computed<VueFlowEdge[]>(() => {
  const nodesById = new Map(props.nodes.map((item) => [item.id, item]));
  return validEdges.value.map((edge) => {
    const target = nodesById.get(edge.target);
    const source = nodesById.get(edge.source);
    const isRisk =
      target?.decision === "block" ||
      target?.risk === "critical" ||
      source?.risk === "critical" ||
      target?.type === "blocked";
    const isEvidence = edge.kind === "evidence";
    const color = isRisk ? "#c91f37" : isEvidence ? "#c98218" : "#8e9aa7";
    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      label: edgeLabel(edge.label),
      animated: isRisk && (props.selectedNodeId === edge.source || props.selectedNodeId === edge.target),
      selectable: false,
      focusable: false,
      markerEnd: { type: MarkerType.ArrowClosed, color, width: 18, height: 18 },
      style: { stroke: color, strokeWidth: isRisk ? 1.8 : 1.35 },
      labelStyle: { fill: color, fontSize: 8, fontWeight: 700 },
      labelShowBg: true,
      labelBgStyle: { fill: "#ffffff", fillOpacity: 0.94 },
      labelBgPadding: [4, 3],
      labelBgBorderRadius: 5,
    };
  });
});

const graphTitle = computed(() => {
  const ordered = graphOrder.value.ordered;
  const byId = new Map(props.nodes.map((item) => [item.id, item]));
  const first = byId.get(ordered[0] ?? "")?.label ?? "运行入口";
  const last = byId.get(ordered.at(-1) ?? "")?.label ?? "执行结果";
  return first === last ? first : `${first} → ${last}`;
});

const layoutLabel = computed(() => (isLinearChain.value && props.nodes.length > CHAIN_COLUMNS ? "蛇形长链" : isLinearChain.value ? "线性链路" : "分层图谱"));
const zoomPercent = computed(() => `${Math.round(zoomLevel.value * 100)}%`);

const fitAll = () => fitView({ padding: 0.16, minZoom: 0.18, maxZoom: 1, duration: 360 });
const resetZoom = () => zoomTo(1, { duration: 260 });

const focusSelected = async (id = props.selectedNodeId) => {
  if (!id || !flowReady.value) return;
  const placed = layout.value.get(id);
  if (!placed) return;
  await nextTick();
  const currentZoom = getViewport().zoom;
  const targetZoom = Math.min(1.08, Math.max(0.82, currentZoom));
  await setCenter(placed.position.x + NODE_WIDTH / 2, placed.position.y + NODE_HEIGHT / 2, {
    zoom: targetZoom,
    duration: 320,
  });
};

const handleInit = () => {
  flowReady.value = true;
  requestAnimationFrame(() => void fitAll());
  window.setTimeout(() => void fitAll(), 180);
};

const handleViewportChange = (viewport: ViewportTransform) => {
  zoomLevel.value = viewport.zoom;
};

watch(
  () => props.selectedNodeId,
  (current, previous) => {
    if (current && current !== previous) void focusSelected(current);
  },
  { flush: "post" },
);

watch(
  () => `${props.nodes.map((item) => item.id).join("|")}::${props.edges.map((edge) => edge.id).join("|")}`,
  async () => {
    if (!flowReady.value) return;
    await nextTick();
    requestAnimationFrame(() => void fitAll());
  },
  { flush: "post" },
);
</script>

<template>
  <section class="path-canvas">
    <header class="canvas-header">
      <div class="graph-heading">
        <small>当前风险图谱 · {{ nodes.length }} 个节点 · {{ edges.length }} 条关系</small>
        <strong>{{ graphTitle }}</strong>
        <span>{{ layoutLabel }} · 拖动画布查看完整 Agent 执行链</span>
      </div>
      <PathLegend />
    </header>

    <div v-if="nodes.length" class="flow-shell">
      <VueFlow
        :id="FLOW_ID"
        class="audit-flow"
        :nodes="flowNodes"
        :edges="flowEdges"
        :min-zoom="0.16"
        :max-zoom="1.8"
        :nodes-draggable="false"
        :nodes-connectable="false"
        :elements-selectable="false"
        :edges-focusable="false"
        :zoom-on-scroll="true"
        :zoom-on-pinch="true"
        :zoom-on-double-click="false"
        :pan-on-drag="true"
        :pan-on-scroll="false"
        :prevent-scrolling="true"
        :fit-view-on-init="false"
        @init="handleInit"
        @viewport-change="handleViewportChange"
      >
        <template #node-audit="{ data, sourcePosition, targetPosition }">
          <div
            class="flow-node-shell"
            :class="[
              `risk-${data.auditNode.risk}`,
              {
                selected: selectedNodeId === data.auditNode.id,
                'decision-block': data.auditNode.decision === 'block',
              },
            ]"
          >
            <Handle
              v-if="data.hasIncoming"
              type="target"
              :position="targetPosition ?? Position.Left"
              :connectable="false"
            />
            <PathNode
              :node="data.auditNode"
              :selected="selectedNodeId === data.auditNode.id"
              @select="$emit('select', $event)"
            />
            <Handle
              v-if="data.hasOutgoing"
              type="source"
              :position="sourcePosition ?? Position.Right"
              :connectable="false"
            />
          </div>
        </template>
      </VueFlow>

      <div class="flow-toolbar" role="toolbar" aria-label="图谱缩放与定位">
        <button type="button" title="缩小图谱" aria-label="缩小图谱" @click="zoomOut({ duration: 180 })"><Minus :size="14" /></button>
        <button class="zoom-value" type="button" title="恢复 100%" @click="resetZoom">{{ zoomPercent }}</button>
        <button type="button" title="放大图谱" aria-label="放大图谱" @click="zoomIn({ duration: 180 })"><Plus :size="14" /></button>
        <i />
        <button type="button" title="定位当前节点" aria-label="定位当前节点" :disabled="!selectedNodeId" @click="focusSelected()"><Focus :size="14" /></button>
        <button class="fit-button" type="button" title="查看完整执行链" @click="fitAll"><Maximize2 :size="13" /><span>全览</span></button>
      </div>

      <div class="flow-tip"><span /> 滚轮缩放 · 拖动平移 · 点击节点查看详情</div>
    </div>
    <div v-else class="empty">本次运行暂无可用图谱。</div>
  </section>
</template>

<style>
@import "@vue-flow/core/dist/style.css";
@import "@vue-flow/core/dist/theme-default.css";
</style>

<style scoped>
.path-canvas {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  padding: 13px 14px 14px;
  overflow: hidden;
  border: 1px solid var(--trace-border);
  border-radius: 13px;
  background: #fff;
  box-shadow: 0 6px 18px rgba(30, 41, 59, .04);
}
.canvas-header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 39px;
  margin-bottom: 9px;
}
.graph-heading { min-width: 0; }
.graph-heading small,
.graph-heading strong,
.graph-heading span { display: block; }
.graph-heading small {
  margin-bottom: 2px;
  color: var(--trace-red);
  font-size: 7px;
  font-weight: 750;
  letter-spacing: .1em;
  text-transform: uppercase;
}
.graph-heading strong {
  max-width: 440px;
  overflow: hidden;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.graph-heading span { margin-top: 3px; color: #929ca8; font-size: 7px; }
.flow-shell {
  position: relative;
  flex: 1;
  min-height: 190px;
  overflow: hidden;
  border: 1px solid #e6e9ed;
  border-radius: 11px;
  background: #fbfcfd;
}
.audit-flow {
  width: 100%;
  height: 100%;
  background-color: #fbfcfd;
  background-image: radial-gradient(circle, rgba(119, 132, 147, .24) 1px, transparent 1.15px);
  background-size: 18px 18px;
}
.audit-flow :deep(.vue-flow__pane) { cursor: grab; }
.audit-flow :deep(.vue-flow__pane.dragging) { cursor: grabbing; }
.audit-flow :deep(.vue-flow__node-audit) {
  width: 174px;
  border: 0;
  border-radius: 12px;
  background: transparent;
  box-shadow: none;
}
.flow-node-shell { position: relative; width: 174px; }
.flow-node-shell :deep(.path-node) {
  min-height: 58px;
  background: rgba(255, 255, 255, .97);
  backdrop-filter: blur(5px);
}
.flow-node-shell :deep(.vue-flow__handle) {
  z-index: 4;
  width: 7px;
  height: 7px;
  border: 2px solid #fff;
  background: #98a3ae;
  box-shadow: 0 0 0 1px rgba(91, 104, 119, .18);
  pointer-events: none;
}
.flow-node-shell.risk-high :deep(.vue-flow__handle),
.flow-node-shell.risk-critical :deep(.vue-flow__handle) { background: var(--trace-red); }
.flow-node-shell.decision-block :deep(.path-node) {
  border-color: #a9142a;
  color: #fff;
  background: linear-gradient(135deg, #c91f37, #a8142b);
  box-shadow: 0 10px 24px rgba(185, 27, 49, .22), 0 0 0 3px rgba(201, 31, 55, .09);
}
.flow-node-shell.decision-block :deep(.node-icon) { color: #fff; background: rgba(255, 255, 255, .16); }
.flow-node-shell.decision-block :deep(.node-copy small),
.flow-node-shell.decision-block :deep(.node-copy code) { color: rgba(255, 255, 255, .72); }
.flow-node-shell.decision-block :deep(.decision) { color: #9f1428; background: #fff; }
.flow-node-shell.decision-block :deep(.vue-flow__handle) { background: #a9142a; }
.audit-flow :deep(.vue-flow__edge-path) { transition: stroke 180ms ease, stroke-width 180ms ease; }
.audit-flow :deep(.vue-flow__edge-textbg) { stroke: #e3e7eb; stroke-width: .7px; }
.flow-toolbar {
  position: absolute;
  z-index: 12;
  top: 9px;
  right: 9px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px;
  border: 1px solid #dfe4e9;
  border-radius: 9px;
  background: rgba(255, 255, 255, .94);
  box-shadow: 0 7px 18px rgba(30, 41, 59, .08);
  backdrop-filter: blur(9px);
}
.flow-toolbar button {
  display: flex;
  height: 27px;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 27px;
  padding: 0 6px;
  border: 0;
  border-radius: 6px;
  color: #647181;
  background: transparent;
  font-size: 7px;
  font-weight: 700;
  cursor: pointer;
  transition: color 150ms ease, background-color 150ms ease, transform 150ms ease;
}
.flow-toolbar button:hover:not(:disabled) { color: var(--trace-red); background: #fff1f2; transform: translateY(-1px); }
.flow-toolbar button:disabled { opacity: .38; cursor: not-allowed; }
.flow-toolbar .zoom-value { min-width: 43px; font: 700 7px var(--trace-font-mono); }
.flow-toolbar .fit-button { padding: 0 8px; color: #fff; background: var(--trace-red); }
.flow-toolbar .fit-button:hover:not(:disabled) { color: #fff; background: #ad162c; }
.flow-toolbar i { width: 1px; height: 17px; margin: 0 2px; background: #e2e6ea; }
.flow-tip {
  position: absolute;
  z-index: 10;
  left: 10px;
  bottom: 9px;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 7px;
  border: 1px solid rgba(222, 227, 232, .86);
  border-radius: 7px;
  color: #8b96a3;
  background: rgba(255, 255, 255, .88);
  font-size: 6px;
  pointer-events: none;
  backdrop-filter: blur(7px);
}
.flow-tip span { width: 5px; height: 5px; border-radius: 50%; background: var(--trace-success); box-shadow: 0 0 0 3px rgba(21, 132, 102, .1); }
.empty { display: grid; flex: 1; place-items: center; color: #8792a0; font-size: 10px; }
@media (max-width: 1120px) {
  .canvas-header :deep(.legend) { display: none; }
  .graph-heading strong { max-width: 300px; }
  .flow-tip { display: none; }
}
</style>
