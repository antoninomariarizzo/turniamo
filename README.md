<div align="center">

<img src="turniamo/assets/turniamo.png" alt="turniamo App Icon" width="180" />

# turniamo

<p>
<a href="https://github.com/antoninomariarizzo/turniamo/releases/latest/download/turniamo-Windows.exe"><img src="https://img.shields.io/badge/Download%20for-Windows-0078D6?style=for-the-badge&amp;logo=windows&amp;logoColor=white" alt="Download for Windows" /></a>
<a href="https://github.com/antoninomariarizzo/turniamo/releases/latest/download/turniamo-macOS-AppleSilicon.zip"><img src="https://img.shields.io/badge/Download%20for-macOS-000000?style=for-the-badge&amp;logo=apple&amp;logoColor=white" alt="Download for macOS" /></a>
</p>

<sub>🪟 Windows portable (x64) · 🍎 macOS (Apple Silicon)</sub>

</div>

[Italiano](#italiano) · [English](#english)

## Italiano

Applicazione locale per turni ospedalieri. Python gestisce calcoli e archivio SQLite;
HTML/CSS/JavaScript costruiscono l’interfaccia dentro una finestra desktop Qt WebEngine.
Un unico progetto per Windows e macOS, con italiano e inglese. Non occorrono account,
server, connessione Internet o servizi esterni durante l’uso.

### Download e installazione

Scarica la versione pronta dai pulsanti in alto o dalla pagina
[Releases](https://github.com/antoninomariarizzo/turniamo/releases/latest).
Non occorre installare Python.

- **Windows (x64):** scarica `turniamo-Windows.exe` e aprilo. È un eseguibile portatile,
  senza procedura di installazione.
- **macOS (Apple Silicon, M1 o successivi):** scarica `turniamo-macOS-AppleSilicon.zip`,
  estrailo e trascina `turniamo.app` in Applicazioni. Il pacchetto non è per Mac Intel.

I pacchetti non hanno firma di distribuzione né notarizzazione: macOS e Windows
possono mostrare un avviso di sicurezza al primo avvio. Su macOS, dopo aver tentato
l’apertura, usa **Impostazioni di Sistema → Privacy e sicurezza → Apri comunque**
per autorizzare l’app scaricata da questo repository.

L’app parte con un archivio vuoto. I dati inseriti restano nella cartella locale
dell’utente: database, backup ed esportazioni non sono inclusi nel repository o nei download.

### Avvio dai sorgenti

Python 3.11 o successivo (consigliato 3.12). Per le versioni correnti di Qt serve macOS 14+
o Windows recente.

macOS, dalla cartella del progetto:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m turniamo
```

Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m turniamo
```

Per i successivi avvii basta l’ultimo comando. La cartella dati è separata dall’app;
si può sceglierla con `--data-dir /percorso/archivio`.

### Interfaccia

- Quattro schede: **Calendario** (icona), **Ore settimanali**, **Turni mensili**, **Riepilogo annuale**. Medici, Esporta e Impostazioni sono accessibili dalle icone in alto a destra.
- Tabella compatta di default. Giorni nel formato `07 LU`, `08 MA`, ecc. In inglese `07 MO`.
- Tre sale: **CHIR 1**, **CHIR 2** e **CHIR 3**; **Reparto**; **ACC-W.S.**;
  **Guardia** con giorno/notte; **Reperibilità** e **Ambulatorio** con mattino/pomeriggio;
  **S.N.**, **Assenza**, **Ferie**, **Recupero**.
- Le fasce mostrano gli orari esatti: sale 07:45–15:00; reparto 07:45–17:00;
  ACC-W.S. 07:45–14:00; guardia 07:45–20:30 / 19:45–08:30;
  reperibilità 07:45–14:00 / 14:00–18:00 / 20:00–08:00; ambulatorio 07:45–13:30 / 15:00–19:00.
  Queste etichette non modificano i pesi orari concordati.
- Un clic su una cella apre l’elenco dei medici. Si possono cercare e spuntare più nomi
  senza chiudere il menu. **✓ Conferma / Invio** salva insieme le scelte; **✕ Annulla / Esc**
  chiude senza modificarle. Anche cliccare fuori dal menu annulla le scelte non confermate.
- Il pulsante `…` accanto a un incarico apre pagamento, persona in formazione e referente.
- Il primo medico del reparto è responsabile, gli altri sono aiuti nella stessa cella.
  Se il responsabile viene rimosso, uno degli aiuti diventa responsabile automaticamente.
- Nel riepilogo, il nome identifica la riga; ci sono soltanto **Ore ordinarie**,
  **Ore a pagamento** e **Stato**. Le ordinarie mostrate includono ferie e recuperi;
  lo stato evidenzia soltanto chi supera le 40h. Accanto a ogni totale, il pulsante
  informazioni mostra giorno, attività e contributo di ciascun incarico.
- Nella scheda Medici, clic sul nome per rinominarlo, Invio o uscita dal campo per salvare.
  Il cestino elimina il medico dalla settimana selezionata e dalle successive, con i suoi incarichi.
- L’ingranaggio contiene lingua, esportazione e importazione database. L’icona di
  condivisione contiene Excel e PDF. Per stampare si apre il PDF.

### Storico e copie di sicurezza

Ogni settimana conserva l’elenco dei propri medici e i nomi di quel periodo. Eliminare o
rinominare un medico non modifica le settimane precedenti a quella selezionata.
Un medico rimosso rimane visibile nei vecchi orari, con un’indicazione discreta che non
fa più parte del gruppo attuale. I nomi della settimana devono essere univoci.

Il file locale è `turniamo.sqlite3`, nella cartella dati dell’utente. Su macOS:
`~/Library/Application Support/turniamo/turniamo/`; su Windows Qt usa la cartella locale
dell’utente. Il database contiene medici, settimane, incarichi e lingua.

L’importazione sostituisce l’archivio solo dopo verifica del database e conferma. Prima
della sostituzione salva una copia nella sottocartella `backups`. Anche la migrazione dalla
prima versione crea una copia: gli incarichi della vecchia colonna **Aiuto reparto**
vengono eliminati; quelli di **CHIR 3** sono conservati. La nuova versione gestisce eventuali
aiuti futuri dentro Reparto. L’importazione di vecchi file Excel non è inclusa.

### Riepiloghi mensili e festività

**Multidisciplinare**, tra Ambulatorio e S.N., è una colonna informativa: zero ore,
nessun conteggio nei riepiloghi e nessuna attività a pagamento. Richiede comunque la presenza: non può coesistere con Assenza, Ferie o Recupero.

Il riepilogo mensile si apre sul mese del lunedì della settimana visualizzata; il selettore permette di consultare altri mesi.
Conta gli incarichi di CHIR 1/2/3 in tutti i giorni; guardie, reperibilità e ambulatorio
solo dal lunedì al venerdì. Sabato/Domenica giorno/notte contano esclusivamente le guardie.
Mattina e pomeriggio di ambulatorio o reperibilità sono incarichi distinti.

Il riepilogo annuale si apre sull’anno del lunedì della settimana visualizzata ed è consultabile anche per altri anni.
Conta una presenza per medico al giorno, indipendentemente dal numero di incarichi,
includendo il lavoro a pagamento e le prime ore dello smonto notte; sono esclusi assenze, ferie, recuperi e Multidisciplinare.
Festività: 25 aprile, 1 maggio, 2 giugno, 4 ottobre, 1 novembre, 8 e 26 dicembre.
Festività speciali: 1 e 6 gennaio, Pasqua, Pasquetta, 15 agosto e 25 dicembre.
In caso di coincidenza la data conta solo fra le festività speciali.
Nel mensile le notti contano nel giorno di inizio; nelle festività conta anche il giorno dello smonto, se festivo. Le icone “i” mostrano le festività incluse e il dettaglio di ogni totale. I riepiloghi includono tutti gli incarichi registrati
nel periodo, anche quelli pianificati, e conservano le persone rimosse.

L’aggiornamento crea una copia dell’archivio prima di portarlo alla versione 3.
Usare la v0.1.4 o successive per riaprire l’archivio aggiornato.

### Conteggi

| Attività | Ore per medico |
| --- | --- |
| Sala | 7h |
| Ambulatorio mattino | 6h |
| Ambulatorio pomeriggio | 4h30m; 4h dopo sala |
| Reperibilità pomeriggio | 4h; 3h dopo sala |
| Reperibilità mattino | 6h30m, solo sabato |
| Reparto, responsabile | 9h solo; 8h con aiuto |
| Reparto, aiuto / ACC-W.S. | 6h30m |
| Guardia diurna | 13h |
| Guardia notturna | 6h30m + 6h30m nello smonto del giorno successivo |
| Assenza | 0h |
| Ferie | +6h20m |
| Recupero | −6h20m |

Le durate sono memorizzate in minuti interi: 6h20m = 380 minuti. Le combinazioni sala +
ambulatorio PM e sala + reperibilità PM valgono 11h e 10h.

La segnalazione oltre 40h usa lavoro ordinario + ferie prima della sottrazione dei recuperi.
Non vengono segnalati i totali sotto le 38h.
Le attività a pagamento, incluso lo smonto di una notte a pagamento, sono sempre separate.
Referenti e persone in formazione non ricevono ore e non hanno controlli di disponibilità.

Guardia notturna lunedì → smonto notte martedì: tutti i turni assegnati martedì sono in arancione, anche nel pomeriggio. Reperibilità notturna lunedì → solo i turni mattutini di martedì in arancione, pomeriggio disponibile. La cella S.N. e mercoledì non ricevono questo avviso. La reperibilità notturna è informativa: zero ore, esclusa dai conteggi e non genera S.N.
Recupero e S.N. sono incompatibili: anche la notte precedente a un recupero è disabilitata.
Il riepilogo annuale include ambulatori e notti a pagamento: ogni fascia ambulatoriale conta un incarico, ogni notte conta una volta nella data di inizio, anche nel fine settimana.
Assenza, ferie e recupero impediscono incarichi lavorativi nello stesso giorno. Lo smonto
è derivato automaticamente anche tra settimane; si modifica dalla notte di origine.
Se manca la notte precedente nell’archivio è possibile inserire S.N. manualmente.

L’Excel esportato usa le stesse colonne, fasce sovrapposte e un riepilogo con formule.
Excel e PDF includono Calendario, Ore settimanali, Turni mensili e Riepilogo annuale. Il PDF usa lo stesso HTML/CSS dell’interfaccia, con ciascuna sezione su pagine separate.
Il dettaglio in minuti è in un foglio interno nascosto. Excel/LibreOffice ricalcolano le
formule all’apertura. Nel riepilogo numerico 6h20m = 6,333… ore, visualizzate con due decimali;
i calcoli mantengono i minuti esatti.

Gli incarichi mattutini contemporanei (sale, Reparto, ACC-W.S., Guardia diurna, Reperibilità e Ambulatorio del mattino) sono evidenziati in arancione. Gli incarichi pomeridiani non ricevono questo avviso.

### Pacchetti desktop

```sh
.venv/bin/python scripts/build.py
```

Eseguire sul sistema di destinazione: `dist/turniamo.exe` per Windows (nessuna installazione
di Python richiesta), `dist/turniamo.app` per macOS. WebEngine è incluso e rende il
pacchetto più grande. I pacchetti locali non hanno firma di distribuzione/notarizzazione.
Il workflow GitHub crea e prova entrambi i pacchetti. Un tag come `v0.1.4`, corrispondente
alla versione in `pyproject.toml`, pubblica una Release solo dopo il successo di entrambe
le build e delle verifiche. I pulsanti di download puntano sempre all’ultima Release.
Da **Actions → Test and package desktop app → Run workflow** si possono creare build
di verifica senza pubblicare una Release, scaricando gli artefatti `turniamo-Windows`
e `turniamo-macOS-AppleSilicon`.

### Verifica

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/preview.py
.venv/bin/python scripts/smoke_packaged.py
```

I test coprono conteggi, storico per settimana, importazione/migrazione, interazione con
la UI HTML e PDF/Excel. Le anteprime usano dati fittizi e non modificano l’archivio reale.

Su Windows usare `.venv\Scripts\python` al posto di `.venv/bin/python` anche per
build e verifiche. La cartella del progetto e il modulo Python si chiamano `turniamo`.
`build/`, `dist/`, `test-output/` e le cache sono artefatti generati e possono essere
rimossi e ricreati; non contengono l’archivio utente predefinito. Dopo aver spostato il
progetto, ricreare `.venv` e reinstallare le dipendenze: gli ambienti virtuali
memorizzano percorsi assoluti.

### Licenza

Il codice di turniamo è distribuito con licenza [BSD-3-Clause](LICENSE),
Copyright © 2026 Antonino Maria Rizzo. Le dipendenze mantengono le proprie licenze.

## English

A local hospital shift planner. Python handles calculations and SQLite storage;
HTML/CSS/JavaScript provide the interface inside a Qt WebEngine desktop window.
The same project supports Windows and macOS, in Italian and English. No accounts,
servers, Internet connection or external services are required during use.

### Download and installation

Use the download buttons above or visit
[Releases](https://github.com/antoninomariarizzo/turniamo/releases/latest).
Python is not required for the packaged application.

- **Windows (x64):** download and open `turniamo-Windows.exe`. This is a portable
  executable with no installation wizard.
- **macOS (Apple Silicon, M1 or later):** download `turniamo-macOS-AppleSilicon.zip`,
  extract it and drag `turniamo.app` into Applications. This package is not for Intel Macs.

Packages are not distribution-signed or notarized, so macOS and Windows may show a
security warning on first launch. On macOS, after attempting to open the app, use
**System Settings → Privacy & Security → Open Anyway** to allow the app downloaded
from this repository.

The application starts with an empty archive. Entered data stays in the user's local
data directory: databases, backups and exports are not included in the repository or downloads.

### Running from source

Requires Python 3.11 or later (3.12 recommended). Current Qt versions require macOS 14+
or a recent Windows version.

On macOS, from the project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m turniamo
```

On Windows (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m turniamo
```

For later launches, only the last command is needed. The data directory is separate
from the application; select a custom location with `--data-dir /path/to/archive`.
Use the gear menu to switch the interface language.

### Interface

- Four tabs: **Calendar** (icon), **Weekly hours**, **Monthly shifts**, **Annual summary**. Doctors, Export and Settings are available through the top-right icons.
- Compact table by default, with day labels such as `07 MO` (`07 LU` in Italian).
- Three operating rooms: **SURG 1**, **SURG 2** and **SURG 3**; ward; **ACC-W.S.**;
  day/night duty; morning/afternoon on-call and outpatient clinic; post-night rest,
  absence, vacation and compensatory leave.
- Time labels: operating rooms 07:45–15:00; ward 07:45–17:00; ACC-W.S. 07:45–14:00;
  duty 07:45–20:30 / 19:45–08:30; on-call 07:45–14:00 / 14:00–18:00 / 20:00–08:00;
  outpatient clinic 07:45–13:30 / 15:00–19:00. These labels do not change the agreed
  hour credits listed below.
- Click a cell to open the doctor picker. Search and select multiple names, then
  **Confirm / Enter** to save them together. **Cancel / Esc**, or clicking outside
  the picker, discards unconfirmed changes.
- The `…` button beside an assignment opens payment, trainee and supervisor options.
- The first ward doctor is the lead; additional doctors are assistants in the same
  cell. Removing the lead automatically promotes an assistant.
- The hours summary shows **Ordinary hours**, **Paid hours** and **Status** for each
  doctor. Ordinary totals include vacation and compensatory leave; status highlights
  only totals exceeding 40 hours. Each total has an information button showing the
  date, activity and credit of every assignment.
- In Doctors, click a name to rename it; Enter or leaving the field saves it.
  The trash button removes the doctor and their assignments from the selected week
  and subsequent weeks.
- The gear menu contains language settings and database import/export. The share
  icon exports Excel and PDF. Open the PDF to print it.

### History and backups

Each week preserves its own roster and doctor names. Renaming or removing a doctor
leaves earlier weeks unchanged. Removed doctors remain visible in historical schedules,
with a discreet indication that they are no longer part of the current team.
Names must be unique within each week.

The local database is `turniamo.sqlite3` in the user's data directory. On macOS:
`~/Library/Application Support/turniamo/turniamo/`. On Windows, Qt uses the user's
local application data directory. The database stores doctors, weeks, assignments
and language settings.

Import replaces the archive only after database validation and confirmation. A backup
is saved in the `backups` subdirectory before replacement. Migration from the first
version also creates a backup: assignments in the former **Ward assistant** column
are removed, while **SURG 3** assignments are preserved. New ward assistants are managed within the
ward cell. Importing old Excel files is not supported.

### Monthly and holiday summaries

**Multidisciplinary**, between Clinic and Night-off, is informational: zero credited
hours, no summary counts and no paid assignments.

The monthly summary opens on the month containing the displayed week’s Monday and allows other months to be selected.
SURG 1/2/3 count assignments on every day; duty, on-call and clinic count weekdays only.
Saturday/Sunday day/night count duty assignments only. Morning and afternoon clinic
or on-call assignments count separately.

The holiday summary opens on the year containing the displayed week’s Monday and supports other years. It counts
one attendance per doctor per date, including paid work and hours after midnight represented by night-off, excluding leave
and Multidisciplinary. Regular holidays: April 25, May 1, June 2, October 4, November 1,
December 8 and 26. Special holidays: January 1 and 6, Easter Sunday and Monday,
August 15 and December 25. Overlapping dates count only as special holidays.
Monthly nights count on their starting date; holiday attendance also includes the following night-off date if it is a holiday. Information buttons show holiday lists and the dates and assignments behind each total. Reports include all recorded assignments in the
period, including planned ones, and retain removed doctors.

The update backs up the archive before upgrading it to schema version 3.
Use v0.1.4 or later to reopen an upgraded archive.

### Hour calculations

| Activity | Hours per doctor |
| --- | --- |
| Operating room | 7h |
| Morning outpatient clinic | 6h |
| Afternoon outpatient clinic | 4h30m; 4h after operating room |
| Afternoon on-call | 4h; 3h after operating room |
| Morning on-call | 6h30m, Saturdays only |
| Ward lead | 9h alone; 8h with an assistant |
| Ward assistant / ACC-W.S. | 6h30m |
| Day duty | 13h |
| Night duty | 6h30m + 6h30m on the following post-night rest day |
| Absence | 0h |
| Vacation | +6h20m |
| Compensatory leave | −6h20m |

Durations are stored as integer minutes: 6h20m = 380 minutes. Operating room plus
afternoon clinic totals 11h; operating room plus afternoon on-call totals 10h.

The over-40-hour indicator uses ordinary work plus vacation before compensatory leave
is deducted. Totals below 38h are not flagged. Paid assignments, including post-night
rest following paid night duty, are always counted separately. Supervisors and trainees
receive no hour credits and are excluded from availability checks.

Monday night duty → Tuesday post-night rest: all Tuesday assignments are orange, including afternoon work. Monday night on-call → only Tuesday morning assignments are orange; afternoon work is allowed. The night-off cell itself and Wednesday have no such warning. Night on-call is informational: zero hours, excluded from counts, and does not generate night-off.
Compensatory leave and night-off are mutually exclusive; the night preceding compensatory leave is also disabled.
The annual summary includes paid clinics and paid nights: each clinic time band counts separately, each night counts once on its starting date, including weekends.
Absence, vacation and compensatory leave prevent work assignments on the same day.
Post-night rest is derived automatically, including across week boundaries, and is
edited through the originating night duty. Manual post-night rest is available when
the preceding night is missing from the archive.

Excel exports use the same columns and grouped time bands, with a formula-based summary
and minute details in a hidden internal sheet. Excel/LibreOffice recalculate formulas
on opening. In numeric summaries, 6h20m = 6.333… hours, displayed with two decimals;
calculations retain exact minutes.

Excel and PDF include Calendar, Weekly hours, Monthly shifts and Annual summary. PDFs use the same HTML/CSS as the interface, with each section on separate pages.

Overlapping morning duties (operating rooms, Ward, ACC-W.S., day duty, morning on-call and morning clinic) are highlighted in orange. Afternoon assignments do not receive this warning. Multidisciplinary assignments require availability and cannot coexist with absence, vacation or compensatory leave.

### Desktop packages

```sh
.venv/bin/python scripts/build.py
```

Build on the target operating system: `dist/turniamo.exe` for Windows (no Python
installation needed), `dist/turniamo.app` for macOS. Bundled WebEngine increases the
package size. Local packages are not distribution-signed or notarized. The GitHub
workflow builds and checks both packages. A tag such as `v0.1.4`, matching the version
in `pyproject.toml`, publishes a Release only after both builds and all checks pass.
The download buttons always point to the latest Release. Use **Actions → Test and
package desktop app → Run workflow** for builds without publishing a Release;
download the `turniamo-Windows` and `turniamo-macOS-AppleSilicon` artifacts.

### Verification and generated files

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/preview.py
.venv/bin/python scripts/smoke_packaged.py
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python` for builds and
verification too. Tests cover hour calculations, weekly history, database import and
migration, HTML UI interactions, and PDF/Excel exports. Previews use fictional data
and do not modify the real archive.

Both the project folder and Python module are named `turniamo`. `build/`, `dist/`,
`test-output/` and caches are generated artifacts that can be removed and recreated;
they do not contain the default user archive. After moving the project, recreate
`.venv` and reinstall dependencies, because virtual environments store absolute paths.

### License

turniamo source code is distributed under the [BSD-3-Clause license](LICENSE),
Copyright © 2026 Antonino Maria Rizzo. Dependencies retain their own licenses.
