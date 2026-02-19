from pydantic import BaseModel

class SpeakerCreate(BaseModel):
    meeting_id: int
    label: str
    name: str | None = None

class SpeakerRead(BaseModel):
    id: int
    meeting_id: int
    label: str
    name: str | None

    model_config = {"from_attributes": True}
