from pathlib import Path
from typing import List
import sherpa_onnx
import time
import argparse
import soundfile as sf

from scripts.utils.transcriber import Transcriber, TranscriptSegment
from scripts.utils import audio_utils

# Paths to the models
SEGMENTATION_MODEL_PATH ="models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
EMBEDDING_MODEL_PATH = "models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"


def load_segmentation_model() -> sherpa_onnx.OfflineSpeakerSegmentationModelConfig:
    pyannote_cfg = sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
        model=str(SEGMENTATION_MODEL_PATH)
    )
    segmentation_cfg = sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
        pyannote=pyannote_cfg
    )
    return segmentation_cfg


def load_embedding_model():
    return sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(EMBEDDING_MODEL_PATH))


def load_diarizer(num_speakers: int = -1, cluster_threshold: float = 0.5):
    segmentation_cfg = load_segmentation_model()
    embedding_cfg = load_embedding_model()
    num_clusters = -1 if num_speakers <= 0 else num_speakers

    clustering_cfg = sherpa_onnx.FastClusteringConfig(
        num_clusters=num_clusters, threshold=cluster_threshold
    )

    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=segmentation_cfg,
        embedding=embedding_cfg,
        clustering=clustering_cfg,
        min_duration_on=0.3,
        min_duration_off=0.5
    )

    return sherpa_onnx.OfflineSpeakerDiarization(config)


def diarize(wav_path: str, num_speakers: int = -1, cluster_threshold: float = 0.5):
    diarizer = load_diarizer(num_speakers=num_speakers, cluster_threshold=cluster_threshold)

    wav_16k_path = audio_utils.convert_to_wav_16k_mono(wav_path, output_dir="output")

    # Checking if audio is stereo
    samples, _sample_rate = sf.read(wav_16k_path)
    if len(samples.shape) > 1:
        samples = samples.mean(axis=1)

    result = diarizer.process(samples=samples, callback=None)

    return result.sort_by_start_time()


def assign_speakers_to_transcript(
    transcript: List[TranscriptSegment], diarization_segments
):
    merged_segments = []
    for t_seg in transcript:
        assigned_speaker = "SPEAKER_UNKNOWN"
        for d_seg in diarization_segments:
            if t_seg.start < d_seg.end and t_seg.end > d_seg.start:
                assigned_speaker = f"speaker_{d_seg.speaker}"
                break
        start_str = time.strftime("%H:%M:%S", time.gmtime(t_seg.start))
        end_str = time.strftime("%H:%M:%S", time.gmtime(t_seg.end))
        merged_segments.append(f"[{start_str} - {end_str}] ({assigned_speaker}) {t_seg.text}")
    return merged_segments


def main():
    parser = argparse.ArgumentParser(description="Diarization + Transcription pipeline")
    parser.add_argument(
        "--audio-file", required=True, help="Path to audio WAV file"
    )
    parser.add_argument(
        "--model", default="large", help="Whisper model size (default: large)"
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=-1,
        help="Number of speakers in audio; -1 = auto-detect",
    )
    args = parser.parse_args()

    transcriber = Transcriber(model_size=args.model)
    transcript = transcriber.transcribe(args.audio_file, language="sr")

    diarization_segments = diarize(args.audio_file, num_speakers=args.num_speakers)

    merged_segments = assign_speakers_to_transcript(transcript, diarization_segments)

    for seg in merged_segments:
        print(seg)


if __name__ == "__main__":
    main()
