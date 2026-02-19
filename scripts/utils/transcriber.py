import time, pathlib
from dataclasses import dataclass
from faster_whisper import WhisperModel
from typing import List, Optional

# Represents a segment of transcribed audio
@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

    def format(self) -> str:
        start_str = time.strftime('%H:%M:%S', time.gmtime(int(self.start)))
        end_str = time.strftime('%H:%M:%S', time.gmtime(int(self.end)))
        return f"[{start_str} - {end_str}] {self.text}"

# Wrapper class for Whisper transcription
class Transcriber:
    def __init__(self, model_size: str = "large", device: str = "cpu"):

        self.model_size = model_size
        self.device = device
        self.model = WhisperModel(model_size, device=device)

    # Transcribe an audio file
    def transcribe(self, audio_path: str, prompt: Optional[str] = None, language: Optional[str] = "sr", verbose=False) -> List[TranscriptSegment]:
        
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


__name__ == "__main__"