## Italiano

### Correzioni

- La Reperibilità pomeridiana **14:00–18:00 del sabato e della domenica vale 0 ore**, anche per gli incarichi già presenti nell’archivio.
- Il conteggio dal lunedì al venerdì resta invariato: 4 ore, oppure 3 ore dopo sala.
- La regola è condivisa dai totali dell’interfaccia e dalle esportazioni PDF ed Excel. README bilingue aggiornato.

### Download e aggiornamento

- **Windows x64:** `turniamo-Windows.exe`, portatile, senza installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; estrarre e sostituire `turniamo.app`. Non è una build per Mac Intel.

Python non è necessario. Chiudere l’app prima di sostituirla; i dati restano nella cartella utente. È consigliata una copia del database dal menu Impostazioni prima dell’aggiornamento. Lo schema SQLite resta alla versione 3. Nessun dato dei medici è incluso nei pacchetti.

I pacchetti non hanno firma di distribuzione né notarizzazione. Per requisiti di sistema e primo avvio, consultare il [README](https://github.com/antoninomariarizzo/turniamo#readme).

## English

### Fixes

- **Saturday and Sunday afternoon on-call (14:00–18:00) now credits 0 hours**, including assignments already in the archive.
- Monday–Friday hours remain unchanged: 4 hours, or 3 hours after surgery.
- UI totals and PDF/Excel exports share the corrected calculation. Updated bilingual README.

### Downloads and updating

- **Windows x64:** `turniamo-Windows.exe`, portable, no installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; extract and replace `turniamo.app`. This is not an Intel Mac build.

Python is not required. Close the app before replacing it; data stays in your user folder. A database backup from Settings is recommended before updating. The SQLite schema remains at version 3. Packages contain no doctor data.

Packages are not distribution-signed or notarized. See the [README](https://github.com/antoninomariarizzo/turniamo#readme) for system requirements and first-launch instructions.

---

Licenza / License: BSD-3-Clause, Copyright © 2026 Antonino Maria Rizzo. Dependencies retain their own licenses.

`SHA256SUMS.txt` contains SHA-256 checksums for both downloads.
