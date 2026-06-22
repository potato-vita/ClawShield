from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: str = "新分析会话"


class ChatRequest(BaseModel):
    message: str


class ApprovalRequest(BaseModel):
    approved: bool
    reason: str = ""


class AbortRequest(BaseModel):
    reason: str = "用户终止"


class MessageAppendRequest(BaseModel):
    role: str
    content: str
    related_event_id: str | None = None
