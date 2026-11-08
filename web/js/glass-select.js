'use strict';
/* Glass dropdown. The native <select> stays in the page as the visible trigger
   (so its styling, layout, id, value and onchange keep working untouched); only
   its popup list, which the browser draws and CSS cannot style, is replaced by a
   semi-transparent, blurred panel. Works for selects added later (delegation).
   Opt out with data-native on a <select>. */
(function () {
    let pop = null, sel = null, items = [], active = -1;

    const eligible = s => s && s.tagName === 'SELECT' && !s.multiple && !(s.size > 1)
                          && !s.disabled && !s.hasAttribute('data-native');

    function build(select) {
        const frag = document.createDocumentFragment();
        items = [];
        const addOption = (o, parent) => {
            const el = document.createElement('div');
            el.className = 'gs-opt';
            el.setAttribute('role', 'option');
            el.textContent = o.textContent;
            if (o.disabled || (parent && parent.disabled)) el.classList.add('gs-disabled');
            if (o.index === select.selectedIndex) { el.classList.add('gs-selected'); el.setAttribute('aria-selected', 'true'); }
            el._opt = o;
            items.push(el);
            frag.appendChild(el);
        };
        [...select.children].forEach(c => {
            if (c.tagName === 'OPTGROUP') {
                const g = document.createElement('div');
                g.className = 'gs-group';
                g.textContent = c.label;
                frag.appendChild(g);
                [...c.children].forEach(o => addOption(o, c));
            } else if (c.tagName === 'OPTION') addOption(c, null);
        });
        return frag;
    }

    function setActive(i, scroll) {
        if (active >= 0 && items[active]) items[active].classList.remove('gs-active');
        active = i;
        if (i >= 0 && items[i]) {
            items[i].classList.add('gs-active');
            if (scroll) items[i].scrollIntoView({ block: 'nearest' });
        }
    }

    function step(dir) {
        if (!items.length) return;
        let i = active;
        for (let n = 0; n < items.length; n++) {
            i = (i + dir + items.length) % items.length;
            if (!items[i].classList.contains('gs-disabled')) return setActive(i, true);
        }
    }

    function position() {
        const r  = sel.getBoundingClientRect();
        const vh = window.innerHeight, vw = window.innerWidth;
        const room = 8;
        const below = vh - r.bottom - room, above = r.top - room;
        const want  = Math.min(pop.scrollHeight, 320);
        const down  = below >= want || below >= above;
        const maxH  = Math.max(120, Math.min(320, down ? below : above));
        pop.style.maxHeight = maxH + 'px';
        pop.style.minWidth  = Math.max(r.width, 120) + 'px';
        const h = Math.min(pop.scrollHeight, maxH);
        let left = r.left;
        const w  = pop.offsetWidth;
        if (left + w > vw - room) left = Math.max(room, vw - room - w);
        pop.style.left = left + 'px';
        pop.style.top  = (down ? r.bottom + 4 : r.top - 4 - h) + 'px';
        pop.classList.toggle('gs-down', down);
        pop.classList.toggle('gs-up', !down);
    }

    function open(select) {
        if (sel === select) return close();
        close();
        sel = select;
        pop = document.createElement('div');
        pop.className = 'gs-pop';
        pop.setAttribute('role', 'listbox');
        const cs = getComputedStyle(select);
        pop.style.fontFamily = cs.fontFamily;
        pop.style.fontSize   = Math.max(13, parseFloat(cs.fontSize)) + 'px';
        pop.appendChild(build(select));
        document.body.appendChild(pop);
        position();
        setActive(select.selectedIndex >= 0 ? items.findIndex(el => el._opt.index === select.selectedIndex) : -1, true);
        requestAnimationFrame(() => pop && pop.classList.add('gs-open'));
        select.setAttribute('aria-expanded', 'true');
    }

    function close() {
        if (!pop) return;
        if (sel) sel.removeAttribute('aria-expanded');
        pop.remove();
        pop = sel = null; items = []; active = -1;
    }

    function choose(el) {
        if (!el || !el._opt || el.classList.contains('gs-disabled')) return;
        const select = sel, changed = select.selectedIndex !== el._opt.index;
        select.selectedIndex = el._opt.index;
        close();
        select.focus();
        if (changed) {
            select.dispatchEvent(new Event('input',  { bubbles: true }));
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // Open on click instead of the native list.
    document.addEventListener('mousedown', e => {
        if (pop && pop.contains(e.target)) { e.preventDefault(); return; }   // keep focus on the select
        const s = e.target.closest && e.target.closest('select');
        if (e.button === 0 && eligible(s)) { e.preventDefault(); s.focus(); open(s); return; }
        close();
    }, true);

    document.addEventListener('click', e => {
        if (!pop) return;
        const el = e.target.closest && e.target.closest('.gs-opt');
        if (el && pop.contains(el)) choose(el);
    });
    document.addEventListener('mousemove', e => {
        if (!pop) return;
        const el = e.target.closest && e.target.closest('.gs-opt');
        if (el && pop.contains(el) && !el.classList.contains('gs-disabled')) setActive(items.indexOf(el), false);
    });

    document.addEventListener('keydown', e => {
        if (pop) {
            switch (e.key) {
                case 'Escape':    e.preventDefault(); e.stopPropagation(); close(); return;
                case 'ArrowDown': e.preventDefault(); step(1);  return;
                case 'ArrowUp':   e.preventDefault(); step(-1); return;
                case 'Home':      e.preventDefault(); setActive(items.findIndex(i => !i.classList.contains('gs-disabled')), true); return;
                case 'End':       e.preventDefault(); { const k = items.map(i => !i.classList.contains('gs-disabled')).lastIndexOf(true); setActive(k, true); } return;
                case 'Enter': case ' ': e.preventDefault(); choose(items[active]); return;
                case 'Tab':       close(); return;
            }
            return;
        }
        const s = e.target;
        if (!eligible(s)) return;
        if (e.key === ' ' || e.key === 'F4' || (e.altKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp'))) {
            e.preventDefault();
            open(s);
        }
    }, true);

    window.addEventListener('resize', close);
    window.addEventListener('blur', close);
    document.addEventListener('scroll', e => { if (pop && !pop.contains(e.target)) close(); }, true);
})();
