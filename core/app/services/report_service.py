from html import escape
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Report
from app.services.dashboard_service import build_dashboard
from app.services.idgen import new_id


def generate_report(db: Session, title: str, time_range: str, session_id: str | None = None) -> Report:
    data = build_dashboard(db, time_range)
    report_id = new_id("report")
    filename = f"{report_id}.html"
    export_dir = Path(__file__).resolve().parent.parent / "data" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    summary = data["summary"]
    event_rows = "".join(
        f"<tr><td>{escape(item['event_id'])}</td><td>{escape(item['risk_level'])}</td><td>{escape(item.get('event_title') or '')}</td><td>{escape(item['timestamp'])}</td></tr>"
        for item in data["high_risk_events"]
    ) or "<tr><td colspan='4'>暂无高危事件</td></tr>"
    html = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>{escape(title)}</title>
<style>body{{font:15px system-ui;max-width:980px;margin:40px auto;color:#17202a}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd3da;padding:8px;text-align:left}}h1{{font-size:26px}}</style></head><body>
<h1>{escape(title)}</h1><p>时间范围：{escape(time_range)}</p>
<p>总告警：{summary['total_alerts']}；高危：{summary['high_risk_count']}；Critical：{summary['critical_count']}</p>
<h2>最新高危事件</h2><table><thead><tr><th>事件 ID</th><th>风险</th><th>标题</th><th>时间</th></tr></thead><tbody>{event_rows}</tbody></table>
<h2>建议措施</h2><ul><li>复核高危事件对应任务目标</li><li>保持敏感文件访问阻断</li><li>定期审查动态策略与审批记录</li></ul></body></html>"""
    path = export_dir / filename
    path.write_text(html, encoding="utf-8")
    report = Report(
        id=report_id, session_id=session_id, title=title, report_type="security_summary",
        time_range=time_range, content_markdown=f"# {title}\n\n总告警：{summary['total_alerts']}",
        content_html_path=f"exports/{filename}",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
