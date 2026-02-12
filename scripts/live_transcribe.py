import sounddevice as sd
import numpy as np
import wave
import argparse
import time
import os
import tempfile
from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps, VadOptions
from queue import Queue
from threading import Thread, Event, Lock
from dataclasses import dataclass
from pathlib import Path
from utils import summarizer, meeting_parser, diarizer

SAMPLE_RATE = 16000
CHANNELS = 1
DEFAULT_CHUNK_DURATION = 5
CHUNK_DURATION = DEFAULT_CHUNK_DURATION
CHUNK_SIZE = SAMPLE_RATE * CHUNK_DURATION
LANGUAGE = "sr"

print_lock = Lock()
stop_event = Event()
pause_event = Event()
audio_queue = Queue()
full_transcript = []
all_chunk_files = []

vad_options = VadOptions(
    threshold=0.5,
    min_speech_duration_ms=200,
    min_silence_duration_ms=150
)

# Represents a segment of transcribed audio
@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

    def format(self) -> str:
        start_str = time.strftime("%M:%S", time.gmtime(int(self.start)))
        end_str = time.strftime("%M:%S", time.gmtime(int(self.end)))
        return f"[{start_str} - {end_str}] {self.text}"
    
def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs)

def save_chunk(data: np.ndarray, counter: int) -> str:
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"chunk_{counter}.wav")

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data.tobytes())

    all_chunk_files.append(filename)

    return filename

def record_chunks():
    chunk_buffer = np.empty((0,), dtype=np.int16)
    chunk_counter = 1
    total_samples = 0

    try:
        # Open input stream from microphone
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16') as stream:
            while not stop_event.is_set():
                if pause_event.is_set():
                    time.sleep(0.1)
                    continue

                # Read small portion of audio (0.5s)
                data, _ = stream.read(CHUNK_SIZE // 10)
                chunk_buffer = np.concatenate((chunk_buffer, data.flatten()))

                # If we have enough data for a full chunk, save it
                if len(chunk_buffer) >= CHUNK_SIZE:
                    float_buffer = chunk_buffer.astype(np.float32) / 32768.0
                    speech_segments = get_speech_timestamps(
                            audio=float_buffer,
                            vad_options=vad_options,
                            sampling_rate=SAMPLE_RATE
                    )

                    for seg in speech_segments:
                        start_sample = seg['start']
                        end_sample = seg['end']
                        voiced_chunk = chunk_buffer[start_sample:end_sample]

                        if len(voiced_chunk) > 0:
                            filename = save_chunk(voiced_chunk, chunk_counter)
                            
                            chunk_start_sec = (total_samples + start_sample) / SAMPLE_RATE
                            audio_queue.put((filename, chunk_start_sec))
                            chunk_counter += 1

                    total_samples += len(chunk_buffer)
                    chunk_buffer = np.empty((0,), dtype=np.int16)

            # Save any remaining audio in buffer
            if len(chunk_buffer) > 0:
                float_buffer = chunk_buffer.astype(np.float32) / 32768.0
                speech_segments = get_speech_timestamps(
                        audio=float_buffer,
                        vad_options=vad_options,
                        sampling_rate=SAMPLE_RATE
                )

                for seg in speech_segments:
                    start_sample = seg['start']
                    end_sample = seg['end']
                    voiced_chunk = chunk_buffer[start_sample:end_sample]
                    if len(voiced_chunk) > 0:
                        filename = save_chunk(voiced_chunk, chunk_counter)
                        chunk_start_sec = (total_samples + start_sample) / SAMPLE_RATE
                        audio_queue.put((filename, chunk_start_sec))
                        chunk_counter += 1

    except KeyboardInterrupt:
        safe_print("\nRecording interrupted by user.")

def merge_wav_files(chunk_files, output_path):
    audio_data = []

    for path in chunk_files:
        with wave.open(path, 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
            audio_data.append(np.frombuffer(frames, dtype=np.int16))

    merged = np.concatenate(audio_data)

    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(merged.tobytes())

def transcribe_audio(whisper_model_name: str):
    model = WhisperModel(whisper_model_name, device="cpu", compute_type="float32")

    while not stop_event.is_set() or not audio_queue.empty():
        try:
            chunk_path, chunk_start = audio_queue.get(timeout=0.5)
        except:
            continue

        segments, _info = model.transcribe(
            chunk_path,
            language=LANGUAGE,
            beam_size=5,
            word_timestamps=False
        )

        # Convert segments to TranscriptSegment with absolute times
        for segment in segments:
            segment_obj = TranscriptSegment(
                start = chunk_start + segment.start,
                end = chunk_start + segment.end,
                text = segment.text.strip()
            )

            if segment_obj.text:
                full_transcript.append(segment_obj)
                safe_print(f"\n{segment_obj.format()}", flush=True)

        audio_queue.task_done()

def save_transcript(transcript, path):
    with open(path, "w", encoding="utf-8") as f:
        for seg in transcript:
            f.write(seg.format() + "\n")

def cleanup_chunks(chunk_files):
    for path in chunk_files:
        try:
            os.remove(path)
        except OSError:
            pass

def command_listener():
    while not stop_event.is_set():
        try:
            with print_lock:
                cmd = input("Enter 'q' to quit, 'p' to pause, 'r' to resume: ").strip().lower()
            if cmd == 'q':
                safe_print("Stopping recording and finishing remaining chunks...")
                stop_event.set()
            elif cmd == 'p':
                if not pause_event.is_set():
                    pause_event.set()
                    safe_print("Recording paused.")
                else:
                    safe_print("Recording is already paused.")
            elif cmd == 'r':
                if pause_event.is_set():
                    pause_event.clear()
                    safe_print("Recording resumed.")
                else:
                    safe_print("Recording is not paused.")
            else:
                safe_print("Unknown command. Use 'q', 'p' or 'r'.")

        except EOFError:
            break


def main():
    parser = argparse.ArgumentParser(description="Live audio recording and transcription")

    parser.add_argument(
        "-o", "--output",
        help="Path to output WAV file (e.g. output/live.wav)"
    )
    parser.add_argument(
        "--chunk-duration",
        type=int,
        default=DEFAULT_CHUNK_DURATION,
        help="Chunk duration in seconds"
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Run summarization after recording (true/false)"
    )

    parser.add_argument(
        "-f", "--format",
        type=str,
        choices=["md", "json", "txt"],
        default="txt",
        help="Format for output file with transcript / summary (default: txt)"
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="meta-llama-3.1-8b-instruct",
        help="LLM model for summarization"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default="large",
        help="Whisper model which will be used (default: large)"
    )
    parser.add_argument(
    "--diarize",
    action="store_true",
    help="Enable speaker diarization (default: False)"
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=-1,
        help="Number of speakers in audio; -1 = auto-detect"
    )
    parser.add_argument(
        "--speaker-map",
        type=str,
        help="Path to file mapping speaker IDs to names (SPEAKER_00=Marko)"
    )


    args = parser.parse_args()

    # ---- apply runtime config ----
    global CHUNK_DURATION, CHUNK_SIZE
    CHUNK_DURATION = args.chunk_duration
    CHUNK_SIZE = SAMPLE_RATE * CHUNK_DURATION
    summarize_flag = args.summarize

    # ---- resolve output paths ----
    output_dir = Path(args.output or "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_wav = Path(output_dir) / f"recording_{timestamp}.wav"
    output_txt = output_wav.with_suffix(".txt")
    summary_file = output_wav.with_name(output_wav.stem + "_summary." + args.format)

    safe_print(f"Recording to: {output_wav}")
    safe_print(f"Transcript:  {output_txt}")
    if summarize_flag:
        safe_print(f"Summary:  {summary_file}")




    safe_print("-----------------------")
    safe_print(f"Output audio     : {os.path.abspath(output_wav)}")
    safe_print(f"Output transcript: {os.path.abspath(output_txt)}")
    safe_print(f"Chunk duration   : {CHUNK_DURATION}s")
    safe_print("-----------------------")

    # ---- threads ----
    record_thread = Thread(target=record_chunks, daemon=True)
    transcribe_thread = Thread(target=transcribe_audio, args=(args.model,), daemon=True)
    command_thread = Thread(target=command_listener, daemon=True)

    record_thread.start()
    transcribe_thread.start()
    command_thread.start()

    try:
        record_thread.join()
    except KeyboardInterrupt:
        safe_print("\nStopping recording...")
        stop_event.set()

    stop_event.set()
    audio_queue.join()
    transcribe_thread.join()
    command_thread.join()

    # ---- post-processing ----
    full_transcript.sort(key=lambda x: x.start)

    merge_wav_files(all_chunk_files, output_wav)
    cleanup_chunks(all_chunk_files)

    # ---- apply speaker diarization ----
    if args.diarize:
        safe_print("Running speaker diarization...")
        merged_wav = output_wav
        diarization_segments = diarizer.diarize(str(merged_wav), num_speakers=args.num_speakers)
        speaker_map = diarizer.load_speaker_map(args.speaker_map) if args.speaker_map else None
        segments_text = diarizer.assign_speakers_to_transcript(full_transcript, diarization_segments, speaker_map)
    else:
        segments_text = [seg.format() for seg in full_transcript]

    with open(output_txt, "w", encoding="utf-8") as f:
        for line in segments_text:
            f.write(line + "\n")

    safe_print(f"Audio saved to     : {output_wav}")
    safe_print(f"Transcript saved to: {output_txt}")

    if summarize_flag:
        safe_print("Running transcript reconstruction and summarization...")
        raw_text = output_txt.read_text(encoding="utf-8")

        cleaned_file = output_txt.with_name(output_txt.stem + "_clean.txt")

        ###summarizer.CHAT_MODEL = args.llm_model
        meeting_parser.CHAT_MODEL = args.llm_model

        list(summarizer.reconstruct_transcript(
            raw_text,
            terms_dict=summarizer.TERMS_TO_CORRECT,
            output_file=cleaned_file
        ))

        minutes = meeting_parser.generate_meeting_minutes_from_file(cleaned_file)


        # Save summary
        if args.format == "json":
            summary_file.write_text(minutes.to_json(), encoding="utf-8")
        else:
            meeting_parser.save_meeting_minutes(minutes, summary_file)


    safe_print("Done!")




if __name__ == "__main__":
    main()
