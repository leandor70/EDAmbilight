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
    renderDevices(_devs);

    _statusLoop();
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

// ── Devices (summary: which devices are on; zones and details live in Devices) ──

function _devSafeId(deviceKey) {
    return deviceKey.replace(/[^a-z0-9]/gi, '_');
}

const _powerSVG = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2.4" stroke-linecap="round" width="13" height="13" aria-hidden="true">
  <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>
  <line x1="12" y1="2" x2="12" y2="12"/>
</svg>`;

const _isOn = key => !!(((_cfg.devices || {})[key] || {}).enabled);

function renderDevices(devs) {
    const container = document.getElementById('devices-container');
    container.innerHTML = '';

    if (!devs.length) {
        container.innerHTML = `
            <div class="devs-empty">
                No devices available.<br>
                <span>Connect OpenRGB first: <a href="settings.html">Settings</a>.</span>
            </div>`;
        _renderDevicesSummary();
        return;
    }

    devs.forEach(dev => {
        const on = _isOn(dev.device_key);
        const b  = document.createElement('button');
        b.type = 'button';
        b.id   = 'dev-chip-' + _devSafeId(dev.device_key);
        b.className = 'dev-chip' + (on ? ' on' : '');
        b.disabled  = !dev.has_topology;
        b.title = dev.has_topology
            ? (on ? 'On: receives the ambilight colors. Click to turn off.' : 'Off. Click to turn on.')
            : 'No zones mapped yet: map them in the Topology Editor.';
        b.setAttribute('aria-pressed', String(on));
        b.innerHTML = `${_powerSVG}<span>${escapeHtml(dev.name)}</span>`;
        b.onclick = () => toggleDevice(dev.device_key, !_isOn(dev.device_key));
        container.appendChild(b);
    });
    _renderDevicesSummary();
}

function _renderDevicesSummary() {
    const sum  = document.getElementById('devices-summary');
    const warn = document.getElementById('devices-warn');
    if (!sum || !warn) return;
    const mapped = _devs.filter(d => d.has_topology);
    const on     = mapped.filter(d => _isOn(d.device_key));
    const zones  = on.reduce((n, d) => n + (d.zones_active || 0), 0);

    sum.textContent = !_devs.length ? ''
        : `${on.length} of ${_devs.length} device${_devs.length === 1 ? '' : 's'} on · ${zones} zone${zones === 1 ? '' : 's'} receiving colors`;

    let msg = '';
    if (!_devs.length)         msg = '';
    else if (!mapped.length)   msg = 'No device has its zones mapped to the screen yet.';
    else if (!on.length)       msg = 'No device is switched on, so nothing will light up.';
    else if (!zones)           msg = 'The devices that are on have no active zones, so nothing will light up.';
    warn.hidden = !msg;
    if (msg) warn.querySelector('span').textContent = msg;
}

function toggleDevice(deviceKey, enable) {
    if (!_cfg.devices) _cfg.devices = {};
    if (!_cfg.devices[deviceKey]) _cfg.devices[deviceKey] = {};
    _cfg.devices[deviceKey].enabled = enable;
    _applyChip(deviceKey, enable);
    api('set_ambilight_device_enabled', deviceKey, enable).then(res => {
        if (apiOk(res)) return;
        _reportApiFailure('update the device', res);   // roll back the optimistic change
        _cfg.devices[deviceKey].enabled = !enable;
        _applyChip(deviceKey, !enable);
    });
}

function _applyChip(deviceKey, on) {
    const chip = document.getElementById('dev-chip-' + _devSafeId(deviceKey));
    if (chip) {
        chip.classList.toggle('on', on);
        chip.setAttribute('aria-pressed', String(on));
    }
    _renderDevicesSummary();
}

// ── Status polling ────────────────────────────────────────────────────────────

let _pollFailures = 0;

// Status every 0.8 s; every 2 s when the window is in the background, 3 s when hidden
async function _statusLoop() {
    try { await pollStatus(); } catch (_) {}
    setTimeout(_statusLoop, document.hidden ? 3000 : document.hasFocus() ? 800 : 2000);
}

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
        background: 'var(--err-bg)', color: 'var(--err-fg)',
        borderBottom: '1px solid var(--err-bd)',
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
        fpsBadge.style.color = low ? 'var(--c-fps-low)' : 'var(--c-strong)';
        const load = s.frame_ms ? ` · ${s.frame_ms} ms per frame of ${Math.round(1000 / target)} available` : '';
        fpsBadge.title = low ? `Reaching ${s.fps} of ${target} fps — try lowering FPS Target or switching Capture Engine${load}`
                             : `Frame rate actually reached${load}`;
    }

    _renderStandbyTest(!!s.standby_preview);

    const capEl = document.getElementById('stat-capturer');
    if (capEl) capEl.textContent = s.capturer || '—';

    const bbEl = document.getElementById('bb-status');
    if (bbEl) {
        if (s.content_rect) {
            const [x0, y0, x1, y1] = s.content_rect;
            bbEl.textContent = `Content area: ${x1 - x0}×${y1 - y0} px — bars cropped`;
            bbEl.style.color = 'var(--c-bb)';
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
    'inactive':   { label: 'INACTIVE',   color: 'var(--st-inactive)', dot: '' },
    'active':     { label: 'ACTIVE',     color: 'var(--st-active)',   dot: 'var(--st-active)' },
    'no-zones':   { label: 'NO ZONES',   color: 'var(--st-nozones)',  dot: 'var(--st-nozones)' },
    'standby':    { label: 'STANDBY',    color: 'var(--st-standby)',  dot: 'var(--st-standby)' },
    'no-devices': { label: 'NO DEVICES', color: 'var(--st-nodev)',    dot: 'var(--st-nodev)' },
};

function updateStatusBadge(active, kind) {
    const el = document.getElementById('status-dot');
    if (!el || active === null || active === undefined) return;
    const st = _STATUS_STYLE[kind || (active ? 'active' : 'inactive')];
    el.className = active
        ? 'w-2 h-2 rounded-full nav-dot-active'
        : 'w-2 h-2 rounded-full';
    el.style.background = st.dot || 'var(--dot-off)';
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
        'no-devices': 'OpenRGB reports no devices. Make sure OpenRGB is running with the SDK server on — see <a href="settings.html">Settings</a>. On Windows, memory and motherboards also need the PawnIO driver (pawnio.eu).',
        'no-zones':   s.mapped_devices
            ? 'Running, but no device receives colors. Switch on a device in the list below.'
            : 'Running, but no zone is mapped to the screen. Map them in the <a href="topology-editor.html">Topology Editor</a>.',
        'standby':    'The screen is not providing frames (display asleep or locked). LEDs follow the Screen standby setting and resume by themselves.',
    }[kind] || '';
    if (hint.dataset.kind !== kind) { hint.innerHTML = html; hint.dataset.kind = kind; }
}

// ── Getting-started checklist ─────────────────────────────────────────────────

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
          text: 'Enable switched on and a device with active zones', link: ['Open Devices', 'devices.html'] },
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
    setTimeout(_accentTick, _cfg.accent_enabled && document.hasFocus() ? 200 : 1000);
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
