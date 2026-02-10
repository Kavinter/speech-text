import requests
from pathlib import Path
from summarizer import parse_meeting_minutes, MeetingMinutes

LM_API_URL = "http://localhost:1234/v1/chat/completions"

GRAMMAR_PATH = Path("data/meeting_summary.gbnf")
GRAMMAR = GRAMMAR_PATH.read_text(encoding="utf-8")

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
def process_chunk(chunk: str, chunk_prompt: str) -> str:

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": chunk_prompt},
            {"role": "user", "content": chunk}
        ],
        "temperature": 0.0,
        "max_tokens": 200
    }

    resp = requests.post(LM_API_URL, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

# Generate meeting minutes from a transcript file
def generate_meeting_minutes_from_file(file_path: Path, system_prompt: str, chunk_prompt: str, lm_api_url: str = LM_API_URL) -> MeetingMinutes:
    if not file_path.is_file():
        raise FileNotFoundError(f"Fajl ne postoji: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    # Chunk the transcript
    chunks = chunk_text(transcript_text)
    partial_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        partial_summaries.append(process_chunk(chunk, chunk_prompt))

    # Combine chunk-level summaries
    combined_summary = "\n\n".join(partial_summaries)

    # Final LLM call to generate structured JSON
    payload = {
      "model": CHAT_MODEL,
      "messages": [
          {"role": "system", "content": system_prompt},
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

# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python meeting_parser.py <transcript_txt_file> <system_prompt_txt> <chunk_prompt_txt>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    system_prompt_file = Path(sys.argv[2])
    chunk_prompt_file = Path(sys.argv[3])

    try:
        SYSTEM_PROMPT = system_prompt_file.read_text(encoding="utf-8")
        CHUNK_PROMPT = chunk_prompt_file.read_text(encoding="utf-8")

        minutes = generate_meeting_minutes_from_file(input_file, SYSTEM_PROMPT, CHUNK_PROMPT)
        json_output = minutes.to_json()

        output_folder = Path("output")
        output_folder.mkdir(exist_ok=True)
        output_file = output_folder / (input_file.stem + ".json")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json_output)

        print(f"\nJSON file saved to: {output_file}")

        with open(output_file, "r", encoding="utf-8") as f:
            loaded_json = f.read()

        loaded_minutes = parse_meeting_minutes(loaded_json)

        print("\nMeeting minutes (loaded from JSON file):\n")
        print_meeting_minutes(loaded_minutes)

    except Exception as e:
        print(f"An error occurred: {e}")