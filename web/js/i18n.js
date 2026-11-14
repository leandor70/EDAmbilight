'use strict';
/* Interface language: English (the source text) or Italian.

   Loaded in <head> right after theme.js, followed by the dictionary (i18n-it.js).
   The pages stay written in English; when Italian is chosen, every text node and
   the translatable attributes are looked up in the dictionary while the parser
   builds the page (a MutationObserver), and again whenever a script adds or
   changes content later (toasts, dialogs, lists rendered from data). With English
   nothing runs at all.

   Dictionary (EDI18n.add('it', {...})):
     strings  : { 'English text': 'Testo italiano' }            exact match
     patterns : { 'Connected — {n} device(s)': 'Connesso — {n} dispositivi' }
                a value can be a function (vars => string), e.g. for plurals;
                captured parts are themselves translated when they match a string;
                the pattern with the most fixed text is tried first
     html     : { 'help.intro': '<b>…</b>' }   for elements with data-i18n="key"
                (their whole innerHTML is replaced: paragraphs with markup inside)

   Opt-out: translate="no", class "notranslate" or data-no-i18n on an element
   leaves it and its children alone (device and zone names, user input).
   Scripts can call EDI18n.t('text', {vars}) for strings that never reach the DOM
   (canvas labels). The choice: localStorage edambi.lang (first paint) plus
   config/settings.json "language" (wins when the two differ; the page reloads). */
(function () {
    const KEY   = 'edambi.lang';
    const LANGS = ['en', 'it'];
    const ATTRS = ['title', 'placeholder', 'aria-label', 'alt', 'data-info', 'data-info-title'];
    const SKIP_TAGS = new Set(['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE', 'PRE', 'svg', 'SVG', 'CANVAS', 'NOSCRIPT']);
    const root  = document.documentElement;

    function stored() {
        try { const v = localStorage.getItem(KEY); return LANGS.includes(v) ? v : 'en'; } catch (_) { return 'en'; }
    }

    const lang  = stored();
    const dicts = {};                 // lang -> { strings: Map, patterns: [{re, names, out}], html: {} }
    const cache = new Map();          // normalized text -> translation | null
    const CACHE_MAX = 4000;

    function dict() { return dicts[lang]; }

    function compilePattern(src, out) {
        const names = [];
        const re = src.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                      .replace(/\\\{(\w+)\\\}/g, (_, n) => { names.push(n); return '([\\s\\S]+?)'; });
        // specificity: how much fixed text the pattern has ('{n} zones' is weak)
        const fixed = src.replace(/\{\w+\}/g, '').replace(/\s+/g, '').length;
        return { re: new RegExp('^' + re + '$'), names, out, fixed };
    }

    function fill(out, vars) {
        if (typeof out === 'function') return String(out(vars));
        return out.replace(/\{(\w+)\}/g, (m, n) => (n in vars ? vars[n] : m));
    }

    const norm = s => s.replace(/\s+/g, ' ').trim();

    // Translation of one piece of text, or null when the dictionary has none
    function lookup(text, depth) {
        const d = dict();
        if (!d) return null;
        const k = norm(text);
        if (!k || !/[A-Za-z]/.test(k)) return null;
        if (cache.has(k)) return cache.get(k);
        let res = d.strings.has(k) ? d.strings.get(k) : null;
        if (typeof res === 'function') res = String(res({}));
        if (res === null) {
            for (const p of d.patterns) {
                const m = p.re.exec(k);
                if (!m) continue;
                const vars = {};
                p.names.forEach((n, i) => {
                    const v = m[i + 1];
                    vars[n] = depth < 1 ? (lookup(v, depth + 1) ?? v) : v;
                });
                res = fill(p.out, vars);
                break;
            }
        }
        if (cache.size > CACHE_MAX) cache.clear();
        cache.set(k, res);
        return res;
    }

    // Italian text this script wrote: never looked up again ("6 zones" -> "6 zone" must
    // not become "6 zona" when the change is observed and '{n} zone' matches it)
    const produced = new Set();

    function translateText(s) {
        if (produced.has(norm(s))) return s;
        const t = lookup(s, 0);
        if (t === null || t === undefined) return s;
        if (produced.size > CACHE_MAX) produced.clear();
        produced.add(norm(t));
        const lead  = s.match(/^\s*/)[0];
        const trail = s.match(/\s*$/)[0];
        return lead + t + trail;
    }

    // data-info: "line\nTerm|Description\n…" — each part is translated on its own
    function translateInfo(v) {
        return v.split('\n').map(line => line.split('|').map(translateText).join('|')).join('\n');
    }

    function skipped(el) {
        for (let e = el; e && e.nodeType === 1; e = e.parentNode) {
            if (SKIP_TAGS.has(e.tagName)) return true;
            if (e.getAttribute('translate') === 'no' || e.hasAttribute('data-no-i18n')) return true;
            const c = e.classList;
            if (c && (c.contains('notranslate') || c.contains('material-symbols-outlined'))) return true;
        }
        return false;
    }

    function doAttrs(el) {
        for (const a of ATTRS) {
            const v = el.getAttribute(a);
            if (!v) continue;
            const t = a === 'data-info' ? translateInfo(v) : translateText(v);
            if (t !== v) el.setAttribute(a, t);
        }
        if (el.tagName === 'INPUT' && (el.type === 'button' || el.type === 'submit') && el.value) {
            const t = translateText(el.value);
            if (t !== el.value) el.value = t;
        }
    }

    function doText(node) {
        const v = node.nodeValue;
        if (!v || !v.trim()) return;
        const t = translateText(v);
        if (t !== v) node.nodeValue = t;
    }

    function doHtmlKey(el) {
        const d = dict();
        const key = el.getAttribute('data-i18n');
        // While the parser runs the element may not be complete yet (its tail would end
        // up after the Italian): the DOMContentLoaded walk does it
        if (document.readyState === 'loading') return;
        if (d && key && d.html[key] !== undefined && el.getAttribute('data-i18n-done') !== lang) {
            el.setAttribute('data-i18n-done', lang);
            el.innerHTML = d.html[key];
        }
    }

    function walk(node) {
        if (node.nodeType === 3) {
            if (!skipped(node.parentNode)) doText(node);
            return;
        }
        if (node.nodeType !== 1 || skipped(node)) return;
        if (node.hasAttribute('data-i18n')) doHtmlKey(node);
        doAttrs(node);
        const tw = document.createTreeWalker(node, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
            acceptNode(n) {
                if (n.nodeType === 1) {
                    if (SKIP_TAGS.has(n.tagName) || n.getAttribute('translate') === 'no' ||
                        n.hasAttribute('data-no-i18n') || n.classList.contains('notranslate') ||
                        n.classList.contains('material-symbols-outlined')) return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            },
        });
        let n;
        while ((n = tw.nextNode())) {
            if (n.nodeType === 3) doText(n);
            else {
                if (n.hasAttribute('data-i18n')) doHtmlKey(n);
                doAttrs(n);
            }
        }
    }

    function translateTitle() {
        const t = translateText(document.title);
        if (t !== document.title) document.title = t;
    }

    window.EDI18n = {
        lang,
        languages: LANGS.slice(),
        add(l, d) {
            const tgt = dicts[l] || (dicts[l] = { strings: new Map(), patterns: [], html: {} });
            for (const [k, v] of Object.entries(d.strings || {})) tgt.strings.set(norm(k), v);
            for (const [k, v] of Object.entries(d.patterns || {})) tgt.patterns.push(compilePattern(norm(k), v));
            tgt.patterns.sort((a, b) => b.fixed - a.fixed);      // most specific first
            Object.assign(tgt.html, d.html || {});
            cache.clear();
            if (l === lang && document.body) walk(document.body);
        },
        // For text that never reaches the DOM (canvas). Placeholders: {name}
        t(text, vars) {
            const d = lang === 'en' ? null : dict();
            const s = d ? d.strings.get(norm(text)) : undefined;
            if (s !== undefined) return fill(s, vars || {});
            const out = d ? (lookup(text, 0) ?? text) : text;
            return vars ? fill(out, vars) : out;
        },
        translate(node) { if (lang !== 'en') walk(node || document.body); },
        set(l, fromSync) {
            l = LANGS.includes(l) ? l : 'en';
            try { localStorage.setItem(KEY, l); } catch (_) {}
            if (!fromSync) save(l);
            if (l !== lang) setTimeout(() => location.reload(), fromSync ? 0 : 150);
        },
    };

    function backend() {
        return (typeof eel !== 'undefined' && eel.get_settings && eel.save_settings) ? eel : null;
    }
    function save(l) {
        const b = backend();
        if (b) { try { b.save_settings({ language: l })(); } catch (_) {} }
    }
    // The file copy wins: the browser's one is lost when the port or the browser changes
    function reconcile() {
        const b = backend();
        if (!b) return;
        try {
            b.get_settings()(s => {
                const saved = s && s.language;
                if (LANGS.includes(saved) && saved !== lang) window.EDI18n.set(saved, true);
            });
        } catch (_) {}
    }
    window.addEventListener('load', () => setTimeout(reconcile, 0));

    if (lang === 'en') return;

    root.setAttribute('lang', lang);

    // Translate while the parser builds the page and whenever scripts change it
    const obs = new MutationObserver(records => {
        for (const r of records) {
            if (r.type === 'childList') {
                r.addedNodes.forEach(walk);
            } else if (r.type === 'characterData') {
                if (!skipped(r.target.parentNode)) doText(r.target);
            } else if (r.type === 'attributes') {
                const el = r.target;
                if (!skipped(el)) doAttrs(el);
            }
            if (r.target === document.head || (r.target.parentNode && r.target.parentNode.tagName === 'TITLE')
                || r.target.tagName === 'TITLE') translateTitle();
        }
    });
    obs.observe(root, {
        childList: true, subtree: true, characterData: true,
        attributes: true, attributeFilter: ATTRS.concat(['value']),
    });
    document.addEventListener('DOMContentLoaded', () => { translateTitle(); walk(document.body); });
})();
