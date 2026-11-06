## Italiano

### Novità

- Barra semplificata: Calendario, Ore settimanali, Turni mensili e Riepilogo annuale; icone Medici, Esporta e Impostazioni in alto a destra. Excel e PDF includono tutte e quattro le sezioni.
- Recupero e smonto notte incompatibili, anche tra settimane diverse.
- Terza fascia di reperibilità 20:00–08:00, senza ore né conteggi; mattina successiva in arancione, pomeriggio disponibile.
- Conteggi annuali degli ambulatori e delle notti a pagamento, con dettagli.

- CHIR 1, CHIR 2 e CHIR 3; nuova colonna informativa Multidisciplinare da zero ore.
- Smonto notte: avviso su tutti i turni della giornata; dopo reperibilità notturna, avviso solo al mattino. La cella S.N. non viene evidenziata.
- Riepilogo mensile degli incarichi e riepilogo annuale delle festività, con selettori di periodo.
- Festività comprensive delle ore dopo mezzanotte, con elenchi e dettagli tramite icone “i”; riepiloghi aperti sul periodo della settimana visualizzata.
- Backup automatico prima dell’aggiornamento dell’archivio; usare v0.1.4 o successive per riaprirlo.

turniamo: pianificazione locale dei turni ospedalieri, in italiano e inglese.

- **Windows x64:** scarica e apri `turniamo-Windows.exe` (portatile, nessun installer).
- **macOS Apple Silicon (M1 o successivi):** scarica `turniamo-macOS-AppleSilicon.zip`, estrailo e trascina `turniamo.app` in Applicazioni. Richiede macOS 14 o successivo; non è una build per Mac Intel.

Python non è necessario. I pacchetti non hanno firma di distribuzione né notarizzazione: il sistema può mostrare un avviso al primo avvio. Su macOS, dopo aver tentato l’apertura, autorizza l’app da **Impostazioni di Sistema → Privacy e sicurezza → Apri comunque**.

L’app crea un archivio locale vuoto: nessun dato dei medici è incluso. Per aggiornare, chiudi l’app e sostituisci l’eseguibile o il bundle; l’archivio resta nella cartella dati dell’utente. Prima di aggiornare puoi esportare una copia del database dal menu ingranaggio.

## English

### Changes

- Simplified toolbar: Calendar, Weekly hours, Monthly shifts and Annual summary; Doctors, Export and Settings icons at the top right. Excel and PDF include all four sections.
- Compensatory leave and night-off are mutually exclusive, including across weeks.
- Third on-call slot, 20:00–08:00, with zero hours and no counts; following morning highlighted, afternoon available.
- Annual paid clinic and paid night counts, with details.

- SURG 1, SURG 2 and SURG 3; informational Multidisciplinary column with zero hours.
- Post-night rest warns on every assignment that day; night on-call warns only on the following morning. The night-off cell itself is not highlighted.
- Monthly assignment counts and annual holiday attendance counts, with period selectors.
- Holiday attendance includes hours after midnight, with information buttons for holiday lists and count details; reports open on the displayed week’s period.
- Automatic backup before archive upgrade; use v0.1.4 or later to reopen it.

turniamo: offline hospital shift planning, in Italian and English.

- **Windows x64:** download and open `turniamo-Windows.exe` (portable, no installer).
- **macOS Apple Silicon (M1 or later):** download `turniamo-macOS-AppleSilicon.zip`, extract it and drag `turniamo.app` into Applications. Requires macOS 14 or later; this is not an Intel Mac build.

Python is not required. Packages are not distribution-signed or notarized, so your system may show a warning on first launch. On macOS, after attempting to open the app, allow it in **System Settings → Privacy & Security → Open Anyway**.

The app creates an empty local archive: no doctor data is included. To update, close the app and replace the executable or app bundle; the archive stays in your user data directory. Before updating, you can export a database backup from the gear menu.

---

Licenza / License: BSD-3-Clause, Copyright © 2026 Antonino Maria Rizzo. See [LICENSE](https://github.com/antoninomariarizzo/turniamo/blob/main/LICENSE). Dependencies retain their own licenses.

`SHA256SUMS.txt` contains SHA-256 checksums for both downloads.
