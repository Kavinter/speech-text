from pydantic import BaseModel
import json
from typing import List

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

    @property
    def topics(self) -> List[str]:
        return json.loads(self.topics_json) if self.topics_json else []

    @property
    def decisions(self) -> List[str]:
        return json.loads(self.decisions_json) if self.decisions_json else []

    @property
    def action_items(self) -> List[str]:
        return json.loads(self.action_items_json) if self.action_items_json else []

    @property
    def discussions(self) -> List[str]:
        return json.loads(self.discussions_json) if self.discussions_json else []

    model_config = {"from_attributes": True}
