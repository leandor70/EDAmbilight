'use strict';
/* Live sampling preview: a small drawing of the screen with the bands and dots the
   ambilight reads and, in Live mode, the colours it is sending. Shared by Control and
   Devices; it needs the markup #sampling-stage / -screen / -canvas / -tip / -caption
   (and optionally #seg-live / #seg-zones). Start it with _initSampling().
   data-max-h on #sampling-stage caps the drawing height (default 230 px). */

// Devices known to the page (names for the tooltip): Control calls them _devs, Devices _devices
function _sampDevices() {
    if (typeof _devs !== 'undefined' && _devs && _devs.length) return _devs;
    if (typeof _devices !== 'undefined' && _devices) return _devices;
    return [];
}

// ── Sampling preview (mini screen in the Status card) ────────────────────────

let _sampMode = _lsGet('edambi.samplingMode') === 'zones' ? 'zones' : 'live';
let _sampBusy = false;
let _sampLast = null;

function setSamplingMode(mode) {
    _sampMode = mode === 'zones' ? 'zones' : 'live';
    _lsSet('edambi.samplingMode', _sampMode);
    _syncSamplingToggle();
    _drawSampling(_sampLast);
}

function _syncSamplingToggle() {
    const live = document.getElementById('seg-live');
    const zones = document.getElementById('seg-zones');
    if (live)  live.setAttribute('aria-pressed',  String(_sampMode === 'live'));
    if (zones) zones.setAttribute('aria-pressed', String(_sampMode === 'zones'));
}

async function _samplingTick() {
    if (!document.hidden && !_sampBusy) {
        _sampBusy = true;
        try {
            const r = await api('get_sampling_preview');
            if (apiOk(r)) { _sampLast = r; _drawSampling(r); }
        } finally { _sampBusy = false; }
    }
    // Colors move fast: poll quicker in Live; geometry only changes with settings
    setTimeout(_samplingTick, _sampMode === 'live' ? 250 : 1000);
}

function _initSampling() {
    _syncSamplingToggle();
    const stage = document.getElementById('sampling-stage');
    if (stage && 'ResizeObserver' in window) {
        new ResizeObserver(() => _drawSampling(_sampLast)).observe(stage);
    }
    const cv = document.getElementById('sampling-canvas');
    if (cv) {
        cv.addEventListener('mousemove', e => {
            const b = cv.getBoundingClientRect();
            _sampMouse = { x: e.clientX - b.left, y: e.clientY - b.top };
            const hit = _hitAt(_sampMouse.x, _sampMouse.y);
            const key = hit ? hit.key : null;
            if (key !== _sampHoverKey) { _sampHoverKey = key; _drawSampling(_sampLast); }
            else _showSamplingTip();
        });
        cv.addEventListener('mouseleave', () => {
            _sampMouse = null; _sampHoverKey = null;
            _drawSampling(_sampLast);
        });
    }
    _drawSampling(null);
    _samplingTick();
}

// Hover support: regions recorded by the last draw, in canvas CSS px
let _sampHits = [];
let _sampHoverKey = null;
let _sampMouse = null;

function _hitAt(x, y) {
    // Dots first: they are small and may sit on top of nothing else, bands are larger
    for (const h of _sampHits) {
        if (h.type === 'dot' && Math.hypot(x - h.cx, y - h.cy) <= h.r) return h;
    }
    // Slack of 3px so thin bands are easy to hit
    for (const h of _sampHits) {
        if (h.type === 'band' && x >= h.x - 3 && x <= h.x + h.w + 3 && y >= h.y - 3 && y <= h.y + h.h + 3) return h;
    }
    for (const h of _sampHits) {
        if (h.type === 'grid' && x >= h.x && x <= h.x + h.w && y >= h.y && y <= h.y + h.h) return h;
    }
    return null;
}

const _EDGE_NAME = { top: 'Top edge', bottom: 'Bottom edge', left: 'Left edge', right: 'Right edge' };

function _showSamplingTip() {
    const tip = document.getElementById('sampling-tip');
    const box = document.getElementById('sampling-screen');
    if (!tip || !box) return;
    const hit = _sampHoverKey && _sampMouse ? _sampHits.find(h => h.key === _sampHoverKey) : null;
    if (!hit) { tip.hidden = true; return; }

    const z = hit.z;
    const dev = _sampDevices().find(d => d.device_key === z.dev);
    const title = document.createElement('b');
    title.textContent = dev ? dev.name : z.dev;
    const zone = document.createElement('div');
    zone.textContent = `Zone: ${z.zone}`;
    const kind = document.createElement('span');
    if (hit.type === 'grid') {
        kind.textContent = `Key grid ${z.cols}×${z.rows}: each key reads the part of the screen it sits under`;
    } else if (hit.type === 'dot') {
        kind.textContent = `Reads one point of the screen (${Math.round(z.x * 100)}% across, ${Math.round(z.y * 100)}% down)`;
    } else {
        const n = z.colors ? z.colors.length / 6 : 0;
        kind.textContent = `${_EDGE_NAME[z.edge] || z.edge} band · ${n} LED${n === 1 ? '' : 's'}`;
    }
    tip.replaceChildren(title, zone, kind);
    if (hit.type === 'dot' && z.colors) {
        const sw = document.createElement('div');
        sw.style.cssText = `margin-top:5px; height:6px; border-radius:3px; background:#${z.colors.slice(0, 6)};`;
        tip.appendChild(sw);
    }

    tip.hidden = false;
    const bw = box.clientWidth, bh = box.clientHeight;
    let left = _sampMouse.x + 14, top = _sampMouse.y + 14;
    if (left + tip.offsetWidth > bw - 4) left = _sampMouse.x - tip.offsetWidth - 14;
    if (top + tip.offsetHeight > bh - 4) top = _sampMouse.y - tip.offsetHeight - 14;
    tip.style.left = Math.max(4, left) + 'px';
    tip.style.top  = Math.max(4, top) + 'px';
}

function _fmtPct(v) {
    return (Math.round(v * 10) / 10).toString() + '%';
}

function _drawSampling(r) {
    const box = document.getElementById('sampling-screen');
    const cv  = document.getElementById('sampling-canvas');
    const cap = document.getElementById('sampling-caption');
    if (!box || !cv) return;

    const snap  = r && r.snapshot;
    const fresh = !!(r && r.running && !r.standby && snap && snap.age < 2);
    const live  = _sampMode === 'live' && fresh;

    // Same proportions as the captured screen (browser screen as fallback)
    const [fw, fh] = snap ? snap.frame : [window.screen.width || 16, window.screen.height || 9];
    // Fill the panel width but cap the height, so very wide screens do not get huge
    const stage = document.getElementById('sampling-stage');
    const MAX_H = +(stage && stage.dataset.maxH) || 230;
    const cssW = Math.round(Math.max(120, Math.min((stage && stage.clientWidth) || 400, MAX_H * fw / fh)));
    const cssH = Math.max(1, Math.round(cssW * fh / fw));
    box.style.width  = cssW + 'px';
    box.style.height = cssH + 'px';
    _sampHits = [];
    const dpr = window.devicePixelRatio || 1;
    if (cv.width !== Math.round(cssW * dpr) || cv.height !== Math.round(cssH * dpr)) {
        cv.width  = Math.round(cssW * dpr);
        cv.height = Math.round(cssH * dpr);
    }
    const ctx = cv.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);

    const s = cssW / fw;
    const rect = snap ? snap.rect : [0, 0, fw, fh];
    const cw = rect[2] - rect[0], ch = rect[3] - rect[1];
    const cropped = cw < fw - 2 || ch < fh - 2;
    const X0 = rect[0] * s, Y0 = rect[1] * s, W = cw * s, H = ch * s;

    // Black bars (outside the content area) vs. picture area
    ctx.fillStyle = '#03080d';
    ctx.fillRect(0, 0, cssW, cssH);
    ctx.fillStyle = '#0a1a26';
    ctx.fillRect(X0, Y0, W, H);
    if (cropped) {
        ctx.save();
        ctx.setLineDash([3, 3]);
        ctx.strokeStyle = 'rgba(20,245,255,.40)';
        ctx.lineWidth = 1;
        ctx.strokeRect(X0 + .5, Y0 + .5, W - 1, H - 1);
        ctx.restore();
    }

    // Band thickness in frame px: real value from the service, else from settings
    const cfgDepth = r ? (r.adaptive ? (r.adaptive_min + r.adaptive_max) / 2 : r.depth) : 10;
    const depthPx = e => (snap && snap.depth && snap.depth[e] != null)
        ? snap.depth[e]
        : Math.round(Math.min(cw, ch) * cfgDepth / 100);

    let zones = snap ? snap.zones : [];
    const noZones = !zones.length;
    if (noZones) {   // nothing is being sampled yet: show the configured bands
        zones = ['top', 'bottom', 'left', 'right'].map(e => ({ edge: e, start: 0, end: 1, colors: '' }));
    }
    const ghost = !live || noZones;

    const FILL_A = 'rgba(20,245,255,.16)', FILL_B = 'rgba(20,245,255,.26)', STROKE = 'rgba(20,245,255,.60)';
    const hexAt = (str, i) => '#' + str.substr(i * 6, 6);

    // 0) Key grids (keyboards): every key is a tile on the screen cell it reads
    for (const z of zones) {
        if (z.edge !== 'matrix') continue;
        const tw = W / z.cols, th = H / z.rows;
        (z.cells || []).forEach(([r, c], i) => {
            const x = X0 + c * tw, y = Y0 + r * th;
            if (live && z.colors) {
                ctx.fillStyle = hexAt(z.colors, i);
                ctx.globalAlpha = .9;
            } else {
                ctx.fillStyle = (r + c) % 2 ? FILL_B : FILL_A;
            }
            ctx.fillRect(x + .5, y + .5, Math.max(1, tw - 1), Math.max(1, th - 1));
            ctx.globalAlpha = 1;
        });
        if (z.dev) _sampHits.push({ type: 'grid', key: z.dev + '|' + z.zone, z, x: X0, y: Y0, w: W, h: H });
    }

    // 1) Area zones (circles) go under the bands
    // Shown as small dots (many overlap); Zones view adds a faint halo with the real sampled radius
    const radius = Math.max(3, 0.18 * Math.min(cw, ch) * s);
    for (const z of zones) {
        if (z.edge !== 'area') continue;
        const cx = X0 + z.x * W, cy = Y0 + z.y * H;
        if (!live) {
            ctx.beginPath();
            ctx.arc(cx, cy, radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(20,245,255,.05)';
            ctx.fill();
        }
        // Solid dots, no outline (an outline on a dark dot reads as a ring). A pale disc
        // underneath keeps the position visible when the LED is dark.
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,.16)';
        ctx.fill();
        ctx.fillStyle = (live && z.colors) ? hexAt(z.colors, 0) : STROKE;
        ctx.fill();
        if (z.dev) _sampHits.push({ type: 'dot', key: z.dev + '|' + z.zone, z, cx, cy, r: 8 });
    }

    // 2) Edge bands: left/right first, then top/bottom (corner overlap like the backend)
    const order = { left: 0, right: 0, top: 1, bottom: 1 };
    const edgeZones = zones.filter(z => z.edge !== 'area' && z.edge !== 'matrix').sort((a, b) => order[a.edge] - order[b.edge]);
    for (const z of edgeZones) {
        const horiz = z.edge === 'top' || z.edge === 'bottom';
        const d = Math.max(2, depthPx(z.edge) * s);          // never thinner than 2px on screen
        const n = z.colors ? z.colors.length / 6 : 0;
        const alongLen = (horiz ? W : H) * (z.end - z.start);
        const alongOrg = (horiz ? X0 : Y0) + (horiz ? W : H) * z.start;
        const crossOrg = z.edge === 'top' ? Y0 : z.edge === 'bottom' ? Y0 + H - d
                       : z.edge === 'left' ? X0 : X0 + W - d;
        const segs = Math.max(1, n);
        const segLen = alongLen / segs;

        for (let i = 0; i < segs; i++) {
            const a = alongOrg + segLen * i;
            if (live && n) {
                ctx.fillStyle = hexAt(z.colors, i);
                ctx.globalAlpha = .95;
            } else {
                ctx.fillStyle = i % 2 ? FILL_B : FILL_A;
                ctx.globalAlpha = 1;
            }
            // +0.5 overlap hides sub-pixel seams between neighbouring segments
            if (horiz) ctx.fillRect(a, crossOrg, segLen + .5, d);
            else       ctx.fillRect(crossOrg, a, d, segLen + .5);
        }
        ctx.globalAlpha = 1;

        if (ghost || !live) {
            ctx.strokeStyle = STROKE; ctx.lineWidth = 1;
            if (horiz) ctx.strokeRect(alongOrg + .5, crossOrg + .5, alongLen - 1, d - 1);
            else       ctx.strokeRect(crossOrg + .5, alongOrg + .5, d - 1, alongLen - 1);
        }
        if (z.dev) {
            _sampHits.push(horiz
                ? { type: 'band', key: z.dev + '|' + z.zone, z, x: alongOrg, y: crossOrg, w: alongLen, h: d }
                : { type: 'band', key: z.dev + '|' + z.zone, z, x: crossOrg, y: alongOrg, w: d, h: alongLen });
        }
    }

    // Highlight whatever is under the mouse
    const hov = _sampHoverKey && _sampHits.find(h => h.key === _sampHoverKey);
    if (hov) {
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5;
        if (hov.type === 'dot') { ctx.beginPath(); ctx.arc(hov.cx, hov.cy, 7, 0, Math.PI * 2); ctx.stroke(); }
        else ctx.strokeRect(hov.x + .5, hov.y + .5, hov.w - 1, hov.h - 1);
    }
    _showSamplingTip();

    // Caption: resolution, depth actually in use, state
    if (cap) {
        let depthTxt;
        const depths = snap && snap.depth ? Object.values(snap.depth) : [];
        if (r && r.adaptive) {
            const eff = depths.length
                ? depths.reduce((a, b) => a + b, 0) / depths.length / Math.min(cw, ch) * 100 : null;
            depthTxt = `Depth ${r.adaptive_min}–${r.adaptive_max}% adaptive` + (eff != null && fresh ? ` · now ${_fmtPct(eff)}` : '');
        } else {
            depthTxt = `Depth ${_fmtPct(r ? r.depth : 10)}`;
        }
        let note = '';
        if (!r || !r.running)       note = 'Service off — showing configured bands';
        else if (r.standby)         note = 'Screen unavailable (standby)';
        else if (noZones)           note = 'No device is receiving colors';
        else if (cropped)           note = `Black bars cropped (${cw}×${ch})`;
        cap.style.whiteSpace = 'pre-line';
        cap.textContent = `${fw}×${fh} · ${depthTxt}` + (note ? '\n' + note : '');
    }
}
