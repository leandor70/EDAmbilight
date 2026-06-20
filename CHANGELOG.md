# Changelog

All notable changes to EDAmbilight will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
