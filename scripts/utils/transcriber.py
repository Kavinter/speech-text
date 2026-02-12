import sys, os
import argparse
import time, pathlib
from dataclasses import dataclass
from faster_whisper import WhisperModel
from typing import List, Optional
from scripts.utils import audio_utils

# Represents a segment of transcribed audio
@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

    def format(self) -> str:
        start_str = time.strftime('%H:%M:%S', time.gmtime(int(self.start)))
        end_str = time.strftime('%H:%M:%S', time.gmtime(int(self.start)))
        return f"[{start_str} - {end_str}] {self.text}"

# Wrapper class for Whisper transcription
class Transcriber:
    def __init__(self, model_size: str = "large", device: str = "cpu"):

        self.model_size = model_size
        self.device = device
        self.model = WhisperModel(model_size, device=device)

    # Transcribe an audio file
    def transcribe(self, audio_path: str, prompt: Optional[str] = None, language: Optional[str] = "sr", verbose=False) -> List[TranscriptSegment]:

        if verbose:
            print(f"Transcription finished in {time.time() - start_time:.2f}s")

        start_time = time.time()

        segments: List[TranscriptSegment] = []

        # Perform transcription
        segments_list, _info = self.model.transcribe(
            audio_path,
            beam_size=5,
            word_timestamps=False,
            initial_prompt=prompt,
            language=language
        )

        # Convert Whisper output to TranscriptSegment objects
        for segment in segments_list:
            segments.append(
                TranscriptSegment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text
                )
            )

        if verbose:
            print(f"Transcription finished in {time.time() - start_time:.2f}s")


        return segments

def main():
    parser = argparse.ArgumentParser(description="Speech to Text Transcription")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument("-m", "--model", default="large", help="Whisper model (default: large)")
    parser.add_argument("--prompt", help="Whisper prompt text or path to a prompt file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable detailed output")
    args = parser.parse_args()

    # Validate input audio
    if not audio_utils.validate_audio_format(args.audio_file):
        print(f"Invalid or non-existent audio file: {args.audio_file}")
        sys.exit(1)

    # Load prompt from file or use string directly
    prompt_text = None
    if args.prompt:
        if os.path.isfile(args.prompt):
            with open(args.prompt, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = args.prompt

    # Convert audio to 16kHz mono WAV for Whisper
    wav_file = audio_utils.convert_to_wav_16k_mono(
        args.audio_file, 
        os.path.dirname(args.output) if args.output else ".",
        verbose=args.verbose
    )

    # Initialize transcriber and process audio
    transcriber = Transcriber(model_size=args.model, device="cpu")
    segments = transcriber.transcribe(wav_file, prompt=prompt_text, 
            language="sr", verbose=args.verbose)

    # Format segments for output
    formatted_text = "\n".join(seg.format() for seg in segments)

    # Save to file or print to stdout
    if args.output:
        if os.path.isdir(args.output):
            base_name = pathlib.Path(wav_file).stem
            args.output = os.path.join(args.output, f"{base_name}.txt")

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted_text)
        if args.verbose:
            print(f"Result saved to: {args.output}")
    else:
        print(formatted_text)

    if args.verbose:
        print("Process completed.")


if __name__ == "__main__":
    main()