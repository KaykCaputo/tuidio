# Tuidio - Almost a DAW (Not even close)

**Tuidio** is a low-resource Digital Audio Workstation (DAW) designed to make music production accessible on low-end computers. By leveraging a Terminal User Interface (TUI), it removes heavy graphical hardware barriers.

Currently, it allows for multi-track recording directly via the terminal.

---

## Screenshot

![Tuidio Demo](screenshots/tuidiodemonstration.png)

## Features

- **Multi-track Recording:** Record multiple audio layers via a terminal interface.
- **Lightweight TUI:** Minimalist Text User Interface for maximum performance.
- **Hardware Efficient:** Designed specifically for low-end machines.

## Roadmap

### 1. Sync and Timeline

- [x] **Timing Engine:** BPM to audio sample conversion for mathematical precision.
- [x] **Metronome:** Synchronized audio clicks and visual beat tracking.
- [x] **Playhead:** A real-time moving cursor indicating playback position.

### 2. Clips and Recording

- [ ] **Multitrack Engine:** Overdubbing support (record while listening to existing tracks).
- [ ] **Clip System:** Non-destructive editing using metadata (start point, offset, and duration).

### 3. Audio Editing

- [ ] **Snapping:** Automatic alignment of clips to the metronome grid.
- [ ] **Editing Commands:** Keyboard shortcuts for:
  - **Split:** Slice clips at specific points.
  - **Move:** Shift clips across the timeline or between tracks.
  - **Delete:** Remove clips from the session.

### 4. Persistence and Output

- [ ] **Project Save/Load:** Session data stored in lightweight `.tuidio` (JSON) files.
- [ ] **Mixdown (Export):** Render all tracks into a final master `.wav` file.

### 5. Low-End Optimization

- [ ] **Latency Compensation:** Automatic adjustment for hardware I/O delay.
- [ ] **Priority Multithreading:** Isolated threads for Audio (Real-time priority) and Interface (Low priority).

---

## Requirements

- **Python:** 3.10+
- **OS:** Linux (recommended for best compatibility)
- **Hardware:** Microphone and speakers/headphones

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repo-url>
   cd tuidio
   ```

2. **Create a virtual environment (Recommended):**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## How to Run

Start the application with:

```bash
python tuidio.py
```

---

## License

This project is licensed under the [MIT License](LICENSE).

---

> **Tuidio** = **TUI** + **Audio** (or **TUI** + **Studio**... you decide)
