import os
import numpy as np
import sounddevice as sd
import time
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Container
from textual.widgets import Button, Label, Static, Select
from textual.reactive import reactive
from audio.engine import AudioTrack
from audio.mixer import Mixer

# --- Device Options Initialization ---
try:
    ALL_DEVICES = sd.query_devices()
    INPUT_OPTS = [
        (f"{d['name'][:18]}", i)
        for i, d in enumerate(ALL_DEVICES)
        if d["max_input_channels"] > 0
    ]
    OUTPUT_OPTS = [
        (f"{d['name'][:18]}", i)
        for i, d in enumerate(ALL_DEVICES)
        if d["max_output_channels"] > 0
    ]
except:
    INPUT_OPTS = [("Default", 0)]
    OUTPUT_OPTS = [("Default", 0)]


## --- Track Widget (Single Track UI) ---
class TrackWidget(Static):
    is_recording = reactive(False)
    volume_lvl = reactive(7)
    is_muted = reactive(False)
    is_soloed = reactive(False)
    playhead_idx = reactive(-1)

    def __init__(self):
        super().__init__()
        self.audio_track = AudioTrack()
        self.last_top = ""
        self.last_bot = ""

    def get_bar(self, level) -> str:
        return "█" * level + "░" * (10 - level)

    # --- Compose Track Widget UI ---
    def compose(self) -> ComposeResult:
        with Horizontal(classes="track-card"):
            with Vertical(classes="track-sidebar"):
                with Horizontal(classes="track-top-row"):
                    yield Label("󰎆 TRK", classes="track-label")
                    yield Button("✖", id="btn-close", classes="btn-close")

                yield Select(
                    options=INPUT_OPTS,
                    prompt="Input Device",
                    id="input-select",
                    classes="mini-select",
                )

                with Horizontal(classes="track-btns"):
                    yield Button("●", id="btn-rec", classes="btn-icon btn-rec")
                    yield Button("■", id="btn-stop", classes="btn-icon")
                    yield Button("▶", id="btn-play", classes="btn-icon")
                    yield Button("M", id="btn-mute", classes="btn-icon")
                    yield Button("S", id="btn-solo", classes="btn-icon")

                with Horizontal(classes="vol-row"):
                    yield Button("-", id="btn-vol-down", classes="btn-vol")
                    yield Label(f"{self.get_bar(self.volume_lvl)}", id="vol-display")
                    yield Button("+", id="btn-vol-up", classes="btn-vol")

            with Vertical(classes="waveform-area"):
                yield Label(" ", id="wave-top", classes="wave-line top")
                yield Label(" ", id="wave-bottom", classes="wave-line bot")

    # --- Update Waveform Visualization ---
    def update_waveform(self):
        try:
            data = self.audio_track.data
            if data is None:
                return

            width = 55
            window_samples = 44100 * 30
            samples_per_char = window_samples // width

            filled_chars = min(width, len(data) // samples_per_char)

            chars_up = ["_", "▂", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
            chars_down = [" ", "▔", "▔", "🬇", "🬆", "🬅", "🬄", "🬃", "🬂", "▀"]

            top_str = ""
            bot_str = ""

            for i in range(width):
                if i < filled_chars:
                    start = i * samples_per_char
                    end = (i + 1) * samples_per_char
                    chunk = data[start:end]
                    amp = np.max(np.abs(chunk)) if len(chunk) > 0 else 0
                    idx = int(amp * 200)
                    top_str += chars_up[min(idx, len(chars_up) - 1)]
                    bot_str += chars_down[min(idx, len(chars_down) - 1)]
                else:
                    top_str += " "
                    bot_str += " "

            self.last_top = top_str
            self.last_bot = bot_str
            self.query_one("#wave-top").update(top_str)
            self.query_one("#wave-bottom").update(bot_str)
        except:
            pass

    def watch_playhead_idx(self, idx: int):
        if not self.last_top:
            return

        t = list(self.last_top)
        b = list(self.last_bot)

        if 0 <= idx < len(t):
            t[idx] = "[bold yellow]█[/]"
            b[idx] = "[bold yellow]█[/]"

        self.query_one("#wave-top").update("".join(t))
        self.query_one("#wave-bottom").update("".join(b))

    # --- Handle Track Button Events ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
            if self.audio_track in self.app.mixer.tracks:
                self.app.mixer.tracks.remove(self.audio_track)
            self.audio_track.cleanup()
            self.remove()
        elif event.button.id == "btn-rec":
            if not self.is_recording:
                self.audio_track.record()
                self.is_recording = True
                self.app.start_timer()
                self.add_class("active-rec")
            else:
                self.stop_and_update()
        elif event.button.id == "btn-stop":
            self.app.stop_all()
        elif event.button.id == "btn-mute":
            self.is_muted = not self.is_muted
            self.audio_track.is_muted = self.is_muted
            if self.is_muted:
                self.add_class("track-muted")
            else:
                self.remove_class("track-muted")
        elif event.button.id == "btn-solo":
            self.is_soloed = not self.is_soloed
            self.audio_track.is_soloed = self.is_soloed
            if self.is_soloed:
                self.add_class("track-solo")
            else:
                self.remove_class("track-solo")
        elif event.button.id == "btn-play":
            self.app.play_track_solo(self)
        elif "vol" in event.button.id:
            self.volume_lvl = min(
                10, max(0, self.volume_lvl + (1 if "up" in event.button.id else -1))
            )
            self.audio_track.volume = self.volume_lvl / 10
            self.query_one("#vol-display").update(self.get_bar(self.volume_lvl))

    # --- Stop Recording and Update UI ---
    def stop_and_update(self):
        self.audio_track.stop_recording()
        self.is_recording = False
        self.app.stop_timer()
        self.remove_class("active-rec")
        if self.audio_track not in self.app.mixer.tracks:
            self.app.mixer.tracks.append(self.audio_track)
        self.update_waveform()

    # --- Handle Input Device Selection ---
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "input-select":
            self.audio_track.set_input_device(event.value)


## --- Main Application Class ---
class Tuidio(App):
    master_volume = reactive(7)
    selected_output = reactive(None)
    time_display = reactive("00:00:00")
    bpm = reactive(120)

    # --- Application CSS Styles ---
    CSS = """
    Screen { background: black; color: #aaa; }
    #app-container { border: solid #222; height: 100%; layout: vertical; }
    #top-bar { height: 3; border-bottom: solid #222; layout: horizontal; align: left middle; padding: 0 1; }
    .btn-text { min-width: 4; height: 1; border: none; background: transparent; color: #eee; }
    .btn-mini { min-width: 3; height: 1; border: none; background: #222; margin: 0 1; }
    .label-out { margin-left: 2; color: #555; }
    #clock { color: #0f0; margin-left: 2; text-style: bold; width: 12; }
    .metronome-on { color: #0ff !important; }

    Select { background: #111; border: none; height: 1; color: white; }
    Select > SelectCurrent { border: none; background: transparent; height: 1; }
    Select > SelectCurrent Static { color: white !important; width: 100%; content-align: left middle; padding: 0 1; }
    #output-select { width: 26; margin-left: 1; }
    
    #main-workspace { layout: horizontal; height: 1fr; }
    #arranger-column { width: 78%; layout: vertical; }
    #side-panel { width: 22%; border-left: solid #222; padding: 1; }

    TrackWidget { height: 7; border-bottom: solid #222; }
    .track-sidebar { width: 26; border-right: solid #222; padding: 0 1; }
    .track-top-row { height: 1; align: left middle; margin-top: 0; }
    .track-label { width: 1fr; text-style: bold; color: #777; }
    .btn-close { min-width: 3; height: 1; background: transparent; border: none; color: #444; }
    .btn-close:hover { color: red; }

    .mini-select { width: 24; height: 1; margin: 0; }
    .track-btns { height: 1; margin: 0; }
    .btn-icon { min-width: 4; height: 1; border: none; background: transparent; color: #eee; }
    .btn-rec { color: #522; }
    .active-rec .btn-rec { color: red; }
    
    .vol-row { height: 1; align: left middle; }
    .btn-vol { min-width: 3; height: 1; border: none; background: transparent; }
    #vol-display { width: 12; text-align: center; color: #333; }

    .waveform-area {
        width: 1fr;
        height: 100%;
        align: center middle;
        padding-left: 1;
    }
    .wave-line { 
        width: 100%;
        height: 1;
        text-style: bold;
        text-wrap: nowrap;
    }
    .wave-line.top { content-align: center bottom; color: white; }
    .wave-line.bot { content-align: center top; color: #666; }

    .track-muted { opacity: 0.4; }
    .track-solo #btn-solo { color: yellow; }
    """

    def __init__(self):
        super().__init__()
        self.mixer = Mixer()

    # --- Compose Main Application UI ---
    def compose(self) -> ComposeResult:
        with Container(id="app-container"):
            with Horizontal(id="top-bar"):
                yield Button("✚", id="add-track", classes="btn-text")
                yield Label(" | ")
                yield Button("▶", id="all-play", classes="btn-text")
                yield Button("■", id="all-stop", classes="btn-text")
                yield Button("󰓟", id="btn-metronome", classes="btn-text")
                yield Label(" BPM:")
                yield Button("-", id="bpm-down", classes="btn-mini")
                yield Label(str(self.bpm), id="bpm-display")
                yield Button("+", id="bpm-up", classes="btn-mini")
                yield Label(" Out:", classes="label-out")
                yield Select(
                    options=OUTPUT_OPTS, prompt="Output Device", id="output-select"
                )
                yield Label(self.time_display, id="clock")

            with Horizontal(id="main-workspace"):
                with Vertical(id="arranger-column"):
                    with ScrollableContainer(id="arranger-scroll"):
                        yield TrackWidget()
                with Vertical(id="side-panel"):
                    yield Label("󰓠 MASTER")
                    with Horizontal(classes="master-vol-row"):
                        yield Button("-", id="m-vol-down", classes="btn-text")
                        yield Label(
                            self.get_bar(self.master_volume), id="m-vol-display"
                        )
                        yield Button("+", id="m-vol-up", classes="btn-text")

    def on_mount(self):
        self.set_interval(0.1, self.sync_ui)

    def sync_ui(self):
        if self.mixer.is_playing:
            elapsed = self.mixer.current_sample / self.mixer.fs
            mins, secs = divmod(int(elapsed), 60)
            msecs = int((elapsed % 1) * 100)
            self.query_one("#clock").update(f"{mins:02}:{secs:02}:{msecs:02}")

            idx = int((self.mixer.current_sample / (self.mixer.fs * 30)) * 55)
            for tw in self.query(TrackWidget):
                tw.playhead_idx = idx

        for tw in self.query(TrackWidget):
            if tw.is_recording:
                tw.update_waveform()

    def play_track_solo(self, track_widget):
        for tw in self.query(TrackWidget):
            tw.audio_track.is_soloed = False
        track_widget.audio_track.is_soloed = True
        self.mixer.start_transport()

    def stop_all(self):
        self.mixer.stop_transport()
        self.stop_timer()
        for tw in self.query(TrackWidget):
            tw.playhead_idx = -1
            tw.update_waveform()

    # --- Volume Bar Helper ---
    def get_bar(self, level):
        return "█" * level + "░" * (10 - level)

    # --- Start Recording Timer ---
    def start_timer(self):
        self.start_rec_time = time.time()
        self.timer_active = True
        self.set_interval(0.1, self.update_clock)

    # --- Stop Recording Timer ---
    def stop_timer(self):
        self.timer_active = False

    # --- Update Recording Clock ---
    def update_clock(self):
        if getattr(self, "timer_active", False):
            elapsed = time.time() - self.start_rec_time
            mins, secs = divmod(int(elapsed), 60)
            msecs = int((elapsed % 1) * 100)
            self.time_display = f"{mins:02}:{secs:02}:{msecs:02}"
            self.query_one("#clock").update(self.time_display)

    # --- Handle Main App Button Events ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-track":
            new_track = TrackWidget()
            self.query_one("#arranger-scroll").mount(new_track)
        elif event.button.id == "btn-metronome":
            self.mixer.metronome_enabled = not self.mixer.metronome_enabled
            event.button.toggle_class("metronome-on")
            if self.mixer.metronome_enabled:
                self.mixer.ensure_stream()
        elif "bpm" in event.button.id:
            self.bpm = max(
                40, min(240, self.bpm + (5 if "up" in event.button.id else -5))
            )
            self.mixer.bpm = self.bpm
            self.query_one("#bpm-display").update(str(self.bpm))
        elif "m-vol" in event.button.id:
            self.master_volume = min(
                10, max(0, self.master_volume + (1 if "up" in event.button.id else -1))
            )
            self.query_one("#m-vol-display").update(self.get_bar(self.master_volume))
        elif event.button.id == "all-play":
            self.mixer.tracks = [tw.audio_track for tw in self.query(TrackWidget)]
            for tw in self.query(TrackWidget):
                tw.audio_track.is_soloed = False
            self.mixer.start_transport()
        elif event.button.id == "all-stop":
            self.stop_all()

    # --- Handle Output Device Selection ---
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "output-select":
            self.selected_output = self.mixer.output_device = event.value
            self.mixer.ensure_stream()
