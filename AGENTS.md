# turniamo — memoria del progetto e istruzioni per gli agenti

Questo file conserva la storia operativa e le decisioni di prodotto della chat iniziale, fino alla pubblicazione della v0.1.5 del 6 novembre 2026. Non è una trascrizione verbatim: conserva richieste, correzioni, motivazioni, risultati e vincoli necessari per continuare in una nuova chat. Le istruzioni successive dell’utente prevalgono; non ripristinare regole storiche superate.

## Identità, repository e collaborazione

- Applicazione desktop locale per pianificare turni ospedalieri, nome **turniamo** in minuscolo. Nome iniziale: **hospital-shifts**; la cartella è stata rinominata `turniamo`. Se il contesto dell’ambiente indica ancora il vecchio percorso, verificare la cartella reale prima di eseguire comandi.
- Repository: https://github.com/antoninomariarizzo/turniamo, account proprietario `antoninomariarizzo`, ramo principale `main`.
- README e release notes in italiano e inglese. Interfaccia bilingue; comunicazione con l’utente prevalentemente in italiano.
- Licenza BSD-3-Clause, copyright Antonino Maria Rizzo. Non attribuire questa licenza alle dipendenze: mantengono le proprie.
- Icona con bordi arrotondati, risorse PNG/ICO/ICNS in `turniamo/assets/`.
- L’utente vuole provare manualmente l’app prima di una nuova pubblicazione. Preparare codice, verifiche e pacchetto locale senza fermarsi a chiedere permesso per attività reversibili. Pubblicare quando arriva il via libera, ad esempio «Procedi con il deploy» o «release the v0.1.5». Non chiedere di nuovo se la versione è già autorizzata. Il via libera a una versione non è un’autorizzazione permanente a tutte le successive.
- La richiesta del 6 novembre 2026 autorizza esplicitamente la release **v0.1.5** e la creazione della skill. Questa annotazione non autorizza versioni successive.
- Non inviare messaggi a terzi. Un deploy qui significa pubblicazione dei pacchetti desktop su GitHub Releases, non deploy di un server o sito.

## Privacy e dati

- **Non pubblicare dati dei medici**, archivi SQLite, backup, esportazioni o credenziali. Non usare dati reali nei test o negli screenshot da condividere. Gli esempi di persone nella chat non sono requisiti e non vengono riprodotti qui.
- L’app funziona offline, senza account o server. Distribuire un’app che inizializza un archivio vuoto; i dati restano separati dall’eseguibile.
- Su macOS il database è normalmente `~/Library/Application Support/turniamo/turniamo/turniamo.sqlite3`; Windows usa la cartella dati utente individuata da Qt. `--data-dir` permette un archivio alternativo.
- Per test e anteprime usare `Store(':memory:')` o directory temporanee. Non aprire l’archivio reale per una prova automatica.
- `.gitignore` esclude ambienti, build/dist, database, backup, documenti esportati e segreti. `scripts/check_public_files.py` applica una allowlist ai file tracciati e controlla firme SQLite e credenziali note. Non sostituisce la revisione dei contenuti: anche un file Python/Markdown può contenere dati privati.
- Il controllo riguarda i file tracciati: rieseguirlo dopo aver aggiunto allo staging i nuovi file previsti. Non usare `git add .` alla cieca. Se un nuovo file pubblico legittimo è respinto, aggiungere soltanto il percorso o la categoria strettamente necessari alla allowlist; non disattivare il controllo.
- `gh` era autenticato al momento delle release precedenti, ma verificare la sessione corrente. Non inserire token in file, log o chat.

## Architettura: dove si trova la logica

| File | Responsabilità |
| --- | --- |
| `turniamo/domain.py` | Attività, minuti, validazione, smonto derivato, vincoli e avvisi |
| `turniamo/storage.py` | SQLite, migrazioni, storico settimanale, salvataggi atomici |
| `turniamo/reports.py` | Conteggi mensili/annuali, festività e dettagli dei totali |
| `turniamo/web_ui.py` | Finestra Qt, bridge WebChannel, stato UI, import/backup, comandi ed export |
| `turniamo/presentation.py` | Modello condiviso fra calendario interattivo e PDF |
| `turniamo/layout.py` | Colonne, gruppi di attività, fasce orarie |
| `turniamo/i18n.py` | Testi italiano/inglese |
| `turniamo/web/{index.html,app.js,style.css}` | UI HTML/CSS/JavaScript in Qt WebEngine |
| `turniamo/exports.py` | Excel con openpyxl; PDF tramite lo stesso HTML/CSS e Chromium/Qt |
| `scripts/build.py` | Pacchetti PyInstaller per il sistema corrente |
| `scripts/smoke_packaged.py` | Avvio del pacchetto con database temporaneo vuoto |
| `scripts/preview.py` | Anteprime con dati fittizi |
| `.github/workflows/build.yml` | Test, build Windows/macOS, artefatti e release |

Python è la fonte delle regole; non duplicarle in JavaScript. Tenere UI, selettori, PDF ed Excel coerenti. La modifica del codice condiviso può incidere sia su Windows sia su macOS: non presumere che una correzione nata su Windows non richieda verifiche su Mac.

## Interfaccia concordata

- Barra: selettore settimana a sinistra; schede al centro; icone Medici, Esporta e Impostazioni a destra. Medici è immediatamente a sinistra di Esporta e usa un’icona, non una scheda testuale.
- Schede: **Calendario** con sola icona accessibile/tooltip, **Ore settimanali**, **Turni mensili**, **Riepilogo annuale**. I vecchi nomi erano Orario settimanale, Riepilogo ore, Riepilogo mensile e Riepilogo festività.
- Eliminato il pulsante «+ Nuova settimana». La navigazione tra settimane resta disponibile; non rimuovere la relativa logica di archivio.
- Ingranaggio ed Esporta devono mantenere la posizione anche nei riepiloghi mensili/annuali. La selezione del periodo di un riepilogo è separata da quella della settimana.
- Colonne: CHIR 1, CHIR 2, CHIR 3, Reparto, ACC-W.S., Guardia, Reperibilità, Ambulatorio, Multidisciplinare, S.N., Assenza, Ferie, Recupero.
- CHIR 1 era CHIR URG: conservato l’identificatore persistente `surgery_urgent`. Rimossi i sottotitoli B3 071 e B3 067. CHIR 3 segue CHIR 2. Multidisciplinare è fra Ambulatorio e S.N.
- Reperibilità ha tre fasce: **07:45–14:00**, **14:00–18:00**, **20:00–08:00**. La fascia AM rimane selezionabile solo il sabato, secondo la regola preesistente. La notte termina il giorno successivo ma non mostra «(+1)», per coerenza con Guardia notturna.
- Multidisciplinare e Reperibilità notturna sono informative: zero ore, escluse dai conteggi mensili/annuali, niente pagamento. La reperibilità notturna non genera S.N.
- Selettore medici: ricerca, selezione multipla, Conferma/Invio; Annulla/Esc o clic esterno non salvano. Gli indisponibili sono disabilitati e grigi, gli avvisi sono arancioni. Gli avvisi non sono blocchi di salvataggio salvo un vincolo esplicito.
- Menu «…» per pagamento, referente e persona in formazione. Questi ultimi sono annotazioni, non assegnazioni con ore e controlli di disponibilità.
- Reparto: primo medico responsabile, altri aiuti nella stessa cella; rimuovendo il responsabile, promuovere un aiuto. Non ricreare la vecchia colonna Aiuto reparto.
- Modifiche e rimozioni dei medici si applicano dalla settimana selezionata in avanti; non riscrivere i nomi e gli organici delle settimane precedenti.

## Regole di disponibilità e avvisi: versione finale

### Assenze e Multidisciplinare

Assenza, Ferie e Recupero impediscono gli incarichi dello stesso giorno, comprese Reperibilità notturna e **Multidisciplinare**. Il carattere informativo/zero ore non esenta dal controllo di presenza. Validare entrambi gli ordini: prima assenza poi incarico, oppure viceversa. Il selettore deve riflettere lo stesso vincolo del salvataggio singolo e multiplo. Segnalare anche incompatibilità già presenti in dati storici senza cancellarle automaticamente.

### Guardia notturna, smonto e recupero

- La guardia della notte fra lunedì e martedì genera S.N. martedì, anche attraversando una settimana, un mese o un anno.
- **Smonto notte significa indisponibilità per tutta la giornata**: ogni turno lavorativo/informativo assegnato martedì è arancione, anche pomeridiano o notturno. La cella S.N. stessa non è arancione per il solo fatto di essere uno smonto. Mercoledì non riceve questo avviso, salvo altri vincoli.
- Lo smonto automatico si modifica dalla notte di origine. S.N. manuale è ammesso se manca la notte precedente; quando essa viene inserita, lo smonto derivato sostituisce quello manuale nei calcoli, senza raddoppiare le ore né perdere il pagamento.
- **Recupero e S.N. sono incompatibili**, anche manuale. Se martedì c’è Recupero, impedire Guardia notturna lunedì. Se c’è già la notte, impedire Recupero martedì. Coprire domenica/lunedì e tutti gli ordini di inserimento.
- S.N. rappresenta lavoro già svolto nelle prime ore della giornata: Ferie/Assenza possono coesistere secondo la regola preesistente; l’incompatibilità aggiuntiva richiesta è con Recupero.

### Reperibilità notturna

Dopo reperibilità notturna lunedì, solo gli incarichi mattutini del martedì sono arancioni; il pomeriggio è disponibile. Non equipararla allo smonto, non attribuirle ore, non generare S.N. Se esiste anche uno smonto effettivo, prevale l’indisponibilità per tutta la giornata.

### Sovrapposizioni del mattino

La v0.1.5 estende il precedente avviso «più sale» alle sovrapposizioni tra CHIR 1/2/3, Reparto/aiuto, ACC-W.S., Guardia diurna, Reperibilità AM e Ambulatorio AM. Evidenziare gli incarichi mattutini coinvolti dello stesso medico e giorno; non propagare questo specifico avviso agli incarichi PM. Multidisciplinare non entra nei conteggi di sovrapposizione. `Issue.activity` limita gli avvisi alle celle corrette.

## Ore: invarianti da preservare

I calcoli usano minuti interi, non decimali arrotondati. Le etichette delle fasce non determinano automaticamente le ore accreditate.

| Attività | Minuti |
| --- | ---: |
| CHIR 1/2/3 | 420 |
| Reparto responsabile solo / con aiuto | 540 / 480 |
| Aiuto reparto, ACC-W.S. | 390 |
| Guardia diurna | 780 |
| Guardia notturna / S.N. successivo | 390 + 390 |
| Reperibilità AM (sabato) | 390 |
| Reperibilità PM / dopo sala | 240 / 180 |
| Ambulatorio AM | 360 |
| Ambulatorio PM / dopo sala | 270 / 240 |
| Ferie | +380 |
| Recupero | −380 |
| Assenza, Multidisciplinare, Reperibilità notturna | 0 |

- Le combinazioni sala + ambulatorio PM e sala + reperibilità PM valgono rispettivamente 11h e 10h.
- Le ore ordinarie mostrate includono Ferie e Recupero. La segnalazione oltre 40h usa lavoro ordinario + Ferie, **prima** della sottrazione dei recuperi. Non segnalare in UI i totali sotto 38h.
- Il pagamento è separato dalle ore ordinarie; lo smonto di una notte a pagamento eredita il pagamento.
- Referenti e persone in formazione non ricevono ore. Non trasformarli in medici assegnati.

## Riepiloghi e periodi

«In corso» significa il periodo del **lunedì della settimana visualizzata nel Calendario**, non la data del computer. All’apertura di Turni mensili/Riepilogo annuale reimpostare mese/anno a quel periodo; il selettore permette poi di consultare altri periodi.

### Turni mensili

Una riga per persona, anche persone rimosse presenti nello storico. Colonne CHIR 1, CHIR 2, CHIR 3, Guardia diurna, Guardia notturna, Reperibilità, Ambulatorio, Sabato giorno, Sabato notte, Domenica giorno, Domenica notte.

- CHIR conta tutti i giorni; Guardia diurna/notturna, Reperibilità e Ambulatorio contano lunedì–venerdì, senza «lun–ven» nell’intestazione.
- Sabato/Domenica giorno/notte contano soltanto le guardie, non ogni incarico del fine settimana.
- Fasce AM e PM distinte; pagamento incluso. Le notti contano nella data di inizio, non una seconda volta nello smonto.
- Consultare l’intero archivio del periodo, non solo gli incarichi della settimana visualizzata. Sono inclusi incarichi pianificati, non solo quelli precedenti alla data odierna.

### Riepilogo annuale

- **Festività**: 25 aprile, 1 maggio, 2 giugno, 4 ottobre, 1 novembre, 8 dicembre, 26 dicembre.
- **Festività speciali**: Capodanno, Epifania, Pasqua, Pasquetta, Ferragosto, Natale. Pasqua calcolata per l’anno. In caso di coincidenza, priorità alla categoria speciale, senza doppio conteggio.
- Una presenza per medico e giorno festivo, anche con più incarichi; pagamento incluso. Escludere assenze, ferie, recupero, Multidisciplinare e Reperibilità notturna.
- Includere le prime ore lavorate nello **smonto notte**, anche manuale e anche se la notte è nell’anno precedente. Una notte può quindi contribuire a due date festive distinte, ma mai due volte nella stessa data.
- **Ambulatori a pagamento**: ogni incarico AM/PM conta separatamente, inclusi sabati e domeniche.
- **Notti a pagamento**: una per guardia, nella data di inizio, senza ricontare lo smonto.
- Icona «i» nelle intestazioni e accanto a ogni totale annuale, anche zero, per spiegare criteri, festività incluse e date/incarichi che compongono il conteggio. I totali delle ore hanno a loro volta il dettaglio in minuti.

## Esportazioni e problemi specifici di piattaforma

- Excel: quattro fogli visibili **Calendario**, **Ore settimanali**, **Turni mensili**, **Riepilogo annuale** (tradotti in inglese se selezionato). Un ulteriore foglio tecnico nascosto alimenta le formule delle ore: non eliminarlo per ottenere letteralmente quattro fogli totali.
- PDF: le stesse quattro sezioni, ognuna su pagine separate; non assumere sempre quattro pagine per archivi grandi. Il nome esportato è Calendario anche se in UI c’è solo l’icona.
- Il bridge passa ai report l’intero archivio: esportare anche conteggi fuori dalla settimana visualizzata. Mantenere pagamento, colori, nomi e dettagli dei referenti.
- La griglia Excel usa sei righe fisiche per giorno per combinare celle a metà e a terzi. Non ripristinare gli indici precedenti di due righe/giorno.
- Le formule delle ore ricalcolano in Excel/LibreOffice. Conservare minuti esatti, protezione dei nomi interpretati come formule ed escape di nomi/note nell’HTML/JavaScript.
- **Bug Windows PDF v0.1.5**: `Path.read_text()` senza encoding leggeva le risorse UTF-8 secondo la codifica locale, producendo caratteri come «Â» presso «·». Leggere HTML/CSS/JS con `encoding='utf-8'`; i titoli PDF usano ora «:». Testare simulando il default cp1252 anche su Mac. Non limitarsi a cambiare font o sostituire il carattere corrotto dopo la decodifica.
- **Prestazioni Windows v0.1.3**: menu «…»/referente scattosi. Eliminata la sfocatura della tabella dietro il dialogo e popolato il dialogo prima di aprirlo. Non reintrodurre il lavoro grafico costoso.
- Export PDF via WebChannel: uscire dalla callback prima di caricare/stampare una seconda pagina Chromium (`QTimer.singleShot`); rendering annidato può bloccare IPC.
- Smoke Windows one-file: terminare l’intero albero di processi (`taskkill /T`), non solo il bootloader, e chiudere esplicitamente le connessioni SQLite. I processi figli/handle aperti impedivano la pulizia dei temporanei.

## Database e migrazioni

Schema corrente: `PRAGMA user_version=3`, introdotto con v0.1.4; non confonderlo con la versione applicativa. La v0.1.5 non richiede un nuovo schema.

- Backup prima della migrazione e prima dell’importazione che sostituisce l’archivio.
- Import accetta schemi 1, 2, 3 dopo validazione, copia privata e controllo d’integrità; rifiutare archivi di versioni future.
- Migrazione da schema 1: conservare CHIR 3, eliminare solo le vecchie assegnazioni della colonna separata Aiuto reparto; la nuova gestione aiuti vive in Reparto.
- Non cancellare dati incompatibili durante una normale correzione di regole. Non riaprire un archivio aggiornato con una versione dell’app che non supporta il suo schema.

## Build, test e release

Usare la skill personale **`$turniamo-release`** per preparare/testare/pubblicare una versione. Le istruzioni seguenti permettono di continuare anche se la skill non è installata su un’altra macchina.

Comandi dalla radice (su Windows usare l’interprete equivalente dell’ambiente):

```sh
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_public_files.py
.venv/bin/python scripts/build.py
.venv/bin/python scripts/smoke_packaged.py
```

Il build produce un pacchetto per il sistema corrente, non cross-compila. Su macOS, creare uno ZIP con `ditto -c -k --sequesterRsrc --keepParent` per conservare permessi e bundle. Nomi locali distinti, ad esempio `dist/turniamo-v0.1.5-macOS-test.zip`; non pubblicarli come artefatti ufficiali per Windows.

Workflow **Test and package desktop app**:

- Runner Windows x64 e macOS Apple Silicon; versione Python/matrici effettive in `.github/workflows/build.yml`.
- Test, build e smoke con archivio vuoto su entrambi i sistemi.
- `workflow_dispatch` crea artefatti scaricabili da Actions, **non** pubblica una release.
- Il push di un tag `v*` crea la release soltanto dopo il successo di entrambe le build. Il tag deve coincidere con `project.version` in `pyproject.toml`.
- Asset pubblici stabili: `turniamo-Windows.exe`, `turniamo-macOS-AppleSilicon.zip`, `SHA256SUMS.txt`, `LICENSE`. Windows è portatile, non un installer; macOS è Apple Silicon, non Intel, con requisito corrente macOS 14+.
- Pacchetti non firmati per distribuzione/notarizzati; le istruzioni per il primo avvio sono nel README. Non dichiararli firmati.
- README: icona centrata in alto, titolo turniamo, badge Windows/macOS. I pulsanti puntano a `/releases/latest/download/<nome-asset>`: conservarne i nomi ed evitare il precedente errore 404.
- Con pubblicazione autorizzata: controllare diff, privacy, versione e tag; commit dei soli file previsti; push ramo/tag preferibilmente atomico; seguire Actions fino al completamento. Verificare release non draft, asset presenti, latest corretta e risposte HTTP dei due download. Non terminare con «workflow avviato» se è stata richiesta la release completa.
- Non spostare/forzare tag già pubblicati o sovrascrivere silenziosamente asset di una release riuscita. In caso di errore diagnosticare prima; distinguere retry di infrastruttura da modifica del codice dopo il tag.

## Cronologia delle richieste e dei risultati

1. **Da hospital-shifts a turniamo.** Richiesti pulizia del progetto/dist, rinomina della cartella, README italiano/inglese e icona arrotondata. Conservare il nuovo nome e non ripubblicare vecchi eseguibili con il nome originario.
2. **Distribuzione GitHub.** Creato il repository dell’account indicato. Richiesti download per macOS/Windows, badge nel README e assenza di dati dei medici. Scelta GitHub Actions + Releases, senza richiedere Python agli utenti finali.
3. **Download e licenza.** Segnalati 404 nei pulsanti e richiesta BSD. Introdotti asset dai nomi stabili e BSD-3-Clause. La cronologia Git conserva il lavoro iniziale e la v0.1.2.
4. **Scatti Windows.** Menu dei tre puntini e gestione referente scattosi: corretti rendering/dialoghi nella v0.1.3. L’utente ha chiesto se ritestare macOS e dove fosse la logica: codice condiviso, regole principalmente in `domain.py`.
5. **Richiesta v0.1.4.** CHIR 3, rinomina CHIR URG, rimozione codici B3, Multidisciplinare, correzione dell’avviso spostato di un giorno, riepiloghi mensili e festività.
6. **Chiarimenti.** Multidisciplinare zero ore e nessun conteggio separato; festività una presenza/giorno. L’utente richiede prova manuale prima del via libera alla pubblicazione.
7. **Affinamento report.** Aggiunte icone informative, dettagli, periodo allineato alla settimana visualizzata e inclusione dello smonto nei giorni festivi. Lo smonto stesso non deve essere colorato come incarico in conflitto.
8. **UI/export e reperibilità.** Rimossa Nuova settimana; rinominate/spostate schede e icone; quattro sezioni negli export; introdotti vincolo Recupero/S.N., conteggi annuali a pagamento e terza cella reperibilità notturna.
9. **Correzione decisiva dello smonto.** La richiesta iniziale consentiva il pomeriggio dopo guardia notturna; è stata esplicitamente **superata**: dopo guardia/S.N. indisponibilità tutto il giorno, dopo sola reperibilità notturna indisponibilità soltanto al mattino. Selettore settimana spostato a sinistra, schede centrate, eliminato «(+1)».
10. **Test e pubblicazione v0.1.4.** Pacchetti locali successivi `test`, `test2`, `test3`, `test4`; ultimo test con 91 verifiche superate e smoke macOS. Dopo «Procedi con il deploy», commit `764e33a`, tag v0.1.4, build e smoke riusciti su entrambi i runner, release pubblicata e download HTTP 200. Run: https://github.com/antoninomariarizzo/turniamo/actions/runs/42204387188.
11. **Bugfix v0.1.5.** Richiesti caratteri PDF Windows corretti, blocco Multidisciplinare durante assenze e avvisi oltre la sola doppia sala. Implementati UTF-8 esplicito, titoli PDF con due punti, disponibilità comune anche agli incarichi informativi e sovrapposizioni mattutine circoscritte alle attività coinvolte. 99 test superati, incluso default cp1252 simulato; build/smoke macOS riusciti e pacchetto locale `dist/turniamo-v0.1.5-macOS-test.zip`.
12. **Memoria e skill.** Richiesta di riversare la storia in questo `AGENTS.md` e creare una skill di versione/release. Durante il lavoro l’utente ha autorizzato: «release the v0.1.5 and continue the skill creation». La skill personale `turniamo-release` è stata creata e validata; la allowlist pubblica include questo `AGENTS.md`.
13. **Pubblicazione v0.1.5 verificata.** Commit applicativo/tag `7c6700a` / `v0.1.5`; run https://github.com/antoninomariarizzo/turniamo/actions/runs/42239546193 completato con successo, inclusi test, build e smoke Windows/macOS. Release https://github.com/antoninomariarizzo/turniamo/releases/tag/v0.1.5 pubblica, stabile e latest al momento della verifica; entrambi i pacchetti, checksum e licenza presenti, download Windows/macOS HTTP 200. Questo aggiornamento documentale è successivo al tag: non spostare il tag per includerlo.

## Come mantenere questa memoria

Aggiornare regole e cronologia quando cambia una decisione sostanziale o una release viene pubblicata; distinguere richieste superate, stato verificato e lavoro ancora locale. Non trattare numeri di test, autenticazione o versione latest qui annotati come dati sempre attuali. Leggere stato Git, configurazione e workflow prima di agire. Non copiare trascrizioni con dati personali o token per rendere la memoria «completa».
