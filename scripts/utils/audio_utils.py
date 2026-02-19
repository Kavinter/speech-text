import os, sys
import ffmpeg
from pathlib import Path
import wave
import contextlib

SUPPORTED_AUDIO_FORMATS = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".webm"}


def validate_audio_format(file_path: str) -> bool:
    p = Path(file_path)

    return p.is_file() and p.suffix.lower() in SUPPORTED_AUDIO_FORMATS

def convert_to_wav_16k_mono(input_path: str, output_dir: str, verbose: bool = False) -> str:

    input_path = Path(input_path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist or is not readable: {input_path}")

    if input_path.suffix.lower() == ".wav" and input_path.stem.endswith("_16k_mono"):
        if verbose:
            print(f"Skipping conversion (already 16k mono): {input_path}")
        return str(input_path)
    
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise ValueError("You must provide a valid output folder")
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    base_name = Path(input_path).stem
    output_path = os.path.join(output_dir, f"{base_name}_16k_mono.wav")

    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, ar=16000, ac=1, format='wav')
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Error converting audio file: {e.stderr.decode()}") from e
    except FileNotFoundError:
        raise EnvironmentError("FFmpeg is not installed or not available in PATH")

    if not os.path.isfile(output_path):
        raise RuntimeError(f"Converted file was not created: {output_path}")

    return output_path

def get_audio_duration(wav_path: str) -> float:
    path = Path(wav_path)
    if not path.exists():
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    with contextlib.closing(wave.open(str(path), 'r')) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration = frames / float(rate)
        return duration

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_folder = sys.argv[2]
    else:
        input_file = input("Enter the path to the audio file: ").strip()
        output_folder = input("Enter the output folder: ").strip()

    if not validate_audio_format(input_file):
        print(f"Invalid audio file: {input_file}")
        sys.exit(1)

    try:
        wav_file = convert_to_wav_16k_mono(input_file, output_folder)
        print(f"Converted file: {wav_file}")
    except Exception as e:
        print(f"Error during conversion: {e}")