# EDAmbilight — Developer Guide

This document covers the source code structure, development setup, and build process.
For end-user documentation see [README.md](README.md).

---

## Project Structure

```
EDAmbilight/
├── src/                         # Python backend
│   ├── main.py                  # Entry point (Eel server + init sequence)
│   ├── settings.py              # Settings model (config/settings.json)
│   ├── api/
│   │   ├── ambilight_api.py     # Eel-exposed endpoints for ambilight control
│   │   ├── settings_api.py      # Eel-exposed endpoints for settings & OpenRGB
│   │   └── topology_api.py      # Eel-exposed endpoints for zone topology
│   ├── core/
│   │   ├── screen_capturer_service.py  # WGC → DXGI → mss capture backend
│   │   ├── openrgb_sdk.py       # Own OpenRGB SDK client (TCP 6742)
│   │   └── audio_capture.py     # System audio loopback (WASAPI) → beats
│   ├── effects/
│   │   ├── ambilight_service.py # Main sampling loop + color processing
│   │   ├── standby_effects.py   # LED effects while the screen is unavailable
│   │   ├── accent_effects.py    # Beat accent: flash / hue shift math and limiter
│   │   ├── beat_detector.py     # Spectral-flux beat detection
│   │   └── openrgb_manager.py   # OpenRGB device/zone abstraction
│   └── utils/
│       ├── openrgb_bootstrap.py # Auto-detect / auto-start OpenRGB
│       └── paths.py             # Base-dir resolution (dev vs frozen exe)
│
├── web/                         # Frontend (HTML + vanilla JS + Tailwind)
│   ├── index.html               # Dashboard
│   ├── loading.html             # Splash screen
│   ├── devices.html             # Device manager
│   ├── settings.html            # OpenRGB / web-port settings
│   ├── preview.html             # WebGL live effect preview
│   ├── topology-editor.html     # Drag-and-drop zone canvas
│   ├── css/
│   │   ├── design-system.css    # Design tokens + component styles
│   │   ├── fonts.css            # @font-face declarations
│   │   ├── glass-select.css     # Translucent dropdown panel (both themes)
│   │   └── tailwind.min.css     # Tailwind CSS (local, no CDN)
│   ├── js/
│   │   ├── ambilight.js         # Dashboard logic (renderDevices, liveUpdate)
│   │   ├── navigation.js        # Sidebar + sonar-ring animations
│   │   ├── common.js            # api() wrapper, showNotification(), escapeHtml
│   │   ├── theme.js             # Light / dark switch (localStorage `edambi.theme`)
│   │   ├── glass-select.js      # Replaces the native <select> popup
│   │   └── topology-editor.js   # Topology canvas logic
│   └── fonts/                   # Self-hosted woff2 (Inter, Orbitron, Rajdhani, Material Symbols)
│
├── config/                      # Runtime config (created on first launch)
│   ├── settings.json
│   ├── ambilight_config.json
│   └── device_topologies.json
│
├── tests/
│   └── test_*.py                # pytest suite: OpenRGB SDK, topology, sampling, accent…
│
├── .interface-design/
│   └── system.md                # Design-system reference
│
├── requirements.txt
├── build.ps1                    # PyInstaller build script
├── icon.ico
└── start.bat / start.ps1        # Run from source shortcuts
```

---

## Development Setup

### Prerequisites

- Python 3.12 (3.10+ should work)
- [OpenRGB](https://openrgb.org) installed and running with SDK Server enabled

### Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

For faster screen capture (optional, Windows only):

```powershell
# Windows Graphics Capture (requires Rust toolchain)
pip install windows-capture

# DXGI Desktop Duplication
pip install dxcam
```

For system tray support (optional):

```powershell
pip install pystray Pillow
```

### Run from source

```powershell
python src/main.py
```

The web UI opens automatically at `http://localhost:8001`.

---

## Architecture

EDAmbilight uses **[Eel](https://github.com/python-eel/Eel)** as the Python↔JavaScript bridge.
Eel runs a lightweight Bottle/WebSocket server; the frontend calls Python functions via `eel.functionName()` and Python can push updates via `eel.jsFunction()`.

```
Browser (HTML/JS)
     │
     │  WebSocket (Eel)
     ▼
Python (Eel server, port 8001)
     │
     ├── AmbilightService      – sampling loop (thread)
     │     └── ScreenCapturerService  – frame acquisition
     │
     └── OpenRGBManager        – device/zone control
           └── core/openrgb_sdk.py – own OpenRGB SDK client (TCP 6742)
```

### Startup sequence

1. `main.py` initialises Eel and starts the WebSocket server
2. `loading.html` opens in the browser; it polls `get_init_status()` every 500 ms
3. A background thread (`_do_init`) runs three steps:
   - Step 1 — bootstrap OpenRGB (detect, optionally launch, connect)
   - Step 2 — start `AmbilightService`
   - Step 3 — register all Eel API modules
4. Once `ready = true`, the loading page redirects to `index.html`

### Screen capture

`ScreenCapturerService` tries backends in order:

1. **WGC** (`windows-capture`) — lowest latency, works with HDR, requires Windows 10 1903+
2. **DXGI** (`dxcam`) — fast, requires a dedicated GPU
3. **mss** — pure Python fallback, always available

Set `capturer` in `ambilight_config.json` to force a specific backend.

### Sampling pipeline (per frame)

```
Raw frame (numpy array, BGR)
  │
  ├─ black-bar detection  →  content rect [x0,y0,x1,y1]
  │
  ├─ per-edge strip extraction  (adaptive depth or fixed)
  │
  ├─ per-LED segment sampling  (percentile / dominant / mean)
  │
  ├─ saturation boost
  │
  ├─ temporal smoothing (EMA)  with scene-cut bypass
  │
  └─ send colors to OpenRGB devices
```

---

## Build (Windows EXE)

```powershell
# Windowed build (no console)
.\build.ps1

# Debug build (console visible)
.\build.ps1 -Console
```

Output: `dist\EDAmbilight\EDAmbilight.exe` + `_internal\` + `web\`

The `web\` folder is copied next to the exe by `build.ps1` after PyInstaller runs.
`config\` and `log\` are created at runtime by the exe.

To create the release zip:

```powershell
Compress-Archive -Path dist\EDAmbilight\* -DestinationPath EDAmbilight-v1.0.0.zip
```

---

## Frontend Notes

- **No build step** — plain HTML + vanilla JS + local Tailwind CSS. Editing `web/` takes effect immediately when running from source.
- **Design system** — use `web/css/design-system.css` tokens for all colors, spacing, and components. See `.interface-design/system.md` for the full reference.
- **Themes** — a page takes part when `<html>` carries `data-themeable` and loads `js/theme.js` in `<head>` (before the first paint). Light values live in the `:root[data-theme="light"]` block of `design-system.css`. The topology canvas is drawn by hand, so its colours come from `_pal()` in `js/topology-editor.js` (it redraws on the `themechange` event).
- **Dropdowns** — include `css/glass-select.css` and `js/glass-select.js`: every `<select>` keeps its native look, id and `onchange`, only the popup list is replaced. Add `data-native` to opt a select out.
- **`topology-editor.html`** — no external requests; keep its dependencies local like the other pages.
- **Fonts** — all self-hosted in `web/fonts/`; no external requests at runtime. Inter is the body font in both themes, Orbitron the heading font of the dark theme. Keep body text at 12 px or more: Inter is wider than the Rajdhani it replaced, so check for wrapping when you add labels.

---

## Running Tests

```powershell
python -m pytest tests/
```

---

## Release Checklist

- [ ] Bump version in `src/version.py`, the `README.md` badge and `CHANGELOG.md`
- [ ] Run `.\build.ps1` and smoke-test the exe
- [ ] Create release zip: `Compress-Archive dist\EDAmbilight\* EDAmbilight-vX.X.X.zip`
- [ ] Tag the commit: `git tag vX.X.X`
- [ ] Push tag and create GitHub Release, attach the zip
