from pathlib import Path
import json

from sqlalchemy.orm import Session

from app.models.db_models import ArtifactDB, EventDB, ReportDB
from app.utils.ids import new_id
from app.utils.time import utc_now


class ReportEngine:
    def __init__(self, db: Session, export_dir: str):
        self.db = db
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def build_evidence_text(self, run_id: str, findings: list[dict]) -> str:
        if not findings:
            return f"任务 {run_id} 未发现高风险行为，执行链均在允许边界内。"

        lines: list[str] = []
        for item in findings:
            lines.append(
                f"命中规则 {item['rule_id']}（{item.get('name', 'UnknownRule')}），"
                f"严重级别 {item.get('severity', 'medium')}：{item.get('message', '')}"
            )
        return "；".join(lines)

    def generate(self, run_id: str, overall_risk_level: str, findings: list[dict], trace_graph: dict) -> ReportDB:
        events = (
            self.db.query(EventDB)
            .filter(EventDB.run_id == run_id)
            .order_by(EventDB.created_at.asc())
            .all()
        )

        summary = {
            "run_id": run_id,
            "event_count": len(events),
            "risk_count": len(findings),
            "findings": findings,
        }
        evidence_text = self.build_evidence_text(run_id=run_id, findings=findings)

        report = ReportDB(
            report_id=new_id("rpt"),
            run_id=run_id,
            overall_risk_level=overall_risk_level,
            summary_json=summary,
            trace_graph_json=trace_graph,
            evidence_text=evidence_text,
            created_at=utc_now(),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        html_path = self.export_dir / f"{report.report_id}.html"
        html = self._render_html(report)
        html_path.write_text(html, encoding="utf-8")

        artifact = ArtifactDB(
            run_id=run_id,
            artifact_type="report_html",
            path=str(html_path),
            created_at=utc_now(),
        )
        self.db.add(artifact)
        self.db.commit()

        return report

    def _render_html(self, report: ReportDB) -> str:
        payload = json.dumps(report.summary_json, ensure_ascii=False, indent=2)
        trace = json.dumps(report.trace_graph_json, ensure_ascii=False, indent=2)
        return (
            "<html><head><meta charset='utf-8'><title>ClawShield Report</title></head><body>"
            f"<h1>Report {report.report_id}</h1>"
            f"<p>Run: {report.run_id}</p>"
            f"<p>Risk: {report.overall_risk_level}</p>"
            f"<p>Evidence: {report.evidence_text}</p>"
            "<h2>Summary</h2>"
            f"<pre>{payload}</pre>"
            "<h2>Trace</h2>"
            f"<pre>{trace}</pre>"
            "</body></html>"
        )
