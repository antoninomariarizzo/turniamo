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
    assert js(window,"document.querySelector('.breakdown').textContent.includes('−6h20m')")
    assert js(window,"document.querySelector('.breakdown-total strong').textContent")=='0h00m'
    js(window,"document.querySelector('#dialog').close()")
    js(window,f"document.querySelector('.info-button[data-doctor=\"{low}\"][data-category=paid]').click()")
    assert js(window,"document.querySelector('.breakdown tbody').rows.length")==2
    assert js(window,"document.querySelector('.breakdown-total strong').textContent")=='13h00m'
    window.close()
