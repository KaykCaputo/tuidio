import numpy as np
import sounddevice as sd


class Mixer:
    def __init__(self, fs=44100):
        self.fs = fs
        self.bpm = 120
        self.is_playing = False
        self.current_sample = 0
        self.tracks = []
        self.metronome_enabled = False
        self.output_device = None
        self._stream = None
        self.metro_counter = 0

    @property
    def samples_per_beat(self):
        return int((self.fs * 60) / self.bpm)

    def audio_callback(self, outdata, frames, time, status):
        outdata.fill(0)

        if self.metronome_enabled:
            for i in range(frames):
                pos = (self.metro_counter + i) % self.samples_per_beat
                if pos < 800:
                    t = pos / self.fs
                    freq = (
                        880
                        if ((self.metro_counter + i) // self.samples_per_beat) % 4 == 0
                        else 440
                    )
                    outdata[i, 0] += 0.1 * np.sin(2 * np.pi * freq * t)
            self.metro_counter += frames

        if self.is_playing:
            any_solo = any(t.is_soloed for t in self.tracks)
            for track in self.tracks:
                chunk = track.get_audio_chunk(self.current_sample, frames)
                if chunk is not None:
                    if any_solo:
                        vol = (
                            track.volume
                            if track.is_soloed and not track.is_muted
                            else 0
                        )
                    else:
                        vol = track.volume if not track.is_muted else 0
                    outdata[: len(chunk), 0] += chunk * vol
            self.current_sample += frames

    def ensure_stream(self):
        if self._stream is None or not self._stream.active:
            if self._stream:
                self._stream.close()
            self._stream = sd.OutputStream(
                samplerate=self.fs,
                device=self.output_device,
                channels=1,
                callback=self.audio_callback,
            )
            self._stream.start()

    def start_transport(self):
        self.current_sample = 0
        self.is_playing = True
        self.ensure_stream()

    def stop_transport(self):
        self.is_playing = False
        self.current_sample = 0

    def stop(self):
        self.stop_transport()
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
