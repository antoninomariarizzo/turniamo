from datetime import date, timedelta
from uuid import uuid4

import pytest

from turniamo.domain import (
    Activity as A, Assignment, Doctor, RuleError, Total, duration,
    effective_assignments, issues_for_week, minutes_for, totals_for_week, validate_assignment,
)

MONDAY = date(2026, 12, 7)


def entry(activity, day=MONDAY, doctor="a", paid=False, **kwargs):
    return Assignment(str(uuid4()), day, activity, doctor, paid, **kwargs)


@pytest.mark.parametrize("activity,expected", [
    (A.SURGERY_URGENT, 420), (A.SURGERY_2, 420), (A.SURGERY_3, 420),
    (A.WARD, 540), (A.WEEK_SERVICE, 390),
    (A.DAY_DUTY, 780), (A.NIGHT_DUTY, 390), (A.NIGHT_OFF, 390),
    (A.ON_CALL_AM, 390), (A.ON_CALL_PM, 240), (A.CLINIC_AM, 360),
    (A.CLINIC_PM, 270), (A.ABSENCE, 0), (A.HOLIDAY, 380), (A.RECOVERY, 0),
])
def test_base_weights(activity, expected):
    a = entry(activity)
    assert minutes_for(a, [a]) == expected


@pytest.mark.parametrize("pm,expected", [(A.CLINIC_PM, 660), (A.ON_CALL_PM, 600)])
def test_surgery_combination(pm, expected):
    assignments = [entry(A.SURGERY_URGENT), entry(pm)]
    assert sum(minutes_for(a, assignments) for a in assignments) == expected


def test_surgery_discount_requires_same_doctor_and_day_and_includes_paid_surgery():
    clinic = entry(A.CLINIC_PM)
    assert minutes_for(clinic, [clinic, entry(A.SURGERY_2, doctor="b")]) == 270
    assert minutes_for(clinic, [clinic, entry(A.SURGERY_2, day=MONDAY + timedelta(days=1))]) == 270
    assert minutes_for(clinic, [clinic, entry(A.SURGERY_2, paid=True)]) == 240


@pytest.mark.parametrize("paid", [False, True])
def test_ward_hours_depend_on_same_day_week_service(paid):
    lead, service = entry(A.WARD, paid=paid), entry(A.WEEK_SERVICE, doctor="b", paid=True)
    assert minutes_for(lead, [lead, service]) == 480
    assert minutes_for(service, [lead, service]) == 390
    assert minutes_for(lead, [lead, entry(A.WEEK_SERVICE, day=MONDAY+timedelta(days=1))]) == 540
    assert minutes_for(lead, [lead]) == 540

@pytest.mark.parametrize("first,second", [
    (a,b) for group in ((A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3),(A.DAY_DUTY,A.NIGHT_DUTY))
    for a in group for b in group if a != b
])
def test_exclusive_assignments(first, second):
    existing = entry(first)
    with pytest.raises(RuleError, match="error_.*_conflict"):
        validate_assignment(entry(second), [existing])
    validate_assignment(entry(second, doctor="b"), [existing])
    validate_assignment(entry(second, day=MONDAY+timedelta(days=2)), [existing])
    assert any(i.severity == "error" for i in issues_for_week(MONDAY, [existing, entry(second)]))


def test_two_main_doctors_get_full_hours_trainee_and_contact_get_none():
    assignments = [entry(A.SURGERY_2, associate_role="training", associate_name="Young"),
                   entry(A.SURGERY_2, doctor="b", associate_role="reference", associate_name="Chief")]
    totals = totals_for_week(MONDAY, assignments, [Doctor("a", "Alpha"), Doctor("b", "Beta"), Doctor("c", "Young")])
    assert totals["a"].ordinary == totals["b"].ordinary == 420
    assert totals["c"].ordinary == 0


@pytest.mark.parametrize("paid", [False, True])
def test_sunday_night_is_split_between_weeks(paid):
    night = entry(A.NIGHT_DUTY, day=MONDAY + timedelta(days=6), paid=paid)
    assignments = effective_assignments([night])
    first = totals_for_week(MONDAY, assignments, [Doctor("a", "Alpha")])["a"]
    next_week = totals_for_week(MONDAY + timedelta(days=7), assignments, [Doctor("a", "Alpha")])["a"]
    assert first.paid == next_week.paid == (390 if paid else 0)
    assert first.ordinary == next_week.ordinary == (0 if paid else 390)
    assert assignments[1].source_id == night.id


def test_manual_night_off_does_not_double_automatic_or_override_paid():
    night = entry(A.NIGHT_DUTY, paid=True)
    manual = entry(A.NIGHT_OFF, day=MONDAY + timedelta(days=1))
    effective = effective_assignments([night, manual])
    assert len(effective) == 2
    assert all(a.paid for a in effective)


def test_night_warning_is_on_night_off_morning_and_trainee_is_ignored():
    night = entry(A.NIGHT_DUTY)
    work_sn = entry(A.CLINIC_AM, day=MONDAY + timedelta(days=1))
    work_after_sn = entry(A.SURGERY_2, day=MONDAY + timedelta(days=2))
    trainee = entry(A.CLINIC_PM, day=MONDAY + timedelta(days=2), doctor="b", associate_role="training", associate_name="Alpha")
    issues = issues_for_week(MONDAY, effective_assignments([night, work_sn, work_after_sn, trainee]))
    assert {(i.key, i.day, i.doctor_id) for i in issues} == {("error_night_off_unavailable", MONDAY + timedelta(days=1), "a")}
    assert {i.activity for i in issues} == {A.CLINIC_AM}


@pytest.mark.parametrize("absence", [A.HOLIDAY, A.RECOVERY, A.ABSENCE])
def test_absences_block_in_both_orders(absence):
    leave, work = entry(absence), entry(A.CLINIC_AM)
    with pytest.raises(RuleError, match="error_unavailable"):
        validate_assignment(work, [leave])
    with pytest.raises(RuleError, match="error_unavailable"):
        validate_assignment(leave, [work])
    validate_assignment(entry(A.CLINIC_AM, doctor="b"), [leave])


def test_night_off_can_coexist_with_leave():
    night = entry(A.NIGHT_DUTY, day=MONDAY - timedelta(days=1))
    validate_assignment(entry(A.HOLIDAY), [night])


def test_saturday_only_and_duplicate_guard():
    with pytest.raises(RuleError, match="error_saturday_only"):
        validate_assignment(entry(A.ON_CALL_AM), [])
    validate_assignment(entry(A.ON_CALL_AM, day=MONDAY + timedelta(days=5)), [])
    a = entry(A.CLINIC_AM)
    with pytest.raises(RuleError, match="error_duplicate_assignment"):
        validate_assignment(entry(A.CLINIC_AM), [a])
    validate_assignment(a, [a])  # Updating the same record is valid.


@pytest.mark.parametrize("minutes,status", [(2279, "below"), (2280, "within"), (2400, "within"), (2401, "above")])
def test_threshold_boundaries(minutes, status):
    assert Total(ordinary=minutes).status == status


def test_recovery_is_excluded_from_alarm_and_paid_does_not_help_threshold():
    total = Total(ordinary=2340, recovery=0, paid=780)
    assert total.net == 2340
    assert total.status == "within"
    assert Total(ordinary=2500, recovery=0).status == "above"
    assert Total(ordinary=2000, paid=780).status == "below"


def test_exact_duration_and_holiday_credit():
    assert duration(380) == "6h20m"
    assert duration(-380) == "−6h20m"
    assert duration(390) == "6h30m"
    assert Total(ordinary=2000, holidays=380).status == "within"


def test_six_days_of_holiday_are_exactly_38_hours():
    assignments = [entry(A.HOLIDAY, day=MONDAY + timedelta(days=i)) for i in range(6)]
    total = totals_for_week(MONDAY, assignments, [Doctor("a", "Alpha")])["a"]
    assert total.holidays == 2280
    assert total.status == "within"


def test_invalid_paid_absence_and_incomplete_associate():
    with pytest.raises(RuleError, match="error_paid_absence"):
        validate_assignment(entry(A.HOLIDAY, paid=True), [])
    with pytest.raises(RuleError, match="error_associate"):
        validate_assignment(entry(A.CLINIC_AM, associate_role="training"), [])


@pytest.mark.parametrize('absence', [A.ABSENCE,A.HOLIDAY,A.RECOVERY])
def test_multidisciplinary_requires_presence_in_both_orders(absence):
    leave, multidisciplinary = entry(absence), entry(A.MULTIDISCIPLINARY)
    with pytest.raises(RuleError,match='error_unavailable'):
        validate_assignment(multidisciplinary,[leave])
    with pytest.raises(RuleError,match='error_unavailable'):
        validate_assignment(leave,[multidisciplinary])
    validate_assignment(entry(A.MULTIDISCIPLINARY,doctor='b'),[leave])
    validate_assignment(entry(A.MULTIDISCIPLINARY,day=MONDAY+timedelta(days=1)),[leave])
    assert minutes_for(multidisciplinary,[multidisciplinary])==0
    issues=issues_for_week(MONDAY,[leave,multidisciplinary])
    assert any(i.key=='error_unavailable' and i.activity==A.MULTIDISCIPLINARY for i in issues)


def test_historical_conflicts_flag_only_involved_activities():
    raw=[entry(A.SURGERY_2),entry(A.WARD),entry(A.ON_CALL_NIGHT),entry(A.MULTIDISCIPLINARY)]
    conflicts=[i for i in issues_for_week(MONDAY,raw) if i.key=='error_time_conflict']
    assert {i.activity for i in conflicts}=={A.SURGERY_2,A.WARD}
    assert all(i.severity=='error' for i in conflicts)


@pytest.mark.parametrize("band", [
    (A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3,A.WARD,A.WEEK_SERVICE,A.DAY_DUTY,A.ON_CALL_AM,A.CLINIC_AM),
    (A.WARD,A.DAY_DUTY,A.ON_CALL_PM,A.CLINIC_PM),
    (A.NIGHT_DUTY,A.ON_CALL_NIGHT),
])
def test_each_band_is_exclusive_in_both_orders(band):
    from itertools import permutations
    for first,second in permutations(band,2):
        if A.ON_CALL_AM in (first,second) and any(a in (A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3,A.WARD,A.WEEK_SERVICE) for a in (first,second)):
            continue
        day=MONDAY+timedelta(days=5) if A.ON_CALL_AM in (first,second) else MONDAY
        for paid in (False,True):
            existing=entry(first,day=day,paid=paid)
            with pytest.raises(RuleError,match='error_time_conflict'):
                validate_assignment(entry(second,day=day),[existing])
            validate_assignment(entry(second,day=day,doctor='b'),[existing])
            validate_assignment(entry(second,day=day+timedelta(days=7)),[existing])


@pytest.mark.parametrize("first,second", [
    (A.SURGERY_2,A.CLINIC_PM),(A.SURGERY_2,A.ON_CALL_PM),
    (A.WEEK_SERVICE,A.CLINIC_PM),(A.CLINIC_AM,A.ON_CALL_PM),
    (A.CLINIC_PM,A.NIGHT_DUTY),
    (A.CLINIC_PM,A.ON_CALL_NIGHT),(A.SURGERY_2,A.MULTIDISCIPLINARY),
])
def test_distinct_bands_remain_available(first,second):
    validate_assignment(entry(first),[entry(second)])
    validate_assignment(entry(second),[entry(first)])


@pytest.mark.parametrize('activity', [A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3,A.WARD,A.WEEK_SERVICE])
@pytest.mark.parametrize('offset', [5,6])
def test_weekend_core_duties_are_blocked(activity,offset):
    with pytest.raises(RuleError,match='error_weekdays_only'):
        validate_assignment(entry(activity,day=MONDAY+timedelta(days=offset)),[])
    validate_assignment(entry(activity),[])


@pytest.mark.parametrize('activity', [A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3,A.WARD,A.WEEK_SERVICE,
                                    A.DAY_DUTY,A.NIGHT_DUTY,A.CLINIC_AM,A.CLINIC_PM,A.ON_CALL_PM,
                                    A.MULTIDISCIPLINARY])
@pytest.mark.parametrize('rest_day', [MONDAY,date(2027,1,1)])
def test_night_rest_blocks_all_work_in_both_orders_across_boundaries(activity,rest_day):
    work=entry(activity,day=rest_day)
    night=entry(A.NIGHT_DUTY,day=rest_day-timedelta(days=1))
    manual=entry(A.NIGHT_OFF,day=rest_day)
    for origin in (night,manual):
        with pytest.raises(RuleError,match='error_night_off_unavailable'):
            validate_assignment(work,[origin])
        with pytest.raises(RuleError,match='error_night_off_unavailable'):
            validate_assignment(origin,[work])
        validate_assignment(entry(A.CLINIC_PM,day=rest_day+timedelta(days=1)),[origin])
        validate_assignment(entry(activity,day=rest_day,doctor='b'),[origin])
        for absence in (A.HOLIDAY,A.ABSENCE):
            validate_assignment(entry(absence,day=rest_day),[origin])


def test_night_rest_blocks_saturday_on_call_and_editing_night_keeps_own_rest_out_of_validation():
    from dataclasses import replace
    friday=MONDAY+timedelta(days=4)
    night=entry(A.NIGHT_DUTY,day=friday)
    with pytest.raises(RuleError,match='error_night_off_unavailable'):
        validate_assignment(entry(A.ON_CALL_AM,day=friday+timedelta(days=1)),[night])
    validate_assignment(replace(night,paid=True),[night])
    validate_assignment(replace(night,day=friday+timedelta(days=1)),[night])


@pytest.mark.parametrize('activity', [A.CLINIC_AM,A.CLINIC_PM,A.ON_CALL_PM])
def test_night_guard_with_nonoverlapping_work_warns_both_entries(activity):
    from turniamo.domain import guard_warning
    night,work=entry(A.NIGHT_DUTY),entry(activity)
    validate_assignment(night,[work]);validate_assignment(work,[night])
    assert guard_warning(MONDAY,'a',activity,[night])=='warning_guard_combination'
    assert guard_warning(MONDAY,'a',A.NIGHT_DUTY,[work])=='warning_guard_combination'
    assert {i.activity for i in issues_for_week(MONDAY,[night,work]) if i.key=='warning_guard_combination'}=={activity,A.NIGHT_DUTY}


@pytest.mark.parametrize('first,second', [(A.DAY_DUTY,A.CLINIC_PM),(A.DAY_DUTY,A.ON_CALL_PM),
    (A.DAY_DUTY,A.ON_CALL_NIGHT),(A.NIGHT_DUTY,A.ON_CALL_NIGHT),(A.CLINIC_PM,A.ON_CALL_PM)])
def test_real_clock_overlaps_remain_blocked(first,second):
    for a,b in ((first,second),(second,first)):
        with pytest.raises(RuleError,match='error_time_conflict'):
            validate_assignment(entry(a),[entry(b)])


@pytest.mark.parametrize('first,second', [(A.CLINIC_AM,A.ON_CALL_PM),(A.CLINIC_AM,A.ON_CALL_NIGHT),
    (A.CLINIC_PM,A.ON_CALL_NIGHT),(A.ON_CALL_AM,A.CLINIC_PM)])
def test_clinic_and_oncall_allow_nonoverlapping_intervals(first,second):
    day=MONDAY+timedelta(days=5)
    validate_assignment(entry(first,day=day),[entry(second,day=day)])
    validate_assignment(entry(second,day=day),[entry(first,day=day)])


@pytest.mark.parametrize('surgery', [A.SURGERY_URGENT,A.SURGERY_2,A.SURGERY_3])
def test_clinic_label_changes_without_changing_after_surgery_credit(surgery):
    from turniamo.layout import TIMES
    clinic=entry(A.CLINIC_PM);operation=entry(surgery)
    assert TIMES[A.CLINIC_PM]=='14:30 - 19:00'
    validate_assignment(clinic,[operation]);validate_assignment(operation,[clinic])
    assert minutes_for(clinic,[clinic,operation])==240
    assert minutes_for(clinic,[clinic])==270


@pytest.mark.parametrize('activity',[A.DAY_DUTY,A.NIGHT_DUTY])
@pytest.mark.parametrize('offset',[5,6])
def test_guard_remains_available_on_weekends(activity,offset):
    validate_assignment(entry(activity,day=MONDAY+timedelta(days=offset)),[])


@pytest.mark.parametrize('activity,paid',[(A.ON_CALL_NIGHT,False),(A.CLINIC_AM,True),(A.CLINIC_PM,True)])
@pytest.mark.parametrize('rest_day',[MONDAY,date(2027,1,1)])
def test_post_night_exceptions_allowed_and_yellow_in_both_orders(activity,paid,rest_day):
    from dataclasses import replace
    work=entry(activity,day=rest_day,paid=paid)
    for origin in (entry(A.NIGHT_DUTY,day=rest_day-timedelta(days=1)),entry(A.NIGHT_OFF,day=rest_day)):
        validate_assignment(work,[origin]);validate_assignment(origin,[work])
        context=effective_assignments([origin,work])
        issues=issues_for_week(rest_day,context)
        assert any(i.key=='warning_night_off_exception' and i.activity==activity and i.severity=='warning' for i in issues)
        assert not any(i.activity==A.NIGHT_OFF for i in issues)
        if paid:
            with pytest.raises(RuleError,match='error_night_off_unavailable'):
                validate_assignment(replace(work,paid=False),context)
        assert minutes_for(work,context)==(0 if activity==A.ON_CALL_NIGHT else 360 if activity==A.CLINIC_AM else 270)


def test_post_night_exception_does_not_override_absences_or_overlap():
    raw=[entry(A.NIGHT_OFF),entry(A.ABSENCE)]
    with pytest.raises(RuleError,match='error_unavailable'):
        validate_assignment(entry(A.CLINIC_PM,paid=True),raw)
    with pytest.raises(RuleError,match='error_unavailable'):
        validate_assignment(entry(A.ON_CALL_NIGHT),raw)


@pytest.mark.parametrize("offset", range(7))
@pytest.mark.parametrize("paid", [False, True])
def test_afternoon_on_call_weekend_zero_hours(offset, paid):
    assignment = entry(A.ON_CALL_PM, day=MONDAY + timedelta(days=offset), paid=paid)
    expected = 0 if offset >= 5 else 240
    assert minutes_for(assignment, [assignment]) == expected
    total = totals_for_week(MONDAY, [assignment], [Doctor("a", "Alpha")])["a"]
    assert total.ordinary == (0 if paid else expected)
    assert total.paid == (expected if paid else 0)
    surgery = entry(A.SURGERY_2, day=assignment.day)
    assert minutes_for(assignment, [assignment, surgery]) == (0 if offset >= 5 else 180)


def test_recovery_preserves_worked_hours():
    data = [entry(A.SURGERY_2), entry(A.RECOVERY, day=MONDAY+timedelta(days=1))]
    total = totals_for_week(MONDAY, data, [Doctor('a', 'Alpha')])['a']
    assert total.net == total.threshold_total == 420
    assert total.recovery == 0
