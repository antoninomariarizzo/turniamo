from datetime import date, timedelta
from turniamo.domain import Activity as A, Assignment, Doctor, effective_assignments, issues_for_week, minutes_for
from turniamo.reports import period_reports, easter, holiday_dates
from turniamo.storage import Store
from turniamo.web_ui import import_database, backup_before_migration, MainWindow
from test_ui_exports import js, wait_js


def assignment(day, activity, id='a', paid=False):
    return Assignment(id+str(day)+activity.value, day, activity, id, paid)


def test_month_counts_weekends_boundaries_and_zero_rows():
    data=[assignment(date(2026,11,6),a) for a in [A.DAY_DUTY,A.NIGHT_DUTY,A.ON_CALL_PM,A.CLINIC_AM,A.CLINIC_PM,A.SURGERY_3]]
    for day in (7,8):
        data += [assignment(date(2026,11,day),a) for a in [A.DAY_DUTY,A.NIGHT_DUTY,A.ON_CALL_PM,A.CLINIC_AM]]
    data += [assignment(date(2026,10,31),A.NIGHT_DUTY), assignment(date(2026,12,1),A.SURGERY_3), assignment(date(2026,11,6),A.MULTIDISCIPLINARY)]
    result=period_reports(date(2026,11,1),effective_assignments(data),[Doctor('a','Alpha'),Doctor('b','Former',False)])
    counts=result['monthly'][0]['counts']
    assert counts == dict(surgery_urgent=0,surgery_2=0,surgery_3=1,day_duty=1,night_duty=1,on_call_group=1,clinic_group=2,saturday_day=1,saturday_night=1,sunday_day=1,sunday_night=1)
    assert set(result['monthly'][1]['counts'].values()) == {0}


def test_festivities_deduplicate_exclude_nonwork_and_count_paid():
    regular,special=holiday_dates(2026)
    assert easter(2026)==date(2026,4,5)
    assert easter(2027)==date(2027,3,28)
    assert date(2026,10,4) in regular
    data=[]
    for day in regular|special:
        data += [assignment(day,A.DAY_DUTY),assignment(day,A.CLINIC_PM,paid=True)]
        data += [assignment(day,a,'b') for a in [A.NIGHT_OFF,A.HOLIDAY,A.ABSENCE,A.RECOVERY,A.MULTIDISCIPLINARY]]
    data += [assignment(date(2025,12,25),A.DAY_DUTY),assignment(date(2026,12,24),A.NIGHT_DUTY,'b')]
    result=period_reports(date(2026,11,1),effective_assignments(data),[Doctor('a','Alpha'),Doctor('b','Beta')])
    assert result['festivities'][0]['counts']=={'festive':7,'special':6,'paid_clinic':13,'paid_nights':0}
    assert result['festivities'][1]['counts']=={'festive':7,'special':6,'paid_clinic':0,'paid_nights':0}
    regular,special=holiday_dates(2038)
    assert date(2038,4,25) in special and not regular & special


def test_sunday_night_warning_monday_all_day():
    monday=date(2026,11,9)
    raw=[assignment(monday-timedelta(days=1),A.NIGHT_DUTY)]
    raw += [assignment(monday,a) for a in [A.CLINIC_AM,A.CLINIC_PM,A.MULTIDISCIPLINARY]]
    raw += [assignment(monday+timedelta(days=1),A.CLINIC_AM)]
    issues=issues_for_week(monday,effective_assignments(raw))
    assert {(i.day,i.activity) for i in issues}=={(monday,a) for a in (A.CLINIC_AM,A.CLINIC_PM,A.MULTIDISCIPLINARY)}
    assert minutes_for(raw[3],raw)==0


def test_new_activities_survive_reopen_and_import(tmp_path):
    path=tmp_path/'source.sqlite3'
    source=Store(path);d=source.save_doctor('Demo');day=date(2026,11,9);source.create_week(day)
    for activity in (A.SURGERY_3,A.MULTIDISCIPLINARY):
        source.set_slot_doctors(day,activity,[d])
    source.close()
    target=Store(tmp_path/'target.sqlite3')
    import_database(target,str(path))
    assert {a.activity for a in target.raw_assignments()}=={A.SURGERY_3,A.MULTIDISCIPLINARY}
    assert target.db.execute('PRAGMA user_version').fetchone()[0]==3
    target.close()
    source=Store(path)
    assert len(source.raw_assignments())==2
    source.db.execute('PRAGMA user_version=2');source.close()
    backup_before_migration(path)
    assert list((tmp_path/'backups').glob('*.sqlite3'))
    source=Store(path);assert len(source.raw_assignments())==2;source.close()


def test_period_tabs_and_month_switch(app):
    store=Store(':memory:');d=store.save_doctor('Demo');store.set_setting('last_week','2026-11-02')
    for day in (date(2026,4,25),date(2026,11,6)):
        store.save_assignment(Assignment(str(day),day,A.SURGERY_3,d))
    window=MainWindow(store);window.show();wait_js(window,'window.turniamoReady === true')
    js(window,"document.querySelector('[data-tab=monthly]').click()")
    wait_js(window,"document.querySelector('.report-table') !== null")
    assert js(window,"document.querySelectorAll('.report-table thead th').length")==12
    js(window,"const month=document.querySelector('input[type=month]');month.value='2026-04';month.dispatchEvent(new Event('change'))")
    wait_js(window,"state.reports.month==='2026-04'")
    assert js(window,"document.querySelector('.report-table tbody tr').children[3].textContent")=='1'
    js(window,"document.querySelector('[data-tab=festivities]').click()")
    wait_js(window,"document.querySelectorAll('.report-table thead th').length===5")
    assert js(window,"document.querySelector('.report-table tbody tr').children[1].textContent")=='1'
    js(window,"document.querySelector('[data-tab=schedule]').click()")
    assert not js(window,"document.querySelector('.week-controls').hidden")
    window.close();store.close()


def test_night_warning_in_picker_and_excel(app):
    from turniamo.web_ui import Bridge
    from turniamo.exports import export_cells
    from turniamo.layout import COLUMNS
    monday=date(2026,11,9)
    store=Store(':memory:');doctor=store.save_doctor('Demo');store.create_week(monday)
    store.save_assignment(Assignment('night',monday,A.NIGHT_DUTY,doctor))
    for offset,activity in [(1,A.CLINIC_AM),(1,A.CLINIC_PM),(2,A.CLINIC_AM)]:
        store.save_assignment(Assignment(str(offset)+activity,monday+timedelta(days=offset),activity,doctor))
    bridge=Bridge(store);bridge.start=monday
    assert bridge.choices(monday+timedelta(days=1),A.SURGERY_3)[0]['disabled']
    assert not bridge.choices(monday+timedelta(days=1),A.SURGERY_3)[0]['warning']
    assert bridge.choices(monday+timedelta(days=1),A.NIGHT_DUTY)[0]['warning']
    assert bridge.choices(monday+timedelta(days=1),A.CLINIC_PM)[0]['warning']
    assert not bridge.choices(monday+timedelta(days=2),A.CLINIC_AM)[0]['warning']
    col=next(i for i,(key,_) in enumerate(COLUMNS,1) if key=='clinic_group')
    cells=export_cells(monday,store.week_context(monday),store.week_doctors(monday),'it')
    warnings={(row,column):warning for row,column,_,_,warning in cells}
    assert warnings[(6,col)] and warnings[(9,col)] and not warnings[(12,col)]
    night_off_col=next(i for i,(key,_) in enumerate(COLUMNS,1) if key=='night_off')
    assert not warnings[(6,night_off_col)]
    store.close()


def test_holiday_overnight_cross_year_deduplicates_and_explains():
    raw=[assignment(date(2025,12,31),A.NIGHT_DUTY),
         assignment(date(2026,1,1),A.NIGHT_OFF),
         assignment(date(2026,1,1),A.DAY_DUTY),
         assignment(date(2026,12,24),A.NIGHT_DUTY),
         assignment(date(2026,12,25),A.NIGHT_DUTY)]
    result=period_reports(date(2026,1,1),raw,[Doctor('a','Demo'),Doctor('b','Empty')])
    row=result['festivities'][0]
    assert row['counts']=={'festive':1,'special':2,'paid_clinic':0,'paid_nights':0}
    newyear=row['details']['special'][0]
    assert newyear['date']=='2026-01-01' and newyear['holiday']=='new_year'
    assert {a['activity'] for a in newyear['assignments']}=={'night_off','day_duty'}
    assert len(newyear['assignments'])==2
    assert row['details']['festive'][0]['date']=='2026-12-26'
    assert result['festivities'][1]['details']=={'festive':[],'special':[],'paid_clinic':[],'paid_nights':[]}
    assert len(result['holiday_catalog']['festive'])==7
    assert len(result['holiday_catalog']['special'])==6


def test_report_info_and_reset_to_schedule_period(app):
    store=Store(':memory:');doctor=store.save_doctor('Demo');store.set_setting('last_week','2026-12-28')
    store.save_assignment(Assignment('night',date(2025,12,31),A.NIGHT_DUTY,doctor))
    window=MainWindow(store);window.show();wait_js(window,'window.turniamoReady === true')
    js(window,"document.querySelector('[data-tab=monthly]').click()")
    wait_js(window,"document.querySelector('input[type=month]') !== null")
    assert js(window,"document.querySelector('input[type=month]').value")=='2026-12'
    js(window,"const month=document.querySelector('input[type=month]');month.value='2025-04';month.dispatchEvent(new Event('change'))")
    wait_js(window,"state.reports.month==='2025-04'")
    js(window,"document.querySelector('[data-tab=festivities]').click()")
    wait_js(window,"document.querySelectorAll('.report-table thead .info-button').length===4")
    assert js(window,"state.reports.year")==2026
    js(window,"document.querySelector('thead .info-button[data-category=special]').click()")
    assert js(window,"document.querySelectorAll('#dialog tbody tr').length")==6
    assert js(window,"document.querySelector('#dialog').textContent.includes('Capodanno')")
    js(window,"document.querySelector('#dialog .primary').click();document.querySelector('.report-table tbody .info-button[data-category=special]').click()")
    assert js(window,"document.querySelector('#dialog .breakdown-total strong').textContent")=='1'
    assert js(window,"document.querySelector('#dialog tbody').textContent.includes('01/01/2026')")
    assert js(window,"document.querySelector('#dialog tbody').textContent.includes('S.N.')")
    js(window,"document.querySelector('#dialog .primary').click();document.querySelector('.report-table tbody .info-button[data-category=festive]').click()")
    assert js(window,"document.querySelector('#dialog .breakdown-total strong').textContent")=='0'
    js(window,"document.querySelector('#dialog .primary').click();document.querySelector('[data-tab=schedule]').click()")
    window.bridge.dispatch('week',{'date':'2027-02-08'});window.bridge.publish()
    wait_js(window,"state.start==='2027-02-08'")
    js(window,"document.querySelector('[data-tab=monthly]').click()")
    wait_js(window,"document.querySelector('input[type=month]') !== null")
    assert js(window,"document.querySelector('input[type=month]').value")=='2027-02'
    window.close();store.close()


def test_recovery_and_night_off_are_exclusive_in_both_orders(app):
    import pytest
    from turniamo.domain import RuleError
    from turniamo.web_ui import Bridge
    monday=date(2026,11,9)
    for activity,day in [(A.NIGHT_DUTY,monday-timedelta(days=1)),(A.NIGHT_OFF,monday)]:
        for recovery_first in (True,False):
            store=Store(':memory:');doctor=store.save_doctor('Demo');store.create_week(monday)
            recovery=Assignment('recovery',monday,A.RECOVERY,doctor)
            night=Assignment('night',day,activity,doctor)
            first,second=(recovery,night) if recovery_first else (night,recovery)
            store.save_assignment(first)
            bridge=Bridge(store);bridge.start=monday
            assert bridge.choices(second.day,second.activity)[0]['disabled']
            with pytest.raises(RuleError,match='error_recovery_night_off'):
                store.save_assignment(second)
            with pytest.raises(RuleError,match='error_recovery_night_off'):
                store.set_slot_doctors(second.day,second.activity,[doctor])
            assert len(store.raw_assignments())==1
            store.close()


def test_night_on_call_warns_next_morning_without_hours_or_counts(app):
    from turniamo.web_ui import Bridge
    monday=date(2026,11,2)
    store=Store(':memory:');doctor=store.save_doctor('Demo')
    store.save_assignment(Assignment('oncall',monday-timedelta(days=1),A.ON_CALL_NIGHT,doctor))
    raw=store.raw_assignments()
    assert minutes_for(raw[0],raw)==0
    assert all(a.activity!=A.NIGHT_OFF for a in effective_assignments(raw))
    report=period_reports(date(2026,11,1),raw,store.doctors())
    assert not any(report['monthly'][0]['counts'].values())
    assert not any(report['festivities'][0]['counts'].values())
    bridge=Bridge(store);bridge.start=monday
    assert bridge.choices(monday,A.CLINIC_AM)[0]['warning']
    assert not bridge.choices(monday,A.CLINIC_PM)[0]['warning']
    for activity in (A.CLINIC_AM,A.CLINIC_PM):
        store.save_assignment(Assignment(activity,monday,activity,doctor))
    assert {i.activity for i in issues_for_week(monday,store.week_context(monday))}=={A.CLINIC_AM}
    store.close()


def test_paid_annual_counts_assignments_not_night_off():
    raw=[assignment(date(2026,11,7),a,paid=True) for a in (A.CLINIC_AM,A.CLINIC_PM,A.NIGHT_DUTY)]
    raw += [assignment(date(2025,12,31),A.NIGHT_DUTY,paid=True),assignment(date(2026,12,31),A.NIGHT_DUTY,paid=True),assignment(date(2026,11,8),A.CLINIC_AM)]
    row=period_reports(date(2026,11,1),raw,[Doctor('a','Demo')])['festivities'][0]
    assert row['counts']['paid_clinic']==2
    assert row['counts']['paid_nights']==2
    assert [d['date'] for d in row['details']['paid_nights']]==['2026-11-07','2026-12-31']


def test_toolbar_positions_and_three_oncall_slots(app):
    store=Store(':memory:');store.set_setting('last_week','2026-11-02')
    window=MainWindow(store);window.show();wait_js(window,'window.turniamoReady === true')
    assert not js(window,"document.querySelector('#new-week') !== null")
    assert js(window,"document.querySelector('[data-tab=schedule]').textContent")==''
    assert js(window,"document.querySelectorAll('[data-activity=on_call_night]').length")==7
    assert js(window,"document.querySelector('#doctors').nextElementSibling.id")=='export'
    assert js(window,"document.querySelector('.week-controls').getBoundingClientRect().left") < 30
    assert js(window,"Math.abs((document.querySelector('#tabs').getBoundingClientRect().left+document.querySelector('#tabs').getBoundingClientRect().right)/2-innerWidth/2)<1")
    assert not js(window,"document.querySelector('main').textContent.includes('(+1)')")
    right=js(window,"document.querySelector('#settings').getBoundingClientRect().right")
    for tab in ('monthly','festivities'):
        js(window,f"document.querySelector('[data-tab={tab}]').click()")
        wait_js(window,f"tab==='{tab}'")
        assert js(window,"document.querySelector('#settings').getBoundingClientRect().right")==right
        assert js(window,"document.querySelector('#export').getBoundingClientRect().width>0")
        assert js(window,"Math.abs((document.querySelector('#tabs').getBoundingClientRect().left+document.querySelector('#tabs').getBoundingClientRect().right)/2-innerWidth/2)<1")
    from PySide6.QtTest import QTest
    QTest.qWait(200)
    window.grab().save('/tmp/turniamo-test4-annual.png')
    window.close();store.close()


def test_export_includes_reports_outside_displayed_week(app,tmp_path,monkeypatch):
    from turniamo.web_ui import Bridge,QFileDialog
    from openpyxl import load_workbook
    store=Store(':memory:');doctor=store.save_doctor('Demo')
    store.set_setting('last_week','2026-11-02')
    store.save_assignment(Assignment('clinic',date(2026,11,30),A.CLINIC_AM,doctor,paid=True))
    store.save_assignment(Assignment('night',date(2026,4,24),A.NIGHT_DUTY,doctor,paid=True))
    store.save_assignment(Assignment('oncall',date(2026,11,2),A.ON_CALL_NIGHT,doctor))
    bridge=Bridge(store);path=tmp_path/'all.xlsx'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(path),''))
    bridge.export('xlsx')
    book=load_workbook(path)
    assert book['Turni mensili']['H3'].value==1
    assert [book['Riepilogo annuale'].cell(3,col).value for col in range(2,6)]==[1,0,1,1]
    assert '20:00 - 08:00' in book['Calendario']['H7'].value
    assert 'Demo' in book['Calendario']['H7'].value
    store.close()


def test_night_duty_and_oncall_have_distinct_rest_windows():
    from turniamo.domain import rest_periods,rest_warning,ACTIVITIES,ABSENCES,MORNING_WORK
    monday=date(2026,11,9)
    for origin in (A.NIGHT_DUTY,A.NIGHT_OFF,A.ON_CALL_NIGHT):
        raw=[assignment(monday if origin==A.NIGHT_OFF else monday-timedelta(days=1),origin)]
        periods=rest_periods(raw)
        for activity in ACTIVITIES:
            expected=activity in MORNING_WORK if origin==A.ON_CALL_NIGHT else activity not in ABSENCES|{A.NIGHT_OFF}
            assert bool(rest_warning(monday,'a',activity,periods))==expected
            assert not rest_warning(monday,'b',activity,periods)
            assert not rest_warning(monday+timedelta(days=1),'a',activity,periods)
    both=[assignment(monday,A.NIGHT_OFF),assignment(monday-timedelta(days=1),A.ON_CALL_NIGHT)]
    assert rest_warning(monday,'a',A.CLINIC_PM,rest_periods(both))=='warning_after_night_off'
