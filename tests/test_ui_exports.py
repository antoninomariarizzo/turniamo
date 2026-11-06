from datetime import timedelta
import json
import time

import pytest
from openpyxl import load_workbook
from PySide6.QtCore import QEventLoop, QTimer, QSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtTest import QTest

from turniamo.domain import Activity as A, Assignment
from turniamo.exports import document_html, export_excel, export_pdf
from turniamo.i18n import TEXT, day_label, tr
from turniamo.storage import Store
from turniamo.web_ui import Bridge, MainWindow
from test_domain import MONDAY


def sample_store():
    store = Store(":memory:")
    first, second = store.save_doctor("Rossi M."), store.save_doctor("Bianchi L.")
    store.create_week(MONDAY)
    store.set_setting("last_week", MONDAY.isoformat())
    store.save_assignment(Assignment("surgery", MONDAY, A.SURGERY_2, first, associate_role="training", associate_name="Verdi A."))
    store.save_assignment(Assignment("clinic", MONDAY, A.CLINIC_PM, first))
    store.save_assignment(Assignment("night", MONDAY, A.NIGHT_DUTY, second, True))
    store.save_assignment(Assignment("after", MONDAY + timedelta(days=2), A.CLINIC_AM, second))
    return store, first, second


def js(window, expression):
    result = []
    loop = QEventLoop()
    window.view.page().runJavaScript(expression, lambda value: (result.append(value), loop.quit()))
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    assert result, "JavaScript did not respond"
    return result[0]


def wait_js(window, expression):
    end = time.monotonic() + 12
    while time.monotonic() < end:
        if js(window, expression):
            return
        QTest.qWait(40)
    raise AssertionError(expression)


def test_html_direct_assignment_edit_remove_language_and_compact_layout(app, tmp_path):
    store, first, second = sample_store()
    window = MainWindow(store)
    window.show()
    wait_js(window, "window.turniamoReady === true")
    assert window.windowTitle() == "turniamo"
    assert js(window, "document.querySelectorAll('#tabs button').length") == 4
    assert js(window, "document.querySelectorAll('.schedule thead th').length") == 14
    assert js(window, "document.querySelector('.schedule tbody th').textContent") == "07 LU"
    assert js(window, "document.querySelector('main').scrollWidth <= document.querySelector('main').clientWidth+1")
    assert not js(window, "document.body.textContent.includes('Pianificazione settimanale')")
    js(window, "document.querySelector('[data-activity=surgery_urgent]').click()")
    wait_js(window, "document.querySelectorAll('.choice').length === 2")
    js(window, f"document.querySelector('[data-doctor=\"{first}\"].choice').click()")
    assert js(window, "!document.querySelector('#popover').hidden")
    assert not any(a.activity == A.SURGERY_URGENT and a.doctor_id == first for a in store.raw_assignments())
    js(window, "document.querySelector('.selection-confirm').click()")
    wait_js(window, "document.querySelector('[data-activity=surgery_urgent] .assignment') !== null")
    assert any(a.activity == A.SURGERY_URGENT and a.doctor_id == first for a in store.raw_assignments())
    js(window, "document.querySelector('[data-activity=surgery_urgent]').click()")
    wait_js(window, "!document.querySelector('#popover').hidden")
    js(window, f"document.querySelector('[data-doctor=\"{first}\"].choice').click()")
    js(window, "document.querySelector('#popover').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))")
    wait_js(window, "document.querySelector('[data-activity=surgery_urgent] .assignment') === null")
    js(window, "document.querySelector('[data-tab=summary]').click()")
    assert js(window, "document.querySelectorAll('.summary thead th').length") == 4  # row labels + 3 data columns
    js(window, "document.querySelector('[data-tab=doctors]').click()")
    assert js(window, "document.querySelectorAll('input[type=checkbox]').length") == 0
    js(window, f"document.querySelector('[data-doctor=\"{first}\"] .doctor-name').click()")
    js(window, "document.querySelector('.doctor-row input').value='Rossi Mario';document.querySelector('.doctor-row input').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))")
    wait_js(window, "Array.from(document.querySelectorAll('.doctor-name')).some(e=>e.textContent==='Rossi Mario')")
    window.bridge.dispatch("language", {"language": "en"});window.bridge.publish()
    wait_js(window, "document.documentElement.lang==='en'")
    assert store.setting("language", "it") == "en"
    window.grab().save(str(tmp_path / "html-ui.png"))
    window.close()


def test_multi_selection_cancel_filter_and_keyboard_confirmation(app):
    store, first, second = sample_store()
    window=MainWindow(store);window.show()
    wait_js(window,"window.turniamoReady === true")
    def open_menu():
        js(window,"document.querySelector('[data-activity=surgery_urgent]').click()")
        wait_js(window,"!document.querySelector('#popover').hidden && document.querySelectorAll('.choice').length===2")
    def select(doctor):
        js(window,f"document.querySelector('.choice[data-doctor=\"{doctor}\"]').click()")
    def duties():
        return [a for a in store.raw_assignments() if a.activity==A.SURGERY_URGENT]
    open_menu();select(first);select(second)
    assert duties()==[]
    js(window,"document.querySelector('.search').value='Rossi';document.querySelector('.search').dispatchEvent(new Event('input'))")
    assert js(window,"document.querySelectorAll('.choice').length") == 1
    js(window,"document.querySelector('.search').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))")
    wait_js(window,"document.querySelector('#popover').hidden")
    assert {a.doctor_id for a in duties()}=={first,second}
    open_menu();select(first);select(second)
    js(window,"document.querySelector('.selection-cancel').click()")
    assert len(duties())==2
    open_menu();select(first)
    js(window,"document.querySelector('.search').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
    assert js(window,"document.querySelector('#popover').hidden")
    assert len(duties())==2
    open_menu();select(first)
    js(window,"document.querySelector('main').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))")
    assert js(window,"document.querySelector('#popover').hidden")
    assert len(duties())==2
    window.close()


def test_bridge_rejects_absence_and_handles_ward_in_one_cell(app):
    store, first, second = sample_store()
    bridge = Bridge(store)
    day = (MONDAY + timedelta(days=1)).isoformat()
    bridge.dispatch("toggle", {"day":day,"activity":"ward","doctor":first})
    bridge.dispatch("toggle", {"day":day,"activity":"ward","doctor":second})
    entries = bridge.slot_entries(MONDAY+timedelta(days=1), A.WARD)
    assert {a.activity for a in entries} == {A.WARD, A.WARD_HELP}
    bridge.dispatch("toggle", {"day":day,"activity":"ward","doctor":first})
    assert bridge.slot_entries(MONDAY+timedelta(days=1), A.WARD)[0].activity == A.WARD
    store.save_assignment(Assignment("leave", MONDAY+timedelta(days=1), A.HOLIDAY, first))
    assert next(d for d in bridge.choices(MONDAY+timedelta(days=1), A.CLINIC_AM) if d['id']==first)['disabled']
    response = json.loads(bridge.request("toggle", json.dumps({"day":day,"activity":"clinic_am","doctor":first})))
    assert not response['ok']


@pytest.mark.parametrize("language", ["it", "en"])
def test_exports_pdf_and_excel(app, tmp_path, language):
    store, _, _ = sample_store()
    assignments, doctors = store.week_context(MONDAY), store.week_doctors(MONDAY)
    html = document_html(MONDAY, assignments, doctors, language)
    path = tmp_path / f"schedule-{language}.pdf"
    export_pdf(path, html)
    pdf = QPdfDocument()
    assert pdf.load(str(path)) == QPdfDocument.Error.None_
    assert pdf.pageCount() == 4
    text = "\n".join(pdf.getAllText(i).text() for i in range(pdf.pageCount()))
    # QtPdf may insert line breaks between individual Chromium PDF glyphs.
    assert "Rossi" in text and "11h00m" in "".join(text.split())
    assert day_label(MONDAY, language) in text
    assert "B3 071" not in text and "B3 067" not in text
    xlsx = tmp_path / f"schedule-{language}.xlsx"
    export_excel(xlsx, MONDAY, assignments, doctors, language)
    workbook = load_workbook(xlsx)
    assert [w.title for w in workbook if w.sheet_state == 'visible'] == [tr(k, language) for k in ('schedule','summary','monthly','festivities')]
    assert workbook.worksheets[0].max_column == 14
    assert workbook.worksheets[1].max_column == 4
    assert workbook.worksheets[0]['A3'].value == day_label(MONDAY, language)
    assert 'SUMIFS' in workbook.worksheets[1]['B5'].value
    details = list(workbook.worksheets[4].values)[1:]
    assert sum(r[6] for r in details if r[3] == tr('yes', language)) == 780
    assert sum(r[6] for r in details if r[1] == 'Rossi M.') == 660


def test_exports_escape_names_and_formulas(app, tmp_path):
    store = Store(':memory:')
    d = store.save_doctor('=1+1')
    store.save_assignment(Assignment('one', MONDAY, A.CLINIC_AM, d, associate_role='reference', associate_name='<Chief & Co>'))
    assignments, doctors = store.week_context(MONDAY), store.week_doctors(MONDAY)
    assert '\\u003cChief & Co>' in document_html(MONDAY, assignments, doctors, 'en')
    path = tmp_path/'escape.xlsx'
    export_excel(path, MONDAY, assignments, doctors, 'en')
    book = load_workbook(path)
    assert book.worksheets[1]['A5'].data_type == 's'
    assert book.worksheets[4]['B2'].data_type == 's'


def test_all_translations_are_present():
    assert all(len(pair)==2 and all(pair) for pair in TEXT.values())


def test_pdf_export_through_webchannel(app, tmp_path, monkeypatch):
    from turniamo.web_ui import QFileDialog
    store, _, _ = sample_store()
    window = MainWindow(store)
    window.show()
    wait_js(window, 'window.turniamoReady === true')
    path = tmp_path / 'from-menu.pdf'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(path), 'PDF (*.pdf)'))
    js(window, "bridge.exportFinished.connect(raw=>window.exportFinished=JSON.parse(raw));window.exportFinished=null")
    js(window, "window.exportResult=null;rpc('export',{kind:'pdf'}).then(()=>window.exportResult='ok').catch(e=>window.exportResult=e.message)")
    wait_js(window, 'window.exportResult !== null')
    assert js(window, 'window.exportResult') == 'ok'
    wait_js(window, 'window.exportFinished !== null')
    assert js(window, 'window.exportFinished.ok')
    assert path.read_bytes().startswith(b'%PDF')
    window.close()


def test_export_defaults_to_downloads_then_desktop(tmp_path, monkeypatch):
    from turniamo.web_ui import default_export_path, QStandardPaths
    downloads, desktop = tmp_path / 'Downloads', tmp_path / 'Desktop'
    downloads.mkdir(); desktop.mkdir()
    locations = {
        QStandardPaths.StandardLocation.DownloadLocation: str(downloads),
        QStandardPaths.StandardLocation.DesktopLocation: str(desktop),
    }
    monkeypatch.setattr(QStandardPaths, 'writableLocation', lambda location: locations.get(location, str(tmp_path)))
    assert default_export_path('week.pdf') == str(downloads / 'week.pdf')
    downloads.rmdir()
    assert default_export_path('week.pdf') == str(desktop / 'week.pdf')


@pytest.mark.parametrize('role', ['reference', 'training'])
def test_assignment_dialog_reopens_cancels_and_saves_associate(app, role):
    store, first, _ = sample_store()
    window = MainWindow(store)
    window.show()
    wait_js(window, 'window.turniamoReady === true')
    more = "document.querySelector('[data-activity=surgery_2] .more')"
    for _ in range(5):
        js(window, more + '.click()')
        assert js(window, "document.querySelector('#dialog').open")
        assert js(window, "getComputedStyle(document.querySelector('#dialog'),'::backdrop').backdropFilter") == 'none'
        assert js(window, "document.querySelector('#popover').hidden")
        assert js(window, "document.querySelector('#associate-name').value") == 'Verdi A.'
        js(window, f"document.querySelector('#associate-role').value='{role}';document.querySelector('#associate-role').dispatchEvent(new Event('change'))")
        assert js(window, "document.activeElement.id") == 'associate-name'
        js(window, "document.querySelector('#associate-name').value='Discarded';document.querySelector('#dialog .quiet-button').click()")
        assert not js(window, "document.querySelector('#dialog').open")
    assert next(a for a in store.raw_assignments() if a.id == 'surgery').associate_name == 'Verdi A.'
    js(window, more + '.click()')
    js(window, f"document.querySelector('#associate-role').value='{role}';document.querySelector('#associate-role').dispatchEvent(new Event('change'));document.querySelector('#associate-name').value='Persona demo';document.querySelector('#dialog .primary').click()")
    wait_js(window, "!document.querySelector('#dialog').open && document.querySelector('[data-activity=surgery_2] .associated').textContent.includes('Persona demo')")
    saved = next(a for a in store.raw_assignments() if a.id == 'surgery')
    assert (saved.associate_role, saved.associate_name) == (role, 'Persona demo')
    js(window, more + '.click()')
    assert js(window, "document.querySelector('#associate-role').value") == role
    assert js(window, "document.querySelector('#associate-name').value") == 'Persona demo'
    js(window, "document.querySelector('#dialog .quiet-button').click()")
    window.close()
    store.close()


@pytest.mark.parametrize('kind', ['remove_doctor', 'derived_assignment'])
def test_other_dialogs_open_complete_and_can_be_dismissed(app, kind):
    store, _, _ = sample_store()
    window = MainWindow(store)
    window.show()
    wait_js(window, 'window.turniamoReady === true')
    if kind == 'remove_doctor':
        js(window, "document.querySelector('[data-tab=doctors]').click();document.querySelector('.trash').click()")
    else:
        js(window, "document.querySelector('[data-activity=night_off] .more').click()")
    assert js(window, "document.querySelector('#dialog').open")
    assert js(window, "document.querySelector('#dialog h2').textContent.length > 0")
    assert js(window, "document.querySelector('#dialog').contains(document.activeElement)")
    dismiss = '.primary' if kind == 'derived_assignment' else '.quiet-button'
    js(window, f"document.querySelector('#dialog {dismiss}').click()")
    assert not js(window, "document.querySelector('#dialog').open")
    assert len(store.raw_assignments()) == 4
    window.close()
    store.close()
