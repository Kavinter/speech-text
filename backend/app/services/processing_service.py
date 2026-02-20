from pathlib import Path
from typing import Optional, List

from scripts.utils.transcriber import TranscriptSegment

from .audio_processor import AudioProcessor
from .transcriber import TranscriptionService
from .diarizer import DiarizationService
from .summarizer import SummarizerService
from .meeting_parser import MeetingParserService


class ProcessingService:
    def __init__(
        self,
        diarization: bool = False,
        num_speakers: int = -1,
        cluster_threshold: float = 0.5,
        model_size: str = "large",
        device: str = "cpu"
    ):
        self.audio_processor = AudioProcessor()
        self.transcriber = TranscriptionService(
            model_size=model_size,
            device=device
        )
        self.summarizer = SummarizerService()
        self.meeting_parser = MeetingParserService()
        self.num_speakers = num_speakers
        self.cluster_threshold = cluster_threshold
        self.diarization_enabled = diarization
        self.diarizer = None
        if diarization:
            self.diarizer = DiarizationService(
                num_speakers=num_speakers, 
                cluster_threshold=cluster_threshold
            )

    def process_meeting_audio(
        self,
        audio_path: str,
        output_dir: Optional[Path] = None
    ) -> dict:

        output_dir = Path(output_dir or "output")
        output_dir.mkdir(parents=True, exist_ok=True)

        if not self.audio_processor.validate_audio_format(audio_path):
            raise ValueError(f"Unsupported audio format: {audio_path}")

        wav_path = self.audio_processor.convert_to_wav_16k_mono(
            audio_path,
            str(output_dir)
        )

        duration = self.audio_processor.get_audio_duration(wav_path)

        segments: List[TranscriptSegment] = self.transcriber.transcribe(
            wav_path,
            language="sr"
        )

        raw_text = "\n".join([seg.format() for seg in segments])

        clean_file = output_dir / f"{Path(audio_path).stem}_clean.txt"

        list(
            self.summarizer.reconstruct_transcript(
                raw_text,
                output_file=clean_file
            )
        )

        clean_lines = clean_file.read_text(encoding="utf-8").splitlines()

        for seg, line in zip(segments, clean_lines):
            if "]" in line:
                seg.text = line.split("]", 1)[1].strip()

        reconstructed_text = "\n".join([seg.format() for seg in segments])
        detected_labels = []

        if self.diarization_enabled and self.diarizer:
            diarization_segments = self.diarizer.diarize(str(wav_path))
            detected_labels = sorted({f"speaker_{seg.speaker}" for seg in diarization_segments})
            speaker_map = {label: None for label in detected_labels}

            segments_text = self.diarizer.assign_speakers(segments, diarization_segments, speaker_map)
            reconstructed_text = "\n".join([s for s in segments_text if s])

        transcript_file = output_dir / f"{Path(audio_path).stem}_final.txt"
        transcript_file.write_text(
            reconstructed_text,
            encoding="utf-8"
        )

        test_text = Path("data/sastanak.txt")

        minutes = MeetingParserService.generate_from_file(test_text)

        summary_dict = {
            "executive_summary": minutes.executive_summary,
            "topics": minutes.topics,
            "decisions": [d.model_dump() for d in minutes.decisions],
            "action_items": [a.model_dump() for a in minutes.action_items],
            "discussions": [d.model_dump() for d in minutes.discussions],
        }

        return {
            "duration": duration,
            "raw_text": raw_text,
            "reconstructed_text": reconstructed_text,
            "detected_speakers": detected_labels,
            "summary": summary_dict
        }
