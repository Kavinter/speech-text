from pydantic import BaseModel

class TranscriptCreate(BaseModel):
    meeting_id: int
    raw_text: str
    reconstructed_text: str | None = None

class TranscriptRead(BaseModel):
    id: int
    meeting_id: int
    raw_text: str
    reconstructed_text: str | None

    model_config = {"from_attributes": True}
