from pathlib import Path
import requests
from typing import Dict, Optional, List
from pydantic import BaseModel, Field, ValidationError

# Optional dictionary of terms to replace (keep Serbian terms as-is)
SRBGLISH_TERMS: Dict[str, str] = {}

TERMS_TO_CORRECT = {
    "šestručnom": "šef stručnom"
}

# Instructions for the LM to clean the transcript
SYSTEM_PROMPT = """
You are a tool for cleaning speech transcripts.
Your task is to:
- fix spelling and grammar errors,
- convert text from ijekavica to ekavica,
- do not change the meaning of the text,
- do not add new sentences,
- keep all timecodes in the format [hh:mm:ss - hh:mm:ss],
- after each timecode, write the corrected text.
"""

LM_API_URL = "http://localhost:1234/v1/chat/completions"

CHAT_MODEL = "google/gemma-3-4b"

# Pydantic models for meeting minutes
class ActionItem(BaseModel):
    task: str
    assignee: str
    deadline: str

class Decision(BaseModel):
    decision: str
    rationale: str

class TopicDiscussion(BaseModel):
    topic: str
    context: str
    key_arguments: List[str]
    conclusion: str

class MeetingMinutes(BaseModel):
    executive_summary: str
    topics: List[str]
    decisions: List[Decision]
    action_items: List[ActionItem]
    discussions: List[TopicDiscussion]

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MeetingMinutes":
        return cls.model_validate_json(json_str)
    
def parse_meeting_minutes(llm_json: str) -> MeetingMinutes:
    try:
        return MeetingMinutes.from_json(llm_json)
    except ValidationError as e:
        print("Invalid meeting minutes JSON.")
        raise


# Yield chunks of text for processing
def chunk_text(lines, chunk_size=5):
    for i in range(0, len(lines), chunk_size):
        yield lines[i:i + chunk_size]

# Main function to clean a transcript
def reconstruct_transcript(raw_text: str, terms_dict: Optional[Dict[str, str]] = None, output_file: Optional[Path] = None):
    if terms_dict is None:
        terms_dict = {}

    # Add instructions for term replacements if provided
    dict_instructions = ""
    if terms_dict:
        dict_instructions = "Koristi sledece ispravne termine:\n"
        for k, v in terms_dict.items():
            dict_instructions += f"- {k} -> {v}\n"

    lines = raw_text.splitlines()

    append_mode = output_file is not None

    if append_mode:
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_text("", encoding="utf-8")

    for chunk_lines in chunk_text(lines, chunk_size=5):
        chunk_text_to_send = "\n".join(chunk_lines)

        payload = {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": dict_instructions + "\nIspravi sledeći tekst:\n" + chunk_text_to_send}
            ],
            "temperature": 0.0,
            "max_tokens": 300
        }

        try:
            resp = requests.post(LM_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            print("DEBUG - LM API response:", data)

            # Extract cleaned text from LM response
            cleaned_chunk = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if append_mode:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(cleaned_chunk + "\n")
            else:
                yield cleaned_chunk

        except requests.exceptions.RequestException as e:
            print(f"Error processing chunk: {e}")
            # fallback: write original chunk if LM request fails
            if append_mode:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(chunk_text_to_send + "\n")

# MAIN BLOCK
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python summarizer.py <input_txt>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.is_file():
        print(f"File does not exist: {input_file}")
        sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{input_file.stem}_clean.txt"

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # Run reconstruction / cleaning
    for _ in reconstruct_transcript(raw_text, terms_dict=TERMS_TO_CORRECT, output_file=output_file):
        pass

    print(f"Cleaning completed, result saved at: {output_file}")