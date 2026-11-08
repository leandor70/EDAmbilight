'use strict';
/* Theme switch: dark (default) or light "glass".
   Loaded in <head>, before the first paint, so the page never flashes the wrong
   theme. Only pages that carry data-themeable on <html> take part; the others
   (Topology, Help, Preview) stay dark. The choice is kept in localStorage. */
(function () {
    const KEY  = 'edambi.theme';
    const root = document.documentElement;

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
        set(theme) {
            theme = theme === 'light' ? 'light' : 'dark';
            root.classList.add('theme-fade');
            apply(theme);
            try { localStorage.setItem(KEY, theme); } catch (_) {}
            setTimeout(() => root.classList.remove('theme-fade'), 320);
            document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
        },
        toggle() { this.set(this.current() === 'light' ? 'dark' : 'light'); },
    };

    apply(stored());
})();
