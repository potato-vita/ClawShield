# TraceShield Frontend Design

## 产品定位

TraceShield Web 是 Agent 工具调用的实时审计工作台。主视图不复制聊天记录，而是把用户意图、工具调用、敏感对象、信任边界和策略决策组成一条可解释路径。

## 信息架构

- Top Status Bar：Core、PostgreSQL、OpenClaw Plugin 和 SSE 状态，点击可查看运行细节。
- Side Rail：Runtime、Tool Calls、Policies、Core 等产品入口。
- Session Panel：风险优先的会话切换，支持折叠、筛选和搜索。
- Runtime Main Area：Path 默认视图，辅以 Timeline、Tool Calls 和 Conversation Summary。
- Inspector：Decision / Evidence / Assistant 三类解释及处置预览。
- Evidence Path：底部按时序呈现经过验证的完整证据链。

## 核心交互

`payroll-leak-demo` 展示 User Request → shell_exec → read_file → process_data → external_send → BLOCKED。选择任意节点后，store 会同时驱动 Inspector 内容和 Evidence Path 高亮。Tool Calls 表格中的行可携带 `tool_call` query 回跳 Runtime 并完成同样的定位。

## 视觉系统

- 基底：暖白画布、白色面板、金属灰细边框。
- 关键色：中国红 `#c91f37`，只用于 BLOCK、高风险、当前选择和关键操作。
- 层次：浅红径向渐变、细边框和轻量金属浮起阴影。
- 动效：BLOCK 脉冲、状态灯呼吸、新会话闪烁、Evidence 平滑滚动。
- 密度：为 1366×768 答辩屏优化，在 1920×1080 下保留更宽路径区和信息层次。

## 数据原则

- 只展示参数摘要、资源提示、分类和指纹，不展示 payroll 原文。
- Conversation 仅保留脱敏意图摘要。
- 数据源分为 mock / core / fallback，API 失败不破坏布局。
- SSE 仅做增量更新，断线后显示 Offline 并自动重连。
