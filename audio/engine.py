import sounddevice as sd
import soundfile as sf
import threading
import os
import queue
import tempfile
import numpy as np
import time
import sys

# --- Linux Audio Backend Configuration ---
if sys.platform.startswith("linux"):
    os.environ["SD_API"] = "alsa"


## --- AudioTrack: Handles Audio Recording and Playback ---
class AudioTrack:
    # --- Initialize AudioTrack State ---
    def __init__(self):
        self.input_device = None
        self.output_device = None
        self.fs = 44100
        self.channels = 1
        self.audio_file = os.path.join(
            tempfile.gettempdir(), f"track_{time.time_ns()}.wav"
        )
        self.is_recording = False
        self.volume = 1.0
        self.is_muted = False
        self.is_soloed = False
        self.start_time = 0
        self.q = queue.Queue()

    # --- Set Input Device and Update Audio Parameters ---
    def set_input_device(self, idx):
        try:
            if idx is None:
                return
            self.input_device = int(idx)
            info = sd.query_devices(self.input_device)
            self.fs = int(info.get("default_samplerate", 44100))
            self.channels = max(1, int(info.get("max_input_channels", 1)))
        except:
            self.fs = 44100

    # --- Start Recording Audio ---
    def record(self):
        if self.is_recording:
            return
        self.is_recording = True
        self.start_time = time.time()
        while not self.q.empty():
            self.q.get()

        def callback(indata, frames, time_info, status):
            self.q.put(indata.copy())

        def _task():
            try:
                with sf.SoundFile(
                    self.audio_file,
                    mode="w",
                    samplerate=self.fs,
                    channels=self.channels,
                    subtype="PCM_16",
                ) as f:
                    with sd.InputStream(
                        samplerate=self.fs,
                        device=self.input_device,
                        channels=self.channels,
                        callback=callback,
                    ):
                        while self.is_recording:
                            try:
                                data = self.q.get(timeout=0.2)
                                f.write(data)
                            except queue.Empty:
                                continue
            except:
                self.is_recording = False

        threading.Thread(target=_task, daemon=True).start()

    # --- Stop Recording Audio ---
    def stop_recording(self):
        self.is_recording = False

    # --- Play Recorded Audio ---
    def play(self, master_vol=1.0):
        if (
            not os.path.exists(self.audio_file)
            or os.path.getsize(self.audio_file) < 100
        ):
            return

        def _task():
            try:
                data, fs = sf.read(self.audio_file)
                data = data * self.volume * master_vol
                sd.play(data, fs, device=self.output_device)
                sd.wait()
            except:
                pass

        threading.Thread(target=_task, daemon=True).start()

    # --- Cleanup Temporary Audio File ---
    def cleanup(self):
        self.is_recording = False
        try:
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
        except:
            pass
