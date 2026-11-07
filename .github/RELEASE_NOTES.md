## Italiano

### Correzioni

- **Reparto e ACC-W.S.** accettano un solo medico per cella. Rimossa l’opzione Aiuto reparto.
- **Ore Reparto:** 8h se nello stesso giorno è assegnato un medico ad ACC-W.S., altrimenti 9h. ACC-W.S. vale 6h30m.
- **Un incarico per fascia:** bloccate le sovrapposizioni tra sale, Reparto, ACC-W.S., Guardia, Ambulatorio e Reperibilità. Guardia diurna e notturna restano incompatibili nella stessa data. Restano consentite sala al mattino + Ambulatorio/Reperibilità pomeridiana.
- **Selettori uniformi:** i medici incompatibili restano visibili, grigi e non selezionabili, con il motivo del blocco. Il controllo vale anche per salvataggi singoli e multipli, in entrambi gli ordini di inserimento.
- README e immagine dimostrativa aggiornati. I conflitti già presenti nell’archivio sono segnalati senza cancellare automaticamente gli incarichi.

### Download e aggiornamento

- **Windows x64:** `turniamo-Windows.exe`, portatile, senza installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; estrarre e sostituire `turniamo.app`. Non è una build per Mac Intel.

Python non è necessario. Chiudere l’app prima di sostituirla; i dati restano nella cartella utente. È consigliata una copia del database dal menu Impostazioni prima dell’aggiornamento. Lo schema SQLite resta alla versione 3. Nessun dato dei medici è incluso nei pacchetti.

I pacchetti non hanno firma di distribuzione né notarizzazione. Per requisiti di sistema e primo avvio, consultare il [README](https://github.com/antoninomariarizzo/turniamo#readme).

## English

### Fixes

- **Ward and ACC-W.S.** allow one doctor per slot. Removed the Ward help option.
- **Ward hours:** 8h when a doctor is assigned to ACC-W.S. on the same day, otherwise 9h. ACC-W.S. counts as 6h30m.
- **One duty per time band:** overlapping assignments across operating rooms, Ward, ACC-W.S., duty, clinic and on-call are blocked. Day and night duty remain incompatible on the same date. Morning surgery + PM clinic/on-call remain allowed.
- **Consistent pickers:** incompatible doctors remain visible, grey and disabled, with the reason for the conflict. Single and bulk saves enforce the same rules in either insertion order.
- Updated README and demo image. Existing conflicts in the archive are flagged without automatically deleting assignments.

### Downloads and updating

- **Windows x64:** `turniamo-Windows.exe`, portable, no installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; extract and replace `turniamo.app`. This is not an Intel Mac build.

Python is not required. Close the app before replacing it; data stays in your user folder. A database backup from Settings is recommended before updating. The SQLite schema remains at version 3. Packages contain no doctor data.

Packages are not distribution-signed or notarized. See the [README](https://github.com/antoninomariarizzo/turniamo#readme) for system requirements and first-launch instructions.

---

Licenza / License: BSD-3-Clause, Copyright © 2026 Antonino Maria Rizzo. Dependencies retain their own licenses.

`SHA256SUMS.txt` contains SHA-256 checksums for both downloads.
