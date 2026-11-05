from dataclasses import replace
from datetime import timedelta
import pytest
from turniamo.domain import Activity as A, Assignment, RuleError
from turniamo.storage import Store
from test_domain import MONDAY


def setup():
    store=Store(':memory:')
    ids=[store.save_doctor(name) for name in ('Alpha','Beta','Gamma')]
    store.create_week(MONDAY)
    return store,ids


def test_bulk_is_atomic_and_retains_existing_metadata():
    s,(a,b,c)=setup()
    original=Assignment('old',MONDAY,A.CLINIC_AM,a,True,'reference','Chief')
    s.save_assignment(original)
    s.save_assignment(Assignment('leave',MONDAY,A.HOLIDAY,c))
    with pytest.raises(RuleError):
        s.set_slot_doctors(MONDAY,A.CLINIC_AM,[b,c])
    assert original in s.raw_assignments()
    assert not any(x.doctor_id==b for x in s.raw_assignments())
    s.set_slot_doctors(MONDAY,A.CLINIC_AM,[a,b])
    assert original in s.raw_assignments()
    assert len([x for x in s.raw_assignments() if x.activity==A.CLINIC_AM])==2
    s.set_slot_doctors(MONDAY,A.CLINIC_AM,[])
    assert [x.id for x in s.raw_assignments()]==['leave']


def test_bulk_ward_promotes_retained_helper_and_respects_selection_order():
    s,(a,b,c)=setup()
    s.set_slot_doctors(MONDAY,A.WARD,[b,a,c])
    assert next(x for x in s.raw_assignments() if x.doctor_id==b).activity==A.WARD
    helper=next(x for x in s.raw_assignments() if x.doctor_id==a)
    s.save_assignment(replace(helper,paid=True,associate_role='training',associate_name='Young'))
    s.set_slot_doctors(MONDAY,A.WARD,[a,c])
    leads=[x for x in s.raw_assignments() if x.activity==A.WARD]
    assert len(leads)==1
    # Deterministic promotion keeps the stored helper metadata, regardless of ID order.
    retained=next(x for x in s.raw_assignments() if x.doctor_id==a)
    assert retained.paid and retained.associate_name=='Young'


def test_bulk_night_off_lock_and_night_carryover():
    s,(a,b,c)=setup()
    s.set_slot_doctors(MONDAY,A.NIGHT_DUTY,[a,b])
    next_day=MONDAY+timedelta(days=1)
    with pytest.raises(RuleError,match='error_derived'):
        s.set_slot_doctors(next_day,A.NIGHT_OFF,[a])
    s.set_slot_doctors(next_day,A.NIGHT_OFF,[a,b,c])
    assert len([x for x in s.week_context(MONDAY) if x.activity==A.NIGHT_OFF])==3
    s.set_slot_doctors(MONDAY,A.NIGHT_DUTY,[])
    assert [x.doctor_id for x in s.week_context(MONDAY) if x.activity==A.NIGHT_OFF]==[c]
