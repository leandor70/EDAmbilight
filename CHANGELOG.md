# Changelog

All notable changes to EDAmbilight will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
