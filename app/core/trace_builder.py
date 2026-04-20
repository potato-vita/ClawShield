from sqlalchemy.orm import Session

from app.models.db_models import EventDB


class TraceBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build(self, run_id: str) -> dict:
        events: list[EventDB] = (
            self.db.query(EventDB)
            .filter(EventDB.run_id == run_id)
            .order_by(EventDB.created_at.asc())
            .all()
        )
        nodes: list[dict] = []
        edges: list[dict] = []
        node_ids: set[str] = set()
        risk_paths: list[list[str]] = []

        run_node = f"run:{run_id}"
        nodes.append({"id": run_node, "type": "run", "label": run_id})
        node_ids.add(run_node)

        sensitive_read_node: str | None = None
        for e in events:
            skill_id = e.metadata_json.get("skill_id") or "unknown_skill"
            tool_id = e.metadata_json.get("tool_id") or "unknown_tool"

            skill_node = f"skill:{skill_id}"
            tool_node = f"tool:{tool_id}"
            res_node = f"res:{e.resource_type}:{e.resource}"

            if skill_node not in node_ids:
                nodes.append({"id": skill_node, "type": "skill", "label": skill_id})
                node_ids.add(skill_node)
            if tool_node not in node_ids:
                nodes.append({"id": tool_node, "type": "tool", "label": tool_id})
                node_ids.add(tool_node)
            if res_node not in node_ids:
                nodes.append({"id": res_node, "type": "resource", "label": e.resource})
                node_ids.add(res_node)

            edges.append({"source": run_node, "target": skill_node, "relation": "executes"})
            edges.append({"source": skill_node, "target": tool_node, "relation": "invoke"})
            edges.append({"source": tool_node, "target": res_node, "relation": e.action})

            if e.action.startswith("file_read") and e.metadata_json.get("sensitive"):
                sensitive_read_node = res_node

            if e.action.startswith("http_request") and sensitive_read_node:
                risk_paths.append([sensitive_read_node, res_node])

        return {
            "run_id": run_id,
            "nodes": nodes,
            "edges": edges,
            "risk_paths": risk_paths,
        }
