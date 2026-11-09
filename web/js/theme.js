'use strict';
/* Theme switch: dark (default) or light "glass".
   Loaded in <head>, before the first paint, so the page never flashes the wrong
   theme. Only pages that carry data-themeable on <html> take part (all of them now).
   The choice is kept in localStorage. */
(function () {
    const KEY  = 'edambi.theme';
    const root = document.documentElement;
    let chosen = false;      // the user picked a theme on this page: a late reply from the file must not undo it

    function stored() {
        try { return localStorage.getItem(KEY) === 'light' ? 'light' : 'dark'; } catch (_) { return 'dark'; }
    }

    function apply(theme) {
        if (!root.hasAttribute('data-themeable')) return;
        if (theme === 'light') root.setAttribute('data-theme', 'light');
        else root.removeAttribute('data-theme');
    }

    window.EDTheme = {
        themeable: () => root.hasAttribute('data-themeable'),
        current:   () => (root.getAttribute('data-theme') === 'light' ? 'light' : 'dark'),
        set(theme, fromSync) {
            theme = theme === 'light' ? 'light' : 'dark';
            root.classList.add('theme-fade');
            apply(theme);
            try { localStorage.setItem(KEY, theme); } catch (_) {}
            if (!fromSync) { chosen = true; save(theme); }
            setTimeout(() => root.classList.remove('theme-fade'), 320);
            document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
        },
        toggle() { this.set(this.current() === 'light' ? 'dark' : 'light'); },
    };

    // The browser copy (localStorage) is what lets the page paint in the right theme at
    // once, but it is lost when the port changes or the browser is another one. The
    // choice is therefore also kept in config/settings.json (ui_theme) and reconciled
    // here: the saved value wins; if there is none yet, the browser's one is saved.
    function backend() {
        return (typeof eel !== 'undefined' && eel.get_settings && eel.save_settings) ? eel : null;
    }
    function save(theme) {
        const b = backend();
        if (b) { try { b.save_settings({ ui_theme: theme })(); } catch (_) {} }
    }
    function reconcile() {
        const b = backend();
        if (!b) return;
        try {
            b.get_settings()(s => {
                if (chosen) return;
                const saved = s && s.ui_theme;
                if (saved === 'light' || saved === 'dark') {
                    if (saved !== window.EDTheme.current() && root.hasAttribute('data-themeable')) window.EDTheme.set(saved, true);
                    else try { localStorage.setItem(KEY, saved); } catch (_) {}
                } else if (root.hasAttribute('data-themeable')) {
                    save(window.EDTheme.current());
                }
            });
        } catch (_) {}
    }

    apply(stored());
    window.addEventListener('load', () => setTimeout(reconcile, 0));
})();
