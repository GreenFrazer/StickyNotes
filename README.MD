# Sticky Notes Desktop App

Cross-platform sticky notes for **Windows** and **macOS** — floating notes, multi-monitor auto-hiding docks, system tray, clipboard integration, and JSON persistence.

Built with Python 3 and PyQt6.

## Key Features

- Unlimited draggable, resizable, frameless sticky notes with auto-save (~500ms)
- 7 colour themes, opacity, always-on-top, compact mode, **private notes** (click-to-reveal masking)
- Copy to clipboard from note window, dock indicators, and hover popups
- Auto-hiding dock per monitor (top or side layout)
- Multi-monitor aware (dock recreated on screen add/remove)
- System tray with note count and quick actions
- Global shortcuts (platform-specific — see below)

## Data Storage

Notes and settings are stored locally as JSON. A note is written to disk the first time it has non-empty content (auto-saved after ~500ms of typing). Empty notes are not persisted.

| Platform | Data directory | Main file | Other files |
|----------|----------------|-----------|-------------|
| **Windows** | `%LOCALAPPDATA%\StickyNotesApp\` | `data.json` | `data.json.bak` (backup), `app.lock` (single-instance) |
| **macOS** | `~/Library/Application Support/StickyNotesApp/` | `data.json` | `data.json.bak`, `app.lock` |

**macOS example (expanded path):**
`/Users/<your-username>/Library/Application Support/StickyNotesApp/data.json`

**What is stored in `data.json`:**
- `notes` — content, position, size, colour, opacity, always-on-top, compact mode, **private** flag, timestamps
- `settings` — dock position (`top` / `side`), dark mode

**Private notes:** Mark a note private to hide its content on screen and in dock previews until you click to reveal. Copy still copies the real text. This is shoulder-surfing protection only — note content is **not encrypted** on disk.

**When files are created:**
- `data.json` — on first note save or first settings change
- `data.json.bak` — rotated backup before each successful save
- `app.lock` — on app launch (released on clean exit)

On macOS, open the data folder in Finder: **Go → Go to Folder…** → paste `~/Library/Application Support/StickyNotesApp`.

## Keyboard Shortcuts

| Action | Windows | macOS |
|--------|---------|-------|
| New note | Ctrl+Shift+N | Cmd+Shift+N **or** Ctrl+Shift+N |
| Hide all notes | Ctrl+Shift+H | Cmd+Shift+H **or** Ctrl+Shift+H |

macOS global shortcuts require **Accessibility** permission (System Settings → Privacy & Security → Accessibility).

## Project Layout

| I want to… | Go to |
|------------|-------|
| Change note/dock UI | `stickynotes/ui/` |
| Fix save/load | `stickynotes/storage.py` |
| Change where notes are stored | `stickynotes/platform/windows/paths.py` or `stickynotes/platform/macos/paths.py` |
| Fix Windows shortcuts | `stickynotes/platform/windows/hotkeys.py` |
| Fix macOS shortcuts | `stickynotes/platform/macos/hotkeys.py` |
| Build Windows `.exe` | `packaging/windows/build.ps1` |
| Deploy Windows to Program Files | `packaging/windows/deploy.ps1` |
| Build macOS `.app` | `packaging/macos/build.sh` |
| Deploy macOS to Applications | `packaging/macos/deploy.sh` |

```
StickyNotes/
├── stickynotes/           # shared application code
│   ├── main.py            # entry: QApplication, QLockFile
│   ├── app_manager.py
│   ├── storage.py
│   ├── models.py, theme.py
│   ├── ui/                # note_window, dock, settings_dialog
│   └── platform/          # windows/, macos/, linux/
├── packaging/
│   ├── windows/           # PyInstaller spec, build.ps1, deploy.ps1
│   └── macos/             # py2app setup.py, build.sh, deploy.sh
├── main.py                # root shim
├── requirements.txt
└── tests/
```

## Run Locally

```bash
pip install -r requirements.txt

# macOS also needs pynput for global hotkeys:
pip install -r requirements-macos.txt

python main.py
```

Legacy entry points `Sticky_notes_app.py` and `python -m stickynotes.main` also work.

## Build & Deploy

Each platform has a **build** script (artifact only) and a **deploy** script (build + install to the standard location). Both use a local `.venv` in the repo root.

| Platform | Build only | Build + deploy |
|----------|------------|----------------|
| **Windows** | `.\packaging\windows\build.ps1` | `.\packaging\windows\deploy.ps1` |
| **macOS** | `bash packaging/macos/build.sh` | `bash packaging/macos/deploy.sh` |

**Install locations:**
- Windows → `C:\Program Files\StickyNotes\StickyNotes.exe` (deploy prompts for admin)
- macOS → `/Applications/Sticky Notes.app`

Optional flags: `--build-only` / `--install-only` (macOS) or `-BuildOnly` / `-InstallOnly` (Windows).

### Windows

```powershell
# Build only → dist\StickyNotes.exe
.\packaging\windows\build.ps1

# Build and install to Program Files
.\packaging\windows\deploy.ps1
```

### macOS

Must be built on a Mac (py2app cannot cross-compile):

```bash
# Build only → dist/Sticky Notes.app
bash packaging/macos/build.sh

# Build and install to /Applications
bash packaging/macos/deploy.sh
```

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Technology

| Component | Technology |
|-----------|------------|
| Language | Python 3 |
| UI | PyQt6 |
| Storage | JSON (atomic writes + `.bak` recovery) |
| Windows packaging | PyInstaller |
| macOS packaging | py2app |
| macOS hotkeys | pynput |
