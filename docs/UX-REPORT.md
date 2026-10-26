# EDAmbilight — Report di analisi UX (punto di vista dell'utente medio)

Data: 2026-10-26 · Versione analizzata: v1.0.9 (main)

**Metodo.** Ho letto il codice di tutte le pagine (`loading`, `index`, `devices`, `settings`, `help`, `topology-editor`, `navigation.js`, `ambilight.js`, `common.js`) e il README. Ho reso la dashboard in un browser a 1280×720 e 1024×600, senza backend collegato. **Non ho potuto provare** l'app con OpenRGB e LED reali, quindi flusso di cattura, topology editor interattivo e pagina Preview sono valutati solo da codice e screenshot esistenti. Il giudizio sulla topologia è quindi meno solido del resto.

**Profilo utente assunto.** Un appassionato di PC gaming/RGB, già con OpenRGB installato, che non è uno sviluppatore. Non conosce EMA, scene-cut, DXGI/WGC, né i concetti di "topologia" e "zona".

---

## 1. Sintesi

| Area | Voto | Commento breve |
|---|---|---|
| Primo avvio / onboarding | 7/10 | Splash con diagnosi OpenRGB e pagina Help al primo lancio: ottimo. Ma il percorso reale (topologia → device → enable) è più lungo e fragile di quanto sembri. |
| Dashboard (Control) | 7/10 | Estetica coerente, tooltip utili, pannelli "Not used" intelligenti. Penalizzata da gergo, layout che non scala e feedback di stato debole. |
| Devices | 6/10 | Semplice e chiara, ma duplica la Control con un linguaggio diverso e ha rollback d'errore morto. |
| Settings | 5/10 | Pulita, ma mancano opzioni documentate (percorso OpenRGB, autostart) e il riavvio non è gestibile dall'UI. |
| Topology Editor | 4/10 | È il passaggio obbligatorio e il più ostico: gergo da editor 3D, voci irrilevanti per l'ambilight, lingue miste. |
| Coerenza e rifinitura | 6/10 | Design system riuscito, ma lingua mista, versione hardcoded, screenshot del README datati. |

**Giudizio complessivo.** L'interfaccia è *bella e professionale*, e la cura per i dettagli (tooltip con effetto "alza/abbassa", pannelli disattivati, splash con diagnosi) è sopra la media dei progetti hobbistici. Il vero punto debole non è l'aspetto ma il **percorso verso il primo risultato funzionante**: per vedere i LED reagire l'utente deve passare dal Topology Editor, che è il pezzo meno adatto a un non esperto.

---

## 2. Cosa funziona bene

1. **Splash con diagnosi (`loading.html`).** Distingue 7 stati OpenRGB (non installato, server spento, UAC negato, timeout, remoto, ecc.) con titolo, dettaglio e azioni (*Download*, *Retry*, *Continue without LEDs*). Rarissimo e prezioso: trasforma un errore criptico in un'azione.
2. **Onboarding al primo avvio.** Se `help_seen` è falso si apre `help.html?first=1` con 4 passi e CTA "Start: open Topology". Il Help è sempre raggiungibile dalla sidebar.
3. **Tooltip informativi "i".** Ogni pannello spiega cosa fa e cosa succede a salire/scendere (`Depth ▲ / ▼`). Traduce parametri tecnici in effetti percepibili. Funziona anche da tastiera (focus).
4. **Pannelli "Not used".** Se l'algoritmo scelto non usa un gruppo di slider, questo si attenua e si disabilita con badge. Riduce molto il carico cognitivo e previene la domanda "perché muovo questo e non cambia nulla?".
5. **Modifiche live, niente "Applica".** Gli slider agiscono subito sui LED: feedback immediato, modello mentale semplice.
6. **Hint sotto gli slider** (`0.05 = smooth · 0.95 = instant`, `1.0 = none · 2.5 = max vivid`) danno i limiti con parole comuni.
7. **Etichette chiare in alcuni punti chiave:** "Capture Engine" con descrizione d'uso ("Chrome-safe", "Exclusive fullscreen"), "keyboards excluded" accanto a Devices, "Active: …" che mostra il motore realmente in uso.
8. **Black bar detect con stato**: mostra "Content area: W×H px — bars cropped", feedback concreto che la funzione sta lavorando.
9. **Coerenza visiva**: palette ciano su scuro, sidebar a icone con etichetta, header uniforme, animazioni d'ingresso misurate, font self-hosted (funziona offline).
10. **Pulsante "Flash" / "Flash All"** per identificare fisicamente un dispositivo: utile e immediato.
11. **Impostazioni di connessione con "Test"** separato da "Save & Reconnect", con stato (pallino + testo).
12. **Tray e privacy**: l'app resta in tray, nessuna rete; dichiarato e rassicurante.

---

## 3. Problemi e debolezze

Gravità: 🔴 alta (blocca o confonde il percorso principale) · 🟠 media · 🟡 bassa.

### 3.1 Percorso di primo successo

🔴 **Il primo risultato richiede il Topology Editor.** Il Help dice: crea zone chiamate `MonitorTop/Right/Bottom/Left`, "qualsiasi altro nome è ignorato". Un utente medio non sa cosa siano le zone né che deve crearle in OpenRGB (*Resizable zones & segments*), un'operazione già complessa. Se i nomi non coincidono, **non succede nulla e nessuna schermata lo dice chiaramente.** È il principale rischio di abbandono.

🔴 **Nessun "stato di salute" sulla Control.** Con tutto spento o non configurato, la dashboard mostra pallino grigio e "—". Con `Enable` attivo ma nessun device abilitato/mappato, `updateStatusBadge` mostra comunque **ACTIVE** (usa solo `s.enabled && s.running`). L'utente vede "ACTIVE", l'anello che pulsa… e i LED fermi. Manca un messaggio tipo "Attivo, ma nessun dispositivo riceve colori".

🟠 **I device partono tutti disabilitati** (`devCfg.enabled ?? false`) e, senza topologia, il pulsante power è `disabled` con un testo minuscolo ("Configura le zone nel Topology Editor…"). Non c'è un link/azione diretta sul device stesso.

🟠 **Ordine dei passi non guidato.** La nota in fondo alla Control ("Configure zones in the Topology Editor first") è a 11px, grigio quasi invisibile, in basso. Il passo più importante è il meno evidente.

### 3.2 Dashboard (Control)

🔴 **Layout non scala sotto ~1100×700.** `main` ha `overflow:hidden` e la griglia usa altezze fisse: a 1024×600 il pannello **Devices viene tagliato e quasi sparisce** (se ne intravede solo il bordo), e non c'è scroll. Su laptop piccoli o finestre non massimizzate la sezione più importante diventa irraggiungibile. Il `Capture Engine` a 1024 tronca anche il testo del select ("Auto (WGC → DXGI →").

🟠 **Gergo tecnico esposto.** EMA Alpha, Scene-cut, Percentile 80%, Dominant, RGB mean, WGC/DXGI/mss, "Depth % of screen minor side". I tooltip aiutano, ma restano **9 slider/opzioni** presentati allo stesso livello. Manca un livello "semplice".
- Nessun **preset** ("Film", "Gaming", "Calmo", "Vivace").
- Nessun pulsante **"Ripristina predefiniti"**: un utente che sballa i parametri non ha un modo semplice di tornare indietro.
- Nessuna indicazione del valore "consigliato" sugli slider.

🟠 **Pannello Status sprecato.** Occupa una colonna alta con una grande area quasi vuota (anello decorativo) mentre le informazioni utili (FPS reali, motore attivo, device attivi, errori) sono sparse altrove. Un riepilogo ("3 dispositivi · 24 zone · 14 fps · WGC") sarebbe più utile dell'animazione.

🟠 **Badge FPS poco leggibile e ambiguo.** Testo 11px bianco "— live" / "14 fps" piccolo e distante dal valore target "15". Non è chiaro che sia il valore *reale*; se è molto inferiore al target (carico) non c'è alcun avviso.

🟠 **Il tooltip è solo hover/focus ma l'Help dice "Click the i".** L'icona è 14px con `cursor:help`: bersaglio piccolo; con mouse funziona, ma l'istruzione è inesatta e su touch/tablet non funzionerebbe.

🟡 **Testi minuscoli e a basso contrasto.** Molti hint e label sono 9–11px con `--c-text-ghost` (bianco ~20–30% su nero). Es.: sottotitolo header 8px, "Control Panel", "Color sampling strategy", hint degli slider, nota Devices. Fuori da WCAG AA, faticosi per chi ha vista non perfetta o monitor luminosi.

🟡 **Etichetta "Algorithm" vs "Strategy"** (README parla di Strategy, UI di Algorithm; "Color sampling strategy" come sottotitolo). Lieve incoerenza. Le opzioni "Adaptive + EMA (best)" vs "Percentile + EMA" non spiegano a colpo d'occhio la differenza senza aprire il tooltip.

🟡 **Titolo "AMBILIGHT / Control Panel"** nell'header: il nome del prodotto (EDAmbilight) non compare nella pagina principale.

🟡 **Aggiornamenti senza debounce.** Ogni evento `input` dello slider chiama il backend: durante un trascinamento partono decine di chiamate. Sulla macchina può non vedersi, ma è un potenziale lag.

### 3.3 Feedback ed errori

🔴 **Errori silenziosi.** `api()` non lancia mai: in caso di errore restituisce `{success:false,…}`. Chi chiama (es. `liveUpdate`, `toggleDevice` su Control) **non controlla il risultato**. Se il backend si ferma, l'UI continua a sembrare viva e a "salvare" modifiche inesistenti. Non c'è un banner "Connessione persa con l'app".

🟠 **Rollback morto su Devices.** `toggleDevice` in `devices.html` ha un `try/catch` con ripristino dell'interruttore, ma `api()` non lancia mai eccezioni → il ramo `catch` non scatta, l'interruttore resta nello stato sbagliato se la chiamata fallisce.

🟠 **Salvataggi non verificati in Settings.** `saveAndReconnect`/`saveWebPort` mostrano "saved" senza controllare l'esito di `save_settings`.

🟠 **Topology Editor senza indicazione di modifiche non salvate.** Non c'è `beforeunload` né stato "modificato": un utente che sposta zone e naviga via perde il lavoro senza avviso. "Save Topology" ha lo stesso aspetto prima e dopo.

🟡 **`confirm()` nativo per "Reset All"**: stona con il resto (toast e modali personalizzati).

🟡 **Toast in alto a destra con pulsante × minuscolo**; per le azioni non critiche (device enabled/disabled) un toast per ogni click può diventare rumore.

### 3.4 Devices

🟠 **Doppia interfaccia per la stessa azione, linguaggio diverso.** Abilitare un device si fa sia in Control (pulsante power + zone) sia in Devices (interruttore). Stili diversi (power button vs toggle), testi diversi e *comportamento diverso* (in Control il pulsante è disabilitato senza topologia; in Devices l'interruttore è sempre attivo). L'utente non capisce quale sia la "fonte di verità". La README dice che si abilitano le zone nella pagina Devices, mentre il Help dice di farlo in Control.

🟠 **"Edit topology" solo per device `linear`.** Un device `single` o `matrix` senza topologia non offre alcun percorso per risolvere; il link porta comunque alla pagina generica senza selezionare il device.

🟠 **"Flash All" sequenziale** (200ms tra device + durata del flash di ciascuno): con molti device richiede molti secondi, senza indicazione di avanzamento né modo di fermarlo.

🟡 **Contatore "With Topology"** grigio e senza spiegazione; "Actions / Flash to identify" occupa un'intera card per un solo pulsante.

🟡 **Lista vuota**: "No devices found. Make sure OpenRGB is running" è corretto ma senza pulsante *Riprova/Rileggi* né link a Settings.

### 3.5 Settings

🟠 **Mancano impostazioni documentate.** Il README descrive `openrgb_path` e `openrgb_autostart`, e la schermata di splash/Help suggerisce "controlla il percorso OpenRGB in Settings", ma la pagina Settings ha solo host, porta OpenRGB e porta web. L'utente è mandato a una schermata che non contiene ciò che gli serve (deve editare JSON a mano).

🟠 **Porta web: "riavvia l'applicazione" senza poterlo fare dall'UI** (nessun pulsante *Riavvia*, né *Esci*). Non c'è nemmeno un modo di chiudere l'app dall'interfaccia: solo tray.

🟡 **About obsoleto**: "v1.0" fisso (anche nella sidebar `v1.0` in `navigation.js`) mentre la release è 1.0.9. Mancano link a GitHub/Changelog, "apri cartella log", verifica aggiornamenti.

🟡 **Nessuna impostazione di avvio con Windows, minimizza in tray, lingua.**

### 3.6 Topology Editor (il punto più critico)

*Valutato da HTML/JS e screenshot, non provato dal vivo.*

🔴 **Gergo e concetti da editor spaziale**: "World units", "BBox / VBBox", "Effect Center (%)", "Quick presets", "Calibration (ring spacing in u)", "Grid size", "Snap to grid", "Physical length (cm)", "Spacing". Per l'ambilight sul bordo schermo la maggior parte di queste voci è irrilevante (Effect Center e "radial effects" sembrano residui di un altro progetto) e **distrae dal compito reale**: assegnare una zona a un lato dello schermo.

🔴 **Il modello mentale non coincide con il Help.** Il Help dice "assegna la zona a un lato (Monitor Top/Right/…)"; l'editor invece mostra una tela libera con posizioni X/Y e rotazioni. Il lato si deduce dal *nome* della zona, non da un controllo "Lato dello schermo". Un utente si aspetterebbe un menu "Lato: Alto / Destra / Basso / Sinistra" e un'anteprima dello schermo con i LED sui bordi.

🟠 **Lingue miste**: preset "Centro / Alto / Basso / Sinistra / Destra" (italiano) in un'interfaccia inglese, `lang="it"` sul tag html, `window.i18n` finto con `getCurrentLanguage: 'en'`.

🟠 **Troppi pulsanti allo stesso livello nella barra comandi** (Reload, Auto Layout, Reset All, Fit View, Calibration, spaziatura, Save). "Reset All" (distruttivo) è accanto a "Fit View" (innocuo) e vicino a Save, con stesso peso visivo. Solo Save è parzialmente evidenziato.

🟠 **Canvas ridotto su schermi piccoli**: due colonne laterali fisse da 252px + sidebar 80px lasciano a 1024px di larghezza ~400px alla tela.

🟠 **Scorciatoie e navigazione nascoste**: `[R]`, `[F]`, pan con tasto centrale, zoom con scroll sono in una riga da 11px in basso. Pan col tasto centrale è difficile su touchpad.

🟡 **Stato iniziale vuoto**: "No devices configured. Enable devices in Device Management" — ma la pagina si chiama *Devices*, non "Device Management", e in Devices non si "configurano" device ma si abilitano. Messaggio fuorviante e circolare.

🟡 **Stato "Zone overlaps detected!"** senza dire quali zone o come risolvere.

### 3.7 Navigazione e struttura

🟠 **Ordine della sidebar non rispecchia il flusso**: Control → Topology → Devices → Settings → Preview → Help. Il flusso reale è Help → Devices → Topology → Control. L'utente nuovo vede la dashboard piena di parametri come pagina "casa" invece di una vista guidata.

🟠 **Funzioni sovrapposte tra Control, Devices e Topology** (abilitare device, vedere zone, mappare zone): tre luoghi per un unico flusso mentale ("configurare i miei LED").

🟡 **Icone**: `memory` (chip) per Devices e `tune` per Settings sono accettabili, ma `settings_brightness` per Control e `auto_awesome` per Preview richiedono l'etichetta; le etichette a 10px uppercase sono piccole.

🟡 **Preview** è una pagina da ~1900 righe (WebGL) con funzione utilissima per capire l'effetto, ma nascosta in quinta posizione e non collegata dal Control ("vedi anteprima").

### 3.8 Rifinitura e documentazione

🟡 **Screenshot del README datati**: la dashboard mostrata non ha l'icona Help, i tooltip "i", "Min brightness", né i testi attuali. Il badge versione README dice `1.0.0`.

🟡 **Lingua mista nell'UI**: `Disabilita/Abilita per ambilight` (tooltip power), "Configura le zone nel Topology Editor…" (Control), preset italiani nell'editor; il resto inglese. Una scelta di lingua (o un vero i18n IT/EN) è consigliabile, soprattutto perché l'utente target è italiano.

🟡 **Animazioni persistenti** (anelli sonar sempre attivi nella sidebar, scanline, glow del pannello, grain) sono belle ma *continue*: aumentano il consumo di GPU/CPU di un'app che dovrebbe stare in background accanto a giochi/video. Manca un rispetto per `prefers-reduced-motion`.

🟡 **Accessibilità tastiera/lettori schermo**: slider senza `aria-label` associati alle label testuali; pallino di stato solo colore (nessun testo alternativo oltre ACTIVE/INACTIVE); interruttori in Devices senza etichetta testuale visibile.

---

## 4. Il viaggio dell'utente medio (narrazione)

1. Scarica lo zip, SmartScreen avverte (documentato, ok).
2. Lancia `EDAmbilight.exe`: splash elegante. Se OpenRGB c'è, parte; se no, riceve una diagnosi **chiara** → *punto forte*.
3. Si apre la pagina Help: legge 4 passi. Passo 2 ("Map your strip to the screen… zone named MonitorTop…") **lo blocca**: non sa cosa siano le zone, deve creare segmenti in OpenRGB.
4. Va nel Topology Editor: vede tela vuota o zone, voci come BBox/Effect Center/Calibration. Incerto su cosa fare e se "Save" sia necessario.
5. Torna in Control, trova "No devices available / no topology" oppure device spenti. Abilita un device, attiva *Enable*: vede **ACTIVE** e l'anello pulsare.
6. Se i LED non reagiscono (nomi zona errati, device senza topologia, HDCP) **l'interfaccia non gli dice perché**.
7. Se invece funziona, si diverte con gli slider: qui l'esperienza è **ottima** (live, tooltip, pannelli attenuati).

Il valore dell'app sta nel passo 7; l'attrito sta nei passi 3–6.

---

## 5. Raccomandazioni prioritarie

### Priorità 1 — Sbloccare il primo successo
1. **Checklist "Per iniziare" nella Control** (3 voci con spunta): *OpenRGB connesso · almeno un device con zone mappate · Enable attivo*, con pulsanti diretti ai passaggi mancanti. Sostituisce la nota grigia in fondo.
2. **Stato onesto**: mostrare "ACTIVE" solo se almeno un device/zona riceve colori; altrimenti "Attivo — nessun dispositivo collegato" con link a Devices.
3. **Selettore "Lato schermo" nelle zone** del Topology Editor (Alto/Destra/Basso/Sinistra/Ignora) al posto della deduzione dal nome, più auto-assegnazione suggerita ("MonitorTop trovato → Alto").
4. **Modalità semplice** per il Topology Editor: nascondere Effect Center, Calibration, BBox, grid, spacing, physical length dietro "Avanzate".

### Priorità 2 — Robustezza e feedback
5. **Banner di connessione persa** quando `api()` restituisce `success:false`; fare in modo che `liveUpdate`/`toggleDevice` verifichino l'esito.
6. Correggere il **rollback morto** in `devices.html` (controllare `result.success`, non l'eccezione).
7. **Indicatore modifiche non salvate** + avviso `beforeunload` nel Topology Editor; sostituire `confirm()` con un modale coerente.
8. **Layout responsive**: permettere scroll verticale del contenuto principale e ridurre le altezze minime, in modo che Devices non venga mai tagliato (< 1100×700).

### Priorità 3 — Semplificare i controlli
9. **Preset** (Film / Gaming / Calmo / Vivace) e **"Ripristina predefiniti"**; mantenere gli slider come "Avanzate" ripiegabili.
10. **Unificare l'abilitazione dei device** in un solo punto (preferibilmente Control) o usare lo stesso componente e le stesse regole in entrambe le pagine; Devices diventa diagnostica (flash, info).
11. Aggiungere a Settings **percorso OpenRGB, autostart, avvio con Windows, riavvia/esci, apri cartella log**.
12. **Debounce** degli slider (es. 60–100 ms) e mostrare gli FPS reali in evidenza con avviso quando restano molto sotto il target.

### Priorità 4 — Rifinitura
13. Scegliere **una lingua** (o implementare IT/EN) e rimuovere i residui misti; correggere `lang`.
14. **Leggere la versione dal backend** (sidebar e About) invece di `v1.0` fisso; aggiornare badge e screenshot del README.
15. **Contrasto e dimensioni**: portare i testi di aiuto ad almeno 12px e contrasto ≥ 4.5:1; supportare `prefers-reduced-motion` e ridurre le animazioni continue in background.
16. Riordinare la sidebar secondo il flusso (o evidenziare la prossima azione consigliata) e collegare Preview dalla Control ("Vedi anteprima").
17. Correggere il testo del Help ("Click the i" → "Passa il mouse sulla i") e il messaggio "Enable devices in Device Management".

---

## 6. Rischi / limiti dell'analisi

- Non ho testato interazioni con LED reali, hardware multipli, né il comportamento dell'editor con zone vere. Alcune critiche al Topology Editor (modello mentale, dimensioni canvas) derivano da codice/screenshot e vanno verificate dal vivo.
- Gli screenshot in `docs/` sono precedenti alle ultime versioni; le valutazioni sul layout si basano sul rendering statico odierno senza dati backend (nessun device in lista).
- Il profilo utente è un'ipotesi; per validarlo servirebbero 3–5 prove con utenti reali (task: "fai reagire i LED in 5 minuti").

## 7. File correlati

- `web/index.html`, `web/js/ambilight.js` — dashboard, stato e device
- `web/devices.html` — duplicazione dell'abilitazione e rollback morto
- `web/settings.html` — impostazioni mancanti
- `web/topology-editor.html`, `web/js/topology-editor.js` — gergo e salvataggio
- `web/js/navigation.js` — versione hardcoded, ordine voci
- `web/js/common.js` — `api()` che non propaga errori
