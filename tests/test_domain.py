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
    (A.WARD, 540), (A.WARD_HELP, 390), (A.WEEK_SERVICE, 390),
    (A.DAY_DUTY, 780), (A.NIGHT_DUTY, 390), (A.NIGHT_OFF, 390),
    (A.ON_CALL_AM, 390), (A.ON_CALL_PM, 240), (A.CLINIC_AM, 360),
    (A.CLINIC_PM, 270), (A.ABSENCE, 0), (A.HOLIDAY, 380), (A.RECOVERY, -380),
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


def test_ward_roles_and_week_service():
    lead, helper = entry(A.WARD), entry(A.WARD_HELP, doctor="b")
    assert minutes_for(lead, [lead, helper]) == 480
    assert minutes_for(helper, [lead, helper]) == 390
    assert minutes_for(lead, [lead, entry(A.WEEK_SERVICE, doctor="b")]) == 540
    assert minutes_for(lead, [lead, entry(A.WARD_HELP)]) == 540


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
    assert {(i.key, i.day, i.doctor_id) for i in issues} == {("warning_after_night_off", MONDAY + timedelta(days=1), "a")}
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
    total = Total(ordinary=2340, recovery=-380, paid=780)
    assert total.net == 1960
    assert total.status == "within"
    assert Total(ordinary=2500, recovery=-380).status == "above"
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
