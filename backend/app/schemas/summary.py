from pydantic import BaseModel, computed_field
import json
from typing import List, Any

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

    @computed_field
    @property
    def topics(self) -> List[Any]:
        return json.loads(self.topics_json) if self.topics_json else []

    @computed_field
    @property
    def decisions(self) -> List[Any]:
        return json.loads(self.decisions_json) if self.decisions_json else []

    @computed_field
    @property
    def action_items(self) -> List[Any]:
        return json.loads(self.action_items_json) if self.action_items_json else []

    @computed_field
    @property
    def discussions(self) -> List[Any]:
        return json.loads(self.discussions_json) if self.discussions_json else []

    model_config = {"from_attributes": True}
