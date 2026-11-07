# Changelog

All notable changes to EDAmbilight will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- Control: **Beat accent** — a short accent on the ambilight at every beat of
  the music playing on the PC (system audio loopback, no microphone). Flash
  mode multiplicative / additive / mixed, flash color picker, intensity,
  duration, optional hue shift (pulse or one step per beat), and a safety
  group (strong beats only, max flashes per second, boost cap, attack). Soft / Punchy / Club
  presets, a **Test accent** button that needs no audio, an audio device
  picker, sensitivity and a level / bass / mid / high meter. While an accent
  is playing the LEDs refresh at 60 steps/s, whatever the capture rate.
  Audio listening needs the optional `PyAudioWPatch` package; without it
  everything else works and the panel says what is missing.

---

## [1.3.1] — 2026-11-07

### Fixed

- The **Preview** page was missing from the 1.2.1 and 1.3.0 packages, so the
  Preview entry in the sidebar and the "Live preview" button led to an error.
  It is included again. The release script now refuses to build a package that
  lacks any page linked from the sidebar.

---

## [1.3.0] — 2026-11-06

### Added

- Control: **Sampling** panel — a scaled copy of the captured screen showing
  where colors are read from (edge bands at their real depth, black bars,
  device points), with a Live view (current LED colors) and a Zones view.
  Hover a band or a dot to see which device and zone it feeds.

### Removed

- Unused `hsv` sampling strategy (never offered in the interface, and it needed
  OpenCV, which is not a dependency). A config that still names it falls back
  to RGB mean.

### Fixed

- **Vertical orientation of side strips and area zones.** The Topology Editor
  draws with y pointing up, but the sampler read y as pointing down: LEDs on
  the left and right sides received the colors of the opposite half of the
  screen, and device points (e.g. motherboard zones) read a mirrored position.
  LED order along each edge is now derived from the LED positions in the
  topology instead of a fixed flag per zone name. Top and bottom strips are
  unchanged. **If you had compensated by drawing a side strip upside down in
  the editor, redraw it as it is physically mounted.**
- Topology Editor: zones OpenRGB reports as `???` are no longer listed (they
  never receive colors); they stay in the configuration so LED offsets do not
  shift when you save.

---

## [1.2.1] — 2026-11-05

### Added

- Control: **Test effect** button in Screen standby — plays the selected
  standby effect on the LEDs right away (stops by itself after 60 s).

### Changed

- License: now a freeware license (personal, non-commercial use) instead of MIT.

---

## [1.2.0] — 2026-11-03

### Added

- Control: **Screen standby** — choose what the LEDs do while the screen gives
  no image (display asleep, lock screen): hold the last colors (default), slow
  fade to black, fade to a dim glow, pulse, rotating colors, aurora, ember
  glow or lights off. A "Standby brightness" slider sets the level of the
  generative effects. The status badge shows STANDBY and normal ambilight
  resumes on its own.

### Fixed

- DXGI capture: after a failed recovery (e.g. display wake-up) the app retries
  quietly every 5 s instead of repeating the full recovery cycle and log noise
  on every frame.
- Zone toggles are keyed by zone index and zones with unreadable names are
  skipped.

---

## [1.1.0] — 2026-10-26

### Added

- Control: the status now tells the truth. Besides ACTIVE / INACTIVE it shows
  **NO ZONES** (running, but no zone receives colors) and **NO DEVICES**
  (OpenRGB reports nothing), with a hint and a link to fix it. A summary
  ("2 devices · 5 zones · WGC") replaces the empty space in the Status panel.
- Control: a "Getting started" checklist (OpenRGB connected / zones mapped /
  Enable on) and an amber dot on the sidebar item of the next step.
- Control: presets (Balanced, Cinema, Gaming, Calm), a Reset button, a
  collapsible Advanced section and a Live preview shortcut.
- Control: the FPS badge turns amber when the real rate stays well below the
  target.
- Settings: OpenRGB executable path and auto-start, Restart / Quit buttons,
  Open log folder, and the real app version.
- Devices: "Map zones" shortcut for devices without topology, Flash All with
  progress and Stop, Rescan button.
- Topology Editor: an Advanced section (grid, effect center, calibration,
  measurements) closed by default, an "Unsaved changes" indicator with a leave
  warning, and the names of the overlapping zones.
- Connection-lost banner when the app stops answering.

### Changed

- Devices and Control now agree on whether a never-configured device is on
  (it is off, as the engine already assumed).
- Slider changes are sent to the app with a short debounce.
- Control scrolls on small windows instead of hiding the Devices list.
- Larger, higher-contrast secondary text; animations are off with the
  system "reduce motion" setting.
- UI texts are English only (the remaining Italian strings are gone) and the
  confirmation dialogs match the rest of the interface.

### Fixed

- Toggling a device on the Devices page did not roll back when the change failed.
- Save errors in Settings were reported as success.

---

## [1.0.9] — 2026-10-25

### Fixed

- The FPS badge on the Control page is now white: it was almost invisible.

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
