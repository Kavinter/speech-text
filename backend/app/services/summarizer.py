# app/services/summarizer_service.py
from pathlib import Path
from typing import Dict, Optional, Generator
from scripts.utils import summarizer as summarizer_utils


class SummarizerService:

    @staticmethod
    def reconstruct_transcript(
        raw_text: str,
        terms_dict: Optional[Dict[str, str]] = None,
        output_file: Optional[Path] = None
    ) -> Generator[str, None, None]:
        return summarizer_utils.reconstruct_transcript(
            raw_text=raw_text,
            terms_dict=terms_dict,
            output_file=output_file
        )

    @staticmethod
    def parse_meeting_minutes(llm_json: str):
        return summarizer_utils.parse_meeting_minutes(llm_json)
