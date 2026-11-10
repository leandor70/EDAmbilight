# Changelog

All notable changes to EDAmbilight will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Changed

- **Where a zone is, not what it is called.** The Topology Editor has a SCREEN rectangle (your monitor):
  **Fit** places it on the strips, corners resize it, the border moves it. LEDs on a side of the rectangle
  follow that side of the screen, LEDs inside read the point of the screen under them, LEDs outside are
  left alone; it works LED by LED, so a zone longer than the screen lights only the part along it. Zone names
  no longer matter. Without a rectangle, setups whose zones are named MonitorTop / Right / Bottom / Left
  keep the old mapping (Fit reproduces it), others use the bounding box of the whole scene.
  The rectangle always has the proportions of the real screen (read from the capture, else from
  Windows): Fit and the automatic rectangle grow to them, corners resize keeping them. A rectangle
  saved with other proportions is adapted when the editor opens and left unsaved, with a warning,
  because growing it can move strips from a side to the inside.
- **LEDs the ambilight does not use are left free.** LEDs outside the screen and zones switched off in
  Devices used to be sent black at every frame, so nothing else could light them. Now only the LEDs in
  use are written (one packet per device when all are used, per zone or per LED otherwise), and a LED
  that stops being used gets black once. The others keep what OpenRGB or another program gives them.
  The OpenRGB client gained zone and single-LED updates. Calibration still blacks out whole devices.
- **Flip Direction now works.** It used to change only the arrow on the canvas: the LED order always
  followed the rotation. Now Flip (F) means the zone is wired the other way round, LED 0 at the far
  end, and the ambilight, the calibration and the screen rectangle all follow it. A zone that was
  saved as "reverse" in an older version will now really run the other way: flip it back if needed.
- Topology Editor: the grey "VBBox" is gone (a leftover from ED:Event2Led, used by nothing here) and
  the Effect Center panel is now **Calibration Center**: it only sets where the calibration rings start.
  Note: once the rectangle is placed, zones read their point relative to the screen, not to the whole
  scene as before, so devices placed away from the monitor may read a different part of the screen.

- **Devices is now the one place for hardware.** Each device is a row with its on/off switch and an
  expandable list of its zones (the zone switches used to be on the Control page, where they were easy
  to miss). A small live Sampling preview at the top shows what
  turning a device or zone on or off does. The Control page keeps only compact on/off chips, a summary
  and a warning when nothing would light up (no device mapped, none on, or no active zone).
- Keyboards are no longer hidden: they are listed like any device, off until you switch them on.
  After updating, a keyboard that was hidden before appears once in the "hardware changed" notice.
- **Key grids.** A zone that OpenRGB describes as a matrix (a keyboard: 24 x 6 cells on an ASUS TUF
  Gaming K7) is no longer one row with one color. A grid of that size is laid over the whole screen
  and every key shows the mean color of the cell it sits under, so the keyboard becomes a tiny copy
  of the picture. The sampling preview draws the keys as tiles; the Devices page names the zone
  "24x6 keys". The OpenRGB client now keeps the key map it used to discard. A key grid has
  nothing to place, so it is no longer shown in the Topology Editor (it stays in the config).
- The chosen theme is now also saved in `config/settings.json` (`ui_theme`), not only in the
  browser. It is no longer lost when the web port changes, when another browser is used or when
  the browser clears site data. The saved value wins at load; an existing browser choice is
  copied into the file the first time.

---

## [1.5.0] — 2026-11-09

### Added

- Light "glass" theme as an alternative to the dark one, on every page, the splash screen and the
  topology canvas. The switch is at the bottom of the sidebar (in the panel header on Preview) and
  the choice is remembered. Accent #0E7490. The sampling screen on the dashboard stays dark: it is a
  drawing of a screen.
- Dropdown lists are now a translucent panel that blurs what is behind it, in both themes (Control,
  Live Preview, Topology Editor). Keyboard: Space / Alt+Down opens, arrows, Home/End, Enter, Esc.
- Tests for the wait on OpenRGB's hardware detection and for the reconnect path that uses it.

### Changed

- Body font is now Inter (was Rajdhani, a narrow font that was hard to read at 11–13 px), and the
  smallest texts are one step larger, on every page including the splash screen and the Topology
  Editor. Orbitron is kept for headings and numbers in the dark theme. Inter is bundled locally
  (SIL OFL 1.1).
- The Topology Editor follows the theme, canvas included: light ground, grid and labels in light
  mode, the accent switches to ocean.
- README, README-dev, Help, the design-system notes and THIRD-PARTY describe the themes, the
  fonts and the dropdowns; all screenshots are new, in dark and light.

### Fixed

- A false "Hardware changed since the last start" notice when EDAmbilight started OpenRGB itself.
  OpenRGB opens its SDK server before it has finished detecting hardware (about 9 s here), so
  EDAmbilight connected, saw 1 of 6 devices, listed the other 5 as "no longer detected" and sent
  them no colors until the next restart. It now waits until the device count has stopped changing
  (at least 5 s, at most 45 s), also after **Retry**. The first start can take about 15 s longer
  when EDAmbilight launches OpenRGB; if OpenRGB is already running nothing changes.
- Topology Editor: the filled part of the Grid Size and calibration speed sliders did not follow
  the thumb.

---

## [1.4.1] — 2026-11-07

### Added

- A notice when the OpenRGB in use is older than 1.0 (read from its log), shown once per
  version, recommending the update and the PawnIO driver.

### Changed

- OpenRGB is started with `--gui --server --startminimized`. With only `--server`,
  OpenRGB 1.x runs without a window or tray icon, so there was nothing to open afterwards.
- The "OpenRGB not installed", "no devices" and Help texts, and the README requirements,
  mention the PawnIO driver that OpenRGB 1.x needs for memory and motherboards.

---

## [1.4.0] — 2026-11-07

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
  everything else works and the panel says what is missing. If the chosen
  audio source is gone (headset unplugged, settings copied to another PC) it
  listens to the default output and says so in the panel.
- A notice at the top of Control, Devices, Settings and Help when the hardware
  changed since the last start: a device was added (it stays off until you
  enable it), removed (its settings are kept) or changed (zones or LED count,
  layout re-synced). It stays until dismissed.

### Changed

- **License.** The source code is now public, under the PolyForm Noncommercial
  License 1.0.0 (see `LICENSE` and `NOTICE.md`). Releases up to 1.3.1 keep the
  freeware license they were distributed with.
- The package is lighter: unused background images are gone.
- OpenRGB is now reached with a small built-in client (`src/core/openrgb_sdk.py`)
  instead of the `openrgb-python` package, which is no longer needed. Behavior is
  unchanged: same devices, zones and colors.

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
