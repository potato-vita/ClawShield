from typing import Any


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = {
            "summarize_tool": self._summarize_tool,
            "search_tool": self._search_tool,
        }

    def exists(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def invoke(self, tool_id: str, payload: dict[str, Any]) -> dict:
        if tool_id not in self._tools:
            return {"ok": False, "error": f"tool '{tool_id}' not registered"}
        return self._tools[tool_id](payload)

    def list_tools(self) -> list[dict]:
        return [{"tool_id": t, "enabled": True} for t in self._tools.keys()]

    def _summarize_tool(self, payload: dict[str, Any]) -> dict:
        text = payload.get("text", "")
        summary = text[:120] + ("..." if len(text) > 120 else "")
        return {"ok": True, "tool": "summarize_tool", "summary": summary}

    def _search_tool(self, payload: dict[str, Any]) -> dict:
        query = payload.get("query", "")
        return {
            "ok": True,
            "tool": "search_tool",
            "query": query,
            "results": [
                {"title": "Mock Result A", "score": 0.92},
                {"title": "Mock Result B", "score": 0.88},
            ],
        }
