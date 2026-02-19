from scripts.utils import audio_utils

class AudioProcessor:

    @staticmethod
    def validate_audio_format(file_path: str) -> bool:
        return audio_utils.validate_audio_format(file_path)

    @staticmethod
    def convert_to_wav_16k_mono(input_path: str, output_dir: str | None = None, verbose: bool = False) -> str:
        return audio_utils.convert_to_wav_16k_mono(input_path, output_dir, verbose)

    @staticmethod
    def get_audio_duration(wav_path: str) -> float:
        return audio_utils.get_audio_duration(wav_path)
