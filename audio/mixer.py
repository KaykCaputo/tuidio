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

    @property
    def samples_per_beat(self):
        return int((self.fs * 60) / self.bpm)

    def audio_callback(self, outdata, frames, time, status):
        outdata.fill(0)

        if not self.is_playing:
            return

        for track in self.tracks:
            chunk = track.get_audio_chunk(self.current_sample, frames)
            if chunk is not None:
                vol = track.v
                if track.is_soloed:
                    pass
                outdata[: len(chunk), 0] += chunk * vol

        if self.metronome_enabled:
            beat_pos = self.current_sample % self.samples_per_beat
            if beat_pos < 800:
                t = np.arange(min(frames, 800 - beat_pos)) / self.fs
                freq = (
                    880
                    if (self.current_sample // self.samples_per_beat) % 4 == 0
                    else 440
                )
                click = 0.1 * np.sin(2 * np.pi * freq * t)
                outdata[: len(click), 0] += click

        self.current_sample += frames

    def start(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()

        self.is_playing = True
        self._stream = sd.OutputStream(
            samplerate=self.fs,
            device=self.output_device,
            channels=1,
            callback=self.audio_callback,
        )
        self._stream.start()

    def stop(self):
        self.is_playing = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.current_sample = 0
