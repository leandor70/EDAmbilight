'use strict';

// ── API call wrapper ──────────────────────────────────────────────────────────

async function api(funcName, ...args) {
    try {
        if (typeof eel === 'undefined') {
            console.error('[API] Eel not loaded');
            return { success: false, error: 'Eel not initialized' };
        }
        const result = await eel[funcName](...args)();
        return result || {};
    } catch (error) {
        console.error(`[API] Error calling ${funcName}:`, error);
        return { success: false, error: error.message || 'Connection error' };
    }
}

// ── Notifications ────────────────────────────────────────────────────────────

function showNotification(message, type = 'info', duration = 4000) {
    const colors = { success: '#10b981', error: '#ef4444', warning: '#f59e0b', info: '#14F5FF' };
    const icons  = { success: 'check_circle', error: 'error', warning: 'warning', info: 'info' };

    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        Object.assign(container.style, {
            position: 'fixed', top: '24px', right: '24px',
            zIndex: '10000', display: 'flex', flexDirection: 'column', gap: '12px',
            pointerEvents: 'none',
        });
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.innerHTML = `
        <div style="display:flex;align-items:center;gap:12px;
            background:rgba(0,0,0,0.95);border:1px solid ${colors[type] || colors.info};
            border-radius:8px;padding:12px 16px;min-width:280px;max-width:400px;
            box-shadow:0 10px 40px rgba(0,0,0,0.5);pointer-events:auto;
            animation:slideInRight 0.3s ease-out;">
            <span class="material-symbols-outlined" style="color:${colors[type]||colors.info};font-size:24px;">
                ${icons[type] || 'info'}
            </span>
            <span style="color:white;flex:1;font-size:14px;">${escapeHtml(message)}</span>
            <button onclick="this.parentElement.parentElement.remove()"
                style="background:none;border:none;color:rgba(255,255,255,0.5);cursor:pointer;font-size:20px;">×</button>
        </div>`;
    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    return String(text ?? '')
        .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function hexToRgb(hex) {
    hex = hex.replace(/^#/, '');
    const r = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return r ? [parseInt(r[1],16), parseInt(r[2],16), parseInt(r[3],16)] : null;
}

function rgbToHex(r, g, b) {
    r = Math.max(0, Math.min(255, Math.round(r)));
    g = Math.max(0, Math.min(255, Math.round(g)));
    b = Math.max(0, Math.min(255, Math.round(b)));
    return '#' + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1).toUpperCase();
}

function debounce(func, wait) {
    let t;
    return function(...args) {
        clearTimeout(t);
        t = setTimeout(() => func(...args), wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) { func(...args); inThrottle = true; setTimeout(() => inThrottle = false, limit); }
    };
}

// ── Toast animations CSS ──────────────────────────────────────────────────────

if (!document.getElementById('toast-animations')) {
    const s = document.createElement('style');
    s.id = 'toast-animations';
    s.textContent = `
        @keyframes slideInRight  { from { transform:translateX(400px);opacity:0; } to { transform:translateX(0);opacity:1; } }
        @keyframes slideOutRight { from { transform:translateX(0);opacity:1; }     to { transform:translateX(400px);opacity:0; } }
    `;
    document.head.appendChild(s);
}

// ── Cancel shutdown on page connect ──────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    if (typeof eel !== 'undefined') {
        try { eel.cancel_shutdown()(); } catch(_) {}
    }
});

console.log('[Common] EDAmbilight utilities loaded');
