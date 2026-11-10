import json
from datetime import timedelta

from PySide6.QtTest import QTest

from turniamo.domain import Activity as A, Assignment
from turniamo.storage import Store
from turniamo.web_ui import MainWindow, Bridge
from turniamo.layout import TIMES
from test_domain import MONDAY
from test_ui_exports import js, wait_js


def test_alphabetic_order_and_growing_cells_with_references(app):
    store=Store(':memory:')
    doctors=[store.save_doctor(n) for n in ('Zulu','Alpha','beta')]
    store.create_week(MONDAY);store.set_setting('last_week',MONDAY.isoformat())
    for index,doctor in enumerate(doctors):
        store.save_assignment(Assignment(str(index),MONDAY,A.ON_CALL_PM,doctor,False,'reference',
                                         'Referente con nome lungo e annotazione su più righe'))
    window=MainWindow(store);window.show()
    wait_js(window,'window.turniamoReady === true')
    assert json.loads(js(window,"JSON.stringify([...document.querySelectorAll('[data-activity=on_call_pm]')][0].querySelectorAll('.name').length)"))==3
    names=json.loads(js(window,"JSON.stringify([...document.querySelector('[data-activity=on_call_pm]').querySelectorAll('.name')].map(e=>e.textContent))"))
    assert names==['Alpha','beta','Zulu']
    for width in (1440,1000):
        window.resize(width,880);QTest.qWait(200)
        assert js(window,"""(()=>{
            const slot=document.querySelector('[data-activity=on_call_pm]');
            const cell=slot.closest('td'), row=cell.parentElement;
            const bottom=slot.getBoundingClientRect().bottom;
            return [...slot.querySelectorAll('.assignment')].every(a=>a.getBoundingClientRect().bottom<=bottom+1)
              && bottom<=cell.getBoundingClientRect().bottom+1
              && cell.getBoundingClientRect().bottom<=row.nextElementSibling.getBoundingClientRect().top+1;
        })()""")
    for activity,text in TIMES.items():
        assert js(window,f"document.querySelector('[data-activity={activity.value}] .slot-label').textContent")==text
    window.close()


def test_summary_only_over_40_and_info_reconciles_signed_and_paid_minutes(app):
    store=Store(':memory:')
    low=store.save_doctor('Below')
    exact=store.save_doctor('Exactly forty')
    high=store.save_doctor('Above forty')
    store.create_week(MONDAY);store.set_setting('last_week',MONDAY.isoformat())
    store.save_assignment(Assignment('holiday',MONDAY,A.HOLIDAY,low))
    store.save_assignment(Assignment('recovery',MONDAY+timedelta(days=1),A.RECOVERY,low))
    store.save_assignment(Assignment('paid',MONDAY+timedelta(days=2),A.NIGHT_DUTY,low,True))
    for i in range(4):
        store.save_assignment(Assignment(f'surgery{i}',MONDAY+timedelta(days=i),A.SURGERY_2,exact))
    for i in (4,5):
        store.save_assignment(Assignment(f'clinic{i}',MONDAY+timedelta(days=i),A.CLINIC_AM,exact))
    for i in range(4):
        store.save_assignment(Assignment(f'duty{i}',MONDAY+timedelta(days=i),A.DAY_DUTY,high))
    store.save_assignment(Assignment('recovery-high',MONDAY+timedelta(days=5),A.RECOVERY,high))
    data=Bridge(store).state()
    assert data['totals'][low]['status']=='normal'
    assert data['totals'][exact]['status']=='normal'
    assert data['totals'][high]['status']=='above'
    window=MainWindow(store);window.show()
    wait_js(window,'window.turniamoReady === true')
    js(window,"document.querySelector('[data-tab=summary]').click()")
    assert js(window,"document.querySelectorAll('.summary .status').length")==1
    assert not js(window,"document.querySelector('.summary').textContent.includes('Sotto 38')")
    js(window,f"document.querySelector('.info-button[data-doctor=\"{low}\"][data-category=ordinary]').click()")
    assert js(window,"document.querySelector('#dialog').open")
    assert js(window,"[...document.querySelectorAll('.breakdown tbody tr')].some(r=>r.textContent.includes('Recupero') && r.textContent.includes('0h00m'))")
    assert js(window,"document.querySelector('.breakdown-total strong').textContent")=='6h20m'
    js(window,"document.querySelector('#dialog').close()")
    js(window,f"document.querySelector('.info-button[data-doctor=\"{low}\"][data-category=paid]').click()")
    assert js(window,"document.querySelector('.breakdown tbody').rows.length")==2
    assert js(window,"document.querySelector('.breakdown-total strong').textContent")=='13h00m'
    window.close()


def test_weekend_cells_oncall_geometry_and_clinic_label_match_excel(app,tmp_path):
    from turniamo.exports import export_excel,export_cells
    from turniamo.layout import COLUMNS
    from turniamo.domain import RuleError
    from openpyxl import load_workbook
    import pytest
    store=Store(':memory:');doctor=store.save_doctor('Demo')
    store.create_week(MONDAY);store.set_setting('last_week',MONDAY.isoformat())
    window=MainWindow(store);window.show();wait_js(window,'window.turniamoReady === true')
    assert js(window,"document.querySelectorAll('[data-activity=on_call_am]').length")==1
    assert js(window,"document.querySelector('[data-activity=on_call_am]').dataset.day")==str(MONDAY+timedelta(days=5))
    assert js(window,"document.querySelector('[data-activity=clinic_pm] .slot-label').textContent")=='14:30 - 19:00'
    core=(A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3,A.WARD,A.WEEK_SERVICE)
    for activity in core:
        assert js(window,f"document.querySelectorAll('[data-activity={activity}][aria-disabled=true]').length")==2
        selector=f'[data-day="{MONDAY+timedelta(days=5)}"][data-activity="{activity}"]'
        js(window,f"document.querySelector('{selector}').click()")
        assert js(window,"document.querySelector('#popover').hidden")
        with pytest.raises(RuleError,match='error_weekdays_only'):
            store.set_slot_doctors(MONDAY+timedelta(days=5),activity,[doctor])
    cells=export_cells(MONDAY,[],store.week_doctors(MONDAY),'it')
    col=next(i for i,(key,_) in enumerate(COLUMNS,1) if key=='on_call_group')
    for day in range(7):
        slots=[c for c in cells if c[1]==col and day*6<=c[0]<(day+1)*6]
        assert len(slots)==(3 if day==5 else 2)
        assert sum(c[3] for c in slots)==6
        assert any('07:45 - 14:00' in c[2] for c in slots)==(day==5)
    path=tmp_path/'weekend.xlsx';export_excel(path,MONDAY,[],store.week_doctors(MONDAY),'it')
    workbook=load_workbook(path)
    for row in (33,39):
        for column in range(2,7):
            assert workbook['Calendario'].cell(row,column).fill.fgColor.rgb=='00EEF0F3'
    assert workbook['Calendario']['I6'].value=='14:30 - 19:00'
    workbook.close();window.close();store.close()


def test_guard_yellow_and_night_rest_grey_in_picker(app):
    store=Store(':memory:');doctor=store.save_doctor('Demo')
    store.create_week(MONDAY);store.set_setting('last_week',MONDAY.isoformat())
    store.save_assignment(Assignment('night',MONDAY,A.NIGHT_DUTY,doctor))
    window=MainWindow(store);window.show();wait_js(window,'window.turniamoReady === true')
    js(window,"document.querySelector('[data-activity=clinic_pm]').click()")
    wait_js(window,"!document.querySelector('#popover').hidden && document.querySelector('.choice')!==null")
    assert js(window,"document.querySelector('.choice').classList.contains('warning')")
    assert not js(window,"document.querySelector('.choice').disabled")
    js(window,"document.querySelector('.selection-cancel').click()")
    next_day=MONDAY+timedelta(days=1)
    js(window,f"document.querySelector('[data-day=\"{next_day}\"][data-activity=on_call_pm]').click()")
    wait_js(window,"!document.querySelector('#popover').hidden")
    assert js(window,"document.querySelector('.choice').disabled")
    assert not js(window,"document.querySelector('.choice').classList.contains('warning')")
    assert js(window,"getComputedStyle(document.querySelector('.choice')).color")=='rgb(133, 139, 147)'
    js(window,"document.querySelector('.selection-cancel').click()")
    store.save_assignment(Assignment('clinic',MONDAY,A.CLINIC_PM,doctor));window.bridge.publish()
    wait_js(window,"document.querySelectorAll('.assignment.warning').length===2")
    assert not js(window,"document.querySelector('[data-activity=night_off] .assignment').classList.contains('warning')")
    window.close();store.close()
