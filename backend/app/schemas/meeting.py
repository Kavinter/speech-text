from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from .speaker import SpeakerRead
from .transcript import TranscriptRead
from .summary import SummaryRead

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
    transcripts: List[TranscriptRead] = []
    summaries: List[SummaryRead] = []

    model_config = {"from_attributes": True}