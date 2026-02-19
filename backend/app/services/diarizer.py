# app/services/diarizer_service.py
import soundfile as sf
from typing import List, Optional
from pathlib import Path
from scripts.utils import diarizer as diarizer_utils
from scripts.utils.transcriber import TranscriptSegment

_diarizer_instance = None

def get_diarizer(num_speakers: int = -1, cluster_threshold: float = 0.5):
    global _diarizer_instance
    if _diarizer_instance is None:
        _diarizer_instance = diarizer_utils.load_diarizer(
            num_speakers=num_speakers,
            cluster_threshold=cluster_threshold
        )
    return _diarizer_instance


class DiarizationService:

    def __init__(self, num_speakers: int = -1, cluster_threshold: float = 0.5):
        self.num_speakers = num_speakers
        self.cluster_threshold = cluster_threshold
        self.diarizer_model = get_diarizer(num_speakers, cluster_threshold)

    def diarize(self, wav_path: str) -> list:
        samples, _sample_rate = sf.read(wav_path)
        segments = self.diarizer_model.process(samples=samples, callback=None)
        return segments.sort_by_start_time()

    def assign_speakers(self, transcript: List[TranscriptSegment], diarization_segments: list, speaker_map: Optional[dict] = None) -> List[str]:
        return diarizer_utils.assign_speakers_to_transcript(
            transcript, diarization_segments, speaker_map
        )

