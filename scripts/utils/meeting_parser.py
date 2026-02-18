import requests
from pathlib import Path
from utils.summarizer import parse_meeting_minutes, MeetingMinutes

# LLM endpoint
LM_API_URL = "http://localhost:1234/v1/chat/completions"

# Paths to grammar and prompt files
GRAMMAR_PATH = Path("data/meeting_summary.gbnf")
GRAMMAR = GRAMMAR_PATH.read_text(encoding="utf-8")

SYSTEM_PROMPT_FILE = Path("config/prompts/llm_summary_system_prompt.txt")
CHUNK_PROMPT_FILE  = Path("config/prompts/llm_summary_chunk_prompt.txt")

SYSTEM_PROMPT = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
CHUNK_PROMPT  = CHUNK_PROMPT_FILE.read_text(encoding="utf-8")

# Default chat model (can be overridden externally if needed)
CHAT_MODEL = "meta-llama-3.1-8b-instruct"

# Split transcript into chunks by max character length
def chunk_text(text: str, max_chars: int = 500):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + max_chars])
        start += max_chars
    return chunks

# Process a single transcript chunk
def process_chunk(chunk: str) -> str:

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": CHUNK_PROMPT},
            {"role": "user", "content": chunk}
        ],
        "temperature": 0.0,
        "max_tokens": 200
    }

    resp = requests.post(LM_API_URL, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

# Generate meeting minutes from a transcript file
def generate_meeting_minutes_from_file(file_path: Path, lm_api_url: str = LM_API_URL) -> MeetingMinutes:
    if not file_path.is_file():
        raise FileNotFoundError(f"File doesn't exist: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    # Chunk the transcript
    chunks = chunk_text(transcript_text)
    partial_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        partial_summaries.append(process_chunk(chunk))

    # Combine chunk-level summaries
    combined_summary = "\n\n".join(partial_summaries)

    # Final LLM call to generate structured JSON
    payload = {
      "model": CHAT_MODEL,
      "messages": [
          {"role": "system", "content": SYSTEM_PROMPT},
          {
              "role": "user",
              "content": (
                    "Based on the following summarized meeting information, "
                    "generate a complete meeting minutes document in JSON format.\n\n"
                    f"{combined_summary}"
                )
          }
      ],
      "grammar": GRAMMAR,
      "temperature": 0.0,
      "max_tokens": 1200
  }

    try:
        resp = requests.post(lm_api_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        llm_json = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with LLM: {e}")
        raise

    # Parse JSON into MeetingMinutes object
    meeting_minutes = parse_meeting_minutes(llm_json)
    return meeting_minutes


def print_meeting_minutes(minutes: MeetingMinutes) -> None:
    print("--- Executive Summary ---")
    print(minutes.executive_summary)

    print("\n--- Topics ---")
    for t in minutes.topics:
        print(f"- {t}")

    print("\n--- Decisions ---")
    for d in minutes.decisions:
        print(f"- {d.decision}: {d.rationale}")

    print("\n--- Action Items ---")
    for a in minutes.action_items:
        print(f"- {a.task} (assignee: {a.assignee}, deadline: {a.deadline})")

    print("\n--- Discussions ---")
    for disc in minutes.discussions:
        print(
            f"- {disc.topic}\n"
            f"  Context: {disc.context}\n"
            f"  Key arguments: {', '.join(disc.key_arguments)}\n"
            f"  Conclusion: {disc.conclusion}\n"
        )

def save_meeting_minutes(minutes: MeetingMinutes, file_path: Path):
    lines = []

    lines.append("--- Executive Summary ---")
    lines.append(minutes.executive_summary)
    lines.append("")

    lines.append("--- Topics ---")
    for t in minutes.topics:
        lines.append(f"- {t}")
    lines.append("")

    lines.append("--- Decisions ---")
    for d in minutes.decisions:
        lines.append(f"- {d.decision}: {d.rationale}")
    lines.append("")

    lines.append("--- Action Items ---")
    for a in minutes.action_items:
        lines.append(f"- {a.task} (assignee: {a.assignee}, deadline: {a.deadline})")
    lines.append("")

    lines.append("--- Discussions ---")
    for disc in minutes.discussions:
        lines.append(f"- {disc.topic}")
        lines.append(f"  Context: {disc.context}")
        lines.append(f"  Key arguments: {', '.join(disc.key_arguments)}")
        lines.append(f"  Conclusion: {disc.conclusion}")
        lines.append("")

    content = "\n".join(lines)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    print(f"Meeting summary saved to: {file_path}")



# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python meeting_parser.py <transcript_txt_file> <system_prompt_txt> <chunk_prompt_txt>")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    try:

        minutes = generate_meeting_minutes_from_file(input_file)
        json_output = minutes.to_json()

        output_folder = Path("output")
        output_folder.mkdir(exist_ok=True)
        output_file = output_folder / (input_file.stem + ".json")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json_output)

        print(f"\nJSON file saved to: {output_file}")

        loaded_minutes = parse_meeting_minutes(json_output)

        print("\nMeeting minutes (loaded from JSON file):\n")
        print_meeting_minutes(loaded_minutes)

    except Exception as e:
        print(f"An error occurred: {e}")