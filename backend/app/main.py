from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import Depends
from .database import engine, SessionLocal
from .models import Meeting
from .schemas.meeting import MeetingCreate, MeetingRead

app = FastAPI(
    title="STT FastAPI App",
    description="Minimal FastAPI backend with MySQL + SQLAlchemy",
    version="0.1.0",
)

# Optional: CORS middleware for frontend apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/meetings/", response_model=MeetingRead)
def create_meeting(meeting: MeetingCreate, db: Session = Depends(get_db)):
    db_meeting = Meeting(**meeting.model_dump())
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

@app.get("/meetings/", response_model=list[MeetingRead])
def read_meetings(db: Session = Depends(get_db)):
    return db.query(Meeting).all()

@app.get("/meetings/{meeting_id}", response_model=MeetingRead)
def read_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting
