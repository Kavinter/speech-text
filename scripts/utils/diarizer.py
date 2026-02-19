import sherpa_onnx
import time
import argparse
import soundfile as sf

from scripts.utils.transcriber import Transcriber
from scripts.utils import audio_utils

# Paths to the models
SEGMENTATION_MODEL_PATH ="models/sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
EMBEDDING_MODEL_PATH = "models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"

MULTI_SPEAKER_THRESHOLD = 0.3
SHORT_SEGMENT_THRESHOLD = 1.5
SHORT_SEGMENT_DOMINANCE = 0.7

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
        min_duration_on=0.5,
        min_duration_off=0.3
    )

    return sherpa_onnx.OfflineSpeakerDiarization(config)

def load_speaker_map(path: str) -> dict:
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line:
                key, val = line.split("=", 1)
                mapping[key.strip()] = val.strip()
    return mapping

def diarize(wav_path: str, num_speakers: int = -1, cluster_threshold: float = 0.5):
    diarizer = load_diarizer(num_speakers=num_speakers, cluster_threshold=cluster_threshold)

    wav_16k_path = audio_utils.convert_to_wav_16k_mono(wav_path, output_dir="output")

    # Checking if audio is stereo
    samples, _sample_rate = sf.read(wav_16k_path)
    if len(samples.shape) > 1:
        samples = samples.mean(axis=1)

    result = diarizer.process(samples=samples, callback=None)

    return result.sort_by_start_time()


def assign_speakers_to_transcript(transcript, diarization_segments, speaker_map=None):
    """
    Assign speakers to transcript using majority voting per transcript segment.
    If second speaker has >= multi_speaker_threshold overlap ratio,
    output as multi-speaker (e.g., speaker_0 + speaker_1).
    """

    output_segments = []
    previous_speaker = None

    for t_seg in transcript:
        seg_start = t_seg.start
        seg_end = t_seg.end
        seg_duration = max(seg_end - seg_start, 0.001)  # safety

        speaker_overlap = {}

        for d_seg in diarization_segments:
            overlap = min(seg_end, d_seg.end) - max(seg_start, d_seg.start)
            if overlap > 0:
                speaker_id = f"speaker_{d_seg.speaker}"
                speaker_overlap[speaker_id] = speaker_overlap.get(speaker_id, 0) + overlap

        if not speaker_overlap:
            assigned_label = previous_speaker if previous_speaker else "SPEAKER_UNKNOWN"

        else:
            sorted_speakers = sorted(
                speaker_overlap.items(),
                key=lambda x: x[1],
                reverse=True
            )

            main_speaker, main_overlap = sorted_speakers[0]
            main_ratio = main_overlap / seg_duration

            # Short segment logic
            if seg_duration < SHORT_SEGMENT_THRESHOLD:
                if main_ratio >= SHORT_SEGMENT_DOMINANCE:
                    assigned_label = main_speaker
                else:
                    assigned_label = previous_speaker if previous_speaker else main_speaker

            else:
                # Multi-speaker logic for normal segments
                if len(sorted_speakers) > 1:
                    second_speaker, second_overlap = sorted_speakers[1]
                    second_ratio = second_overlap / seg_duration

                    if second_ratio >= MULTI_SPEAKER_THRESHOLD:
                        assigned_label = f"{main_speaker} + {second_speaker}"
                    else:
                        assigned_label = main_speaker
                else:
                    assigned_label = main_speaker

        if speaker_map:
            if " + " in assigned_label:
                parts = assigned_label.split(" + ")
                assigned_label = " + ".join(speaker_map.get(p, p) or p for p in parts)
            else:
                assigned_label = speaker_map.get(assigned_label, assigned_label) or assigned_label


        previous_speaker = assigned_label

        segment_text = t_seg.text.strip() if t_seg.text else ""
        output_segments.append(
            f"[{time.strftime('%H:%M:%S', time.gmtime(seg_start))} - "
            f"{time.strftime('%H:%M:%S', time.gmtime(seg_end))}] "
            f"({assigned_label}) {segment_text}"
        )

    return output_segments



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
