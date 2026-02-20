from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .speaker import SpeakerRead

class MeetingCreate(BaseModel):
    title: str
    date: datetime

class MeetingRead(BaseModel):
    id: int
    title: str
    date: datetime
    audio_file_path: str
    duration: Optional[float]
    status: str
    created_at: datetime
    speakers: List[SpeakerRead] = []

    model_config = {"from_attributes": True}