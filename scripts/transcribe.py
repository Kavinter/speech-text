import sys, os
import argparse
from scripts.utils.transcriber import Transcriber, TranscriptSegment
from scripts.utils import audio_utils, diarizer, summarizer
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Speech to Text Transcription with summarization")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("-o", "--output", default="output", help="Output file or directory (default: output)")
    parser.add_argument("-m", "--model", default="large", help="Whisper model (default: large)")
    parser.add_argument("--prompt", help="Whisper prompt text or path to a prompt file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable detailed output")
    parser.add_argument("--diarize", action="store_true", help="Enable speaker diarization (default: False)")
    parser.add_argument("--num-speakers", type=int, default=-1, help="Number of speakers; -1 = auto-detect")
    parser.add_argument("--speaker-map", type=str, help="Path to file mapping speaker IDs to names (SPEAKER_00=Marko)")

    args = parser.parse_args()

    # --- Validate audio ---
    if not audio_utils.validate_audio_format(args.audio_file):
        print(f"Invalid or non-existent audio file: {args.audio_file}")
        sys.exit(1)

    # --- Load prompt ---
    prompt_text = None
    if args.prompt:
        if os.path.isfile(args.prompt):
            with open(args.prompt, "r", encoding="utf-8") as f:
                prompt_text = f.read()
        else:
            prompt_text = args.prompt

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # --- Convert to 16kHz mono WAV ---
    wav_file = audio_utils.convert_to_wav_16k_mono(
        args.audio_file,
        args.output
    )

    # --- Transcribe ---
    transcriber = Transcriber(model_size=args.model, device="cpu")
    segments = transcriber.transcribe(wav_file, prompt=prompt_text, language="sr", verbose=args.verbose)

    # --- Diarization if enabled ---
    if args.diarize:
        diarization_segments = diarizer.diarize(wav_file, num_speakers=args.num_speakers)
        speaker_map = diarizer.load_speaker_map(args.speaker_map) if args.speaker_map else None
        segments_text = diarizer.assign_speakers_to_transcript(segments, diarization_segments, speaker_map)
    else:
        segments_text = [seg.format() for seg in segments]

   # --- Save raw transcript ---
    base_name = Path(wav_file).stem
    raw_output = output_path / f"{base_name}.txt"
    clean_output = output_path / f"{base_name}_clean.txt"

    with open(raw_output, "w", encoding="utf-8") as f:
        f.write("\n".join(segments_text))
    if args.verbose:
        print(f"Raw transcript saved to: {raw_output}")

    # --- Summarization / Cleaning ---
    raw_text = "\n".join(segments_text)
    list(summarizer.reconstruct_transcript(raw_text, terms_dict=summarizer.TERMS_TO_CORRECT, output_file=clean_output))
    if args.verbose:
        print(f"Clean transcript saved to: {clean_output}")

    if args.verbose:
        print("\nProcess completed.")

if __name__ == "__main__":
    main()
