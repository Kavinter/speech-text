from pathlib import Path
import requests
from typing import Dict, Optional

SRBGLISH_TERMS: Dict[str, str] = {}

TERMS_TO_CORRECT = {
    "šestručnom": "šef stručnom"
}

SYSTEM_PROMPT = """
Ti si alat za čišćenje transkripata govora.
Tvoj zadatak je da:
- ispraviš pravopisne i gramatičke greške,
- prebacuješ tekst iz ijekavice u ekavicu,
- ne menjaš značenje teksta,
- ne dodaješ nove rečenice,
- zadržiš sve vremenske oznake u formatu [hh:mm:ss - hh:mm:ss],
- posle njih ispisuješ ispravljen tekst.
"""

LM_API_URL = "http://localhost:1234/v1/chat/completions"

def chunk_text(lines, chunk_size=5):
    for i in range(0, len(lines), chunk_size):
        yield lines[i:i + chunk_size]

def reconstruct_transcript(raw_text: str, terms_dict: Optional[Dict[str, str]] = None, output_file: Optional[Path] = None):
    if terms_dict is None:
        terms_dict = {}

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
            "model": "google/gemma-3-4b",
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
            print(f"Greska pri obradi chunk-a: {e}")
            if append_mode:
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(chunk_text_to_send + "\n")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python summarizer.py <input_txt>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    if not input_file.is_file():
        print(f"Ne postoji fajl: {input_file}")
        sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{input_file.stem}_clean.txt"

    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    for _ in reconstruct_transcript(raw_text, terms_dict=TERMS_TO_CORRECT, output_file=output_file):
        pass

    print(f"Ciscenje zavrseno, rezultat sacuvan u: {output_file}")
