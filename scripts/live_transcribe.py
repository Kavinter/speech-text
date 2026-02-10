import sounddevice as sd
import numpy as np
import wave
import time
import os
import tempfile
from faster_whisper import WhisperModel
from faster_whisper.vad import get_speech_timestamps, VadOptions
from queue import Queue
from threading import Thread, Event
from dataclasses import dataclass

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 5
CHUNK_SIZE = SAMPLE_RATE * CHUNK_DURATION
LANGUAGE = "sr"

stop_event = Event()
pause_event = Event()
audio_queue = Queue()
full_transcript = []

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

def save_chunk(data: np.ndarray, counter: int):
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"chunk_{counter}.wav")

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data.tobytes())

    return filename


def record_chunks():
    print("Recording started. Press Ctrl+C or 'q' to stop.")
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
        print("\nRecording interrupted by user.")

def transcribe_audio():
    model = WhisperModel("large", device="cpu", compute_type="float32")

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

        audio_queue.task_done()

def command_listener():
    while not stop_event.is_set():
        try:
            cmd = input("Enter 'q' to quit, 'p' to pause, 'r' to resume: ").strip().lower()
            if cmd == 'q':
                stop_event.set()
            elif cmd == 'p':
                pause_event.set()
                print("Recording paused.")
            elif cmd == 'r':
                pause_event.clear()
                print("Recording resumed.")
        except EOFError:
            break


def main():
    record_thread = Thread(target=record_chunks)
    transcribe_thread = Thread(target=transcribe_audio)
    command_thread = Thread(target=command_listener)

    record_thread.start()
    transcribe_thread.start()
    command_thread.start()

    try:
        record_thread.join()
        print("Recording finished. Processing remaining chunks...")
        audio_queue.join()
        transcribe_thread.join()
    except KeyboardInterrupt:
        print("\nCtrl+C detected, stopping...")
        stop_event.set()

    
    command_thread.join()

    full_transcript.sort(key=lambda x: x.start)

    print("\nFULL TRANSCRIPT:")
    for seg in full_transcript:
        print(seg.format())

if __name__ == "__main__":
    main()
