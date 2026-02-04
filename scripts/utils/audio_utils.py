import os
import ffmpeg
from pathlib import Path


SUPPORTED_AUDIO_FORMATS = {".mp3", ".mp4", ".m4a", ".wav", ".ogg", ".webm"}

def validate_audio_format(file_path: str) -> bool:

    if not file_path:
        return False
    
    if not os.path.isfile(file_path):
        return False

    name, ext = os.path.splitext(file_path)
    ext = ext.lower()

    return ext in SUPPORTED_AUDIO_FORMATS

def convert_to_wav_16k_mono(input_path: str, output_dir: str) -> str:

    if not isinstance(input_path, str) or not os.path.isfile(input_path):
        raise FileNotFoundError(f"Ulazni fajl ne postoji ili nije citljiv: {input_path}")
    
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise ValueError("Morate zadati validan output folder")
    
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
        raise RuntimeError(f"Greska pri konverziji audio fajla: {e.stderr.decode()}") from e
    except FileNotFoundError:
        raise EnvironmentError("FFmpeg nije instaliran ili nije dostupan u PATH")

    if not os.path.isfile(output_path):
        raise RuntimeError(f"Konvertovani fajl nije kreiran: {output_path}")

    return output_path


input_file = input("Unesi putanju do audio fajla: ").strip()
output_folder = input("Unesi folder gde ce se sacuvati konvertovani fajl: ").strip()

if not validate_audio_format(input_file):
    print(f"Nevalidan audio fajl ili fajl ne postoji: {input_file}")
else:
    try:
        wav_file = convert_to_wav_16k_mono(input_file, output_folder)
        print(f"Konvertovani fajl uspesno kreiran: {wav_file}")

        if os.path.isfile(wav_file):
            print("Fajl postoji i konverzija je uspesna")
        else:
            print("Greska: konvertovani fajl nije kreiran")

    except Exception as e:
        print(f"Greska pri konverziji: {e}")