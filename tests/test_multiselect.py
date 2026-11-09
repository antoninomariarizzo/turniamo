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


@pytest.mark.parametrize("activity", [A.WARD, A.WEEK_SERVICE])
def test_single_doctor_slots_are_atomic_and_allow_replacement(activity):
    s,(a,b,c)=setup()
    original=Assignment('old',MONDAY,activity,a,True,'reference','Chief')
    s.save_assignment(original)
    with pytest.raises(RuleError,match='error_single_doctor'):
        s.save_assignment(Assignment('extra',MONDAY,activity,b))
    with pytest.raises(RuleError,match='error_single_doctor'):
        s.set_slot_doctors(MONDAY,activity,[b,c])
    assert s.raw_assignments()==[original]
    s.set_slot_doctors(MONDAY,activity,[a])
    assert s.raw_assignments()==[original]
    s.set_slot_doctors(MONDAY,activity,[b])
    assert [(x.activity,x.doctor_id) for x in s.raw_assignments()]==[(activity,b)]
    s.set_slot_doctors(MONDAY,activity,[])
    assert s.raw_assignments()==[]

@pytest.mark.parametrize("first,second", [(A.SURGERY_2,A.SURGERY_3),(A.DAY_DUTY,A.NIGHT_DUTY),(A.NIGHT_DUTY,A.DAY_DUTY)])
def test_bulk_conflict_rolls_back(first,second):
    s,(a,b,c)=setup()
    s.set_slot_doctors(MONDAY,first,[a])
    before=s.raw_assignments()
    with pytest.raises(RuleError):
        s.set_slot_doctors(MONDAY,second,[b,a])
    assert s.raw_assignments()==before


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


@pytest.mark.parametrize('manual', [False,True])
@pytest.mark.parametrize('work_first', [False,True])
def test_bulk_night_rest_is_atomic_in_both_orders(manual,work_first):
    s,(a,b,c)=setup()
    rest_day=MONDAY+timedelta(days=1)
    origin_day,origin_activity=(rest_day,A.NIGHT_OFF) if manual else (MONDAY,A.NIGHT_DUTY)
    if work_first:
        s.set_slot_doctors(rest_day,A.ON_CALL_PM,[a])
        before=s.raw_assignments()
        with pytest.raises(RuleError,match='error_night_off_unavailable'):
            s.set_slot_doctors(origin_day,origin_activity,[b,a])
    else:
        s.set_slot_doctors(origin_day,origin_activity,[a])
        s.set_slot_doctors(rest_day,A.ON_CALL_PM,[b])
        before=s.raw_assignments()
        with pytest.raises(RuleError,match='error_night_off_unavailable'):
            s.set_slot_doctors(rest_day,A.ON_CALL_PM,[c,a])
    assert s.raw_assignments()==before
    s.close()
