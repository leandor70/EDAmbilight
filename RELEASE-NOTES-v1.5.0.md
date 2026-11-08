# EDAmbilight v1.5.0

A light theme, easier-to-read text, glass dropdowns, and a fix for a false "Hardware changed"
notice at startup.

## What's new

### Light theme

Every page now also comes in a light "glass" theme: the dashboard, devices, settings, live
preview, help, the topology editor (canvas included) and the splash screen. Use the sun / moon
button at the bottom of the sidebar (in the panel header on Live Preview). Your choice is
remembered and applied before the first paint, so the splash screen and every page open in the
theme you picked, without a flash of the other one.

![Dashboard, light theme](https://raw.githubusercontent.com/leandor70/EDAmbilight-src/main/docs/ss-dashboard-light.png)

The sampling preview on the dashboard stays dark in both themes: it is a drawing of your screen.

### Text you can read

The dark theme was hard to read: most text was Rajdhani at 11–13 px, a narrow font with a small
x-height. The body font is now **Inter** in both themes, and the smallest texts are one step larger. Orbitron stays for headings and numbers in the dark theme. This applies everywhere,
including the splash screen and the Topology Editor.

### Dropdowns that blur what is behind them

Dropdown lists (Control, Live Preview, Topology Editor) are now translucent frosted-glass panels
instead of the browser's list, in both themes. They work with the keyboard: Space or Alt+Down
opens, arrows / Home / End move, Enter selects, Esc closes.

## Fixes

- **False "Hardware changed since the last start"** when EDAmbilight started OpenRGB itself.
  OpenRGB opens its SDK server before it has finished detecting hardware (about 9 seconds on a
  machine with 6 devices). EDAmbilight connected too early, saw only 1 of 6 devices, listed the
  other 5 as "no longer detected" and sent them no colors until the next restart. It now waits
  until the device list stops changing, also after **Retry**. Nothing was lost: your settings and
  topologies were kept.
- **Topology Editor sliders:** the filled part of the Grid Size and calibration speed sliders did
  not follow the thumb.

## Good to know

- When EDAmbilight launches OpenRGB itself, the first start takes about **15 seconds longer**
  (the wait for hardware detection). If OpenRGB is already running, nothing changes.
- New files in the package: the Inter font (`web/fonts/Inter-variable.woff2`) and its license
  (`licenses/OFL-inter.txt`, SIL Open Font License 1.1).

## OpenRGB compatibility

| OpenRGB | Status |
|---|---|
| **1.1** | Tested on real hardware (this release) |
| **1.0rc2** | Tested on real hardware |
| 0.9 and older | The client negotiates the SDK protocol (0 to 4) and is covered by tests against a simulated server; **not tested on real hardware** |
| Newer than 1.1 | Expected to work: the client asks for protocol 4 and the server answers with the highest version both understand. Not tested yet |

OpenRGB 1.0 or later is recommended. On Windows it needs the **PawnIO** driver
([pawnio.eu](https://pawnio.eu)) to detect memory modules and motherboards.

## Requirements

Windows 10 / 11 (64-bit), OpenRGB with the SDK Server enabled. See the
[README](https://github.com/leandor70/EDAmbilight-src/blob/main/README.md#-requirements).

## Download

Attach `EDAmbilight-v1.5.0.zip` and its `.sha256` file. To verify the download:

```
certutil -hashfile EDAmbilight-v1.5.0.zip SHA256
```

Full list of changes: [CHANGELOG.md](https://github.com/leandor70/EDAmbilight-src/blob/main/CHANGELOG.md).
