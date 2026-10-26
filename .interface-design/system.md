# EDAmbilight — Interface Design System

## Intent

**Who:** Tech enthusiast alla scrivania di notte, monitor acceso, luce spenta.  
**Task:** Attivare ambilight, regolare FPS/depth/smoothing, vedere subito se funziona.  
**Feel:** Pannello broadcast professionale in sala buia — preciso, tecnico, vivo.  
**Signature:** Luce che emana da schermi nell'oscurità.

---

## Palette

| Token | Value | Uso |
|---|---|---|
| `--c-abyss` | `#020b0f` | Background pagina |
| `--c-deep` | `#051420` | Superficie base card |
| `--c-cyan` | `#14F5FF` | Accent primario — tutto interattivo |
| `--c-cyan-80` | `rgba(20,245,255,.80)` | Testo accent |
| `--c-cyan-25` | `rgba(20,245,255,.25)` | Border default |
| `--c-cyan-12` | `rgba(20,245,255,.12)` | Fill button ghost |
| `--c-cyan-08` | `rgba(20,245,255,.08)` | Fill card hover, bg button |
| `--c-success` | `#22D3A5` | OK / connected |
| `--c-error` | `#F05454` | Errore |
| `--c-warning` | `#FF9F1C` | Warning / no-topology |
| `--c-purple` | `#A78BFA` | Dispositivi MATRIX |
| `--c-text` | `#CDD6E0` | Testo principale |
| `--c-text-dim` | `rgba(255,255,255,.28)` | Label, secondario |
| `--c-text-ghost` | `rgba(255,255,255,.12)` | Hint, note |

---

## Typography

- **Display:** `Orbitron` — Numeri grandi, titoli pagina, valori metrici
- **Body:** `Rajdhani` — Tutto il resto
- **Label pattern:** `10px / font-weight:700 / uppercase / tracking:.12em / color:--c-text-dim`
- **Big number:** classe `ds-num` — Orbitron, colore cyan, `font-size` variabile (1.2rem – 2.4rem)
- **Titoli pagina:** Orbitron 30px, tracking `.3em`, bianco

---

## Profondità / Card

Classe: `ds-card` (alias backward-compat: `sci-fi-border`)

- Background: `linear-gradient(135deg, rgba(5,18,29,.96), rgba(2,11,16,.98))`  
- Border: `1px solid rgba(20,245,255,.25)` → `.44` on hover  
- Corner brackets: `::before` top-left, `::after` bottom-right — 14px → 20px on hover  
- Shadow: `0 4px 28px rgba(0,0,0,.55)` + `borderPulse` animation (7s)  
- Hover: border luminosa + glow sm + corner brackets che crescono

Texture: `ds-carbon` (alias: `carbon-pattern`) — radial dots 4px grid

---

## Animazioni chiave

| Nome | Durata | Uso |
|---|---|---|
| `slideUp` | 500ms ease-out | Card appear on load (stagger via `ds-appear`) |
| `sonarRing` | 3s ease-out infinite | Logo sidebar, logo loading |
| `breatheDot` | 2s ease-in-out infinite | Status dot quando ambilight è attivo |
| `shimmerBar` | 3.5s linear infinite | Linee gradient nell'header |
| `borderPulse` | 7s ease-in-out infinite | Glow sottile su tutte le card |
| `scanLine` | 10s linear infinite | Background — scan orizzontale (doppio, offset 5s) |
| `pop` | 250ms spring | Numero che cambia valore |
| `letterIn` | 450ms ease-out staggered | Title letter-by-letter su loading.html |
| `coreGlow` | 2.5s alternate | Logo sidebar — glow respirante |

---

## Slider (range input)

- Fill via CSS custom property `--fill` settato da JS `updateFill(el)`
- Background: gradient da `--c-cyan` a `rgba(255,255,255,.10)` al valore corrente
- Thumb: 16px, cyan, `box-shadow` glow, `scale(1.25)` on hover, `scale(.88)` active
- Nessun `-webkit-slider-runnable-track` override (lascia le ombre al CSS)

```js
function updateFill(el) {
    const min = parseFloat(el.min)||0, max = parseFloat(el.max)||100;
    el.style.setProperty('--fill',
        ((parseFloat(el.value)-min)/(max-min)*100).toFixed(1)+'%');
}
```

Inizializzazione: `setTimeout(() => document.querySelectorAll('input[type=range]').forEach(updateFill), 450)`

---

## Toggle glass

Classi: `.glass-toggle-container / .glass-toggle-input / .glass-toggle-track / .glass-toggle-thumb / .glass-toggle-label`

- Off: track traslucido, thumb bianco
- On: track cyan `rgba(20,245,255,.18)`, thumb cyan, glow `16px`, thumb `left:26px`
- Transition: `.35s cubic-bezier(.34,1.56,.64,1)` (spring) sul thumb

---

## Sidebar

- Width: **72px**
- Background: `rgba(1,7,14,.97)`, border-right `rgba(20,245,255,.10)`
- Logo: cerchio 38px con sonar rings animati (`sonarRing` 3s, 2 rings offset 1s)
- Active indicator: `div` assoluto left-0, `2.5px`, `background:--c-cyan`, `box-shadow:glow`
- Nav items: icon 20px + label 8px uppercase; hover: `rgba(20,245,255,.65)`

---

## Background animato

Struttura HTML in ogni pagina:
```html
<div class="ds-bg">
    <div class="ds-bg-glow"></div>
    <div class="ds-scan"></div>
    <div class="ds-scan"></div>  <!-- delay 5s -->
</div>
```

- `ds-bg-glow`: 3 radial-gradient statici (cyan left, cyan right, deep blue bottom)
- `ds-scan`: linea orizzontale 1px che scorre dall'alto in basso ogni 10s

---

## File CSS

`web/css/design-system.css` — Carica **dopo** `tailwind.min.css`.  
Contiene backward-compat per: `.sci-fi-border`, `.carbon-pattern`, `.glass-toggle-*`,  
`.nav-dot-active`, `.badge-*`, `.btn`, `.btn-primary`, `.btn-secondary`, `.field-label`,  
`.dot-ok/.dot-err/.dot-nul`, `.has-topology/.no-topology`, `.device-card`

---

## Pagine

| File | Nota |
|---|---|
| `loading.html` | Standalone — no tailwind, no design-system.css (self-contained per velocità) |
| `index.html` | Dashboard principale con grid 4col + grid 330px/1fr |
| `devices.html` | Lista device con flash animato |
| `settings.html` | Form connessione OpenRGB + web port + about |
| `topology-editor.html` | **Non modificato** — canvas editor autocontenuto, rischio rottura troppo alto |
| `js/navigation.js` | Sidebar 72px con sonar rings dinamici in JS |

---

## Pattern aggiunti in v1.1.0

- **Stato Status a 4 livelli** (`index.html` + `ambilight.js:_statusKind`): `INACTIVE` (grigio) · `ACTIVE` (ciano) · `NO ZONES` (ambra `#fbbf24`) · `NO DEVICES` (rosso `#f87171`). "ACTIVE" solo se almeno una zona riceve colori. Un hint con link d'azione sta sotto il titolo.
- **Checklist "Getting started"** (`.checklist`): 3 passi con spunta, nascosta quando completa o chiusa (`localStorage edambi.checklistDismissed`). Un punto ambra (`.nav-hint`) sulla sidebar indica la prossima azione.
- **Barra preset** (`.preset-bar`, `.preset-chip.active`): Balanced / Cinema / Gaming / Calm + Reset + Advanced + Live preview. `Custom` compare quando i valori non corrispondono a nessun preset. I default stanno in `DEFAULT_CFG` (`ambilight.js`).
- **Banner di connessione persa** (`#conn-banner`, 3 poll falliti) e `apiOk(res)` / evento `api-error` in `common.js`. Ogni chiamata che modifica stato deve controllare `apiOk` e mostrare un toast d'errore.
- **`confirmDialog(msg, okLabel, {danger})`** in `common.js` sostituisce `window.confirm` (Esc annulla, Invio conferma).
- **Blocco Advanced** del Topology Editor: classe `.adv-only` visibile solo con `body.adv-open` (`localStorage edambi.topoAdvanced`). Dirty state dell'editor: confronto snapshot (`markTopologySaved`, `isTopologyDirty`) + `beforeunload`. Nota: `topology-editor.html` ora è stato modificato in modo additivo (nessun cambio al modello dati).
- **Testo**: minimo 11–12px; `--c-text-ghost/dim/mid` portati a .50/.60/.74 per contrasto ≥ 4.5:1. `prefers-reduced-motion` disattiva animazioni e overlay (`design-system.css`, in fondo).
- **Lingua UI**: solo inglese.
