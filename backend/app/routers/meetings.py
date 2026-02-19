from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil, json, os
from datetime import datetime

from app import models, schemas
from app.database import get_db, SessionLocal
from scripts.utils import audio_utils, diarizer, summarizer, meeting_parser
from scripts.utils.transcriber import Transcriber


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
        meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
        if not meeting:
            return

        meeting.status = "processing"
        db.commit()

        # Convert to 16kHz mono
        converted_audio = audio_utils.convert_to_wav_16k_mono(
            audio_path,
            str(OUTPUT_DIR)
        )

        meeting.duration = audio_utils.get_audio_duration(converted_audio)
        db.commit()

        # Transcription
        transcriber = Transcriber(model_size="large")
        segments = transcriber.transcribe(converted_audio, language="sr")

        raw_text = "\n".join([s for s in (seg.format() for seg in segments or []) if s])


        raw_output_file = OUTPUT_DIR / f"{meeting_id}_raw.txt"
        raw_output_file.write_text(raw_text, encoding="utf-8")

        # Clean transcript
        cleaned_file = OUTPUT_DIR / f"{meeting_id}_clean.txt"
        list(
            summarizer.reconstruct_transcript(
                raw_text,
                output_file=cleaned_file
            )
        )

        # Changing segments to use cleaned text instead of raw text
        clean_lines = cleaned_file.read_text(encoding="utf-8").splitlines()
        for seg, clean_line in zip(segments, clean_lines):
            if "]" in clean_line:
                seg.text = clean_line.split("]", 1)[1].strip()

        # Speaker diarization
        diarization_segments = diarizer.diarize(converted_audio, NUM_SPEAKERS)

        detected_labels = sorted(
            set(f"speaker_{seg.speaker}" for seg in diarization_segments)
        )

        speaker_map = {label: None for label in detected_labels}
        
        segments_text = diarizer.assign_speakers_to_transcript(
            transcript=segments,
            diarization_segments=diarization_segments,
            speaker_map=speaker_map
        )

        reconstructed_with_speakers = "\n".join([s for s in segments_text if s])

        # Remove old speakers if re-processing
        db.query(models.Speaker).filter(
            models.Speaker.meeting_id == meeting_id
        ).delete()

        # Save Transcript
        db_transcript = models.Transcript(
            meeting_id=meeting_id,
            raw_text=raw_text,
            reconstructed_text=reconstructed_with_speakers
        )
        db.add(db_transcript)

        ### Test with example meeting txt, because example audios are not from meetings.
        test_tekst = Path("data/sastanak.txt")

        # Generate Summary
        minutes = meeting_parser.generate_meeting_minutes_from_file(test_tekst)

        db_summary = models.Summary(
            meeting_id=meeting_id,
            executive_summary=minutes.executive_summary,
            topics_json=json.dumps(minutes.topics),
            decisions_json=json.dumps([d.model_dump() for d in minutes.decisions]),
            action_items_json=json.dumps([a.model_dump() for a in minutes.action_items]),
            discussions_json=json.dumps([d.model_dump() for d in minutes.discussions])
        )
        db.add(db_summary)

        # Save speakers in DB
        for label in detected_labels:
            db.add(models.Speaker(
                meeting_id=meeting_id,
                label=label,
                name=None
            ))

        meeting.status = "completed"
        db.commit()

    except Exception as e:
        print(f"Processing error: {e}")
        meeting = db.query(models.Meeting).filter(models.Meeting.id == meeting_id).first()
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
        lines = []
        if transcript:
            lines.append("--- Transcript ---")
            lines.append(transcript.reconstructed_text)
        if summary:
            lines.append("--- Executive Summary ---")
            lines.append(summary.executive_summary or "")
            lines.append("--- Topics ---")
            lines.extend(json.loads(summary.topics_json))
            lines.append("--- Decisions ---")
            for d in json.loads(summary.decisions_json):
                lines.append(f"{d['decision']}: {d['rationale']}")
            lines.append("--- Action Items ---")
            for a in json.loads(summary.action_items_json):
                lines.append(f"{a['task']} (assignee: {a['assignee']}, deadline: {a['deadline']})")
            lines.append("--- Discussions ---")
            for disc in json.loads(summary.discussions_json):
                lines.append(f"{disc['topic']}: {disc['conclusion']}")
        out_file = AUDIO_DIR / f"meeting_{meeting_id}.{format}"
        out_file.write_text("\n".join(lines), encoding="utf-8")
        return FileResponse(out_file, media_type="text/plain", filename=out_file.name)

    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
