from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import json, os
from datetime import datetime

from app import models, schemas
from app.database import get_db, SessionLocal
from app.services.processing_service import ProcessingService
from app.services.meeting_parser import MeetingParserService


router = APIRouter(
    prefix="/api/meetings",
    tags=["meetings"]
)

AUDIO_DIR = Path("data")
OUTPUT_DIR = Path("output")
AUDIO_DIR.mkdir(exist_ok=True, parents=True)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
NUM_SPEAKERS = 2

def process_meeting_audio(meeting_id: int, audio_path: str):
    db = SessionLocal()

    try:
        meeting = db.query(models.Meeting).filter(
            models.Meeting.id == meeting_id
        ).first()

        if not meeting:
            return

        meeting.status = "processing"
        db.commit()

        processing_service = ProcessingService(
            num_speakers=NUM_SPEAKERS,
            model_size="large",
            device="cpu"
        )

        result = processing_service.process_meeting_audio(
            audio_path=audio_path,
            output_dir=OUTPUT_DIR
        )

        # =============================
        # UPDATE MEETING
        # =============================

        meeting.duration = result["duration"]

        # Remove old transcript/summary/speakers if re-processing
        db.query(models.Transcript).filter(
            models.Transcript.meeting_id == meeting_id
        ).delete()

        db.query(models.Summary).filter(
            models.Summary.meeting_id == meeting_id
        ).delete()

        db.query(models.Speaker).filter(
            models.Speaker.meeting_id == meeting_id
        ).delete()

        # =============================
        # SAVE TRANSCRIPT
        # =============================

        db_transcript = models.Transcript(
            meeting_id=meeting_id,
            raw_text=result["raw_text"],
            reconstructed_text=result["reconstructed_text"]
        )

        db.add(db_transcript)

        # =============================
        # SAVE SUMMARY
        # =============================

        summary = result["summary"]

        db_summary = models.Summary(
            meeting_id=meeting_id,
            executive_summary=summary["executive_summary"],
            topics_json=json.dumps(summary["topics"]),
            decisions_json=json.dumps(summary["decisions"]),
            action_items_json=json.dumps(summary["action_items"]),
            discussions_json=json.dumps(summary["discussions"])
        )

        db.add(db_summary)

        # =============================
        # SAVE SPEAKERS
        # =============================

        for label in result["detected_speakers"]:
            db.add(models.Speaker(
                meeting_id=meeting_id,
                label=label,
                name=None
            ))

        meeting.status = "completed"
        db.commit()

    except Exception as e:
        print(f"Processing error: {e}")

        meeting = db.query(models.Meeting).filter(
            models.Meeting.id == meeting_id
        ).first()

        if meeting:
            meeting.status = "failed"
            db.commit()

    finally:
        db.close()


@router.post("/", response_model=schemas.MeetingRead)
async def create_meeting(
    title: str = Form(...),
    date: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    
    audio_path = AUDIO_DIR / file.filename

    meeting = models.Meeting(
        title=title,
        date=datetime.fromisoformat(date),
        audio_file_path=str(audio_path),
        status="pending"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting


@router.get("/", response_model=list[schemas.MeetingRead])
def list_meetings(db: Session = Depends(get_db)):
    meetings = db.query(models.Meeting).order_by(models.Meeting.created_at.desc()).all()
    return meetings


@router.get("/{meeting_id}", response_model=schemas.MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.delete("/{meeting_id}")
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # delete audio file
    if meeting.audio_file_path and os.path.isfile(meeting.audio_file_path):
        os.remove(meeting.audio_file_path)

    db.delete(meeting)
    db.commit()
    return {"detail": "Meeting deleted"}


@router.post("/{meeting_id}/process")
def process_meeting(meeting_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not os.path.isfile(meeting.audio_file_path):
        raise HTTPException(status_code=400, detail="Audio file missing")

    background_tasks.add_task(process_meeting_audio, meeting_id, meeting.audio_file_path)
    return {"detail": "Processing started"}


@router.get("/{meeting_id}/status")
def meeting_status(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"status": meeting.status}


@router.put("/{meeting_id}/speakers")
def update_speakers(meeting_id: int, speakers: list[schemas.SpeakerCreate], db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    for sp in speakers:
        speaker = db.query(models.Speaker).filter(
            models.Speaker.meeting_id == meeting_id, models.Speaker.label == sp.label
        ).first()
        if speaker:
            speaker.name = sp.name
        else:
            db.add(models.Speaker(meeting_id=meeting_id, label=sp.label, name=sp.name))
    db.commit()
    return {"detail": "Speakers updated"}


@router.get("/{meeting_id}/export")
def export_meeting(meeting_id: int, format: str = "txt", db: Session = Depends(get_db)):
    meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = db.query(models.Transcript).filter(models.Transcript.meeting_id == meeting_id).first()
    summary = db.query(models.Summary).filter(models.Summary.meeting_id == meeting_id).first()
    speakers = db.query(models.Speaker).filter(models.Speaker.meeting_id == meeting_id).all()

    if format == "json":
        data = {
            "meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "date": str(meeting.date),
                "status": meeting.status,
            },
            "transcript": transcript.reconstructed_text if transcript else None,
            "summary": {
                "executive_summary": summary.executive_summary if summary else None,
                "topics": json.loads(summary.topics_json) if summary else [],
                "decisions": json.loads(summary.decisions_json) if summary else [],
                "action_items": json.loads(summary.action_items_json) if summary else [],
                "discussions": json.loads(summary.discussions_json) if summary else []
            },
            "speakers": [{ "label": s.label, "name": s.name } for s in speakers]
        }
        out_file = OUTPUT_DIR / f"meeting_{meeting_id}.json"
        out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return FileResponse(out_file, media_type="application/json", filename=out_file.name)

    elif format in ["txt", "md"]:

        out_file = OUTPUT_DIR / f"meeting_{meeting_id}.{format}"

        lines = []

        if transcript:
            lines.append("--- Transcript ---")
            lines.append(transcript.reconstructed_text)
            lines.append("")

        if summary:
            minutes = MeetingParserService.from_db_summary(summary)

            temp_summary_file = OUTPUT_DIR / f"_temp_summary_{meeting_id}.txt"
            MeetingParserService.save_minutes_to_file(minutes, temp_summary_file)

            summary_text = temp_summary_file.read_text(encoding="utf-8")
            lines.append(summary_text)

            temp_summary_file.unlink(missing_ok=True)

        out_file.write_text("\n".join(lines), encoding="utf-8")

        return FileResponse(out_file, media_type="text/plain", filename=out_file.name)

    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
