from utils.summarizer import MeetingMinutes
from pathlib import Path

file_path = Path("data/meeting2.json")
with open(file_path, "r", encoding="utf-8") as f:
    json_str = f.read()

try:
    meeting = MeetingMinutes.from_json(json_str)
    print(meeting.to_json())
except Exception as e:
    print("Greška pri parsiranju:", e)
