from typing import List
from scripts.utils.transcriber import Transcriber, TranscriptSegment

_transcriber_instance: Transcriber | None = None

def get_transcriber(model_size: str = "large", device: str = "cpu") -> Transcriber:
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = Transcriber(model_size=model_size, device=device)
    return _transcriber_instance


class TranscriptionService:
    def __init__(self, model_size: str = "large", device: str = "cpu"):
        self.transcriber: Transcriber = get_transcriber(model_size=model_size, device=device)

    def transcribe(self, audio_path: str, language: str = "sr", verbose: bool = False) -> List[TranscriptSegment]:
        return self.transcriber.transcribe(audio_path, language=language, verbose=verbose)
