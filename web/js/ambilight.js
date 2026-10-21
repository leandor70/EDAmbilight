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

// ── Config apply ──────────────────────────────────────────────────────────────

function applyConfig(cfg) {
    setToggle('ctrl-enabled', cfg.enabled);
    setSlider('ctrl-fps',       'val-fps',       cfg.fps              ?? 15);
    setSlider('ctrl-depth',     'val-depth',     cfg.depth            ?? 10);
    setSlider('ctrl-sat',       'val-sat',       cfg.saturation_boost ?? 1.4);
    setSlider('ctrl-ema',       'val-ema',       cfg.ema_alpha        ?? 0.35);
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

function liveUpdate(key, value, spanId) {
    if (spanId) document.getElementById(spanId).textContent = value;
    _cfg[key] = value;
    api('set_ambilight_config', { [key]: value });
}

function toggleEnabled(checked) {
    _cfg.enabled = checked;
    api('set_ambilight_config', { enabled: checked });
    updateStatusBadge(checked ? null : false);
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
                    title="${enabled ? 'Disabilita' : 'Abilita'} per ambilight"
                    onclick="toggleDevice('${escapeAttr(dev.device_key)}', ${!enabled}, this)"
                    ${!dev.has_topology ? 'disabled' : ''}>
                    ${_powerSVG}
                </button>
            </div>
            ${!dev.has_topology ? `
            <div class="dev-no-topo">
                Configura le zone nel Topology Editor per abilitare questo device.
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
    api('set_ambilight_device_enabled', deviceKey, enable);

    const safeId  = _devSafeId(deviceKey);
    const card    = document.getElementById('dev-card-'  + safeId);
    const btn     = btnEl || document.getElementById('dev-btn-'  + safeId);
    const zonesEl = document.getElementById('zones-'     + safeId);

    // Card state
    if (card) card.classList.toggle('dev-card--on', enable);

    // Button state + ripple animation
    if (btn) {
        btn.classList.toggle('enabled', enable);
        btn.title = (enable ? 'Disabilita' : 'Abilita') + ' per ambilight';
        btn.onclick = () => toggleDevice(deviceKey, !enable, btn);

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

    container.innerHTML = `
        <div class="dev-zones-grid">
            ${zones.map(z => `
            <label class="dev-zone-item">
                <input type="checkbox" class="dev-zone-check"
                    ${zonesEna[z.name] !== false ? 'checked' : ''}
                    onchange="toggleZone('${escapeAttr(deviceKey)}', '${escapeAttr(z.name)}', this.checked)">
                <span class="dev-zone-name">${escapeHtml(z.name)}</span>
                <span class="dev-zone-edge">${escapeHtml(z.edge)}</span>
            </label>`).join('')}
        </div>`;
}

function toggleZone(deviceKey, zoneName, enabled) {
    api('set_ambilight_zone_enabled', deviceKey, zoneName, enabled);
    if (!_cfg.devices) _cfg.devices = {};
    if (!_cfg.devices[deviceKey]) _cfg.devices[deviceKey] = {};
    if (!_cfg.devices[deviceKey].zones_enabled) _cfg.devices[deviceKey].zones_enabled = {};
    _cfg.devices[deviceKey].zones_enabled[zoneName] = enabled;
}

// ── Status polling ────────────────────────────────────────────────────────────

async function pollStatus() {
    const s = await api('get_ambilight_status');
    if (!s) return;

    const fpsBadge = document.getElementById('fps-badge');
    if (fpsBadge) fpsBadge.textContent = s.running ? `${s.fps} fps` : '— fps';

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

    updateStatusBadge(s.enabled && s.running);
}

function updateStatusBadge(active) {
    const el = document.getElementById('status-dot');
    if (!el || active === null || active === undefined) return;
    el.className = active
        ? 'w-2 h-2 rounded-full nav-dot-active'
        : 'w-2 h-2 rounded-full bg-white/20';
    el.style.background = active ? 'rgba(20,245,255,0.9)' : '';
    const lbl = document.getElementById('status-label');
    if (lbl) {
        lbl.textContent = active ? 'ACTIVE' : 'INACTIVE';
        lbl.style.color = active ? 'rgba(20,245,255,0.9)' : 'rgba(255,255,255,0.4)';
    }
}

