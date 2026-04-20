from pydantic import BaseModel, Field


class RuleCreate(BaseModel):
    rule_id: str
    name: str
    category: str
    severity: str = "medium"
    decision: str = "alert"
    enabled: bool = True
    definition_json: dict = Field(default_factory=dict)
    description: str = ""


class RuleRead(RuleCreate):
    model_config = {"from_attributes": True}
