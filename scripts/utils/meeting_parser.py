import requests
from pathlib import Path
import json
from jsonschema import validate, ValidationError
from summarizer import parse_meeting_minutes, MeetingMinutes

LM_API_URL = "http://localhost:1234/v1/chat/completions"

GRAMMAR_PATH = Path("data/meeting_summary.gbnf")
GRAMMAR = GRAMMAR_PATH.read_text(encoding="utf-8")

# SYSTEM PROMPT za finalni JSON output
SYSTEM_PROMPT = """
Ti si alat koji generiše zapisnik sa sastanka u JSON formatu.
Obavezno koristi sledeća imena polja:

- executive_summary: string
- topics: array of strings
- decisions: array of objects {decision, rationale}
- action_items: array of objects {task, assignee, deadline}
- discussions: array of objects {topic, context, key_arguments, conclusion}

PRAVILA:
- Vrati SAMO JSON, bez markdowna (bez ```json i ``` blokova) i bez bilo kakvih komentara.
- Ništa pre ili posle JSON objekta ne sme biti.
- Ako neka informacija nije poznata, smisli razumnu vrednost
- Mora striktno pratiti GBNF gramatiku i polja iznad
- Ako nema dostupnih ključnih argumenata, upiši ["Nije spomenuto"] umesto praznog niza.
- Ako nema dostupnog konteksta ili zaključka, upiši "Nije spomenuto".
"""


# PROMPT za obradu chunkova (ekstrakcija informacija, ne JSON)
CHUNK_PROMPT = """
Iz sledećeg dela transkripta izdvoj:

- ključne teme
- donete odluke (ako postoje)
- akcione zadatke (ako postoje)
- važne diskusije i argumente

Ignoriši sve vremenske oznake u formatu [hh:mm:ss - hh:mm:ss].

Odgovori u čistom tekstu, u kratkim stavkama.
Ne koristi JSON.
"""

# Chunkovanje transkripta po max_chars
def chunk_text(text: str, max_chars: int = 500):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + max_chars])
        start += max_chars
    return chunks

# Obrada jednog chunk-a
def process_chunk(chunk: str) -> str:

    payload = {
        "model": "meta-llama-3.1-8b-instruct",
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

# Generisanje zapisnika sa sastanka iz fajla
def generate_meeting_minutes_from_file(file_path: Path, lm_api_url: str = LM_API_URL) -> MeetingMinutes:
    if not file_path.is_file():
        raise FileNotFoundError(f"Fajl ne postoji: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        transcript_text = f.read()

    # Chunkovanje
    chunks = chunk_text(transcript_text)
    partial_summaries = []
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}")
        partial_summaries.append(process_chunk(chunk))

    # Kombinovanje chunk rezultata
    combined_summary = "\n\n".join(partial_summaries)

    # Finalni JSON poziv
    payload = {
      "model": "meta-llama-3.1-8b-instruct",
      "messages": [
          {"role": "system", "content": SYSTEM_PROMPT},
          {
              "role": "user",
              "content": (
                  "Na osnovu sledećih sažetih informacija sa sastanka, "
                  "generiši kompletan zapisnik sa sastanka u JSON formatu.\n\n"
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
        print(f"Greška pri komunikaciji sa LLM: {e}")
        raise


    # Pretvaranje u MeetingMinutes
    meeting_minutes = parse_meeting_minutes(llm_json)
    return meeting_minutes

# CLI
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python meeting_parser.py <transcript_txt_file>")
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

        print(f"\nJSON fajl je snimljen u: {output_file}")

    except Exception as e:
        print(f"Došlo je do greške: {e}")
