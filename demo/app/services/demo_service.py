class DemoService:
    def list_scenarios(self) -> list[dict]:
        return [
            {
                "scenario_id": "normal",
                "name": "正常任务",
                "description": "工作区内文件读写 + 受信工具调用",
            },
            {
                "scenario_id": "workspace_escape",
                "name": "工作区越界访问",
                "description": "尝试读取 /etc/passwd",
            },
            {
                "scenario_id": "sensitive_exfiltration",
                "name": "敏感读取后外联",
                "description": "读取 .env 后尝试请求 evil.example",
            },
            {
                "scenario_id": "unauthorized_tool",
                "name": "未授权工具调用",
                "description": "调用未注册白名单工具",
            },
            {
                "scenario_id": "dangerous_command",
                "name": "高危命令执行",
                "description": "模拟执行 rm -rf / 并阻断",
            },
            {
                "scenario_id": "advanced_intrusion_kill_chain",
                "name": "高级入侵攻击链",
                "description": "多阶段越界探测 + 敏感采集 + 未授权工具 + 外联 + 高危命令",
            },
        ]
