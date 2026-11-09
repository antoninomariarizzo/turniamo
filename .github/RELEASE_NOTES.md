## Italiano

### Correzioni e novità

- **Smonto notte:** nel giorno di S.N. sono consentiti Reperibilità notturna e Ambulatorio AM/PM a pagamento, evidenziati in giallo. Gli altri incarichi restano bloccati. Il selettore indica quando l’ambulatorio deve essere pagato; il controllo vale anche per smonto manuale e in entrambi gli ordini di inserimento.
- **Recuperi annuali:** nuova colonna nel Riepilogo annuale con il numero di incarichi Recupero per persona nell’intero anno e il dettaglio delle date. Inclusa in PDF ed Excel.
- **Esclusività giornaliera:** una sola attività per medico tra CHIR 1/2/3, Reparto, ACC-W.S. e Guardia diurna/notturna, indipendentemente dall’orario. Guardia con Ambulatorio/Reperibilità resta consentita solo senza sovrapposizioni, con avviso giallo.
- **Fine settimana:** CHIR 1/2/3, Reparto e ACC-W.S. sono disabilitati sabato e domenica. Reperibilità mattutina compare solo il sabato, anche negli export.
- **Ambulatorio PM:** label anticipata alle 14:30; ore invariate, 4h dopo sala e 4h30m altrimenti.
- **Dettagli turno:** selezione della persona associata tramite tre opzioni visibili, eliminando la dipendenza dal popup nativo problematico su Windows. Aggiunto il pulsante Elimina turno; lo smonto automatico si rimuove dalla notte di origine.
- README bilingue e immagine dimostrativa aggiornati. I dati storici incompatibili restano conservati e segnalati.

### Download e aggiornamento

- **Windows x64:** `turniamo-Windows.exe`, portatile, senza installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; estrarre e sostituire `turniamo.app`. Non è una build per Mac Intel.

Python non è necessario. Chiudere l’app prima di sostituirla; i dati restano nella cartella utente. È consigliata una copia del database dal menu Impostazioni prima dell’aggiornamento. Lo schema SQLite resta alla versione 3. Nessun dato dei medici è incluso nei pacchetti.

I pacchetti non hanno firma di distribuzione né notarizzazione. Per requisiti di sistema e primo avvio, consultare il [README](https://github.com/antoninomariarizzo/turniamo#readme).

## English

### Fixes and additions

- **Post-night rest:** Night on-call and paid AM/PM clinics are allowed on the post-night day, highlighted in yellow. Other duties remain blocked. The picker indicates when a clinic must be paid; validation also covers manual post-night entries and either insertion order.
- **Annual time off in lieu:** new Annual summary column counts each person’s recovery assignments across the whole year, with date details. Included in PDF and Excel exports.
- **Daily exclusivity:** one assignment per doctor among SURG 1/2/3, Ward, ACC-W.S. and Day/Night duty, regardless of time. Duty combined with clinic/on-call remains allowed only without overlapping times, with a yellow warning.
- **Weekends:** SURG 1/2/3, Ward and ACC-W.S. are disabled on Saturdays and Sundays. Morning on-call appears only on Saturdays, including in exports.
- **PM clinic:** displayed start changed to 14:30; credited hours remain 4h after surgery and 4h30m otherwise.
- **Shift details:** three visible associated-person options replace the native popup that was problematic on Windows. Added Delete shift; automatic post-night entries are removed through their originating night.
- Updated bilingual README and demo image. Incompatible historical data is preserved and flagged.

### Downloads and updating

- **Windows x64:** `turniamo-Windows.exe`, portable, no installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; extract and replace `turniamo.app`. This is not an Intel Mac build.

Python is not required. Close the app before replacing it; data stays in your user folder. A database backup from Settings is recommended before updating. The SQLite schema remains at version 3. Packages contain no doctor data.

Packages are not distribution-signed or notarized. See the [README](https://github.com/antoninomariarizzo/turniamo#readme) for system requirements and first-launch instructions.

---

Licenza / License: BSD-3-Clause, Copyright © 2026 Antonino Maria Rizzo. Dependencies retain their own licenses.

`SHA256SUMS.txt` contains SHA-256 checksums for both downloads.
