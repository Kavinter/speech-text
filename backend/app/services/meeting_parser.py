from pathlib import Path
from scripts.utils.meeting_parser import generate_meeting_minutes_from_file, save_meeting_minutes
from scripts.utils.summarizer import MeetingMinutes, parse_meeting_minutes
import json


class MeetingParserService:

    @staticmethod
    def generate_from_file(file_path: Path) -> MeetingMinutes:
        return generate_meeting_minutes_from_file(file_path)
    
    @staticmethod
    def from_db_summary(summary_model) -> MeetingMinutes:
        json_data = {
            "executive_summary": summary_model.executive_summary,
            "topics": json.loads(summary_model.topics_json),
            "decisions": json.loads(summary_model.decisions_json),
            "action_items": json.loads(summary_model.action_items_json),
            "discussions": json.loads(summary_model.discussions_json),
        }

        return parse_meeting_minutes(json.dumps(json_data))

    @staticmethod
    def save_minutes_to_file(minutes: MeetingMinutes, file_path: Path):
        save_meeting_minutes(minutes, file_path)
