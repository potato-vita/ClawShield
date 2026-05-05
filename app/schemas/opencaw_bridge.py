from __future__ import annotations

from pydantic import BaseModel, Field


class SessionBootstrapRequest(BaseModel):
    session_id: str = Field(min_length=1)
    user_input: str = Field(min_length=1)

