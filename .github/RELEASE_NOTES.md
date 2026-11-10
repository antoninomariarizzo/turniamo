## Italiano

### Correzioni

- **Ferie/Corsi:** aggiornata l’etichetta della colonna del calendario; credito invariato a 6h20m.
- **Turni mensili:** pulsante info accanto a ogni contatore, anche zero, con date, attività e indicazione del pagamento degli incarichi inclusi nell’intero mese.
- **Recupero: 0 ore**, come Assenza, senza sottrarre ore già lavorate. Le colonne rimangono separate; invariati i vincoli di disponibilità e il conteggio annuale dei recuperi. La regola si applica anche agli incarichi già presenti e ai totali negli export PDF/Excel.
- Aggiornati testi esplicativi e README italiano/inglese.

### Download e aggiornamento

- **Windows x64:** `turniamo-Windows.exe`, portatile, senza installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; estrarre e sostituire `turniamo.app`. Non è una build per Mac Intel.

Python non è necessario. Chiudere l’app prima di sostituirla; i dati restano nella cartella utente. È consigliata una copia del database dal menu Impostazioni prima dell’aggiornamento. Lo schema SQLite resta alla versione 3. Nessun dato dei medici è incluso nei pacchetti.

I pacchetti non hanno firma di distribuzione né notarizzazione. Per requisiti di sistema e primo avvio, consultare il [README](https://github.com/antoninomariarizzo/turniamo#readme).

## English

### Fixes

- **Leave/Courses:** updated calendar column label; the 6h20m credit is unchanged.
- **Monthly shifts:** an info button beside every count, including zero, lists dates, activities and payment status for assignments included across the whole month.
- **Time off in lieu: 0 hours**, like Absence, without deducting hours already worked. The columns remain separate; availability rules and annual recovery counts are unchanged. The calculation also applies to existing assignments and PDF/Excel totals.
- Updated explanatory text and Italian/English README.

### Downloads and updating

- **Windows x64:** `turniamo-Windows.exe`, portable, no installer.
- **macOS Apple Silicon:** `turniamo-macOS-AppleSilicon.zip`; extract and replace `turniamo.app`. This is not an Intel Mac build.

Python is not required. Close the app before replacing it; data stays in your user folder. A database backup from Settings is recommended before updating. The SQLite schema remains at version 3. Packages contain no doctor data.

Packages are not distribution-signed or notarized. See the [README](https://github.com/antoninomariarizzo/turniamo#readme) for system requirements and first-launch instructions.

---

Licenza / License: BSD-3-Clause, Copyright © 2026 Antonino Maria Rizzo. Dependencies retain their own licenses.

`SHA256SUMS.txt` contains SHA-256 checksums for both downloads.
