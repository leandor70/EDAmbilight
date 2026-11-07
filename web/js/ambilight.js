'use strict';

// ── State ─────────────────────────────────────────────────────────────────────

let _cfg  = {};
let _devs = [];

// ── Init ──────────────────────────────────────────────────────────────────────

window.addEventListener('load', async () => {
    const [cfg, devs] = await Promise.all([
        api('get_ambilight_config'),
        api('get_ambilight_devices'),
    ]);
    _cfg  = cfg  || {};
    _devs = devs || [];

    applyConfig(_cfg);
    _labelControls();
    toggleAdvanced(_lsGet('edambi.advanced') !== '0');
    renderDevices(_devs, _cfg);

    // Carica zone per device già abilitati (dopo renderDevices, _devs è già popolato)
    for (const dev of _devs) {
        const devCfg = (_cfg.devices || {})[dev.device_key] || {};
        if (devCfg.enabled && dev.has_topology) {
            await loadDeviceZones(dev.device_key);
        }
    }

    pollStatus();
    setInterval(pollStatus, 800);
    _initSampling();
    _initAccent();
});

// Give every range input an accessible name taken from its visible label
function _labelControls() {
    document.querySelectorAll('input[type=range]').forEach(el => {
        if (el.getAttribute('aria-label')) return;
        const row = el.closest('.slider-row');
        const txt = row && row.querySelector('.slider-label-text');
        el.setAttribute('aria-label', txt ? txt.textContent.trim() : 'FPS Target');
    });
    const dot = document.getElementById('status-dot');
    if (dot) dot.setAttribute('aria-hidden', 'true');   // state is also written as text
}

// ── Config apply ──────────────────────────────────────────────────────────────

function applyConfig(cfg) {
    setToggle('ctrl-enabled', cfg.enabled);
    setSlider('ctrl-fps',       'val-fps',       cfg.fps              ?? 15);
    setSlider('ctrl-depth',     'val-depth',     cfg.depth            ?? 10);
    setSlider('ctrl-sat',       'val-sat',       cfg.saturation_boost ?? 1.4);
    setSlider('ctrl-min-lum',   'val-min-lum',   cfg.min_luminance    ?? 0);
    setSlider('ctrl-ema',      'val-ema',       cfg.ema_alpha        ?? 0.35);
    setSlider('ctrl-scene-cut', 'val-scene-cut', cfg.scene_cut        ?? 60);
    setSlider('ctrl-adap-min',  'val-adap-min',  cfg.adaptive_min     ?? 3);
    setSlider('ctrl-adap-max',  'val-adap-max',  cfg.adaptive_max     ?? 20);
    setToggle('ctrl-bb', cfg.black_bar_detect ?? true);
    setSlider('ctrl-standby-bri', 'val-standby-bri', cfg.standby_brightness ?? 60);
    const sbSel = document.getElementById('ctrl-standby');
    if (sbSel) sbSel.value = cfg.standby_mode ?? 'hold';

    const capSel = document.getElementById('ctrl-capturer');
    if (capSel) capSel.value = cfg.capturer ?? 'auto';

    const stratSel = document.getElementById('ctrl-strategy');
    if (stratSel) {
        stratSel.value = cfg.strategy ?? 'adaptive_smooth';
        updateStrategyVisibility(stratSel.value);
    }
    applyAccentConfig(cfg);
    refreshPresetChips();
}

function setToggle(id, value) {
    const el = document.getElementById(id);
    if (el) el.checked = !!value;
}

function setSlider(inputId, spanId, value) {
    const el = document.getElementById(inputId);
    if (el) el.value = value;
    const sp = document.getElementById(spanId);
    if (sp) sp.textContent = value;
}

// ── Live controls ─────────────────────────────────────────────────────────────

// Label and local state update instantly; the backend call is debounced per key
// (trailing, so the final slider value is always the one sent).
const _pendingCfg    = {};
const _cfgTimers     = {};
const CFG_DEBOUNCE   = 80;

function _reportApiFailure(what, res) {
    showNotification(`Could not ${what}: ${(res && res.error) || 'no response from the app'}`, 'error');
}

function liveUpdate(key, value, spanId) {
    if (spanId) document.getElementById(spanId).textContent = value;
    _cfg[key] = value;
    _pendingCfg[key] = value;
    refreshPresetChips();
    refreshAccentChips();
    clearTimeout(_cfgTimers[key]);
    _cfgTimers[key] = setTimeout(async () => {
        const v = _pendingCfg[key];
        delete _pendingCfg[key];
        const res = await api('set_ambilight_config', { [key]: v });
        if (!apiOk(res)) _reportApiFailure('apply the change', res);
    }, CFG_DEBOUNCE);
}

// ── Screen standby test ───────────────────────────────────────────────────────

function _renderStandbyTest(on) {
    const b = document.getElementById('btn-standby-test');
    if (!b) return;
    b.textContent = on ? 'Stop test' : 'Test effect';
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
}

async function toggleStandbyPreview() {
    const b = document.getElementById('btn-standby-test');
    const on = b && b.getAttribute('aria-pressed') !== 'true';
    // Apply the dropdown choice first: the change is debounced
    if (on && _pendingCfg.standby_mode !== undefined) {
        await api('set_ambilight_config', { standby_mode: _pendingCfg.standby_mode });
    }
    const res = await api('set_standby_preview', on);
    if (!apiOk(res)) { _reportApiFailure('start the test', res); return; }
    _renderStandbyTest(on);
}

async function toggleEnabled(checked) {
    _cfg.enabled = checked;
    updateStatusBadge(checked ? null : false);
    const res = await api('set_ambilight_config', { enabled: checked });
    if (!apiOk(res)) {
        _cfg.enabled = !checked;
        setToggle('ctrl-enabled', !checked);
        _reportApiFailure('change the Enable state', res);
    }
}

function onStrategyChange(value) {
    updateStrategyVisibility(value);
    liveUpdate('strategy', value, null);
}

function updateStrategyVisibility(strategy) {
    const isAdaptive = strategy.includes('adaptive');
    const isSmooth   = strategy.includes('smooth');
    _setGroupActive('group-depth', !isAdaptive);
    _setGroupActive('group-adaptive', isAdaptive);
    _setGroupActive('group-smooth', isSmooth);
}

function _setGroupActive(id, active) {
    const g = document.getElementById(id);
    g.classList.toggle('is-off', !active);
    g.querySelectorAll('input').forEach(i => { i.disabled = !active; });
}

// ── Devices ───────────────────────────────────────────────────────────────────

function _devSafeId(deviceKey) {
    return deviceKey.replace(/[^a-z0-9]/gi, '_');
}

// Power button SVG (classic power symbol)
const _powerSVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2.2" stroke-linecap="round" width="15" height="15"
    style="position:relative;z-index:1;pointer-events:none;">
  <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
  <line x1="12" y1="2" x2="12" y2="12"/>
</svg>`;

function renderDevices(devs, cfg) {
    const container = document.getElementById('devices-container');
    container.innerHTML = '';

    if (!devs.length) {
        container.innerHTML = `
            <div style="color:var(--c-text-dim);font-size:.875rem;text-align:center;padding:2rem 0;">
                No devices available.<br>
                <span style="font-size:.75rem;">Connect OpenRGB and configure topologies.</span>
            </div>`;
        return;
    }

    const devicesCfg = cfg.devices || {};

    devs.forEach(dev => {
        const devCfg  = devicesCfg[dev.device_key] || {};
        const enabled = devCfg.enabled ?? false;
        const safeId  = _devSafeId(dev.device_key);
        const tType   = dev.topology_type || 'single';

        const iconName = tType === 'matrix' ? 'keyboard'
                       : tType === 'linear' ? 'linear_scale'
                       : 'fiber_manual_record';

        const zonesTxt = dev.has_topology
            ? `${dev.zone_count} zone${dev.zone_count !== 1 ? 's' : ''}`
            : `<span style="color:rgba(251,191,36,.62);">no topology</span>`;

        const card = document.createElement('div');
        card.id        = 'dev-card-' + safeId;
        card.className = 'dev-card' + (enabled ? ' dev-card--on' : '');
        card.innerHTML = `
            <div class="dev-card-header">
                <div class="dev-icon" id="dev-icon-${safeId}">
                    <span class="material-symbols-outlined" style="font-size:19px;">${iconName}</span>
                </div>
                <div class="dev-info">
                    <div class="dev-name">${escapeHtml(dev.name)}</div>
                    <div class="dev-meta">
                        ${dev.led_count} LED &middot; ${tType} &middot; ${zonesTxt}
                    </div>
                </div>
                <button
                    id="dev-btn-${safeId}"
                    class="dev-power-btn${enabled ? ' enabled' : ''}"
                    title="${enabled ? 'Turn off' : 'Turn on'} for ambilight"
                    aria-label="${escapeAttr(dev.name)}: ${enabled ? 'turn off' : 'turn on'} for ambilight"
                    aria-pressed="${enabled}"
                    onclick="toggleDevice('${escapeAttr(dev.device_key)}', ${!enabled}, this)"
                    ${!dev.has_topology ? 'disabled' : ''}>
                    ${_powerSVG}
                </button>
            </div>
            ${!dev.has_topology ? `
            <div class="dev-no-topo">
                Map its zones in the <a href="topology-editor.html" style="color:var(--c-cyan);">Topology Editor</a> to use this device.
            </div>` : ''}
            <div id="zones-${safeId}" class="dev-zones"></div>
        `;
        container.appendChild(card);

        if (enabled && dev.has_topology) {
            loadDeviceZones(dev.device_key);
        }
    });
}

function toggleDevice(deviceKey, enable, btnEl) {
    // Update config state
    if (!_cfg.devices) _cfg.devices = {};
    if (!_cfg.devices[deviceKey]) _cfg.devices[deviceKey] = {};
    _cfg.devices[deviceKey].enabled = enable;
    api('set_ambilight_device_enabled', deviceKey, enable).then(res => {
        if (apiOk(res)) return;
        // Roll back the optimistic UI change
        _reportApiFailure('update the device', res);
        const rb = document.getElementById('dev-btn-' + _devSafeId(deviceKey));
        if (!rb) return;
        _cfg.devices[deviceKey].enabled = !enable;
        _applyDeviceUi(deviceKey, !enable, rb);
    });
    _applyDeviceUi(deviceKey, enable, btnEl);
}

function _applyDeviceUi(deviceKey, enable, btnEl) {
    const safeId  = _devSafeId(deviceKey);
    const card    = document.getElementById('dev-card-'  + safeId);
    const btn     = btnEl || document.getElementById('dev-btn-'  + safeId);
    const zonesEl = document.getElementById('zones-'     + safeId);

    // Card state
    if (card) card.classList.toggle('dev-card--on', enable);

    // Button state + ripple animation
    if (btn) {
        btn.classList.toggle('enabled', enable);
        btn.title = (enable ? 'Turn off' : 'Turn on') + ' for ambilight';
        btn.onclick = () => toggleDevice(deviceKey, !enable, btn);
        btn.setAttribute('aria-pressed', String(enable));

        const ripple = document.createElement('span');
        ripple.className = 'dev-power-ripple';
        btn.appendChild(ripple);
        setTimeout(() => ripple.remove(), 700);
    }

    // Zones section
    if (enable) {
        const dev = _devs.find(d => d.device_key === deviceKey);
        if (dev?.has_topology && zonesEl) {
            zonesEl.innerHTML = '<div class="dev-zones-loading">Loading zones...</div>';
            setTimeout(() => loadDeviceZones(deviceKey), 60);
        }
    } else {
        if (zonesEl) zonesEl.innerHTML = '';
    }
}

async function loadDeviceZones(deviceKey) {
    const safeId    = _devSafeId(deviceKey);
    const container = document.getElementById('zones-' + safeId);
    if (!container) return;

    const zones = await api('get_ambilight_device_zones', deviceKey);
    if (!zones || !zones.length) {
        container.innerHTML = `<div class="dev-zones-loading">No zones detected.</div>`;
        return;
    }

    const cfg      = _cfg.devices?.[deviceKey] || {};
    const zonesEna = cfg.zones_enabled || {};

    // Zones are keyed by index; the name key is what older versions saved.
    const isOn = z => (zonesEna[String(z.zone_index)] ?? zonesEna[z.name]) !== false;
    // OpenRGB sometimes hands over unreadable names ("???")
    const label = z => /^[?\s]*$/.test(z.name || '') ? `Zone ${z.zone_index}` : z.name;

    container.innerHTML = `
        <div class="dev-zones-grid">
            ${zones.map(z => `
            <label class="dev-zone-item">
                <input type="checkbox" class="dev-zone-check"
                    ${isOn(z) ? 'checked' : ''}
                    onchange="toggleZone('${escapeAttr(deviceKey)}', ${Number(z.zone_index)}, this.checked)">
                <span class="dev-zone-name">${escapeHtml(label(z))}</span>
                <span class="dev-zone-edge">${escapeHtml(z.edge)}</span>
            </label>`).join('')}
        </div>`;
}

function toggleZone(deviceKey, zoneIndex, enabled) {
    api('set_ambilight_zone_enabled', deviceKey, zoneIndex, enabled).then(res => {
        if (!apiOk(res)) _reportApiFailure('update the zone', res);
    });
    if (!_cfg.devices) _cfg.devices = {};
    if (!_cfg.devices[deviceKey]) _cfg.devices[deviceKey] = {};
    if (!_cfg.devices[deviceKey].zones_enabled) _cfg.devices[deviceKey].zones_enabled = {};
    _cfg.devices[deviceKey].zones_enabled[String(zoneIndex)] = enabled;
}

// ── Status polling ────────────────────────────────────────────────────────────

let _pollFailures = 0;

function _setConnectionBanner(lost) {
    let b = document.getElementById('conn-banner');
    if (!lost) { if (b) b.remove(); return; }
    if (b) return;
    b = document.createElement('div');
    b.id = 'conn-banner';
    b.setAttribute('role', 'alert');
    Object.assign(b.style, {
        position: 'fixed', top: '0', left: '80px', right: '0', zIndex: '9000',
        padding: '8px 20px', textAlign: 'center', fontSize: '13px',
        background: 'rgba(60,10,10,.96)', color: '#ff9a9a',
        borderBottom: '1px solid rgba(255,70,70,.45)',
    });
    b.textContent = 'Connection to EDAmbilight lost — changes are not being applied. Reconnecting…';
    document.body.appendChild(b);
}

async function pollStatus() {
    const s = await api('get_ambilight_status');
    if (!apiOk(s)) {
        if (++_pollFailures >= 3) {
            _setConnectionBanner(true);
            updateStatusBadge(false);
            const fpsBadge = document.getElementById('fps-badge');
            if (fpsBadge) fpsBadge.textContent = '— fps';
        }
        return;
    }
    if (_pollFailures) { _pollFailures = 0; _setConnectionBanner(false); }

    const fpsBadge = document.getElementById('fps-badge');
    if (fpsBadge) {
        fpsBadge.textContent = s.running ? `${s.fps} fps` : '— fps';
        // Warn when the real rate stays well under the target (system overloaded)
        const target = _cfg.fps || 15;
        _lowFpsPolls = (s.enabled && s.running && s.fps < target * 0.7) ? _lowFpsPolls + 1 : 0;
        const low = _lowFpsPolls >= 3;
        fpsBadge.style.color = low ? '#fbbf24' : '#fff';
        fpsBadge.title = low ? `Reaching ${s.fps} of ${target} fps — try lowering FPS Target or switching Capture Engine`
                             : 'Frame rate actually reached';
    }

    _renderStandbyTest(!!s.standby_preview);

    const capEl = document.getElementById('stat-capturer');
    if (capEl) capEl.textContent = s.capturer || '—';

    const bbEl = document.getElementById('bb-status');
    if (bbEl) {
        if (s.content_rect) {
            const [x0, y0, x1, y1] = s.content_rect;
            bbEl.textContent = `Content area: ${x1 - x0}×${y1 - y0} px — bars cropped`;
            bbEl.style.color = 'rgba(20,245,255,.55)';
        } else {
            bbEl.textContent = '';
        }
    }

    const kind = _statusKind(s);
    updateStatusBadge(kind === 'active', kind);
    _renderStatusInfo(s, kind);
    _renderChecklist(s);
}

let _lowFpsPolls = 0;

// inactive | no-devices | no-zones | active
function _statusKind(s) {
    if (!(s.enabled && s.running)) return 'inactive';
    if (!s.devices_total)          return 'no-devices';
    if (!s.active_zones)           return 'no-zones';
    if (s.standby)                 return 'standby';
    return 'active';
}

const _STATUS_STYLE = {
    'inactive':   { label: 'INACTIVE',   color: 'rgba(255,255,255,0.4)', dot: '' },
    'active':     { label: 'ACTIVE',     color: 'rgba(20,245,255,0.9)',  dot: 'rgba(20,245,255,0.9)' },
    'no-zones':   { label: 'NO ZONES',   color: '#fbbf24',               dot: '#fbbf24' },
    'standby':    { label: 'STANDBY',    color: 'rgba(167,139,250,0.9)', dot: 'rgba(167,139,250,0.9)' },
    'no-devices': { label: 'NO DEVICES', color: '#f87171',               dot: '#f87171' },
};

function updateStatusBadge(active, kind) {
    const el = document.getElementById('status-dot');
    if (!el || active === null || active === undefined) return;
    const st = _STATUS_STYLE[kind || (active ? 'active' : 'inactive')];
    el.className = active
        ? 'w-2 h-2 rounded-full nav-dot-active'
        : 'w-2 h-2 rounded-full bg-white/20';
    el.style.background = st.dot;
    const lbl = document.getElementById('status-label');
    if (lbl) {
        lbl.textContent = st.label;
        lbl.style.color = st.color;
    }
}

function _renderStatusInfo(s, kind) {
    const sum  = document.getElementById('status-summary');
    const hint = document.getElementById('status-hint');
    const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;
    if (sum) {
        sum.textContent = kind === 'active'
            ? `${plural(s.active_devices, 'device')} · ${plural(s.active_zones, 'zone')} · ${s.capturer || '—'}`
            : 'Ambilight service';
    }
    if (!hint) return;
    const html = {
        'no-devices': 'OpenRGB reports no devices. Make sure OpenRGB is running with the SDK server on — see <a href="settings.html">Settings</a>.',
        'no-zones':   s.mapped_devices
            ? 'Running, but no device receives colors. Switch on a device in the list below.'
            : 'Running, but no zone is mapped to the screen. Map them in the <a href="topology-editor.html">Topology Editor</a>.',
        'standby':    'The screen is not providing frames (display asleep or locked). LEDs follow the Screen standby setting and resume by themselves.',
    }[kind] || '';
    if (hint.dataset.kind !== kind) { hint.innerHTML = html; hint.dataset.kind = kind; }
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
    const dev = (_devs || []).find(d => d.device_key === z.dev);
    const title = document.createElement('b');
    title.textContent = dev ? dev.name : z.dev;
    const zone = document.createElement('div');
    zone.textContent = `Zone: ${z.zone}`;
    const kind = document.createElement('span');
    if (hit.type === 'dot') {
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
    const MAX_H = 230;
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
    const edgeZones = zones.filter(z => z.edge !== 'area').sort((a, b) => order[a.edge] - order[b.edge]);
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

// ── Getting-started checklist ─────────────────────────────────────────────────

function _lsGet(k) { try { return localStorage.getItem(k); } catch (_) { return null; } }
function _lsSet(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }

function dismissChecklist() {
    _lsSet('edambi.checklistDismissed', '1');
    const c = document.getElementById('checklist');
    if (c) c.hidden = true;
}

// Amber dot on a sidebar item = "this is the next thing to do"
function _setNavHint(href, on) {
    const a = document.querySelector(`#sidebar-nav a[href="${href}"]`);
    if (!a) return;
    let dot = a.querySelector('.nav-hint');
    if (!on) { if (dot) dot.remove(); return; }
    if (dot) return;
    dot = document.createElement('span');
    dot.className = 'nav-hint';
    dot.setAttribute('aria-label', 'Next step');
    Object.assign(dot.style, {
        position: 'absolute', top: '10px', right: '18px', width: '8px', height: '8px',
        borderRadius: '50%', background: '#fbbf24', boxShadow: '0 0 8px rgba(251,191,36,.8)',
    });
    a.appendChild(dot);
}

function _renderChecklist(s) {
    _setNavHint('settings.html',        !s.devices_total);
    _setNavHint('topology-editor.html', s.devices_total > 0 && !s.mapped_devices);
    const box   = document.getElementById('checklist');
    const items = document.getElementById('checklist-items');
    if (!box || !items) return;
    const steps = [
        { done: s.devices_total > 0,
          text: 'OpenRGB connected and devices found', link: ['Settings', 'settings.html'] },
        { done: s.mapped_devices > 0,
          text: 'At least one device has zones mapped to the screen', link: ['Open Topology Editor', 'topology-editor.html'] },
        { done: !!(s.enabled && s.active_zones > 0),
          text: 'Enable switched on and a device selected below', link: null },
    ];
    const allDone = steps.every(x => x.done);
    box.hidden = allDone || _lsGet('edambi.checklistDismissed') === '1';
    if (box.hidden) return;
    items.innerHTML = steps.map(x => `
        <li class="${x.done ? 'done' : ''}">
            <span class="ck" aria-hidden="true">${x.done ? '✓' : ''}</span>
            <span>${x.text}${!x.done && x.link ? ` — <a href="${x.link[1]}">${x.link[0]}</a>` : ''}</span>
        </li>`).join('');
}

// ── Presets / reset / advanced ────────────────────────────────────────────────

const DEFAULT_CFG = {
    fps: 15, strategy: 'adaptive_smooth', depth: 10, saturation_boost: 1.4, min_luminance: 0,
    ema_alpha: 0.35, scene_cut: 60, adaptive_min: 3, adaptive_max: 20,
};

const PRESETS = {
    balanced: { ...DEFAULT_CFG },
    cinema:   { ...DEFAULT_CFG, fps: 24, ema_alpha: 0.25, scene_cut: 50, saturation_boost: 1.5 },
    gaming:   { ...DEFAULT_CFG, fps: 30, ema_alpha: 0.6,  scene_cut: 45, saturation_boost: 1.7, adaptive_max: 15 },
    calm:     { ...DEFAULT_CFG, fps: 15, ema_alpha: 0.15, scene_cut: 80, saturation_boost: 1.2, adaptive_min: 5, adaptive_max: 25, min_luminance: 10 },
};

async function _applyValues(values, okMsg) {
    Object.keys(values).forEach(k => { clearTimeout(_cfgTimers[k]); delete _pendingCfg[k]; });
    Object.assign(_cfg, values);
    applyConfig(_cfg);
    document.querySelectorAll('input[type=range]').forEach(el => { if (typeof updateFill === 'function') updateFill(el); });
    refreshPresetChips();
    refreshAccentChips();
    const res = await api('set_ambilight_config', values);
    if (apiOk(res)) showNotification(okMsg, 'success', 1800);
    else _reportApiFailure('apply the preset', res);
}

function applyPreset(name) {
    const p = PRESETS[name];
    if (p) _applyValues(p, `Preset applied: ${name[0].toUpperCase()}${name.slice(1)}`);
}

function resetToDefaults() { _applyValues({ ...DEFAULT_CFG }, 'Defaults restored'); }

function refreshPresetChips() {
    const val  = k => _cfg[k] ?? DEFAULT_CFG[k];
    const same = p => Object.keys(p).every(k =>
        typeof p[k] === 'string' ? val(k) === p[k] : Math.abs(Number(val(k)) - p[k]) < 1e-9);
    let match = null;
    document.querySelectorAll('.preset-chip').forEach(btn => {
        const on = same(PRESETS[btn.dataset.preset]);
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-pressed', String(on));
        if (on) match = btn.dataset.preset;
    });
    const custom = document.getElementById('preset-custom');
    if (custom) custom.classList.toggle('show', !match);
}

function toggleAdvanced(force) {
    const row = document.getElementById('param-row');
    const btn = document.getElementById('btn-advanced');
    if (!row || !btn) return;
    const show = typeof force === 'boolean' ? force : row.hidden;
    row.hidden = !show;
    btn.setAttribute('aria-expanded', String(show));
    _lsSet('edambi.advanced', show ? '1' : '0');
}

// ── Beat accent ───────────────────────────────────────────────────────────────

const ACCENT_DEFAULTS = {
    accent_mode: 'mix', accent_dark_lift: 20, accent_intensity: 25, accent_duration: 200,
    accent_color: '#ffffff', accent_hue_mode: 'off', accent_hue_deg: 40, accent_hue_decay: 1500,
    accent_max_per_sec: 3, accent_max_boost: 100, accent_attack: 15, accent_sensitivity: 50,
    accent_min_strength: 40,
};

// Presets leave alone: on/off, audio device, sensitivity and flash color
const ACCENT_PRESETS = {
    soft:   { accent_mode: 'mix', accent_dark_lift: 20,  accent_intensity: 15, accent_duration: 250,
              accent_hue_mode: 'off',   accent_hue_deg: 40, accent_hue_decay: 1500,
              accent_max_per_sec: 2, accent_max_boost: 60,  accent_attack: 20, accent_min_strength: 40 },
    punchy: { accent_mode: 'mix', accent_dark_lift: 40,  accent_intensity: 45, accent_duration: 180,
              accent_hue_mode: 'pulse', accent_hue_deg: 20, accent_hue_decay: 1500,
              accent_max_per_sec: 3, accent_max_boost: 100, accent_attack: 10, accent_min_strength: 30 },
    club:   { accent_mode: 'add', accent_dark_lift: 100, accent_intensity: 90, accent_duration: 130,
              accent_hue_mode: 'step',  accent_hue_deg: 45, accent_hue_decay: 1500,
              accent_max_per_sec: 5, accent_max_boost: 150, accent_attack: 0,  accent_min_strength: 20 },
};

function applyAccentConfig(cfg) {
    const v = k => cfg[k] ?? ACCENT_DEFAULTS[k];
    setToggle('ctrl-acc-enabled', cfg.accent_enabled);
    setSlider('ctrl-acc-lift',  'val-acc-lift',  v('accent_dark_lift'));
    setSlider('ctrl-acc-int',   'val-acc-int',   v('accent_intensity'));
    setSlider('ctrl-acc-dur',   'val-acc-dur',   v('accent_duration'));
    setSlider('ctrl-acc-deg',   'val-acc-deg',   v('accent_hue_deg'));
    setSlider('ctrl-acc-decay', 'val-acc-decay', v('accent_hue_decay'));
    setSlider('ctrl-acc-rate',  'val-acc-rate',  v('accent_max_per_sec'));
    setSlider('ctrl-acc-cap',   'val-acc-cap',   v('accent_max_boost'));
    setSlider('ctrl-acc-att',   'val-acc-att',   v('accent_attack'));
    setSlider('ctrl-acc-sens',  'val-acc-sens',  v('accent_sensitivity'));
    setSlider('ctrl-acc-str',   'val-acc-str',   v('accent_min_strength'));
    setAccentRateLabel(v('accent_max_per_sec'));
    const mode = document.getElementById('ctrl-acc-mode'); if (mode) mode.value = v('accent_mode');
    const hue  = document.getElementById('ctrl-acc-hue');  if (hue)  hue.value  = v('accent_hue_mode');
    const col  = document.getElementById('ctrl-acc-color'); if (col) col.value  = v('accent_color');
    _setAccentDevice(cfg.accent_device || '');
    updateAccentVisibility();
    refreshAccentChips();
}

function setAccentRateLabel(n) {
    const el = document.getElementById('val-acc-rate');
    if (el) el.textContent = n === 0 ? 'off' : n;
}

function _hideRow(id, hidden) {
    const el = document.getElementById(id);
    if (el) el.hidden = hidden;
}

// Only the controls that matter for the chosen mode are shown
function updateAccentVisibility() {
    const mode = (document.getElementById('ctrl-acc-mode') || {}).value;
    const hue  = (document.getElementById('ctrl-acc-hue')  || {}).value;
    _hideRow('row-acc-lift',  mode !== 'mix');
    _hideRow('row-acc-color', mode === 'mul');
    _hideRow('row-acc-deg',   hue === 'off');
    _hideRow('row-acc-decay', hue !== 'step');
}

function onAccentMode(value) { liveUpdate('accent_mode', value, null);     updateAccentVisibility(); }
function onAccentHue(value)  { liveUpdate('accent_hue_mode', value, null); updateAccentVisibility(); }

function applyAccentPreset(name) {
    const p = ACCENT_PRESETS[name];
    if (p) _applyValues(p, `Accent preset applied: ${name[0].toUpperCase()}${name.slice(1)}`);
}

function refreshAccentChips() {
    const val  = k => _cfg[k] ?? ACCENT_DEFAULTS[k];
    const same = p => Object.keys(p).every(k =>
        typeof p[k] === 'string' ? val(k) === p[k] : Math.abs(Number(val(k)) - p[k]) < 1e-9);
    let match = null;
    document.querySelectorAll('.accent-chip').forEach(btn => {
        const on = same(ACCENT_PRESETS[btn.dataset.accent]);
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-pressed', String(on));
        if (on) match = btn.dataset.accent;
    });
    const custom = document.getElementById('accent-custom');
    if (custom) custom.classList.toggle('show', !match);
}

// Send the edits still waiting in the debounce, so a test uses what is on screen
async function _flushPendingCfg() {
    const keys = Object.keys(_pendingCfg);
    if (!keys.length) return;
    const values = {};
    keys.forEach(k => { clearTimeout(_cfgTimers[k]); values[k] = _pendingCfg[k]; delete _pendingCfg[k]; });
    await api('set_ambilight_config', values);
}

async function testAccent() {
    await _flushPendingCfg();
    const res = await api('test_accent');
    if (!apiOk(res)) { _reportApiFailure('fire the test accent', res); return; }
    const b = document.getElementById('btn-accent-test');
    if (b) { b.classList.add('fired'); setTimeout(() => b.classList.remove('fired'), 220); }
    if (res.accepted === false) {
        showNotification('Skipped by the flash limit: wait a moment or raise Max flashes/s', 'info', 2000);
    }
}

// ── Audio input: device list and meter ────────────────────────────────────────

function _setAccentDevice(name) {
    const sel = document.getElementById('ctrl-acc-dev');
    if (!sel) return;
    if (name && ![...sel.options].some(o => o.value === name)) {
        const o = document.createElement('option');
        o.value = name; o.textContent = `${name} (not found)`;
        sel.appendChild(o);
    }
    sel.value = name;
}

async function _loadAudioDevices() {
    const sel = document.getElementById('ctrl-acc-dev');
    if (!sel) return;
    const r = await api('list_audio_devices');
    const keep = _cfg.accent_device || '';
    sel.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
    ((r && r.devices) || []).forEach(name => {
        const o = document.createElement('option');
        o.value = name; o.textContent = name;
        sel.appendChild(o);
    });
    _setAccentDevice(keep);
}

let _accentBusy = false;

async function _accentTick() {
    if (!document.hidden && !_accentBusy) {
        _accentBusy = true;
        try { _renderMeter(await api('get_audio_status')); } finally { _accentBusy = false; }
    }
    setTimeout(_accentTick, _cfg.accent_enabled ? 200 : 1000);
}

function _renderMeter(s) {
    const bar = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.style.width = Math.round(Math.max(0, Math.min(1, v || 0)) * 100) + '%';
    };
    const listening = !!_cfg.accent_enabled && !!(s && s.running);
    bar('m-level', listening ? s.level : 0);
    bar('m-bass',  listening ? s.bass  : 0);
    bar('m-mid',   listening ? s.mid   : 0);
    bar('m-high',  listening ? s.high  : 0);
    const dot = document.getElementById('m-beat');
    if (dot) dot.classList.toggle('on', listening && s.beat_age != null && s.beat_age < 0.25);

    const st = document.getElementById('m-status');
    if (!st) return;
    let text;
    if (!_cfg.accent_enabled)       text = 'Audio listening is off';
    else if (s && s.error)          text = s.error;
    else if (!s || !s.running)      text = 'Starting audio capture…';
    else if (s.silent)              text = 'Listening: no sound is playing';
    else if (s.notice)              text = `${s.notice} (${s.device})`;
    else                            text = `Listening to ${s.device || 'the default output'}`;
    if (st.textContent !== text) st.textContent = text;
}

function _initAccent() {
    updateAccentVisibility();
    _loadAudioDevices();
    _accentTick();
}
