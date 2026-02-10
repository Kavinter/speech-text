import sounddevice as sd
import numpy as np
import wave
import time
import os
import tempfile
from threading import Thread, Event

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 5
CHUNK_SIZE = SAMPLE_RATE * CHUNK_DURATION

stop_event = Event()
pause_event = Event()

def record_chunks():
    """Record audio from microphone and save chunks as WAV files."""
    print("Recording started. Press Ctrl+C or 'q' to stop.")
    chunk_buffer = np.empty((0,), dtype=np.int16)
    chunk_counter = 1

    try:
        # Open input stream from microphone
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16') as stream:
            start_time = time.time()
            while not stop_event.is_set():
                if pause_event.is_set():
                    time.sleep(0.1)
                    continue

                # Read small portion of audio (0.5s)
                data, _ = stream.read(CHUNK_SIZE // 10)
                chunk_buffer = np.concatenate((chunk_buffer, data.flatten()))

                # If we have enough data for a full chunk, save it
                if len(chunk_buffer) >= CHUNK_SIZE:
                    save_chunk(chunk_buffer[:CHUNK_SIZE], chunk_counter)
                    chunk_buffer = chunk_buffer[CHUNK_SIZE:]
                    chunk_counter += 1

                    elapsed = int(time.time() - start_time)
                    print(f"Chunk {chunk_counter-1} saved. Elapsed time: {elapsed}s")

            # Save any remaining audio in buffer
            if len(chunk_buffer) > 0:
                save_chunk(chunk_buffer, chunk_counter)
                print(f"Chunk {chunk_counter} saved (remaining audio).")

    except KeyboardInterrupt:
        print("\nRecording interrupted by user.")

def save_chunk(data: np.ndarray, counter: int):
    """Save numpy array as a temporary WAV file."""
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"chunk_{counter}.wav")
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data.tobytes())
    print(f"WAV file saved: {filename}")

def main():
    thread = Thread(target=record_chunks)
    thread.start()

    try:
        while thread.is_alive():
            cmd = input("Enter 'q' to quit, 'p' to pause, 'r' to resume: ").strip().lower()
            if cmd == 'q':
                stop_event.set()
            elif cmd == 'p':
                pause_event.set()
                print("Recording paused.")
            elif cmd == 'r':
                pause_event.clear()
                print("Recording resumed.")
    except KeyboardInterrupt:
        stop_event.set()
    
    thread.join()
    print("Recording finished.")

if __name__ == "__main__":
    main()
