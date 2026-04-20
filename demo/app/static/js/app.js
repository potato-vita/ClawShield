(function () {
  const chartEl = document.getElementById("traceChart");
  if (!chartEl || typeof echarts === "undefined" || typeof window.CLAW_TRACE === "undefined") {
    return;
  }
  const graph = window.CLAW_TRACE || { nodes: [], edges: [] };
  const chart = echarts.init(chartEl);
  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    series: [
      {
        type: "graph",
        layout: "force",
        roam: true,
        draggable: true,
        force: { repulsion: 260, edgeLength: 120 },
        label: { show: true, color: "#1f2430" },
        edgeSymbol: ["none", "arrow"],
        edgeSymbolSize: 8,
        lineStyle: { color: "#0f766e", width: 2, curveness: 0.18 },
        data: (graph.nodes || []).map((node) => ({
          id: node.id,
          name: node.label,
          category: node.type,
          symbolSize: node.type === "run" ? 56 : node.type === "skill" ? 42 : 34,
          itemStyle: {
            color:
              node.type === "run"
                ? "#f59e0b"
                : node.type === "skill"
                ? "#0f766e"
                : node.type === "tool"
                ? "#1d4ed8"
                : "#475569",
          },
        })),
        links: (graph.edges || []).map((edge) => ({
          source: edge.source,
          target: edge.target,
          value: edge.relation,
          label: { show: true, formatter: edge.relation },
        })),
      },
    ],
  };
  chart.setOption(option);
  window.addEventListener("resize", () => chart.resize());
})();
