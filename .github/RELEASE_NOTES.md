## Italiano

### Correzioni

- PDF su Windows: lettura UTF-8 esplicita delle risorse e separatore “:” nei titoli, per evitare caratteri alterati.
- Multidisciplinare non assegnabile a medici assenti, in ferie o in recupero; controllo in entrambi gli ordini di inserimento.
- Avvisi per sovrapposizioni tra incarichi mattutini, estesi a Reparto, ACC-W.S., Guardia diurna, Reperibilità e Ambulatorio del mattino. Gli incarichi pomeridiani non vengono evidenziati per queste sovrapposizioni.

turniamo: pianificazione locale dei turni ospedalieri, in italiano e inglese.

- **Windows x64:** scarica e apri `turniamo-Windows.exe` (portatile, nessun installer).
- **macOS Apple Silicon (M1 o successivi):** scarica `turniamo-macOS-AppleSilicon.zip`, estrailo e trascina `turniamo.app` in Applicazioni. Richiede macOS 14 o successivo; non è una build per Mac Intel.

Python non è necessario. I pacchetti non hanno firma di distribuzione né notarizzazione: il sistema può mostrare un avviso al primo avvio. Su macOS, dopo aver tentato l’apertura, autorizza l’app da **Impostazioni di Sistema → Privacy e sicurezza → Apri comunque**.

L’app crea un archivio locale vuoto: nessun dato dei medici è incluso. Per aggiornare, chiudi l’app e sostituisci l’eseguibile o il bundle; l’archivio resta nella cartella dati dell’utente. Prima di aggiornare puoi esportare una copia del database dal menu ingranaggio.

## English

### Fixes

- Windows PDFs: explicit UTF-8 resource decoding and “:” heading separators prevent corrupted characters.
- Multidisciplinary assignments cannot coexist with absence, vacation or compensatory leave, regardless of insertion order.
- Morning overlap warnings now cover Ward, ACC-W.S., day duty, morning on-call and morning clinic as well as operating rooms. Afternoon assignments are not highlighted for these overlaps.

turniamo: offline hospital shift planning, in Italian and English.

- **Windows x64:** download and open `turniamo-Windows.exe` (portable, no installer).
- **macOS Apple Silicon (M1 or later):** download `turniamo-macOS-AppleSilicon.zip`, extract it and drag `turniamo.app` into Applications. Requires macOS 14 or later; this is not an Intel Mac build.

Python is not required. Packages are not distribution-signed or notarized, so your system may show a warning on first launch. On macOS, after attempting to open the app, allow it in **System Settings → Privacy & Security → Open Anyway**.

The app creates an empty local archive: no doctor data is included. To update, close the app and replace the executable or app bundle; the archive stays in your user data directory. Before updating, you can export a database backup from the gear menu.

---

Licenza / License: BSD-3-Clause, Copyright © 2026 Antonino Maria Rizzo. See [LICENSE](https://github.com/antoninomariarizzo/turniamo/blob/main/LICENSE). Dependencies retain their own licenses.

`SHA256SUMS.txt` contains SHA-256 checksums for both downloads.
