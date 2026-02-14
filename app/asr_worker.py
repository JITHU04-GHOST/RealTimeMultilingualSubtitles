import threading
import time
import os
import numpy as np
import soundfile as sf
import whisper


# Load Whisper ONCE at app startup
print("Loading Whisper-medium model (global load)…")
WHISPER_MODEL = whisper.load_model("medium", device="cuda")
print("Whisper model READY.")


class ASRWorker(threading.Thread):
    def __init__(self, get_time_fn, send_fn, audio_path):
        super().__init__(daemon=True)
        self.get_time = get_time_fn
        self.send = send_fn
        self.audio_path = audio_path
        self.sr = 16000
        self.chunk = 1.5
        self.stop_flag = False

    def stop(self):
        self.stop_flag = True

    def run(self):

        while not os.path.exists(self.audio_path):
            time.sleep(0.05)

        print("ASR Thread running...")

        while not self.stop_flag:
            t = self.get_time()
            start = int(t * self.sr)
            frames = int(self.chunk * self.sr)

            try:
                data, _ = sf.read(self.audio_path, start=start, frames=frames, dtype="float32")
            except:
                time.sleep(0.05)
                continue

            if np.mean(np.abs(data)) < 0.01:
                continue

            sf.write("chunk.wav", data, self.sr)
            result = WHISPER_MODEL.transcribe("chunk.wav", language="en")

            for seg in result.get("segments", []):
                txt = seg.get("text", "").strip()
                if txt:
                    self.send({"text": txt})
