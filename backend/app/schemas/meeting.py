from pydantic import BaseModel
from datetime import datetime

class MeetingCreate(BaseModel):
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime | None = None

class MeetingRead(BaseModel):
    id: int
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime | None

    class Config:
        orm_mode = True