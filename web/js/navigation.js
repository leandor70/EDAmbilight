'use strict';

const NAV_ITEMS = [
    { id: 'index',           icon: 'settings_brightness', label: 'Control',  href: 'index.html' },
    { id: 'topology-editor', icon: 'hub',                 label: 'Topology', href: 'topology-editor.html' },
    { id: 'devices',         icon: 'memory',              label: 'Devices',  href: 'devices.html' },
    { id: 'settings',        icon: 'tune',                label: 'Settings', href: 'settings.html' },
    { id: 'preview',         icon: 'auto_awesome',        label: 'Preview',  href: 'preview.html' },
    { id: 'help',            icon: 'help',                label: 'Help',     href: 'help.html' },
];

/* Inject keyframes + nav-item animation once per page */
(function injectNavStyles() {
    if (document.getElementById('nav-styles')) return;
    const s = document.createElement('style');
    s.id = 'nav-styles';
    s.textContent = `
        @keyframes navItemIn {
            from { opacity:0; transform:translateX(-18px); filter:blur(7px); }
            to   { opacity:1; transform:translateX(0);     filter:blur(0);   }
        }
        .nav-item {
            animation: navItemIn .7s cubic-bezier(0.23,1,0.32,1) both;
        }
        .nav-item:nth-child(1) { animation-delay:.12s; }
        .nav-item:nth-child(2) { animation-delay:.24s; }
        .nav-item:nth-child(3) { animation-delay:.36s; }
        .nav-item:nth-child(4) { animation-delay:.48s; }
        .nav-item:nth-child(5) { animation-delay:.60s; }
        .nav-item:nth-child(6) { animation-delay:.72s; }

        /* Logo fade-down */
        @keyframes logoIn {
            from { opacity:0; transform:translateY(-12px); filter:blur(5px); }
            to   { opacity:1; transform:translateY(0);     filter:blur(0);   }
        }
        .nav-logo {
            animation: logoIn .65s cubic-bezier(0.23,1,0.32,1) .04s both;
        }
    `;
    document.head.appendChild(s);
})();

function _buildSidebar() {
    const container = document.getElementById('sidebar-nav');
    if (!container) return;

    const activePage = container.dataset.activePage || '';
    const isActive   = id => id === activePage || (activePage === '' && id === 'index');

    container.innerHTML = `
        <nav class="app-nav">
            <!-- Logo -->
            <div class="nav-logo" style="
                padding:18px 0 16px;
                display:flex; justify-content:center; align-items:center;
                border-bottom:1px solid var(--line-soft);
            ">
                <div style="position:relative; width:46px; height:46px;
                            display:flex; align-items:center; justify-content:center;"
                     title="EDAmbilight">
                    <div style="
                        position:absolute; width:46px; height:46px;
                        border:1px solid rgba(20,245,255,.35); border-radius:50%;
                        animation:sonarRing 3s cubic-bezier(0.23,1,0.32,1) infinite;
                    "></div>
                    <div style="
                        position:absolute; width:46px; height:46px;
                        border:1px solid rgba(20,245,255,.18); border-radius:50%;
                        animation:sonarRing 3s cubic-bezier(0.23,1,0.32,1) 1.1s infinite;
                    "></div>
                    <div style="
                        width:42px; height:42px; border-radius:50%; padding:2px;
                        background:rgba(255,255,255,.03);
                        border:1px solid rgba(255,255,255,.07);
                        box-shadow:0 0 0 1px rgba(0,0,0,.28);
                        display:flex; align-items:center; justify-content:center;
                        position:relative; z-index:1;
                    ">
                        <div style="
                            width:38px; height:38px; border-radius:50%;
                            border:1.5px solid rgba(20,245,255,.60);
                            background:radial-gradient(circle, rgba(20,245,255,.09) 0%, transparent 70%);
                            display:flex; align-items:center; justify-content:center;
                            animation:coreGlow 2.5s ease-in-out infinite alternate;
                        ">
                            <span class="material-symbols-outlined"
                                  style="font-size:18px; color:rgba(20,245,255,.88);
                                         font-variation-settings:'FILL' 0,'wght' 200,'GRAD' 0,'opsz' 20;">
                                settings_brightness
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Nav items -->
            <div style="flex:1; display:flex; flex-direction:column; padding:10px 0; gap:2px;">
                ${NAV_ITEMS.map(item => {
                    const active = isActive(item.id);
                    return `
                    <a href="${item.href}"
                       class="nav-item"
                       data-active="${active}"
                       title="${item.label}"
                       style="
                        display:flex; flex-direction:column; align-items:center;
                        justify-content:center; padding:14px 0; gap:7px;
                        cursor:pointer; text-decoration:none; position:relative;
                        color:${active ? 'var(--nav-active)' : 'var(--nav-item)'};
                        background:${active ? 'var(--nav-active-bg)' : 'transparent'};
                        transition: color .2s cubic-bezier(0.23,1,0.32,1),
                                    background .2s cubic-bezier(0.23,1,0.32,1),
                                    transform .15s cubic-bezier(0.23,1,0.32,1);
                       ">
                        ${active ? `
                        <div style="
                            position:absolute; left:0; top:8px; bottom:8px; width:2.5px;
                            background:linear-gradient(to bottom,
                                rgba(20,245,255,.25) 0%, rgba(20,245,255,1) 50%, rgba(20,245,255,.25) 100%);
                            box-shadow:0 0 10px rgba(20,245,255,.8);
                            border-radius:0 2px 2px 0;
                        "></div>` : ''}
                        <span class="material-symbols-outlined" style="
                            font-size:26px; line-height:1;
                            font-variation-settings:'FILL' ${active ? '1' : '0'},'wght' ${active ? '300' : '200'},'GRAD' 0,'opsz' 24;
                            transition: font-variation-settings .2s cubic-bezier(0.23,1,0.32,1);
                        ">${item.icon}</span>
                        <span style="
                            font-size:12px; letter-spacing:.07em;
                            font-family:'Rajdhani',sans-serif;
                            text-transform:uppercase; font-weight:700;
                            line-height:1;
                        ">${item.label}</span>
                    </a>`;
                }).join('')}
            </div>

            <!-- Theme switch (only on pages that have a light theme) + version -->
            <div style="
                padding:12px 0; text-align:center;
                border-top:1px solid var(--line-soft);
            ">
                ${(window.EDTheme && EDTheme.themeable()) ? `
                <button type="button" id="theme-toggle" class="theme-toggle"
                        aria-label="Switch to light theme" title="Switch to light theme">
                    <span class="material-symbols-outlined" aria-hidden="true">light_mode</span>
                </button>` : ''}
                <span id="nav-version" style="font-size:11px; color:var(--nav-ver);
                             font-family:monospace; letter-spacing:.06em;"></span>
            </div>
        </nav>
    `;

    try {
        if (typeof eel !== 'undefined') {
            eel.get_app_version()(v => {
                const el = document.getElementById('nav-version');
                if (el && typeof v === 'string') el.textContent = 'v' + v;
            });
        }
    } catch (_) {}

    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        // The button names the theme it switches TO; the icon shows that theme.
        const sync = () => {
            const light = EDTheme.current() === 'light';
            const label = light ? 'Switch to dark theme' : 'Switch to light theme';
            toggle.setAttribute('aria-label', label);
            toggle.title = label;
            toggle.firstElementChild.textContent = light ? 'dark_mode' : 'light_mode';
        };
        toggle.addEventListener('click', () => EDTheme.toggle());
        document.addEventListener('themechange', sync);
        sync();
    }

    container.querySelectorAll('.nav-item').forEach(el => {
        if (el.dataset.active === 'true') return;
        el.addEventListener('mouseenter', () => {
            el.style.color      = 'var(--nav-hover)';
            el.style.background = 'var(--nav-hover-bg)';
        });
        el.addEventListener('mouseleave', () => {
            el.style.color      = 'var(--nav-item)';
            el.style.background = 'transparent';
        });
        el.addEventListener('mousedown', () => {
            el.style.transform = 'scale(0.93)';
        });
        el.addEventListener('mouseup', () => {
            el.style.transform = 'scale(1)';
        });
    });
}

document.addEventListener('DOMContentLoaded', _buildSidebar);

/* ── Hardware change notices ─────────────────────────────────────────────────
   Shown on every page that has the sidebar, until the user dismisses them:
   a device was added, removed or changed since the last start. */
const _NOTICE_ICONS = { added: 'add_circle', removed: 'link_off', changed: 'sync_alt', version: 'system_update' };
const _HARDWARE_KINDS = ['added', 'removed', 'changed'];

function _renderHardwareNotices(notices) {
    const old = document.getElementById('hw-notices');
    if (old) old.remove();
    const main = document.querySelector('main');
    if (!main || !Array.isArray(notices) || notices.length === 0) return;

    const box = document.createElement('div');
    box.id = 'hw-notices';
    box.setAttribute('role', 'status');
    Object.assign(box.style, {
        flexShrink: '0', margin: '12px 24px 0', padding: '12px 16px',
        background: 'rgba(245,158,11,.08)', border: '1px solid rgba(245,158,11,.38)',
        borderRadius: '10px', display: 'flex', gap: '14px', alignItems: 'flex-start',
        fontFamily: "'Rajdhani', sans-serif", fontSize: '15px', color: 'var(--text-main, #CDD6E0)',
    });

    const list = document.createElement('div');
    list.style.cssText = 'flex:1;display:flex;flex-direction:column;gap:6px;';
    const title = document.createElement('div');
    const onlyHardware = notices.every(n => _HARDWARE_KINDS.includes(n.kind));
    const noHardware   = notices.every(n => !_HARDWARE_KINDS.includes(n.kind));
    title.textContent = onlyHardware ? 'Hardware changed since the last start'
                      : noHardware   ? 'OpenRGB' : 'Notices';
    title.style.cssText = 'font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:14px;color:#f59e0b;';
    list.appendChild(title);

    notices.forEach(n => {
        const row = document.createElement('div');
        row.style.cssText = 'display:flex;gap:8px;align-items:flex-start;';
        const icon = document.createElement('span');
        icon.className = 'material-symbols-outlined';
        icon.textContent = _NOTICE_ICONS[n.kind] || 'info';
        icon.style.cssText = 'font-size:20px;line-height:1.2;color:#f59e0b;';
        const text = document.createElement('span');
        text.textContent = n.text;           // device names come from the hardware: never HTML
        row.append(icon, text);
        list.appendChild(row);
    });

    const dismiss = document.createElement('button');
    dismiss.type = 'button';
    dismiss.className = 'btn';
    dismiss.textContent = 'Dismiss';
    dismiss.addEventListener('click', () => {
        box.remove();
        try { eel.dismiss_hardware_notices()(); } catch (_) {}
    });

    box.append(list, dismiss);
    main.insertBefore(box, main.firstChild);
}

function _loadHardwareNotices(attempt = 0) {
    try {
        if (typeof eel === 'undefined' || typeof eel.get_hardware_notices !== 'function') throw 0;
        eel.get_hardware_notices()(_renderHardwareNotices);
    } catch (_) {
        if (attempt < 10) setTimeout(() => _loadHardwareNotices(attempt + 1), 500);
    }
}

document.addEventListener('DOMContentLoaded', () => _loadHardwareNotices());

/* ── New version on GitHub ───────────────────────────────────────────────────
   A toast with a link to the release page; nothing is downloaded or installed.
   The check runs in the background at startup (at most once a day), so a page
   opened right away asks again a little later. */
let _updateShown = false;

function _showUpdateToast(u) {
    if (_updateShown || !u || !u.show || document.getElementById('update-toast')) return;
    _updateShown = true;
    const container = toastContainer();

    const box = document.createElement('div');
    box.id = 'update-toast';
    box.setAttribute('role', 'status');
    box.style.cssText = 'display:flex;gap:12px;align-items:flex-start;background:var(--pop-bg);' +
        'border:1px solid var(--toast-info);border-radius:8px;padding:12px 16px;min-width:280px;max-width:min(470px, calc(100vw - 48px));' +
        'box-shadow:var(--pop-shadow);pointer-events:auto;animation:slideInRight 0.3s ease-out;';

    const icon = document.createElement('span');
    icon.className = 'material-symbols-outlined';
    icon.textContent = 'system_update';
    icon.style.cssText = 'color:var(--toast-info);font-size:24px;';

    const body = document.createElement('div');
    body.style.cssText = 'flex:1;display:flex;flex-direction:column;gap:8px;font-size:14px;color:var(--c-strong);';
    const text = document.createElement('div');
    text.textContent = `EDAmbilight ${u.latest} is available (you have ${u.current}).`;
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;';
    const link = document.createElement('a');
    link.className = 'btn';
    link.href = u.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = "What's new / download";
    const skip = document.createElement('button');
    skip.type = 'button';
    skip.className = 'btn';
    skip.textContent = 'Skip this version';
    skip.title = 'No notice for this version again; a newer one will be shown';
    row.append(link, skip);
    body.append(text, row);

    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = '×';
    close.title = 'Close (shown again at the next start)';
    close.setAttribute('aria-label', 'Close');
    close.style.cssText = 'background:none;border:none;color:var(--c-faint);cursor:pointer;font-size:20px;';

    const hide = skipIt => {
        box.remove();
        try { eel.close_update_notice(skipIt)(); } catch (_) {}
    };
    close.addEventListener('click', () => hide(false));
    skip.addEventListener('click', () => hide(true));
    link.addEventListener('click', () => hide(false));

    box.append(icon, body, close);
    container.appendChild(box);
}

function _loadUpdateInfo(attempt = 0) {
    const later = [1500, 5000, 15000, 30000];
    try {
        if (typeof eel === 'undefined' || typeof eel.get_update_info !== 'function') throw 0;
        eel.get_update_info()(u => {
            _showUpdateToast(u);
            if (!_updateShown && attempt < later.length) setTimeout(() => _loadUpdateInfo(attempt + 1), later[attempt]);
        });
    } catch (_) {
        if (attempt < later.length) setTimeout(() => _loadUpdateInfo(attempt + 1), later[attempt]);
    }
}

document.addEventListener('DOMContentLoaded', () => _loadUpdateInfo());
