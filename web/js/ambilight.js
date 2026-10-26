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

    const capSel = document.getElementById('ctrl-capturer');
    if (capSel) capSel.value = cfg.capturer ?? 'auto';

    const stratSel = document.getElementById('ctrl-strategy');
    if (stratSel) {
        stratSel.value = cfg.strategy ?? 'adaptive_smooth';
        updateStrategyVisibility(stratSel.value);
    }
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
    clearTimeout(_cfgTimers[key]);
    _cfgTimers[key] = setTimeout(async () => {
        const v = _pendingCfg[key];
        delete _pendingCfg[key];
        const res = await api('set_ambilight_config', { [key]: v });
        if (!apiOk(res)) _reportApiFailure('apply the change', res);
    }, CFG_DEBOUNCE);
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
    return 'active';
}

const _STATUS_STYLE = {
    'inactive':   { label: 'INACTIVE',   color: 'rgba(255,255,255,0.4)', dot: '' },
    'active':     { label: 'ACTIVE',     color: 'rgba(20,245,255,0.9)',  dot: 'rgba(20,245,255,0.9)' },
    'no-zones':   { label: 'NO ZONES',   color: '#fbbf24',               dot: '#fbbf24' },
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
    }[kind] || '';
    if (hint.dataset.kind !== kind) { hint.innerHTML = html; hint.dataset.kind = kind; }
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

