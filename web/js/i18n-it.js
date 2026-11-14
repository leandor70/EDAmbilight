'use strict';
/* Italian dictionary for i18n.js. Keys are the English text exactly as it appears
   in the pages, the scripts and the backend messages (whitespace is collapsed before
   the lookup). One add() per area; a key defined twice: the last one wins. */
// Control + shared scripts
EDI18n.add('it', {
    strings: {
        // ── Sidebar (navigation.js) ──
        'Control': 'Controllo',
        'Topology': 'Topologia',
        'Devices': 'Dispositivi',
        'Settings': 'Impostazioni',
        'Preview': 'Anteprima',
        'Help': 'Guida',
        'Switch to light theme': 'Passa al tema chiaro',
        'Switch to dark theme': 'Passa al tema scuro',

        // ── Hardware notices / update toast (navigation.js) ──
        'Hardware changed since the last start': 'Hardware cambiato dall\'ultimo avvio',
        'Notices': 'Avvisi',
        'Dismiss': 'Chiudi',
        'What\'s new / download': 'Novità / download',
        'Skip this version': 'Salta questa versione',
        'No notice for this version again; a newer one will be shown': 'Nessun altro avviso per questa versione; una più recente verrà segnalata',
        'Close (shown again at the next start)': 'Chiudi (riappare al prossimo avvio)',
        'Close': 'Chiudi',

        // ── common.js ──
        'Cancel': 'Annulla',
        'Confirm': 'Conferma',
        'Eel not initialized': 'Eel non inizializzato',
        'Connection error': 'Errore di connessione',

        // ── Control: page / header ──
        'EDAmbilight — Control': 'EDAmbilight — Controllo',
        'Control Panel': 'Pannello di controllo',

        // ── Control: Status card ──
        'Status': 'Stato',
        'Shows whether the Ambilight service is running and sending colors to your devices.': 'Indica se il servizio Ambilight è in esecuzione e sta inviando i colori ai tuoi dispositivi.',
        'Enable': 'Attiva',
        'Turns the effect on or off. When off, devices return to their normal lighting.': 'Accende o spegne l\'effetto. Da spento, i dispositivi tornano alla loro illuminazione normale.',
        'Ambilight service': 'Servizio Ambilight',
        'INACTIVE': 'INATTIVO',
        'ACTIVE': 'ATTIVO',
        'NO ZONES': 'NESSUNA ZONA',
        'STANDBY': 'STANDBY',
        'NO DEVICES': 'NESSUN DISPOSITIVO',
        // status hint (innerHTML split by links: translated piece by piece)
        'OpenRGB reports no devices. Make sure OpenRGB is running with the SDK server on — see': 'OpenRGB non segnala dispositivi. Assicurati che OpenRGB sia avviato con il server SDK attivo — vedi',
        '. On Windows, memory and motherboards also need the PawnIO driver (pawnio.eu).': '. Su Windows, memorie e schede madri richiedono anche il driver PawnIO (pawnio.eu).',
        'Running, but no device receives colors. Switch on a device in the list below.': 'In esecuzione, ma nessun dispositivo riceve colori. Accendi un dispositivo nell\'elenco qui sotto.',
        'Running, but no zone is mapped to the screen. Map them in the': 'In esecuzione, ma nessuna zona è mappata sullo schermo. Mappale nel',
        'Topology Editor': 'Editor topologia',
        'The screen is not providing frames (display asleep or locked). LEDs follow the Screen standby setting and resume by themselves.': 'Lo schermo non fornisce immagini (monitor in sospensione o bloccato). I LED seguono l\'impostazione Standby schermo e ripartono da soli.',
        'Connection to EDAmbilight lost — changes are not being applied. Reconnecting…': 'Connessione a EDAmbilight persa — le modifiche non vengono applicate. Riconnessione…',

        // ── Control: FPS ──
        'FPS Target': 'FPS obiettivo',
        'How many times per second the screen is captured and the LEDs are updated.': 'Quante volte al secondo lo schermo viene catturato e i LED aggiornati.',
        'Higher': 'Più alto',
        'Smoother and more reactive LEDs, but more CPU/GPU load.': 'LED più fluidi e reattivi, ma più carico su CPU/GPU.',
        'Lower': 'Più basso',
        'Lighter on the system, but colors follow the image with visible lag or steps.': 'Più leggero per il sistema, ma i colori seguono l\'immagine con ritardo o scatti visibili.',
        'The badge shows the real rate being reached.': 'Il valore in alto mostra la frequenza realmente raggiunta.',
        'Frame rate actually reached': 'Frequenza effettivamente raggiunta',
        '— live': '— live',

        // ── Control: Capture engine ──
        'Capture Engine': 'Motore di cattura',
        'The method used to grab the screen image.': 'Il metodo usato per catturare l\'immagine dello schermo.',
        'Tries WGC, then DXGI, then mss. Best choice for most setups.': 'Prova WGC, poi DXGI, poi mss. La scelta migliore nella maggior parte dei casi.',
        'Works with browsers and windowed apps.': 'Funziona con browser e app in finestra.',
        'Needed for exclusive-fullscreen games.': 'Necessario per i giochi a schermo intero esclusivo.',
        'Slow CPU-only fallback, use it only if the others fail.': 'Ripiego lento solo CPU: usalo solo se gli altri non funzionano.',
        'Protected (HDCP) content may appear black with any engine.': 'I contenuti protetti (HDCP) possono apparire neri con qualsiasi motore.',
        'Auto (recommended)': 'Auto (consigliato)',
        'WGC — windows, browsers': 'WGC — finestre, browser',
        'DXGI — fullscreen games': 'DXGI — giochi a schermo intero',
        'mss — CPU fallback': 'mss — ripiego CPU',
        'Active:': 'Attivo:',

        // ── Control: Screen standby ──
        'Screen standby': 'Standby schermo',
        'What the LEDs do while the screen gives no image (display asleep, lock screen). Normal ambilight resumes by itself.': 'Cosa fanno i LED mentre lo schermo non dà immagine (monitor in sospensione, schermata di blocco). L\'ambilight normale riprende da solo.',
        'Hold': 'Mantieni',
        'Keep the last colors, as before.': 'Mantiene gli ultimi colori, come prima.',
        'Slow fade': 'Dissolvenza lenta',
        'Fades to black over 20 s.': 'Sfuma al nero in 20 s.',
        'Dim glow': 'Bagliore tenue',
        'Fades to a faint glow of the last colors.': 'Sfuma a un tenue bagliore degli ultimi colori.',
        'Pulse': 'Pulsazione',
        'Last colors breathe slowly.': 'Gli ultimi colori pulsano lentamente.',
        'Rotating colors': 'Colori rotanti',
        'Rainbow drifting along the LEDs.': 'Arcobaleno che scorre lungo i LED.',
        'Aurora': 'Aurora',
        'Slow cyan, green and violet waves.': 'Lente onde ciano, verdi e viola.',
        'Ember': 'Brace',
        'Warm flickering orange.': 'Arancione caldo e tremolante.',
        'Lights off': 'Luci spente',
        'Black immediately.': 'Nero subito.',
        'Hold last colors': 'Mantieni ultimi colori',
        'Slow fade to black': 'Dissolvenza lenta al nero',
        'Fade to dim glow': 'Sfuma a bagliore tenue',
        'Pulse (breathing)': 'Pulsazione (respiro)',
        'Ember glow': 'Bagliore di brace',
        'Play the selected effect on the LEDs now, as if the screen were asleep (stops by itself after 60 s)': 'Riproduce subito l\'effetto scelto sui LED, come se lo schermo fosse in sospensione (si ferma da solo dopo 60 s)',
        'Test effect': 'Prova effetto',
        'Stop test': 'Ferma prova',
        'Standby brightness': 'Luminosità standby',
        'Rotating colors, Aurora and Ember only': 'Solo Colori rotanti, Aurora e Brace',

        // ── Control: Algorithm ──
        'Algorithm': 'Algoritmo',
        'How each LED color is calculated from the screen edge. It decides which parameters below are active.': 'Come si calcola il colore di ogni LED dal bordo dello schermo. Decide quali parametri qui sotto sono attivi.',
        'Adaptive + EMA': 'Adattivo + EMA',
        'Auto sampling depth plus smoothing. Best overall.': 'Profondità di campionamento automatica più smussatura. Il migliore in generale.',
        'Adaptive depth': 'Profondità adattiva',
        'Auto depth, no smoothing: reacts instantly.': 'Profondità automatica, senza smussatura: reagisce all\'istante.',
        'Percentile + EMA': 'Percentile + EMA',
        'Fixed depth, bright-area color, smoothed.': 'Profondità fissa, colore delle zone chiare, smussato.',
        'Percentile 80%': 'Percentile 80%',
        'Mean of the brightest 20% of the area: vivid colors, stable.': 'Media del 20% più luminoso dell\'area: colori vivaci, stabili.',
        'Dominant color': 'Colore dominante',
        'Median color: ignores small bright details.': 'Colore mediano: ignora i piccoli dettagli luminosi.',
        'RGB mean': 'Media RGB',
        'Plain average: calm but washed-out colors.': 'Media semplice: colori calmi ma slavati.',
        'Black bar detect': 'Rileva bande nere',
        'Ignores black letterbox bars so colors match the actual picture.': 'Ignora le bande nere del letterbox, così i colori seguono l\'immagine reale.',
        'Adaptive + EMA (best)': 'Adattivo + EMA (migliore)',
        'Color sampling strategy': 'Strategia di campionamento del colore',

        // ── Control: Presets bar ──
        'Presets': 'Preset',
        'Balanced': 'Bilanciato',
        'Cinema': 'Cinema',
        'Gaming': 'Gaming',
        'Calm': 'Calmo',
        'Balanced: everyday use (the defaults). 15 fps, medium smoothing': 'Bilanciato: uso quotidiano (i valori predefiniti). 15 fps, smussatura media',
        'Cinema: films and series. 24 fps, soft smoothing, richer colors': 'Cinema: film e serie. 24 fps, smussatura morbida, colori più ricchi',
        'Gaming: action games, shooters, racing. 30 fps, follows the picture quickly': 'Gaming: giochi d\'azione, sparatutto, corse. 30 fps, segue l\'immagine rapidamente',
        'Calm: strategy and management games, desktop, reading. 15 fps, slow and steady changes': 'Calmo: strategici e gestionali, desktop, lettura. 15 fps, cambi lenti e costanti',
        'Custom': 'Personalizzato',
        'See the effect in the browser': 'Guarda l\'effetto nel browser',
        'Live preview': 'Anteprima live',
        'Restore the default values of all sliders': 'Ripristina i valori predefiniti di tutti i cursori',
        'Reset': 'Ripristina',
        'Advanced': 'Avanzate',
        'Defaults restored': 'Valori predefiniti ripristinati',

        // ── Control: Sampling area ──
        'Sampling Area': 'Area di campionamento',
        'How far from the screen edge pixels are read to compute each LED color. Used by fixed-depth algorithms.': 'Fino a che distanza dal bordo dello schermo si leggono i pixel per calcolare il colore di ogni LED. Usato dagli algoritmi a profondità fissa.',
        'Depth ▲': 'Profondità ▲',
        'Larger area: more averaged, calmer color that also reflects what is further from the edge.': 'Area più ampia: colore più mediato e calmo, che riflette anche ciò che è più lontano dal bordo.',
        'Depth ▼': 'Profondità ▼',
        'Thin strip: colors follow the exact edge, more precise but more flickery.': 'Striscia sottile: i colori seguono il bordo esatto, più precisi ma più tremolanti.',
        'Value is a % of the screen\'s shorter side.': 'Il valore è una % del lato corto dello schermo.',
        'Not used': 'Non usato',
        'Depth': 'Profondità',
        '% of screen minor side': '% del lato corto dello schermo',

        // ── Control: Adaptive area ──
        'Adaptive Area': 'Area adattiva',
        'The sampling depth changes automatically with the image content, always staying between these two limits.': 'La profondità di campionamento cambia da sola in base al contenuto dell\'immagine, restando sempre tra questi due limiti.',
        'Min depth ▲': 'Profondità min ▲',
        'The area never gets very thin: more stable, less edge precision.': 'L\'area non diventa mai molto sottile: più stabile, meno precisione sul bordo.',
        'Min depth ▼': 'Profondità min ▼',
        'Allows a very thin strip on busy or detailed edges.': 'Consente una striscia molto sottile sui bordi movimentati o ricchi di dettagli.',
        'Max depth ▲': 'Profondità max ▲',
        'The area can grow a lot on uniform edges: smoother, more averaged color.': 'L\'area può allargarsi molto sui bordi uniformi: colore più morbido e mediato.',
        'Max depth ▼': 'Profondità max ▼',
        'Caps the area: colors stay closer to the edge.': 'Limita l\'area: i colori restano più vicini al bordo.',
        'Max should stay above Min.': 'Max deve restare sopra Min.',
        'Min depth': 'Profondità min',
        'Max depth': 'Profondità max',

        // ── Control: Temporal smoothing ──
        'Temporal Smoothing': 'Smussatura temporale',
        'Blends each new frame with the previous ones to reduce flicker.': 'Fonde ogni nuovo fotogramma con i precedenti per ridurre lo sfarfallio.',
        'EMA Alpha ▲': 'EMA Alpha ▲',
        'LEDs follow the image faster, with more flicker (0.95 = almost instant).': 'I LED seguono l\'immagine più in fretta, con più sfarfallio (0.95 = quasi istantaneo).',
        'EMA Alpha ▼': 'EMA Alpha ▼',
        'Slower, softer color changes, with some delay (0.05 = very smooth).': 'Cambi di colore più lenti e morbidi, con un po\' di ritardo (0.05 = molto fluido).',
        'Scene-cut ▲': 'Cambio scena ▲',
        'Only very big color changes skip the smoothing: more fading between scenes.': 'Solo i cambi di colore molto grandi saltano la smussatura: più dissolvenza tra le scene.',
        'Scene-cut ▼': 'Cambio scena ▼',
        'Even small color changes make the LEDs jump instantly: less smoothing effect.': 'Anche piccoli cambi di colore fanno scattare subito i LED: meno effetto di smussatura.',
        'Scene-cut': 'Cambio scena',
        '0.05 = smooth · 0.95 = instant': '0.05 = fluido · 0.95 = istantaneo',
        'Instant jump above threshold': 'Salto immediato oltre la soglia',

        // ── Control: Output ──
        'Output': 'Uscita',
        'Final adjustment applied to the colors before they are sent to the devices.': 'Regolazione finale applicata ai colori prima di inviarli ai dispositivi.',
        'Saturation boost ▲': 'Aumento saturazione ▲',
        'More vivid, intense colors (2.5 = max).': 'Colori più vivaci e intensi (2.5 = max).',
        'Saturation boost ▼': 'Aumento saturazione ▼',
        'Paler colors, closer to the real picture (1.0 = no change, below 1.0 = desaturated).': 'Colori più pallidi, più vicini all\'immagine reale (1.0 = invariato, sotto 1.0 = desaturato).',
        'Min brightness ▲': 'Luminosità min ▲',
        'Dark colors are brightened to this level (hue kept), so LEDs over dim areas stay visible.': 'I colori scuri vengono schiariti fino a questo livello (tinta invariata), così i LED sulle zone scure restano visibili.',
        'Min brightness ▼': 'Luminosità min ▼',
        '0 = off: dark areas are shown as they are. Pure black always stays off.': '0 = disattivato: le zone scure restano come sono. Il nero puro resta sempre spento.',
        'Saturation boost': 'Aumento saturazione',
        'Min brightness': 'Luminosità min',
        '1.0 = none · 2.5 = max vivid': '1.0 = nessuno · 2.5 = massima vivacità',
        '0 = off · dark colors lifted to this level, pure black stays off': '0 = disattivato · colori scuri alzati a questo livello, il nero puro resta spento',

        // ── Control: Beat accent ──
        'Beat accent': 'Accento sul beat',
        'A short accent on the ambilight colors at every beat of the music playing on this PC.': 'Un breve accento sui colori dell\'ambilight a ogni battito della musica in riproduzione su questo PC.',
        'Mode': 'Modalità',
        'Multiplicative keeps the hue and never lights a black LED. Additive adds the flash color, so dark LEDs light up too. Mixed does both: Light dark LEDs sets how much is additive.': 'Moltiplicativo mantiene la tinta e non accende mai un LED nero. Additivo aggiunge il colore del flash, così si accendono anche i LED scuri. Misto fa entrambe le cose: Accendi LED scuri decide quanto è additivo.',
        'Intensity': 'Intensità',
        'How big the jump is at each beat.': 'Quanto è grande il salto a ogni beat.',
        'Duration': 'Durata',
        'How long the flash takes to fade.': 'Quanto impiega il flash a svanire.',
        'Color shift': 'Cambio tinta',
        'Rotates the hue at the beat. Pulse comes back at once; Step adds one notch per beat and fades back slowly.': 'Ruota la tinta sul beat. Impulso torna subito indietro; Passo aggiunge una tacca per beat e rientra lentamente.',
        'Safety': 'Sicurezza',
        'Strong beats only skips the weak beats, so the accent follows the main hits instead of every note. Max flashes/s skips beats that come too fast, Boost cap limits the jump, Attack softens the rise. Set Max flashes/s to off to experiment.': 'Solo beat forti salta i battiti deboli, così l\'accento segue i colpi principali invece di ogni nota. Max flash/s salta i beat troppo ravvicinati, Limite boost limita il salto, Attacco ammorbidisce la salita. Imposta Max flash/s su off per sperimentare.',
        'Test accent': 'Prova accento',
        'Fires one beat without any audio, to tune the look.': 'Genera un beat senza audio, per regolare l\'aspetto.',
        'Listen to audio': 'Ascolta l\'audio',
        'Soft': 'Morbido',
        'Punchy': 'Incisivo',
        'Club': 'Club',
        'Fire one beat with these settings, without audio': 'Genera un beat con queste impostazioni, senza audio',
        'Flash': 'Flash',
        'Flash mode': 'Modalità flash',
        'Multiplicative (keeps hue)': 'Moltiplicativo (mantiene la tinta)',
        'Additive (lights dark LEDs)': 'Additivo (accende i LED scuri)',
        'Mixed': 'Misto',
        'Light dark LEDs': 'Accendi LED scuri',
        '0 = only brightens · 100 = fully additive': '0 = schiarisce soltanto · 100 = del tutto additivo',
        'Flash color': 'Colore flash',
        'Color shift mode': 'Modalità cambio tinta',
        'Pulse (comes back at once)': 'Impulso (torna subito)',
        'Step (one notch per beat)': 'Passo (una tacca per beat)',
        'Amount': 'Quantità',
        'Hue rotation applied at the beat': 'Rotazione della tinta applicata sul beat',
        'Return time': 'Tempo di ritorno',
        'How slowly Step goes back to the real colors': 'Con che lentezza Passo torna ai colori reali',
        'Strong beats only': 'Solo beat forti',
        '0 = every beat · 100 = only the strongest': '0 = ogni beat · 100 = solo i più forti',
        'Max flashes/s': 'Max flash/s',
        'Faster beats are skipped · off = no limit': 'I beat più rapidi vengono saltati · off = nessun limite',
        'Boost cap': 'Limite boost',
        'Limits the jump whatever the intensity': 'Limita il salto qualunque sia l\'intensità',
        'Attack': 'Attacco',
        '0 = instant · higher = softer rise': '0 = istantaneo · più alto = salita più morbida',
        'Audio input': 'Ingresso audio',
        'Audio device': 'Dispositivo audio',
        'Default output (what you hear)': 'Uscita predefinita (ciò che senti)',
        'Sensitivity': 'Sensibilità',
        'Higher = more beats are detected': 'Più alto = più beat rilevati',
        'Level': 'Livello',
        'Bass': 'Bassi',
        'Mid': 'Medi',
        'High': 'Alti',
        'Audio listening is off': 'Ascolto audio disattivato',
        'Starting audio capture…': 'Avvio cattura audio…',
        'Listening: no sound is playing': 'In ascolto: nessun suono in riproduzione',
        'the default output': 'l\'uscita predefinita',
        'Skipped by the flash limit: wait a moment or raise Max flashes/s': 'Saltato per il limite di flash: attendi un attimo o alza Max flash/s',

        // ── Control: Sampling preview (index.html + sampling-view.js) ──
        'Sampling': 'Campionamento',
        'A scaled copy of the captured screen showing where colors are read from.': 'Una copia in scala dello schermo catturato che mostra da dove vengono letti i colori.',
        'Live': 'Live',
        'Each band segment and dot shows the color currently sent to its LED.': 'Ogni segmento di banda e ogni punto mostra il colore inviato in questo momento al suo LED.',
        'Zones': 'Zone',
        'Shows only the sampled areas, without colors.': 'Mostra solo le aree campionate, senza colori.',
        'Bands': 'Bande',
        'Zones around the monitor frame. Thickness follows the Depth setting (adaptive strategies change it by themselves).': 'Zone attorno alla cornice del monitor. Lo spessore segue l\'impostazione Profondità (le strategie adattive lo cambiano da sole).',
        'Dots': 'Punti',
        'Devices that are not on the monitor frame: each reads the color at one point of the screen, chosen from its position in the Topology Editor.': 'Dispositivi che non sono sulla cornice del monitor: ognuno legge il colore in un punto dello schermo, scelto in base alla sua posizione nell\'Editor topologia.',
        'Black bars': 'Bande nere',
        'When detected, bars are greyed out and the bands follow the real picture.': 'Quando vengono rilevate, le bande nere appaiono in grigio e le bande seguono l\'immagine reale.',
        'Hover a band or a dot to see which device it feeds': 'Passa sopra una banda o un punto per vedere quale dispositivo alimenta',
        'Sampling view': 'Vista campionamento',
        'Screen sampling preview': 'Anteprima del campionamento dello schermo',
        'Service off — showing configured bands': 'Servizio spento — bande configurate',
        'Screen unavailable (standby)': 'Schermo non disponibile (standby)',
        'No device is receiving colors': 'Nessun dispositivo riceve colori',
        'Top edge': 'Bordo superiore',
        'Bottom edge': 'Bordo inferiore',
        'Left edge': 'Bordo sinistro',
        'Right edge': 'Bordo destro',

        // ── Control: Devices panel ──
        'Which lighting devices receive the Ambilight colors.': 'Quali dispositivi di illuminazione ricevono i colori Ambilight.',
        'On/off': 'Acceso/spento',
        'Click a device to include or exclude it from the effect.': 'Fai clic su un dispositivo per includerlo o escluderlo dall\'effetto.',
        'Zones and details': 'Zone e dettagli',
        'Which zones of each device are used, the topology and the identify (Flash) button are in the Devices page.': 'Quali zone di ogni dispositivo si usano, la topologia e il pulsante di identificazione (Flash) sono nella pagina Dispositivi.',
        'Manage devices →': 'Gestisci dispositivi →',
        'Open Devices': 'Apri Dispositivi',
        'Getting started': 'Primi passi',
        'Dismiss checklist': 'Chiudi la lista',
        'No devices available.': 'Nessun dispositivo disponibile.',
        'Connect OpenRGB first:': 'Prima collega OpenRGB:',
        'On: receives the ambilight colors. Click to turn off.': 'Acceso: riceve i colori dell\'ambilight. Fai clic per spegnerlo.',
        'Off. Click to turn on.': 'Spento. Fai clic per accenderlo.',
        'No zones mapped yet: map them in the Topology Editor.': 'Nessuna zona ancora mappata: mappale nell\'Editor topologia.',
        'No device has its zones mapped to the screen yet.': 'Nessun dispositivo ha ancora le zone mappate sullo schermo.',
        'No device is switched on, so nothing will light up.': 'Nessun dispositivo è acceso, quindi non si illuminerà nulla.',
        'The devices that are on have no active zones, so nothing will light up.': 'I dispositivi accesi non hanno zone attive, quindi non si illuminerà nulla.',
        'Next step': 'Prossimo passo',
        // checklist (the text node ends with " —" when the step is not done)
        'OpenRGB connected and devices found': 'OpenRGB connesso e dispositivi trovati',
        'OpenRGB connected and devices found —': 'OpenRGB connesso e dispositivi trovati —',
        'At least one device has zones mapped to the screen': 'Almeno un dispositivo ha zone mappate sullo schermo',
        'At least one device has zones mapped to the screen —': 'Almeno un dispositivo ha zone mappate sullo schermo —',
        'Enable switched on and a device with active zones': 'Attiva acceso e un dispositivo con zone attive',
        'Enable switched on and a device with active zones —': 'Attiva acceso e un dispositivo con zone attive —',
        'Open Topology Editor': 'Apri Editor topologia',

        // ── Backend errors shown on Control (ambilight_api.py, audio_capture.py) ──
        'Service not initialized': 'Servizio non inizializzato',
        'Turn on Ambilight first: the accent is drawn on top of it': 'Prima attiva Ambilight: l\'accento viene disegnato sopra di esso',
        'no response from the app': 'nessuna risposta dall\'app',
        'Audio capture needs the PyAudioWPatch package (pip install PyAudioWPatch)': 'La cattura audio richiede il pacchetto PyAudioWPatch (pip install PyAudioWPatch)',
        'The audio stream stopped (device removed or changed?)': 'Il flusso audio si è interrotto (dispositivo rimosso o cambiato?)',
        'No loopback device found for the default audio output': 'Nessun dispositivo loopback trovato per l\'uscita audio predefinita',
    },
    patterns: {
        // Info buttons
        'Info: {x}': 'Info: {x}',

        // Toasts (ambilight.js) — preset names are translated through strings
        'Preset applied: {name}': 'Preset applicato: {name}',
        'Accent preset applied: {name}': 'Preset accento applicato: {name}',
        'Could not apply the change: {err}': 'Impossibile applicare la modifica: {err}',
        'Could not start the test: {err}': 'Impossibile avviare la prova: {err}',
        'Could not change the Enable state: {err}': 'Impossibile cambiare lo stato di Attiva: {err}',
        'Could not update the device: {err}': 'Impossibile aggiornare il dispositivo: {err}',
        'Could not apply the preset: {err}': 'Impossibile applicare il preset: {err}',
        'Could not fire the test accent: {err}': 'Impossibile generare l\'accento di prova: {err}',

        // FPS badge tooltip (the load suffix may be missing: specific one first)
        'Reaching {fps} of {target} fps — try lowering FPS Target or switching Capture Engine · {ms} ms per frame of {avail} available':
            'Raggiunti {fps} di {target} fps — prova ad abbassare FPS obiettivo o a cambiare Motore di cattura · {ms} ms per fotogramma su {avail} disponibili',
        'Reaching {fps} of {target} fps — try lowering FPS Target or switching Capture Engine':
            'Raggiunti {fps} di {target} fps — prova ad abbassare FPS obiettivo o a cambiare Motore di cattura',
        'Frame rate actually reached · {ms} ms per frame of {avail} available':
            'Frequenza effettivamente raggiunta · {ms} ms per fotogramma su {avail} disponibili',

        // Black bar status
        'Content area: {dims} px — bars cropped': 'Area del contenuto: {dims} px — bande tagliate',

        // Status summary
        '{d} device · {z} zone · {cap}': '{d} dispositivo · {z} zona · {cap}',
        '{d} device · {z} zones · {cap}': '{d} dispositivo · {z} zone · {cap}',
        '{d} devices · {z} zone · {cap}': '{d} dispositivi · {z} zona · {cap}',
        '{d} devices · {z} zones · {cap}': '{d} dispositivi · {z} zone · {cap}',

        // Devices summary
        '{on} of {total} devices on · {z} zones receiving colors': 'Dispositivi accesi: {on} su {total} · zone che ricevono colori: {z}',
        '{on} of {total} devices on · {z} zone receiving colors': 'Dispositivi accesi: {on} su {total} · zone che ricevono colori: {z}',
        '{on} of {total} device on · {z} zones receiving colors': 'Dispositivi accesi: {on} su {total} · zone che ricevono colori: {z}',
        '{on} of {total} device on · {z} zone receiving colors': 'Dispositivi accesi: {on} su {total} · zone che ricevono colori: {z}',

        // Audio meter status (notice + device name; the notice alone too)
        'Audio source "{src}" is not available: using the default output instead ({dev})':
            'La sorgente audio "{src}" non è disponibile: uso l\'uscita predefinita ({dev})',
        'Audio source "{src}" is not available: using the default output instead':
            'La sorgente audio "{src}" non è disponibile: uso l\'uscita predefinita',
        'Listening to {dev}': 'In ascolto: {dev}',
        '{name} (not found)': '{name} (non trovato)',
        'Audio library could not be loaded: {err}': 'Impossibile caricare la libreria audio: {err}',
        'Could not list audio devices: {err}': 'Impossibile elencare i dispositivi audio: {err}',
        'Audio processing error: {err}': 'Errore di elaborazione audio: {err}',
        'Could not capture audio: {err}': 'Impossibile catturare l\'audio: {err}',

        // Sampling caption (first line); most specific first
        '{res} · Depth {min}–{max}% adaptive · now {now}': '{res} · Profondità {min}–{max}% adattiva · ora {now}',
        '{res} · Depth {min}–{max}% adaptive': '{res} · Profondità {min}–{max}% adattiva',
        '{res} · Depth {d}': '{res} · Profondità {d}',
        'Black bars cropped ({dims})': 'Bande nere tagliate ({dims})',

        // Sampling tooltip
        'Zone: {zone}': 'Zona: {zone}',
        'Key grid {dims}: each key reads the part of the screen it sits under': 'Griglia tasti {dims}: ogni tasto legge la parte di schermo che ha sotto',
        'Reads one point of the screen ({x}% across, {y}% down)': 'Legge un punto dello schermo ({x}% in orizzontale, {y}% in verticale)',
        'Top edge band · {n} LED': 'Banda del bordo superiore · {n} LED',
        'Top edge band · {n} LEDs': 'Banda del bordo superiore · {n} LED',
        'Bottom edge band · {n} LED': 'Banda del bordo inferiore · {n} LED',
        'Bottom edge band · {n} LEDs': 'Banda del bordo inferiore · {n} LED',
        'Left edge band · {n} LED': 'Banda del bordo sinistro · {n} LED',
        'Left edge band · {n} LEDs': 'Banda del bordo sinistro · {n} LED',
        'Right edge band · {n} LED': 'Banda del bordo destro · {n} LED',
        'Right edge band · {n} LEDs': 'Banda del bordo destro · {n} LED',

        // Update toast (navigation.js)
        'EDAmbilight {latest} is available (you have {current}).': 'È disponibile EDAmbilight {latest} (hai la {current}).',

        // Hardware notices (texts from src/api/topology_api.py and src/utils/openrgb_version.py,
        // shown by navigation.js on every page)
        'New device detected: {dev} ({n} zone imported). It is off until you enable it in Control.':
            'Nuovo dispositivo rilevato: {dev} (1 zona importata). Resta spento finché non lo attivi in Controllo.',
        'New device detected: {dev} ({n} zones imported). It is off until you enable it in Control.':
            'Nuovo dispositivo rilevato: {dev} ({n} zone importate). Resta spento finché non lo attivi in Controllo.',
        'Device no longer detected: {dev}. Its settings are kept and it receives no colors.':
            'Dispositivo non più rilevato: {dev}. Le sue impostazioni restano salvate e non riceve colori.',
        '{dev} changed on the hardware ({diff}). Its layout was updated; check it in Topology.':
            '{dev} è cambiato nell\'hardware ({diff}). La sua disposizione è stata aggiornata; controllala in Topologia.',
        'OpenRGB {v} detected. Version 1.0 or later is recommended: it identifies hardware more accurately and fixes bugs. Get it from openrgb.org. On Windows it also needs the PawnIO driver (pawnio.eu) to reach memory and motherboards.':
            'Rilevato OpenRGB {v}. Si consiglia la versione 1.0 o successiva: identifica l\'hardware con più precisione e corregge vari bug. Scaricala da openrgb.org. Su Windows richiede anche il driver PawnIO (pawnio.eu) per accedere a memorie e schede madri.',
    },
    html: {
    },
});

// Devices + Topology editor
EDI18n.add('it', {
    strings: {
        // ── Devices page (devices.html) ─────────────────────────────────────
        'EDAmbilight — Devices': 'EDAmbilight — Dispositivi',
        'Devices': 'Dispositivi',
        'OpenRGB Hardware': 'Hardware OpenRGB',
        'Total Devices': 'Dispositivi totali',
        'With Topology': 'Con topologia',
        'Actions': 'Azioni',
        'Flash to identify': 'Lampeggia per identificare',
        'Flash All': 'Lampeggia tutti',
        'Sampling': 'Campionamento',
        'What the lights read now. Hover a band or a dot to see which device it feeds': 'Cosa leggono le luci adesso. Passa sopra una banda o un punto per vedere quale dispositivo alimenta',
        'Sampling view': 'Vista campionamento',
        'Live': 'Live',
        'Zones': 'Zone',
        'Screen sampling preview': 'Anteprima del campionamento dello schermo',
        'Loading devices...': 'Caricamento dispositivi...',
        'No devices found.': 'Nessun dispositivo trovato.',
        'Rescan': 'Ricerca di nuovo',
        'No topology': 'Nessuna topologia',
        'Edit topology': 'Modifica topologia',
        'Map zones': 'Mappa le zone',
        'Include in ambilight lighting': 'Includi nell\'illuminazione ambilight',
        'Map its zones in the Topology Editor first': 'Prima mappa le sue zone nell\'Editor topologia',
        // device type badges
        'keyboard': 'tastiera',
        'linear': 'lineare',
        'matrix': 'matrice',
        'single': 'singolo',
        // what a zone reads
        'outside the screen': 'fuori dallo schermo',
        'screen point': 'punto dello schermo',
        'top edge': 'bordo superiore',
        'bottom edge': 'bordo inferiore',
        'left edge': 'bordo sinistro',
        'right edge': 'bordo destro',
        'off edge': 'nessun bordo',
        'Keyboard: each zone shows a single color taken from one point of the screen.': 'Tastiera: ogni zona mostra un solo colore preso da un punto dello schermo.',
        'Device enabled': 'Dispositivo attivato',
        'Device disabled': 'Dispositivo disattivato',
        'unknown error': 'errore sconosciuto',

        // ── Topology editor (topology-editor.html) ──────────────────────────
        'EDAmbilight — Topology Editor': 'EDAmbilight — Editor topologia',
        'Topology Editor': 'Editor topologia',
        'Multi-Zone Spatial Configuration': 'Configurazione spaziale multizona',
        'Multi-Zone Devices': 'Dispositivi multizona',
        'Grid Config': 'Griglia',
        'Grid Size:': 'Dimensione griglia:',
        'Snap to Grid': 'Aggancia alla griglia',
        'Show Grid': 'Mostra griglia',
        'Put every zone back to its default position': 'Riporta ogni zona nella posizione predefinita',
        'Reset All': 'Ripristina tutto',
        'Reload zone LED counts from OpenRGB hardware': 'Ricarica il numero di LED delle zone dall\'hardware OpenRGB',
        'Reload': 'Ricarica',
        'Auto Layout': 'Disposizione auto',
        'Fit all zones in view': 'Inquadra tutte le zone',
        'Fit View': 'Adatta vista',
        'Show grid, calibration center, calibration and measurements': 'Mostra griglia, centro di calibrazione, calibrazione e misure',
        'Advanced': 'Avanzate',
        'Toggle calibration overlay': 'Mostra/nascondi la sovrapposizione di calibrazione',
        'Calibration': 'Calibrazione',
        'Ring spacing in world units': 'Distanza tra gli anelli in unità della scena',
        'Unsaved changes': 'Modifiche non salvate',
        'Save Topology': 'Salva topologia',
        'Zone Inspector': 'Ispettore zona',
        'No zone selected': 'Nessuna zona selezionata',
        'Zone Name': 'Nome zona',
        'Zone name': 'Nome zona',
        'Position X': 'Posizione X',
        'Position Y': 'Posizione Y',
        'Rotation': 'Rotazione',
        'Direction': 'Direzione',
        'Forward (0→N)': 'Avanti (0→N)',
        'Reverse (N→0)': 'Inversa (N→0)',
        'Flip Direction': 'Inverti direzione',
        'Physical Length (cm)': 'Lunghezza fisica (cm)',
        'optional': 'facoltativa',
        'e.g. 120': 'es. 120',
        'Spacing:': 'Spaziatura:',
        '1.0 (default)': '1.0 (predefinita)',
        'Device:': 'Dispositivo:',
        'Zone Index:': 'Indice zona:',
        'LED Count:': 'Numero LED:',
        // Screen panel
        'Screen': 'Schermo',
        'Make the screen cover every zone, with the proportions of your screen; then drag it onto your monitor': 'Fa coprire allo schermo tutte le zone, con le proporzioni del tuo schermo; poi trascinalo sul tuo monitor',
        'Fit': 'Adatta',
        'Forget the rectangle placed by hand': 'Dimentica il rettangolo posizionato a mano',
        'Automatic': 'Automatico',
        'Drag a corner to resize (the proportions stay those of your screen), the border to move. A dot on a LED: it reads the point of the screen under it. A faded LED: outside the screen (black; a zone wholly outside is left alone).': 'Trascina un angolo per ridimensionare (le proporzioni restano quelle del tuo schermo), il bordo per spostare. Un punto su un LED: legge il punto dello schermo sotto di sé. Un LED sbiadito: fuori dallo schermo (nero; una zona tutta fuori viene lasciata stare).',
        'Placed by hand. LEDs on a side read that side of the screen, LEDs inside read the point under them, LEDs outside get no colour (a zone wholly outside is left alone).': 'Posizionato a mano. I LED su un lato leggono quel lato dello schermo, i LED all\'interno leggono il punto sotto di loro, i LED all\'esterno non ricevono colore (una zona tutta fuori viene lasciata stare).',
        'Automatic: the screen covers every zone. Drag a corner or the border to place it where your monitor is: then save.': 'Automatico: lo schermo copre tutte le zone. Trascina un angolo o il bordo per metterlo dove si trova il tuo monitor, poi salva.',
        'Proportions of your screen: not known yet (start the ambilight once).': 'Proporzioni del tuo schermo: non ancora note (avvia l\'ambilight una volta).',
        // canvas labels (drawn through EDI18n.t)
        'SCREEN': 'SCHERMO',
        'SCREEN (automatic)': 'SCHERMO (automatico)',
        // Calibration center
        'Calibration Center': 'Centro di calibrazione',
        'Center X (%)': 'Centro X (%)',
        'Center Y (%)': 'Centro Y (%)',
        'Quick Presets': 'Preset rapidi',
        'Center (50,50)': 'Centro (50,50)',
        'Center': 'Centro',
        'Top (50,90)': 'Alto (50,90)',
        'Top': 'Alto',
        'Bottom (50,10)': 'Basso (50,10)',
        'Bottom': 'Basso',
        'Left (10,50)': 'Sinistra (10,50)',
        'Left': 'Sinistra',
        'Right (90,50)': 'Destra (90,50)',
        'Right': 'Destra',
        'Drag the cyan crosshair on the canvas. The Calibration button lights your LEDs in rings of colour around this point, to check that the zones on the canvas are where the LEDs really are. The ambilight does not use it.': 'Trascina il mirino ciano sull\'area di disegno. Il pulsante Calibrazione accende i LED ad anelli di colore attorno a questo punto, per verificare che le zone disegnate siano dove si trovano davvero i LED. L\'ambilight non lo usa.',
        // Calibration settings
        'Calibration Settings': 'Impostazioni calibrazione',
        'Center LED': 'LED centrale',
        'Blink': 'Lampeggio',
        'White rings': 'Anelli bianchi',
        'Red rings': 'Anelli rossi',
        'Blue rings': 'Anelli blu',
        'Green rings': 'Anelli verdi',
        // Overlaps
        'Zone overlaps detected!': 'Zone sovrapposte rilevate!',
        // Notifications and dialogs (topology-editor.js)
        'Scene reloaded from OpenRGB': 'Scena ricaricata da OpenRGB',
        'Reload failed': 'Ricaricamento non riuscito',
        'Failed to reload from OpenRGB': 'Impossibile ricaricare da OpenRGB',
        'The screen rectangle was adapted to the proportions of your screen. Check that the strips are still on its sides, then save.': 'Il rettangolo dello schermo è stato adattato alle proporzioni del tuo schermo. Controlla che le strisce siano ancora sui suoi lati, poi salva.',
        'Could not save the screen rectangle': 'Impossibile salvare il rettangolo dello schermo',
        '✓ Auto layout applied': '✓ Disposizione automatica applicata',
        'Reset all zones to their default positions? Unsaved layout changes are lost.': 'Riportare tutte le zone alle posizioni predefinite? Le modifiche non salvate alla disposizione andranno perse.',
        'Reset all': 'Ripristina tutto',
        '✓ Topology reset': '✓ Topologia ripristinata',
        'No zones to fit the screen on': 'Nessuna zona su cui adattare lo schermo',
        'Scene saved': 'Scena salvata',
        'Save failed': 'Salvataggio non riuscito',
        'Failed to save scene': 'Impossibile salvare la scena',
        'forward': 'avanti',
        'reverse': 'inversa',

        // ── Backend messages (topology_api.py, ambilight_api.py) ────────────
        'The rectangle has no area': 'Il rettangolo non ha area',
        'Could not write device_topologies.json': 'Impossibile scrivere device_topologies.json',
        'Manager not initialized': 'Gestore non inizializzato',
        'Service not initialized': 'Servizio non inizializzato',
        'No calibration LEDs': 'Nessun LED di calibrazione',
        'File write failed': 'Scrittura del file non riuscita',
        'File write error': 'Errore di scrittura del file',
        'Invalid zones data': 'Dati delle zone non validi',
        'Error saving topology': 'Errore nel salvataggio della topologia',
        // header of the notices box (navigation.js) shown for these hardware notices
        'Hardware changed since the last start': 'Hardware cambiato dall\'ultimo avvio',
    },
    patterns: {
        // ── Devices page ────────────────────────────────────────────────────
        // "Zones 2/3" (button that opens the zone list); "Zones" alone is in strings
        'Zones {on}/{n}': 'Zone {on}/{n}',
        // several sides: "top + right edge"
        '{a} + {b} edge': v => {
            const S = { top: 'superiore', bottom: 'inferiore', left: 'sinistro', right: 'destro' };
            return 'bordi ' + [v.a].concat(v.b.split(' + ')).map(s => S[s] || s).join(' + ');
        },
        // sides mixed with screen points: "point + top", "top + point", "top + point + right"
        'point + {rest}': v => {
            const S = { top: 'bordo superiore', bottom: 'bordo inferiore', left: 'bordo sinistro', right: 'bordo destro', point: 'punto' };
            return 'punto + ' + v.rest.split(' + ').map(s => S[s] || s).join(' + ');
        },
        '{a} + point + {b}': v => {
            const S = { top: 'bordo superiore', bottom: 'bordo inferiore', left: 'bordo sinistro', right: 'bordo destro', point: 'punto' };
            return [v.a, 'point'].concat(v.b.split(' + ')).map(s => S[s] || s).join(' + ');
        },
        '{a} + point': v => {
            const S = { top: 'bordo superiore', bottom: 'bordo inferiore', left: 'bordo sinistro', right: 'bordo destro', point: 'punto' };
            return v.a.split(' + ').map(s => S[s] || s).join(' + ') + ' + punto';
        },
        'Each key shows the color of the part of the screen it sits under (a {c}×{r} grid laid over the whole screen). It has nothing to place in the Topology Editor.':
            'Ogni tasto mostra il colore della parte di schermo sotto cui si trova (una griglia {c}×{r} stesa su tutto lo schermo). Non ha nulla da posizionare nell\'Editor topologia.',
        'Include {name} in ambilight': 'Includi {name} nell\'ambilight',
        'Could not update the zone: {err}': 'Impossibile aggiornare la zona: {err}',
        'Could not update device: {err}': 'Impossibile aggiornare il dispositivo: {err}',
        'Flashing: {name}': 'Lampeggio: {name}',
        'Stop ({i}/{n})': 'Ferma ({i}/{n})',
        '{n} device(s) found': v => v.n == 1 ? '1 dispositivo trovato' : v.n + ' dispositivi trovati',

        // ── Topology editor ─────────────────────────────────────────────────
        '{z} zones · {l} LEDs': v => (v.z == 1 ? '1 zona' : v.z + ' zone') + ' · ' + v.l + ' LED',
        '{n} LEDs · {r}° · {d}': '{n} LED · {r}° · {d}',
        '{sp} units/LED': '{sp} unità/LED',
        'Overlapping: {list}': 'Sovrapposte: {list}',
        'Proportions of your screen: {w}×{h} ({r}:1), always kept.': 'Proporzioni del tuo schermo: {w}×{h} ({r}:1), sempre mantenute.',

        // ── Backend messages ────────────────────────────────────────────────
        'Scene saved: {n} zones': 'Scena salvata: {n} zone',
        'Reloaded {n} zones': 'Ricaricate {n} zone',
        'Topology saved: {n} zones': 'Topologia salvata: {n} zone',
        'Invalid rectangle: {err}': 'Rettangolo non valido: {err}',
        'Device not found: {id}': 'Dispositivo non trovato: {id}',
        'No topology for {id}': 'Nessuna topologia per {id}',
        // hardware notices (add_hardware_notice / _add_notice, shown by navigation.js)
        'New device detected: {name} ({n} zone imported). It is off until you enable it in Control.':
            'Nuovo dispositivo rilevato: {name} ({n} zona importata). Resta spento finché non lo attivi in Controllo.',
        'New device detected: {name} ({n} zones imported). It is off until you enable it in Control.':
            'Nuovo dispositivo rilevato: {name} ({n} zone importate). Resta spento finché non lo attivi in Controllo.',
        'Device no longer detected: {name}. Its settings are kept and it receives no colors.':
            'Dispositivo non più rilevato: {name}. Le sue impostazioni sono conservate e non riceve colori.',
        '{name} changed on the hardware ({diff}). Its layout was updated; check it in Topology.': v => {
            const parts = v.diff.split('; ').map(d => {
                let m;
                if (d === 'repeated zone indexes renumbered') return 'indici di zona ripetuti rinumerati';
                if ((m = /^zone '(.*)' renamed '(.*)'$/.exec(d))) return 'zona \'' + m[1] + '\' rinominata \'' + m[2] + '\'';
                if ((m = /^zone '(.*)' LEDs (.*)$/.exec(d))) return 'zona \'' + m[1] + '\' LED ' + m[2];
                if ((m = /^zone '(.*)' added$/.exec(d))) return 'zona \'' + m[1] + '\' aggiunta';
                if ((m = /^zone '(.*)' removed$/.exec(d))) return 'zona \'' + m[1] + '\' rimossa';
                return d;
            });
            return v.name + ' è cambiato sull\'hardware (' + parts.join('; ') + '). La sua disposizione è stata aggiornata; controllala in Topologia.';
        },
        // utils/openrgb_version.py
        'OpenRGB {label} detected. Version 1.0 or later is recommended: it identifies hardware more accurately and fixes bugs. Get it from openrgb.org. On Windows it also needs the PawnIO driver (pawnio.eu) to reach memory and motherboards.':
            'Rilevato OpenRGB {label}. Si consiglia la versione 1.0 o successiva: riconosce l\'hardware con più precisione e corregge vari bug. Scaricala da openrgb.org. Su Windows serve anche il driver PawnIO (pawnio.eu) per raggiungere memorie e schede madri.',

        // ── Broad patterns: keep them LAST (the first pattern that matches wins) ──
        '{n} zones': v => /^\d+$/.test(v.n) ? v.n + ' zone' : v.n + ' zones',
        '{n} zone': v => /^\d+$/.test(v.n) ? v.n + ' zona' : v.n + ' zone',
        'Zone {n}': v => /^\d+$/.test(v.n) ? 'Zona ' + v.n : 'Zone ' + v.n,
        '{c}×{r} keys': v => /^\d+$/.test(v.c) ? v.c + '×' + v.r + ' tasti' : v.c + '×' + v.r + ' keys',
    },
    html: {
        'devices.empty_hint': 'Assicurati che OpenRGB sia in esecuzione con il server SDK attivo.<br>Host e porta sono in <a href="settings.html" style="color:var(--c-cyan);">Impostazioni</a>.',
        'topo.no_devices': 'Nessun dispositivo trovato.<br>Controlla che OpenRGB sia connesso in<br><a href="devices.html" style="color:var(--c-cyan);">Dispositivi</a>.',
        'topo.hint': 'Trascina le zone · <b>R</b> ruota · <b>F</b> inverti · Tasto centrale per spostare · Rotella per lo zoom',
    },
});

// Preview
EDI18n.add('it', {
    strings: {
        // ── preview.html: page title, WebGL fallback ──
        'EDAmbilight — Live Preview': 'EDAmbilight — Anteprima live',
        'WebGL not available': 'WebGL non disponibile',
        'This page needs WebGL to render the effects. Enable hardware acceleration in your browser settings and reload.':
            'Questa pagina richiede WebGL per disegnare gli effetti. Attiva l\'accelerazione hardware nelle impostazioni del browser e ricarica.',
        'Back': 'Indietro',

        // ── preview.html: header (effects, theme, fullscreen) ──
        'Plasma': 'Plasma',
        'Fluid': 'Fluido',
        'Aurora': 'Aurora',
        'Lava': 'Lava',
        'Neon': 'Neon',
        'Flame': 'Fiamma',
        'Switch to light theme': 'Passa al tema chiaro',
        'Switch to dark theme': 'Passa al tema scuro',
        'Fullscreen (F)': 'Schermo intero (F)',

        // ── preview.html: Animation / Particles ──
        'Animation': 'Animazione',
        'Speed': 'Velocità',
        'Scale': 'Scala',
        'Amplitude': 'Ampiezza',
        'Noise': 'Rumore',
        'Turb': 'Turb.',
        'Turb Speed': 'Vel. turb.',
        'Particles': 'Particelle',
        'Mode': 'Modalità',
        'Off': 'Spento',
        'Orbs': 'Sfere',
        'Fireworks': 'Fuochi d\'artificio',
        'Embers': 'Braci',
        'Comets': 'Comete',
        'Flares': 'Bagliori',
        'Rate': 'Frequenza',
        'Size': 'Grandezza',
        'Glow': 'Bagliore',
        'Gravity': 'Gravità',

        // ── preview.html: Color ──
        'Color': 'Colore',
        'Palette': 'Palette',
        'Rainbow': 'Arcobaleno',
        'Fire': 'Fuoco',
        'Ocean': 'Oceano',
        'Sunset': 'Tramonto',
        'Shift': 'Offset',
        'Cycle': 'Ciclo',

        // ── preview.html: Post FX ──
        'Post FX': 'Post-effetti',
        'Saturation': 'Saturaz.',
        'Contrast': 'Contrasto',
        'Vignette': 'Vignetta',
        'Rotation': 'Rotazione',
        'Kaleido': 'Caleido',
        'Quality': 'Qualità',
        'Low 50%': 'Bassa 50%',
        'Med 75%': 'Media 75%',
        'High 100%': 'Alta 100%',
        'Native DPI': 'DPI nativi',

        // ── preview.html: Music Sync ──
        'Music Sync': 'Sincro musica',
        'Load Audio': 'Carica audio',
        'No file — drop audio anywhere': 'Nessun file — trascina un audio qui',
        'Loading…': 'Caricamento…',
        'Audio decode failed': 'Decodifica audio non riuscita',
        'Bass →': 'Bassi →',
        'Mid →': 'Medi →',
        'Treble →': 'Acuti →',
        'Beat →': 'Beat →',
        'Color Cycle': 'Ciclo colore',
        'Particle Glow': 'Bagliore particelle',
        'Particle Burst': 'Esplosione particelle',
        'Color Shift': 'Spostamento colore',
        'Play/Pause (Space)': 'Riproduci/Pausa (Spazio)',
        'Volume': 'Volume',

        // ── preview.html: Visualizers ──
        'Visualizers': 'Visualizzatori',
        'Spectrum': 'Spettro',
        'Waveform': 'Forma d\'onda',
        'VU Meter': 'VU meter',
        'Opacity': 'Opacità',
        'Bands': 'Bande',
        'Height': 'Altezza',
        'Smooth': 'Smussa',
        'Style': 'Stile',
        'Bars': 'Barre',
        'Mirror': 'Specchio',
        'Fill': 'Pieno',
        'Thickness': 'Spessore',
        'Line': 'Linea',
        'Circle': 'Cerchio',
        'Width': 'Larghezza',
        'Segments': 'Segmenti',
        'Gradient': 'Sfumatura',
        // canvas labels of the VU meter (EDI18n.t)
        'BASS': 'BASSI',
        'HI': 'ALTI',

        // ── preview.html: footer (presets, shortcuts) ──
        'Presets': 'Preset',
        'Preset…': 'Preset…',
        'Save preset': 'Salva preset',
        'Delete preset': 'Elimina preset',
        'Reset to defaults': 'Ripristina predefiniti',
        'F fullscreen · H hide UI · Space play · ←→ seek · 1-6 effects':
            'F schermo intero · H nascondi UI · Spazio play · ←→ cerca · 1-6 effetti',
        'Preset saved': 'Preset salvato',
        'Preset deleted': 'Preset eliminato',
    },
    patterns: {
        // music-status after a failed load: 'Error: ' + e.message
        'Error: {msg}': 'Errore: {msg}',
    },
    html: {
        // VU legend in the Music section: B / M / H (bass, mid, high) -> B / M / A (alti)
        'preview.vuHigh': 'A',
    },
});

// Settings + Help + Loading
EDI18n.add('it', {
    strings: {
        // ── Page titles ─────────────────────────────────────────────────────
        'EDAmbilight — Settings': 'EDAmbilight — Impostazioni',
        'EDAmbilight — Help': 'EDAmbilight — Guida',

        // ── Settings: header ────────────────────────────────────────────────
        'Settings': 'Impostazioni',
        'Configuration': 'Configurazione',

        // ── Settings: Language ──────────────────────────────────────────────
        'Language': 'Lingua',
        'Language of the interface': 'Lingua dell\'interfaccia',

        // ── Settings: OpenRGB connection ────────────────────────────────────
        'OpenRGB Connection': 'Connessione OpenRGB',
        'LED device server': 'Server dei dispositivi LED',
        'Host': 'Host',
        'Port': 'Porta',
        'OpenRGB executable': 'Eseguibile di OpenRGB',
        '(optional)': '(facoltativo)',
        'Leave empty to auto-detect, e.g. C:\\Program Files\\OpenRGB\\OpenRGB.exe': 'Lascia vuoto per il rilevamento automatico, es. C:\\Program Files\\OpenRGB\\OpenRGB.exe',
        'Start OpenRGB automatically': 'Avvia OpenRGB automaticamente',
        'Not tested': 'Non verificato',
        'Test': 'Verifica',
        'Save & Reconnect': 'Salva e riconnetti',
        'Testing...': 'Verifica in corso...',
        'Invalid port (1–65535)': 'Porta non valida (1–65535)',
        'Invalid port number': 'Numero di porta non valido',
        'OpenRGB connected!': 'OpenRGB connesso!',
        'Connection failed': 'Connessione non riuscita',
        'Connection failed:': 'Connessione non riuscita:',
        'Error:': 'Errore:',
        'Could not save settings': 'Impossibile salvare le impostazioni',
        'Could not save settings:': 'Impossibile salvare le impostazioni:',
        'Settings saved and reconnected!': 'Impostazioni salvate, riconnesso!',
        'Failed': 'Non riuscito',
        'Saved but reconnect failed:': 'Salvato, ma la riconnessione non è riuscita:',

        // ── Settings: Web server ────────────────────────────────────────────
        'Web Server': 'Server web',
        'Local Eel server port': 'Porta del server Eel locale',
        'Change takes effect on next application start.': 'La modifica ha effetto al prossimo avvio dell\'app.',
        'Off (recommended): only this PC can open EDAmbilight; requests from other devices, and from web pages that try to reach it through the browser, are refused. On: phones and PCs of your network can open it at http://<this PC\'s address>:<port> and control the LEDs and the app, with no password.':
            'Spento (consigliato): solo questo PC può aprire EDAmbilight; le richieste da altri dispositivi, e dalle pagine web che provano a raggiungerlo tramite il browser, vengono rifiutate. Acceso: telefoni e PC della tua rete possono aprirlo su http://<indirizzo di questo PC>:<porta> e controllare i LED e l\'app, senza password.',
        'Allow other devices on the network': 'Consenti altri dispositivi della rete',
        'Off by default: only this PC can connect. Takes effect on next application start.': 'Spento di default: solo questo PC può connettersi. Ha effetto al prossimo avvio dell\'app.',
        'Save port': 'Salva porta',
        'Restart now': 'Riavvia ora',
        'Let any device on your network control EDAmbilight? There is no password: anyone on the same network (Wi-Fi guests included) can change the lighting, restart or quit the app.':
            'Permettere a qualsiasi dispositivo della tua rete di controllare EDAmbilight? Non c\'è password: chiunque sia sulla stessa rete (ospiti del Wi-Fi compresi) può cambiare l\'illuminazione, riavviare o chiudere l\'app.',
        'Allow': 'Consenti',
        'Network access saved. Restart the app to apply.': 'Accesso dalla rete salvato. Riavvia l\'app per applicarlo.',
        'Only this PC will be able to connect. Restart the app to apply.': 'Solo questo PC potrà connettersi. Riavvia l\'app per applicare.',
        'Could not save:': 'Impossibile salvare:',
        'Invalid port (1024–65535)': 'Porta non valida (1024–65535)',
        'Could not save port:': 'Impossibile salvare la porta:',
        'Web port saved. Restart the app to apply.': 'Porta web salvata. Riavvia l\'app per applicarla.',

        // ── Settings: Application ───────────────────────────────────────────
        'Application': 'Applicazione',
        'Closing the window keeps EDAmbilight running in the system tray': 'Chiudendo la finestra, EDAmbilight resta attivo nell\'area di notifica',
        'Restart': 'Riavvia',
        'Quit EDAmbilight': 'Esci da EDAmbilight',
        'Quit': 'Esci',
        'Open log folder': 'Apri cartella log',
        'Restart EDAmbilight? The LEDs stop following the screen for a few seconds.': 'Riavviare EDAmbilight? I LED smettono di seguire lo schermo per qualche secondo.',
        'Could not restart:': 'Impossibile riavviare:',
        'Restarting… a new browser tab will open.': 'Riavvio in corso… si aprirà una nuova scheda del browser.',
        'Quit EDAmbilight? The LEDs will stop following the screen.': 'Uscire da EDAmbilight? I LED smetteranno di seguire lo schermo.',
        'Could not quit:': 'Impossibile uscire:',
        'EDAmbilight is closing. You can close this tab.': 'EDAmbilight si sta chiudendo. Puoi chiudere questa scheda.',
        'Could not open the log folder:': 'Impossibile aprire la cartella dei log:',

        // ── Settings: About / updates ───────────────────────────────────────
        'About': 'Informazioni',
        'Application info': 'Informazioni sull\'applicazione',
        'Standalone ambilight controller based on OpenRGB.': 'Controller ambilight autonomo basato su OpenRGB.',
        'Samples screen edges and maps colors to LED strips in real-time.': 'Campiona i bordi dello schermo e ne porta i colori sulle strisce LED in tempo reale.',
        'Supports WGC, DXGI, and mss capture backends.': 'Supporta i motori di cattura WGC, DXGI e mss.',
        'At startup, at most once a day, EDAmbilight asks GitHub for the latest release and shows a notice with a link when it is newer. Nothing is downloaded or installed. It is the only connection to the internet the app makes: GitHub sees your IP address, nothing else.':
            'All\'avvio, al massimo una volta al giorno, EDAmbilight chiede a GitHub l\'ultima release e, se è più recente, mostra un avviso con un link. Non viene scaricato né installato nulla. È l\'unica connessione a internet che l\'app fa: GitHub vede il tuo indirizzo IP, nient\'altro.',
        'Tell me when a new version is out': 'Avvisami quando esce una nuova versione',
        'Check now': 'Controlla ora',
        'You will be told when a new version is out': 'Riceverai un avviso quando esce una nuova versione',
        'No more checks for new versions': 'Nessun controllo di nuove versioni',
        'Asking GitHub…': 'Chiedo a GitHub…',
        'GitHub could not be reached. Try again later.': 'Impossibile raggiungere GitHub. Riprova più tardi.',
        'What\'s new / download': 'Novità / download',

        // ── Help ────────────────────────────────────────────────────────────
        'Help': 'Guida',
        'Getting started': 'Primi passi',
        'WELCOME TO EDAMBILIGHT': 'BENVENUTO IN EDAMBILIGHT',
        'EDAmbilight reads the colors at the edges of your screen and sends them to your RGB devices through OpenRGB, so your lights follow what is on screen.':
            'EDAmbilight legge i colori ai bordi dello schermo e li invia ai tuoi dispositivi RGB tramite OpenRGB, così le luci seguono quello che c\'è sullo schermo.',
        'Make sure OpenRGB is running': 'Assicurati che OpenRGB sia in esecuzione',
        'Map your strip to the screen': 'Mappa la striscia sullo schermo',
        'Where you put a zone decides what it shows; its name never does: LEDs on a side of the rectangle follow that side of the screen, LEDs inside read the point of the screen under them, LEDs outside get no screen color (they are drawn faded): they are black when part of their zone is in use, and left alone when the whole zone is outside, so it keeps the color OpenRGB or another program gives it. The same goes for a zone you switch off in Devices.':
            'È la posizione di una zona a decidere cosa mostra, mai il suo nome: i LED su un lato del rettangolo seguono quel lato dello schermo, quelli all\'interno leggono il punto dello schermo sotto di loro, quelli all\'esterno non ricevono colori dallo schermo (sono disegnati sbiaditi): restano neri se parte della loro zona è in uso, e non vengono toccati se l\'intera zona è fuori, così mantiene il colore che le danno OpenRGB o un altro programma. Lo stesso vale per una zona che spegni in Dispositivi.',
        'Choose devices and switch it on': 'Scegli i dispositivi e accendi',
        'Fine-tune the look': 'Rifinisci la resa',
        'Changes apply live: no need to save or restart.': 'Le modifiche si applicano dal vivo: non serve salvare né riavviare.',
        'Good to know': 'Buono a sapersi',
        'Open Topology': 'Apri Topologia',
        'Start: open Topology': 'Inizia: apri Topologia',

        // ── Loading page ────────────────────────────────────────────────────
        'Ambient Lighting Controller': 'Controller di illuminazione ambientale',
        'OpenRGB · Screen Sampling · Real-time LEDs': 'OpenRGB · Campionamento schermo · LED in tempo reale',
        'Initializing...': 'Inizializzazione...',
        'Ready — OpenRGB needs attention': 'Pronto — OpenRGB richiede attenzione',
        'OpenRGB not installed': 'OpenRGB non installato',
        'OpenRGB SDK server is off': 'Il server SDK di OpenRGB è spento',
        'Administrator permission denied': 'Permesso di amministratore negato',
        'SDK server did not respond': 'Il server SDK non ha risposto',
        'Remote OpenRGB unreachable': 'OpenRGB remoto non raggiungibile',
        'OpenRGB auto-start disabled': 'Avvio automatico di OpenRGB disattivato',
        'OpenRGB error': 'Errore di OpenRGB',
        'Retrying...': 'Nuovo tentativo...',
        'Download OpenRGB': 'Scarica OpenRGB',
        'Retry': 'Riprova',
        'Continue without LEDs': 'Continua senza LED',

        // ── Backend: startup steps (src/main.py) ────────────────────────────
        'Starting...': 'Avvio...',
        'Connecting to OpenRGB...': 'Connessione a OpenRGB...',
        'OpenRGB detecting devices...': 'OpenRGB sta rilevando i dispositivi...',
        'Starting ambilight service...': 'Avvio del servizio ambilight...',
        'Initializing APIs...': 'Inizializzazione delle API...',
        'Ready!': 'Pronto!',
        'Retrying OpenRGB...': 'Nuovo tentativo con OpenRGB...',
        'Reconnection failed': 'Riconnessione non riuscita',
        'Not initialized': 'Non inizializzato',

        // ── Backend: OpenRGB bootstrap (src/utils/openrgb_bootstrap.py) ─────
        'Starting OpenRGB (administrator prompt)...': 'Avvio di OpenRGB (richiesta di amministratore)...',
        'OpenRGB starting, waiting for SDK server...': 'OpenRGB in avvio, in attesa del server SDK...',
        'OpenRGB auto-start disabled in settings.': 'Avvio automatico di OpenRGB disattivato nelle impostazioni.',
        'Auto-launch is only supported on Windows.': 'L\'avvio automatico è supportato solo su Windows.',
        'OpenRGB is running but its SDK server is off. In OpenRGB open Settings → SDK Server and press Start Server.':
            'OpenRGB è in esecuzione ma il suo server SDK è spento. In OpenRGB apri Settings → SDK Server e premi Start Server.',
        'OpenRGB is not installed (or not in a known location). After installing it, also install the PawnIO driver (pawnio.eu): without it memory modules and motherboards are not detected.':
            'OpenRGB non è installato (o non è in un percorso noto). Dopo averlo installato, installa anche il driver PawnIO (pawnio.eu): senza, i moduli di memoria e le schede madri non vengono rilevati.',
        'Administrator permission was denied. OpenRGB needs it for hardware access.': 'Il permesso di amministratore è stato negato. OpenRGB ne ha bisogno per accedere all\'hardware.',
        'OpenRGB was started but the SDK server did not come up. In OpenRGB check Settings → SDK Server.':
            'OpenRGB è stato avviato ma il server SDK non si è attivato. In OpenRGB controlla Settings → SDK Server.',

        // ── Backend: settings API errors (src/api/settings_api.py) ─────────
        'Settings not initialized': 'Impostazioni non inizializzate',
        'Update check not available': 'Controllo aggiornamenti non disponibile',

        // ── Backend: OpenRGB client errors shown by Test / Reconnect ────────
        'Truncated data from the OpenRGB server': 'Dati troncati dal server OpenRGB',
        'Connection to OpenRGB is closed': 'La connessione a OpenRGB è chiusa',
        'OpenRGB closed the connection': 'OpenRGB ha chiuso la connessione',
        'Unexpected data from the OpenRGB server': 'Dati inattesi dal server OpenRGB',
    },
    patterns: {
        // Settings
        'Connected — {n} device(s)': v => 'Connesso — ' + (v.n == 1 ? '1 dispositivo' : v.n + ' dispositivi'),
        'Connection failed: {msg}': 'Connessione non riuscita: {msg}',
        'Could not save settings: {msg}': 'Impossibile salvare le impostazioni: {msg}',
        'Saved but reconnect failed: {msg}': 'Salvato, ma la riconnessione non è riuscita: {msg}',
        'Could not save port: {msg}': 'Impossibile salvare la porta: {msg}',
        'Could not save: {msg}': 'Impossibile salvare: {msg}',
        'Could not restart: {msg}': 'Impossibile riavviare: {msg}',
        'Could not quit: {msg}': 'Impossibile uscire: {msg}',
        'Could not open the log folder: {msg}': 'Impossibile aprire la cartella dei log: {msg}',
        'You have the latest version ({v}).': 'Hai l\'ultima versione ({v}).',
        'EDAmbilight {latest} is available (you have {current}).': 'È disponibile EDAmbilight {latest} (hai la {current}).',
        'Error: {msg}': 'Errore: {msg}',

        // Backend: startup (main.py) and bootstrap
        'Initialization error: {e}': 'Errore di inizializzazione: {e}',
        'SDK server reachable but connection failed: {e}': 'Server SDK raggiungibile ma connessione non riuscita: {e}',
        'Waiting for OpenRGB SDK server... ({n}s)': 'In attesa del server SDK di OpenRGB... ({n}s)',
        'OpenRGB detecting devices... ({have} of {total})': 'OpenRGB sta rilevando i dispositivi... ({have} di {total})',
        'OpenRGB host {addr} is remote and unreachable.': 'L\'host OpenRGB {addr} è remoto e non raggiungibile.',
        'Could not start {exe}.': 'Impossibile avviare {exe}.',

        // Backend: OpenRGB client errors (the specific one before "Cannot connect to {addr}")
        'Cannot connect to OpenRGB at {addr}: {exc}': 'Impossibile connettersi a OpenRGB su {addr}: {exc}',
        'Lost connection to OpenRGB: {exc}': 'Connessione a OpenRGB persa: {exc}',
        'Cannot connect to {addr}': 'Impossibile connettersi a {addr}',
    },
    html: {
        // help.html — paragraphs split by inline markup
        'help.welcome': 'Segui questi quattro passaggi una volta sola. Puoi tornare a questa pagina in qualsiasi momento dal pulsante <b>Guida</b> nella barra laterale.',
        'help.s1.intro': 'EDAmbilight comunica con le tue luci tramite <b>OpenRGB</b>. Lo avvia per te se riesce a trovarlo.',
        'help.s1.admin': 'OpenRGB ha bisogno dei <b>diritti di amministratore</b> per raggiungere i tuoi dispositivi: al suo avvio Windows mostra una richiesta di autorizzazione. Fai clic su <b>Sì</b>, altrimenti non verrà trovato nessun dispositivo.',
        'help.s1.sdk': 'In OpenRGB apri la scheda <b>SDK Server</b> e fai clic su <b>Start Server</b> (porta predefinita 6742).',
        'help.s1.pawnio': 'I moduli di memoria e le schede madri richiedono il driver <b>PawnIO</b> (<b>pawnio.eu</b>). Senza, OpenRGB 1.x non li rileva. È consigliato OpenRGB 1.0 o successivo.',
        'help.s1.fail': 'Se la connessione non riesce, controlla host, porta e percorso di OpenRGB in <a href="settings.html">Impostazioni</a>.',
        'help.s2.intro': 'Apri la pagina <a href="topology-editor.html">Topologia</a>. Al primo avvio le zone dei tuoi dispositivi vengono importate automaticamente da OpenRGB (il pulsante <b>Ricarica</b> lo rifà in qualsiasi momento).',
        'help.s2.screen': 'Il rettangolo <b>SCHERMO</b> sul canvas è il tuo monitor. Trascinane angoli e bordi in modo che stia dove si trovano le strisce attorno al monitor (<b>Adatta</b> gli fa coprire tutte le zone, come punto di partenza).',
        'help.s2.flip': 'Il piccolo 0 indica dove si trova il LED 0 di una zona. Se i colori scorrono nel verso sbagliato lungo un lato, premi <b>Inverti direzione</b> (o <b>F</b>): il LED 0 passa all\'altra estremità. Poi premi <b>Salva topologia</b>.',
        'help.s2.tip': 'Suggerimento: una striscia che gira attorno al monitor richiede una zona per lato. Dividila in segmenti in OpenRGB (Resizable zones &amp; segments), poi premi <b>Ricarica</b>. Le zone che OpenRGB chiama &ldquo;???&rdquo; sono LED che non esistono sull\'hardware: EDAmbilight le esclude da tutto.',
        'help.s3.devices': 'In <a href="devices.html">Dispositivi</a> accendi o spegni ogni dispositivo e, sotto <b>Zone</b>, scegli quali sue zone usare. Anche le tastiere sono elencate e partono spente; i loro tasti mostrano la parte di schermo sotto cui si trovano. L\'anteprima in alto mostra cosa cambia. La pagina Controllo ha gli stessi interruttori in una riga compatta.',
        'help.s3.enable': 'Accendi l\'interruttore <b>Attiva</b> nel pannello Stato. L\'anello pulsa quando l\'ambilight è in funzione.',
        'help.s4.info': 'Passa il mouse (o arriva con Tab) sulla <b>i</b> accanto al titolo di ogni pannello per vedere cosa fa ogni parametro e cosa succede quando lo alzi o lo abbassi.',
        'help.s4.preset': 'Scegli un <b>preset</b> per partire subito: <b>Bilanciato</b> per l\'uso di tutti i giorni, <b>Cinema</b> per film e serie, <b>Gaming</b> per i giochi d\'azione (sparatutto, corse: segue l\'immagine rapidamente), <b>Calmo</b> per strategici e gestionali, il desktop e la lettura (cambi lenti e stabili); <b>Ripristina</b> riporta i valori predefiniti e <b>Avanzate</b> mostra o nasconde i cursori di regolazione fine.',
        'help.s4.notused': 'I parametri che l\'algoritmo selezionato non usa sono attenuati e hanno il badge <b>Non usato</b>.',
        'help.s4.standby': 'Scegli cosa fanno i LED quando lo schermo va in sospensione o si blocca in <b>Standby schermo</b> (dissolvenza, pulsazione, aurora e altro); l\'impostazione predefinita mantiene gli ultimi colori.',
        'help.gtk.black': '<b>Schermo nero / LED spenti:</b> i video protetti (HDCP), come quelli di alcune app di streaming, non possono essere catturati. Prova un altro <b>Motore di cattura</b> nella pagina Controllo.',
        'help.gtk.fullscreen': '<b>Giochi a schermo intero esclusivo:</b> scegli <b>DXGI</b> come motore di cattura.',
        'help.gtk.window': '<b>Finestra chiusa:</b> l\'app resta attiva nell\'area di notifica. Fai clic destro sulla sua icona per riaprirla o uscire.',
        'help.gtk.slow': '<b>Avvio lento:</b> quando è EDAmbilight ad avviare OpenRGB, il primo avvio può richiedere circa 15 secondi in più mentre OpenRGB rileva l\'hardware. L\'app aspetta per non perdere nessun dispositivo.',
        'help.gtk.theme': '<b>Chiaro o scuro:</b> il pulsante sole / luna in fondo alla barra laterale (nell\'intestazione del pannello in Anteprima live) cambia il tema. La scelta viene ricordata.',
        'help.gtk.updates': '<b>Nuove versioni:</b> quando esce una release più recente, un avviso in alto a destra rimanda alla sua pagina (novità, download). Nulla viene scaricato o installato per te: estrai il nuovo zip e copiaci dentro la tua cartella <b>config</b>. <b>Salta questa versione</b> lo nasconde per sempre. Per saperlo, l\'app interroga GitHub all\'avvio, al massimo una volta al giorno; puoi disattivarlo in <a href="settings.html">Impostazioni</a> &gt; Informazioni.',
        'help.gtk.logs': 'I log vengono scritti in <b>log/edambilight.log</b> accanto all\'exe.',
    },
});

// Sidebar: 80px wide, a shorter word where the usual one does not fit (data-i18n="nav.<page>")
EDI18n.add('it', {
    html: {
        'nav.settings': 'Opzioni',
    },
});
