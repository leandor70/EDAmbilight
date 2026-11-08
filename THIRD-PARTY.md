# Third-party components

EDAmbilight itself is licensed under the [PolyForm Noncommercial License
1.0.0](LICENSE). The components below are not covered by that license: each keeps
its own, and each license allows being bundled with EDAmbilight. The full texts
are in the [`licenses/`](licenses) folder.

## Bundled with the web interface (`web/`)

| Component | Use | License | Text |
|---|---|---|---|
| Orbitron | Headings and numbers (dark theme) | SIL Open Font License 1.1 | [OFL-orbitron.txt](licenses/OFL-orbitron.txt) |
| Rajdhani | Sidebar labels and a few small canvas labels | SIL Open Font License 1.1 | [OFL-rajdhani.txt](licenses/OFL-rajdhani.txt) |
| Inter | Body font (both themes) and headings of the light theme | SIL Open Font License 1.1 | [OFL-inter.txt](licenses/OFL-inter.txt) |
| Material Symbols Outlined | Icons | Apache License 2.0 | [Apache-2.0.txt](licenses/Apache-2.0.txt) |
| Tailwind CSS 3.4 (`tailwind.min.css`, built subset) | Utility styles | MIT | [MIT-Tailwind.txt](licenses/MIT-Tailwind.txt) |

The fonts are redistributed unmodified, as `.woff2` files. The OFL does not allow
selling the fonts on their own; they are included here only as part of the
application.

## Python packages (installed with `pip`, bundled in the Windows build)

| Package | License |
|---|---|
| Python | PSF License |
| Eel (with Bottle, bottle-websocket, gevent, gevent-websocket) | MIT |
| NumPy | BSD-3-Clause |
| mss | MIT |
| dxcam (optional, DXGI capture) | MIT |
| PyAudioWPatch (optional, beat accent) | Apache License 2.0 |
| Pillow and pystray (optional, tray icon) | HPND / LGPL-3.0 |
| PyInstaller (build tool) | GPL-2.0-or-later with an exception for the programs it builds |

Packages are installed from their own distribution and are not modified.

## OpenRGB

EDAmbilight talks to [OpenRGB](https://openrgb.org) over its network SDK. It does
not contain OpenRGB code and no OpenRGB library is bundled: the client in
`src/core/openrgb_sdk.py` is original work written from the public protocol
description. OpenRGB is a separate program under its own license (GPL-2.0).

"Elite Dangerous" is a trademark of Frontier Developments plc. EDAmbilight is not
affiliated with or endorsed by Frontier Developments, OpenRGB or any hardware
maker.
