import sys, os
import argparse
import time, pathlib
from dataclasses import dataclass
from faster_whisper import WhisperModel
from typing import List, Optional
from scripts.utils import audio_utils

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

class Transcriber:
    def __init__(self, model_size: str = "large", device: str = "cpu"):

        self.model_size = model_size
        self.device = device
        self.model = WhisperModel(model_size, device=device)

    def transcribe(self, audio_path: str, prompt: Optional[str] = None, language: Optional[str] = "sr", verbose=False) -> List[TranscriptSegment]:

        if verbose:
            print(f"Pokretanje transkripcije: {audio_path} sa modelom {self.model_size}")

        start_time = time.time()

        segments: List[TranscriptSegment] = []

        segments_list, info = self.model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=False,
            initial_prompt=prompt,
            language=language
        )

        for segment in segments_list:
            segments.append(
                TranscriptSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text
                )
            )

        if verbose:
            print(f"Transkripcija završena u {time.time() - start_time:.2f}s")


        return segments

def format_segments(segments: List[TranscriptSegment]) -> str:
    lines = []
    for seg in segments:
        start_str = time.strftime('%H:%M:%S', time.gmtime(seg.start))
        end_str = time.strftime('%H:%M:%S', time.gmtime(seg.end))
        lines.append(f"[{start_str} - {end_str}] {seg.text}")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Speech to Text Transcription")
    parser.add_argument("audio_file", help="Putanja do audio fajla")
    parser.add_argument("-o", "--output", help="Izlazni fajl (default: stdout)")
    parser.add_argument("-m", "--model", default="large", help="Whisper model (default: large)")
    parser.add_argument("--prompt", help="Whisper prompt tekst ili putanja do fajla sa prompt-om")
    parser.add_argument("-v", "--verbose", action="store_true", help="Detaljan ispis")
    args = parser.parse_args()

    if not audio_utils.validate_audio_format(args.audio_file):
        print(f"Nevalidan ili nepostojeći audio fajl: {args.audio_file}")
        sys.exit(1)

    prompt_text = None
    if args.prompt:
        if os.path.isfile(args.prompt):
            with open(args.prompt, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = args.prompt

    wav_file = audio_utils.convert_to_wav_16k_mono(
        args.audio_file, 
        os.path.dirname(args.output) if args.output else ".",
        verbose=args.verbose
    )

    transcriber = Transcriber(model_size=args.model, device="cpu")
    segments = transcriber.transcribe(wav_file, prompt=prompt_text, 
            language="sr", verbose=args.verbose)

    formatted_text = format_segments(segments)

    if args.output:
        if os.path.isdir(args.output):
            base_name = pathlib.Path(wav_file).stem
            args.output = os.path.join(args.output, f"{base_name}.txt")

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        if args.verbose:
            print(f"Rezultat sačuvan u: {args.output}")
    else:
        print(formatted_text)

    if args.verbose:
        print("Proces završen.")


if __name__ == "__main__":
    main()