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
        <nav style="
            width:80px; height:100%; flex-shrink:0; z-index:20; position:relative;
            background:rgba(2,8,14,.98);
            border-right:1px solid rgba(255,255,255,.055);
            display:flex; flex-direction:column;
        ">
            <!-- Logo -->
            <div class="nav-logo" style="
                padding:18px 0 16px;
                display:flex; justify-content:center; align-items:center;
                border-bottom:1px solid rgba(255,255,255,.04);
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
                        color:${active ? 'rgba(20,245,255,.92)' : 'rgba(255,255,255,.35)'};
                        background:${active
                            ? 'linear-gradient(90deg, rgba(20,245,255,.10) 0%, rgba(20,245,255,.04) 100%)'
                            : 'transparent'};
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
                            font-size:10px; letter-spacing:.07em;
                            font-family:'Rajdhani',sans-serif;
                            text-transform:uppercase; font-weight:700;
                            line-height:1;
                        ">${item.label}</span>
                    </a>`;
                }).join('')}
            </div>

            <!-- Version -->
            <div style="
                padding:12px 0; text-align:center;
                border-top:1px solid rgba(255,255,255,.04);
            ">
                <span style="font-size:9px; color:rgba(255,255,255,.15);
                             font-family:monospace; letter-spacing:.06em;">v1.0</span>
            </div>
        </nav>
    `;

    container.querySelectorAll('.nav-item').forEach(el => {
        if (el.dataset.active === 'true') return;
        el.addEventListener('mouseenter', () => {
            el.style.color      = 'rgba(20,245,255,.72)';
            el.style.background = 'rgba(20,245,255,.05)';
        });
        el.addEventListener('mouseleave', () => {
            el.style.color      = 'rgba(255,255,255,.35)';
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
