import os
import numpy as np
import sounddevice as sd
import time
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer, Container
from textual.widgets import Button, Label, Static, Select
from textual.reactive import reactive
from daw import AudioTrack

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


class TrackWidget(Static):
    is_recording = reactive(False)
    volume_lvl = reactive(7)
    is_muted = reactive(False)
    is_soloed = reactive(False)

    def __init__(self):
        super().__init__()
        self.audio_track = AudioTrack()

    def get_bar(self, level) -> str:
        return "█" * level + "░" * (10 - level)

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

    def update_waveform(self):
        try:
            path = self.audio_track.audio_file
            if os.path.exists(path) and os.path.getsize(path) > 100:
                import soundfile as sf

                data, _ = sf.read(path)
                if data.ndim > 1:
                    data = data[:, 0]

                width = 55
                chunks = np.array_split(data, width)

                chars_up = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                chars_down = [" ", " ", "▔", "🬇", "🬆", "🬅", "🬄", "🬃", "🬂", "▀"]

                top_str = ""
                bot_str = ""

                for c in chunks:
                    amp = np.max(np.abs(c)) if len(c) > 0 else 0
                    if amp < 0.001:
                        top_str += " "
                        bot_str += " "
                    else:
                        idx = int(amp * 250)
                        top_str += chars_up[min(idx, len(chars_up) - 1)]
                        bot_str += chars_down[min(idx, len(chars_down) - 1)]

                self.query_one("#wave-top").update(top_str)
                self.query_one("#wave-bottom").update(bot_str)
        except:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close":
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
            self.stop_and_update()
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
            self.audio_track.output_device = self.app.selected_output
            self.audio_track.play(master_vol=self.app.master_volume / 10)
        elif "vol" in event.button.id:
            self.volume_lvl = min(
                10, max(0, self.volume_lvl + (1 if "up" in event.button.id else -1))
            )
            self.audio_track.volume = self.volume_lvl / 10
            self.query_one("#vol-display").update(self.get_bar(self.volume_lvl))

    def stop_and_update(self):
        sd.stop()
        self.audio_track.stop_recording()
        self.is_recording = False
        self.app.stop_timer()
        self.remove_class("active-rec")
        self.set_timer(0.5, self.update_waveform)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "input-select":
            self.audio_track.set_input_device(event.value)


class Tuidio(App):
    master_volume = reactive(7)
    selected_output = reactive(None)
    time_display = reactive("00:00:00")

    CSS = """
    Screen { background: black; color: #aaa; }
    #app-container { border: solid #222; height: 100%; layout: vertical; }
    #top-bar { height: 3; border-bottom: solid #222; layout: horizontal; align: left middle; padding: 0 1; }
    .btn-text { min-width: 4; height: 1; border: none; background: transparent; color: #eee; }
    .label-out { margin-left: 2; color: #555; }
    #clock { color: #0f0; margin-left: 2; text-style: bold; width: 12; }

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

    def compose(self) -> ComposeResult:
        with Container(id="app-container"):
            with Horizontal(id="top-bar"):
                yield Button("✚", id="add-track", classes="btn-text")
                yield Label(" | ")
                yield Button("▶", id="all-play", classes="btn-text")
                yield Button("■", id="all-stop", classes="btn-text")
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

    def get_bar(self, level):
        return "█" * level + "░" * (10 - level)

    def start_timer(self):
        self.start_rec_time = time.time()
        self.timer_active = True
        if not hasattr(self, "clock_timer"):
            self.clock_timer = self.set_interval(0.1, self.update_clock)

    def stop_timer(self):
        self.timer_active = False

    def update_clock(self):
        if hasattr(self, "timer_active") and self.timer_active:
            elapsed = time.time() - self.start_rec_time
            mins, secs = divmod(int(elapsed), 60)
            msecs = int((elapsed % 1) * 100)
            self.time_display = f"{mins:02}:{secs:02}:{msecs:02}"
            self.query_one("#clock").update(self.time_display)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-track":
            self.query_one("#arranger-scroll").mount(TrackWidget())
        elif "m-vol" in event.button.id:
            self.master_volume = min(
                10, max(0, self.master_volume + (1 if "up" in event.button.id else -1))
            )
            self.query_one("#m-vol-display").update(self.get_bar(self.master_volume))
        elif event.button.id == "all-play":
            tracks = list(self.query(TrackWidget))
            any_solo = any(t.is_soloed for t in tracks)
            for tw in tracks:
                if (any_solo and tw.is_soloed) or (not any_solo and not tw.is_muted):
                    tw.audio_track.output_device = self.selected_output
                    tw.audio_track.play(master_vol=self.master_volume / 10)
        elif event.button.id == "all-stop":
            sd.stop()
            self.stop_timer()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "output-select":
            self.selected_output = event.value


if __name__ == "__main__":
    Tuidio().run()
