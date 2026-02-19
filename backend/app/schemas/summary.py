from pydantic import BaseModel

class SummaryCreate(BaseModel):
    meeting_id: int
    executive_summary: str | None = None
    topics_json: str | None = None
    decisions_json: str | None = None
    action_items_json: str | None = None
    discussions_json: str | None = None

class SummaryRead(BaseModel):
    id: int
    meeting_id: int
    executive_summary: str | None
    topics_json: str | None
    decisions_json: str | None
    action_items_json: str | None
    discussions_json: str | None

    model_config = {"from_attributes": True}
