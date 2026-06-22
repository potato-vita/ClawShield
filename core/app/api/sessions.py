import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import AnalysisSession, Approval, ChatMessage, UploadedDocument
from app.db.session import get_db
from app.schemas.sessions import AbortRequest, ApprovalRequest, ChatRequest, MessageAppendRequest, SessionCreate
from app.services.idgen import new_id
from app.services.report_service import generate_report
from app.services.sanitizer import redact_text
from app.services.session_service import add_message, build_analysis_answer, sse_payload

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
def list_sessions(db: Session = Depends(get_db)) -> list[dict]:
    sessions = db.scalars(
        select(AnalysisSession).where(AnalysisSession.status != "deleted").order_by(AnalysisSession.updated_at.desc())
    ).all()
    return [{"id": item.id, "title": item.title, "created_at": item.created_at.isoformat(), "updated_at": item.updated_at.isoformat()} for item in sessions]


@router.post("")
def create_session(request: SessionCreate, db: Session = Depends(get_db)) -> dict:
    session = AnalysisSession(id=new_id("session"), title=request.title)
    db.add(session)
    db.commit()
    return {"id": session.id}


@router.delete("/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = _session_or_404(db, session_id)
    session.status = "deleted"
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True}


@router.get("/{session_id}/render")
def render_session(session_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    _session_or_404(db, session_id)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.order_index)).all()
    text = "\n\n".join(f"{item.role}: {item.content}" for item in messages)
    return StreamingResponse(iter([sse_payload(text, [])]), media_type="text/event-stream")


@router.post("/{session_id}/chat")
def chat(session_id: str, request: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    _session_or_404(db, session_id)
    add_message(db, session_id, "user", redact_text(request.message, 4000))
    answer, event_ids = build_analysis_answer(db, request.message)
    download_url = None
    report_id = None
    if "报告" in request.message or "导出" in request.message:
        report = generate_report(db, "TraceShield 安全分析报告", "7d", session_id)
        report_id = report.id
        download_url = f"/api/module4/exports/{Path(report.content_html_path or '').name}"
        answer += f"\n\n报告已生成：{download_url}"
    add_message(db, session_id, "assistant", answer, event_ids[0] if event_ids else None, report_id)
    db.commit()
    return StreamingResponse(iter([sse_payload(answer, event_ids, download_url)]), media_type="text/event-stream")


@router.post("/{session_id}/messages")
def append_session_message(
    session_id: str,
    request: MessageAppendRequest,
    db: Session = Depends(get_db),
) -> dict:
    _session_or_404(db, session_id)
    if request.role not in {"user", "assistant", "system"}:
        raise HTTPException(status_code=422, detail="Unsupported message role")
    message = add_message(
        db,
        session_id,
        request.role,
        redact_text(request.content, 8_000),
        request.related_event_id,
    )
    db.commit()
    return {"success": True, "message_id": message.id}


@router.post("/{session_id}/approve")
def approve(session_id: str, request: ApprovalRequest, db: Session = Depends(get_db)) -> dict:
    _session_or_404(db, session_id)
    approval = db.scalar(
        select(Approval).where(Approval.session_id == session_id, Approval.status == "pending").order_by(Approval.requested_at.desc())
    )
    if approval is None:
        raise HTTPException(status_code=404, detail="No pending approval")
    approval.status = "approved" if request.approved else "rejected"
    approval.reason = redact_text(request.reason, 500)
    approval.resolved_at = datetime.now(timezone.utc)
    approval.approved_by = "frontend-user"
    add_message(db, session_id, "assistant", f"审批结果：{approval.status}。{approval.reason or ''}")
    db.commit()
    return {"success": True, "approval_id": approval.id, "status": approval.status}


@router.post("/{session_id}/abort")
def abort(session_id: str, request: AbortRequest, db: Session = Depends(get_db)) -> dict:
    session = _session_or_404(db, session_id)
    session.status = "aborted"
    add_message(db, session_id, "assistant", f"会话已终止：{redact_text(request.reason)}")
    db.commit()
    return {"success": True}


@router.post("/{session_id}/docs")
async def upload_document(session_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    _session_or_404(db, session_id)
    content = await file.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(file.filename or "upload.bin").name)
    target_dir = Path(__file__).resolve().parent.parent / "data" / "uploads" / session_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / safe_name
    target.write_bytes(content)
    preview = redact_text(content.decode("utf-8", errors="replace"), 1000)
    document = UploadedDocument(
        id=new_id("doc"), session_id=session_id, original_name=file.filename or safe_name,
        stored_path=str(target.relative_to(Path(__file__).resolve().parent.parent)),
        file_hash=hashlib.sha256(content).hexdigest(), mime_type=file.content_type,
        size_bytes=len(content), parsed_text_preview=preview,
    )
    db.add(document)
    db.commit()
    return {"success": True, "document_id": document.id, "filename": safe_name, "size": len(content)}


def _session_or_404(db: Session, session_id: str) -> AnalysisSession:
    session = db.get(AnalysisSession, session_id)
    if session is None or session.status == "deleted":
        raise HTTPException(status_code=404, detail="Session not found")
    return session
