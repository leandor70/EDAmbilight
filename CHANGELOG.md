# Changelog

All notable changes to EDAmbilight will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.8] — 2026-10-25

### Changed

- At startup and after every OpenRGB reconnect, `device_topologies.json` is
  checked against the hardware, which always wins. New devices are imported;
  zones whose name or LED count differ are re-synced, keeping the layout of
  the zones that still exist. Devices that are no longer detected are left
  alone and simply receive no colors.

### Fixed

- Zones with segments now get unique indexes. Before, two segmented zones
  shared the same indexes, so changes could go undetected and a re-sync could
  mix up their layout. Topologies saved by older versions are renumbered
  automatically on first start.
- DXGI capture is restarted also when dxcam clears its own capture thread
  after a crash (the LEDs used to stay frozen). Capture restart and FPS
  changes no longer race.

---

## [1.0.7] — 2026-10-24

### Added

- **Min brightness** slider in the Output panel (`min_luminance`, 0 = off).
  Colors darker than the chosen level are lifted to it with their hue kept,
  so LEDs over dim areas of the screen no longer look switched off. Pure
  black still keeps the LEDs off.

### Changed

- Keyboards are now excluded by the device type OpenRGB reports, not by
  matching keywords in the device name, so other devices whose name happens
  to contain a model like "K7" are no longer skipped by mistake.

---

## [1.0.6] — 2026-10-23

### Fixed

- DXGI capture no longer stops for good after a display mode change, lock
  screen or driver reset. The capture thread is now monitored and restarted
  automatically, with up to 10 retries and increasing back-off.

---

## [1.0.5] — 2026-10-21

### Added

- Help page with a four-step getting-started guide. It opens automatically on
  first run and can be reopened any time from the sidebar.

### Changed

- On first run the Topology Editor imports the zones from OpenRGB
  automatically, so a fresh install no longer starts with an empty editor.

---

## [1.0.4] — 2026-10-21

### Added

- Control page: an info (i) button on every panel opens a tooltip explaining
  the parameters and what happens when each one is raised or lowered.

### Changed

- Parameter panels not used by the selected algorithm are now shown dimmed and
  disabled with a "Not used" badge instead of being hidden.

### Fixed

- Slider and on/off toggle thumbs are now centered on their tracks.

---

## [1.0.3] — 2026-10-14

### Fixed

- Ambilight thread no longer crashes at startup when neither `windows-capture`
  nor `dxcam` is installed: the `wgc` preference now falls back to dxcam and
  then to mss, like `auto` already did.
- DXGI capture in the bundled exe returned no frames: `dxcam` converts to BGR
  through OpenCV, which it does not install. Frames are now requested as BGRA
  and the alpha channel is dropped, so OpenCV is not needed.
- The auto-switch no longer flips DXGI -> WGC -> mss every time the foreground
  window changes when `windows-capture` is not installed (dxcam is a singleton,
  a second instance failed with "Capture is already running").
- Startup no longer fails with `'charmap' codec can't encode character '→'`
  on consoles using cp1252: stdout/stderr are forced to UTF-8.

### Changed

- `dxcam` is now bundled in the exe (`build.ps1`), so DXGI capture works
  without any extra install.
- The exe writes its output to `log/edambilight.log` for diagnostics.
- `start.bat` reports which screen-capture backend is available.

---

## [1.0.2] — 2026-06-21

### Fixed

- Topology calibration no longer crashes with `IndexError` when the saved
  topology declares more LEDs than the hardware reports — out-of-range LED
  indices are skipped (same root cause as the 1.0.1 color-count fix).
- Devices that share the same name (e.g. two identical Corsair RAM modules)
  no longer collide on a single device key. They previously mapped to one
  key, so one module was unreachable and its topology zones were duplicated
  in the editor. Duplicates now get a `#N` suffix; the first occurrence keeps
  the bare key, so existing single-device configs are unaffected.
- Physical LEDs now match the calibration overlay drawn in the editor. The
  ring color of each LED was computed twice (canvas in JS, hardware in
  Python) with diverging geometry — different ring center, a half-LED
  positional offset, and limited rotation handling — so physical LEDs lit
  up differently from the drawing. The editor canvas is now the single
  source of truth: it sends the per-LED ring map to the backend, which just
  applies it.

### Changed

- Calibration and device identification now fully suspend the ambilight so
  they render correctly without the sampling loop fighting them: `pause()`
  blacks out every managed device, the sampling loop skips a write if a pause
  arrives mid-frame, and `flash_topology_device` pauses sampling and
  serializes its writes through the device lock.
- Leaving the topology editor (page navigation or window close) now stops an
  active calibration automatically, instead of leaving its thread driving the
  LEDs with the ambilight stuck paused. Handled both client-side (`pagehide`)
  and reliably server-side via the browser close callback; stopping is a
  no-op when no calibration is running, so normal navigation is undisturbed.

---

## [1.0.1] — 2026-06-21

### Fixed

- Resolved "Number of colors doesn't match number of LEDs" error: color counts
  sent to a device are now reconciled with the LED count reported by the
  hardware (padded with black or truncated as needed).

### Added

- Topology validation on zone load: a warning is logged once per device when
  the LED count declared in `device_topologies.json` does not match the
  hardware, pointing to the stale config entry.

---

## [1.0.0] — 2026-06-16

### Added

- Real-time screen ambient lighting via OpenRGB (right / top / left / bottom edges)
- Automatic screen capture backend selection: WGC → DXGI → mss fallback
- Black bar detection for letterboxed and pillarboxed content
- Sampling strategies: `adaptive_smooth`, `smooth`, `percentile`, `dominant`, `mean`
- Adaptive sampling depth — automatically narrows depth on scene content
- Exponential moving average smoothing with scene-cut bypass
- Saturation boost for vivid LED output
- Visual topology editor — drag-and-drop canvas to map LED zones to screen regions
- WebGL live effect preview panel
- Web-based UI served locally (no internet required)
- System tray support — minimize to tray, reopen from tray icon
- OpenRGB auto-start — launches OpenRGB automatically if not running
- Device and zone enable/disable per-device configuration
- Settings page: OpenRGB host/port, web UI port
- Splash screen with step-by-step initialization progress
- Graceful shutdown with configurable delay when browser window closes
