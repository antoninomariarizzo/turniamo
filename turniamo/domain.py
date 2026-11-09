"""Scheduling rules. Durations are integer minutes; no GUI or storage dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
import unicodedata


class Activity(StrEnum):
    SURGERY_URGENT = "surgery_urgent"
    SURGERY_2 = "surgery_2"
    SURGERY_3 = "surgery_3"
    WARD = "ward"
    WEEK_SERVICE = "week_service"
    DAY_DUTY = "day_duty"
    NIGHT_DUTY = "night_duty"
    ON_CALL_AM = "on_call_am"
    ON_CALL_PM = "on_call_pm"
    ON_CALL_NIGHT = "on_call_night"
    CLINIC_AM = "clinic_am"
    CLINIC_PM = "clinic_pm"
    MULTIDISCIPLINARY = "multidisciplinary"
    NIGHT_OFF = "night_off"
    ABSENCE = "absence"
    HOLIDAY = "holiday"
    RECOVERY = "recovery"


# Displayed clock intervals and overlap checks share one source. Credited minutes
# remain separate in minutes_for; overnight ends are relative to the start date.
ACTIVITY_INTERVALS = {
    Activity.SURGERY_URGENT: (465, 900), Activity.SURGERY_2: (465, 900),
    Activity.SURGERY_3: (465, 900), Activity.WARD: (465, 1020),
    Activity.WEEK_SERVICE: (465, 840), Activity.DAY_DUTY: (465, 1230),
    Activity.NIGHT_DUTY: (1185, 1950), Activity.ON_CALL_AM: (465, 840),
    Activity.ON_CALL_PM: (840, 1080), Activity.ON_CALL_NIGHT: (1200, 1920),
    Activity.CLINIC_AM: (465, 810), Activity.CLINIC_PM: (870, 1140),
}


ACTIVITIES = tuple(Activity)
SURGERIES = frozenset((Activity.SURGERY_URGENT, Activity.SURGERY_2, Activity.SURGERY_3))
WEEKDAY_ONLY = SURGERIES | {Activity.WARD, Activity.WEEK_SERVICE}
DAILY_EXCLUSIVE = WEEKDAY_ONLY | {Activity.DAY_DUTY, Activity.NIGHT_DUTY}
SINGLE_DOCTOR_ACTIVITIES = frozenset((Activity.WARD, Activity.WEEK_SERVICE))
ABSENCES = frozenset((Activity.ABSENCE, Activity.HOLIDAY, Activity.RECOVERY))
WORK = frozenset(ACTIVITIES) - ABSENCES - {Activity.NIGHT_OFF, Activity.MULTIDISCIPLINARY, Activity.ON_CALL_NIGHT}

# Informational duties still require the doctor to be present.
AVAILABILITY_REQUIRED = frozenset(ACTIVITIES) - ABSENCES - {Activity.NIGHT_OFF}


class RuleError(ValueError):
    """An invalid proposed change, with a translatable message key."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(key)


def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFKC", " ".join(name.split())).casefold()


def monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def duration(minutes: int) -> str:
    sign = "−" if minutes < 0 else ""
    hours, mins = divmod(abs(minutes), 60)
    return f"{sign}{hours}h{mins:02d}m"


@dataclass(frozen=True)
class Doctor:
    id: str
    name: str
    active: bool = True


@dataclass(frozen=True)
class Assignment:
    id: str
    day: date
    activity: Activity
    doctor_id: str
    paid: bool = False
    associate_role: str = ""
    associate_name: str = ""
    source_id: str | None = None


@dataclass(frozen=True)
class Issue:
    key: str
    doctor_id: str
    day: date
    severity: str = "warning"
    activity: Activity | None = None


@dataclass(frozen=True)
class Total:
    ordinary: int = 0
    holidays: int = 0
    recovery: int = 0
    paid: int = 0

    @property
    def net(self) -> int:
        return self.ordinary + self.holidays + self.recovery

    @property
    def threshold_total(self) -> int:
        # Recovery never creates an under-hours alarm or hides over-hours.
        return self.ordinary + self.holidays

    @property
    def status(self) -> str:
        if self.threshold_total < 38 * 60:
            return "below"
        if self.threshold_total > 40 * 60:
            return "above"
        return "within"


def effective_assignments(raw: list[Assignment]) -> list[Assignment]:
    """Derive night-off from nights, including across week boundaries.

    A manually entered incoming night-off is allowed when the previous night is
    unavailable. If the night is later entered it replaces the manual entry in
    calculation/display; it never doubles the hours or overrides payment status.
    """
    result = [a for a in raw if a.activity != Activity.NIGHT_OFF]
    generated = {}
    for a in raw:
        if a.activity == Activity.NIGHT_DUTY:
            day = a.day + timedelta(days=1)
            generated[(day, a.doctor_id)] = Assignment(
                f"night-off:{a.id}", day, Activity.NIGHT_OFF, a.doctor_id,
                paid=a.paid, source_id=a.id,
            )
    result.extend(a for a in raw if a.activity == Activity.NIGHT_OFF
                  and (a.day, a.doctor_id) not in generated)
    result.extend(generated.values())
    return sorted(result, key=lambda a: (a.day, ACTIVITIES.index(a.activity), a.id))


def minutes_for(a: Assignment, assignments: list[Assignment]) -> int:
    same_day = [x for x in assignments if x.day == a.day]
    has_surgery = any(x.doctor_id == a.doctor_id and x.activity in SURGERIES for x in same_day)
    if a.activity in SURGERIES:
        return 420
    if a.activity == Activity.WARD:
        has_help = any(x.activity == Activity.WEEK_SERVICE for x in same_day)
        return 480 if has_help else 540
    if a.activity in (Activity.WEEK_SERVICE, Activity.NIGHT_DUTY,
                       Activity.NIGHT_OFF, Activity.ON_CALL_AM):
        return 390
    if a.activity == Activity.DAY_DUTY:
        return 780
    if a.activity == Activity.ON_CALL_PM:
        return 180 if has_surgery else 240
    if a.activity == Activity.CLINIC_PM:
        return 240 if has_surgery else 270
    if a.activity == Activity.CLINIC_AM:
        return 360
    if a.activity == Activity.HOLIDAY:
        return 380
    if a.activity == Activity.RECOVERY:
        return -380
    return 0


def totals_for_week(start: date, assignments: list[Assignment], doctors: list[Doctor]) -> dict[str, Total]:
    buckets = {d.id: dict(ordinary=0, holidays=0, recovery=0, paid=0) for d in doctors}
    for a in assignments:
        if not start <= a.day <= start + timedelta(days=6):
            continue
        bucket = buckets.setdefault(a.doctor_id, dict(ordinary=0, holidays=0, recovery=0, paid=0))
        key = ("paid" if a.paid else "holidays" if a.activity == Activity.HOLIDAY
               else "recovery" if a.activity == Activity.RECOVERY else "ordinary")
        bucket[key] += minutes_for(a, assignments)
    return {doctor_id: Total(**values) for doctor_id, values in buckets.items()}


def activity_day_error(day: date, activity: Activity) -> str:
    if activity in WEEKDAY_ONLY and day.weekday() >= 5:
        return "error_weekdays_only"
    if activity == Activity.ON_CALL_AM and day.weekday() != 5:
        return "error_saturday_only"
    return ""


def hidden_activities(day: date):
    return {Activity.ON_CALL_AM} if day.weekday() != 5 else set()


def night_off_exception(activity: Activity, paid: bool = False) -> bool:
    return activity == Activity.ON_CALL_NIGHT or (activity in {Activity.CLINIC_AM, Activity.CLINIC_PM} and paid)


def selection_assignment(assignment_id, day, activity, doctor_id, raw):
    # The picker explicitly labels clinics during post-night rest as paid only.
    paid = activity in {Activity.CLINIC_AM, Activity.CLINIC_PM} and any(
        a.day == day and a.doctor_id == doctor_id and a.activity == Activity.NIGHT_OFF
        for a in effective_assignments(raw)
    )
    return Assignment(assignment_id, day, activity, doctor_id, paid=paid)


def validate_assignment(proposal: Assignment, raw: list[Assignment]) -> None:
    day_error = activity_day_error(proposal.day, proposal.activity)
    if day_error:
        raise RuleError(day_error)
    if proposal.paid and proposal.activity in ABSENCES | {Activity.MULTIDISCIPLINARY, Activity.ON_CALL_NIGHT}:
        raise RuleError("error_paid_absence")
    if proposal.associate_role not in ("", "training", "reference"):
        raise RuleError("error_associate")
    if bool(proposal.associate_role) != bool(proposal.associate_name.strip()):
        raise RuleError("error_associate")
    others = [a for a in effective_assignments(raw) if a.id != proposal.id and a.source_id != proposal.id]
    if proposal.activity in SINGLE_DOCTOR_ACTIVITIES and any(
        a.day == proposal.day and a.activity == proposal.activity for a in others
    ):
        raise RuleError("error_single_doctor")
    same = [a for a in others if a.day == proposal.day and a.doctor_id == proposal.doctor_id]
    if any(a.activity == proposal.activity for a in same):
        raise RuleError("error_duplicate_assignment")
    if any(activities_conflict(proposal.activity, a.activity) for a in same):
        raise RuleError("error_time_conflict")
    if proposal.activity == Activity.RECOVERY and any(a.activity == Activity.NIGHT_OFF for a in same):
        raise RuleError("error_recovery_night_off")
    if proposal.activity == Activity.NIGHT_OFF and any(a.activity == Activity.RECOVERY for a in same):
        raise RuleError("error_recovery_night_off")
    if proposal.activity == Activity.NIGHT_DUTY and any(a.doctor_id == proposal.doctor_id and a.day == proposal.day + timedelta(days=1) and a.activity == Activity.RECOVERY for a in others):
        raise RuleError("error_recovery_night_off")
    if proposal.activity in AVAILABILITY_REQUIRED and not night_off_exception(proposal.activity, proposal.paid) and any(a.activity == Activity.NIGHT_OFF for a in same):
        raise RuleError("error_night_off_unavailable")
    if proposal.activity == Activity.NIGHT_OFF and any(a.activity in AVAILABILITY_REQUIRED and not night_off_exception(a.activity, a.paid) for a in same):
        raise RuleError("error_night_off_unavailable")
    if proposal.activity == Activity.NIGHT_DUTY and any(
        a.doctor_id == proposal.doctor_id and a.day == proposal.day + timedelta(days=1)
        and a.activity in AVAILABILITY_REQUIRED and not night_off_exception(a.activity, a.paid) for a in others
    ):
        raise RuleError("error_night_off_unavailable")
    # Night-off counts a previous night's work. Leave on that calendar day does
    # not introduce a new work assignment and is therefore allowed.
    if proposal.activity in ABSENCES:
        if any(a.activity in AVAILABILITY_REQUIRED | ABSENCES for a in same):
            raise RuleError("error_unavailable")
    elif proposal.activity in AVAILABILITY_REQUIRED and any(a.activity in ABSENCES for a in same):
        raise RuleError("error_unavailable")


MORNING_WORK = SURGERIES | {Activity.WARD, Activity.WEEK_SERVICE, Activity.DAY_DUTY, Activity.ON_CALL_AM, Activity.CLINIC_AM}


def activities_conflict(first: Activity, second: Activity) -> bool:
    if first == second:
        return False  # Duplicate assignments have a dedicated validation error.
    if first in DAILY_EXCLUSIVE and second in DAILY_EXCLUSIVE:
        return True
    # These PM duties start after surgery and have dedicated credited durations.
    if (first in SURGERIES and second in {Activity.CLINIC_PM, Activity.ON_CALL_PM}) or (
        second in SURGERIES and first in {Activity.CLINIC_PM, Activity.ON_CALL_PM}
    ):
        return False
    left, right = ACTIVITY_INTERVALS.get(first), ACTIVITY_INTERVALS.get(second)
    return bool(left and right and max(left[0], right[0]) < min(left[1], right[1]))


def guard_warning(day, doctor_id, activity, assignments):
    guards = {Activity.DAY_DUTY, Activity.NIGHT_DUTY}
    if activity not in AVAILABILITY_REQUIRED:
        return ""
    if any(a.day == day and a.doctor_id == doctor_id and a.activity != activity
           and a.activity in AVAILABILITY_REQUIRED
           and (activity in guards or a.activity in guards)
           and not activities_conflict(activity, a.activity) for a in assignments):
        return "warning_guard_combination"
    return ""


def rest_periods(assignments):
    full_days = {(a.day, a.doctor_id) for a in effective_assignments(assignments) if a.activity == Activity.NIGHT_OFF}
    mornings = {(a.day + timedelta(days=1), a.doctor_id) for a in assignments if a.activity == Activity.ON_CALL_NIGHT}
    return full_days, mornings


def rest_warning(day, doctor_id, activity, periods, paid=False):
    full_days, mornings = periods
    if (day, doctor_id) in full_days and activity not in ABSENCES | {Activity.NIGHT_OFF}:
        return "warning_night_off_exception" if night_off_exception(activity, paid) else "error_night_off_unavailable"
    if (day, doctor_id) in mornings and activity in MORNING_WORK:
        return "warning_after_on_call_night"
    return ""


def issues_for_week(start: date, assignments: list[Assignment]) -> list[Issue]:
    issues: set[Issue] = set()
    periods = rest_periods(assignments)
    for a in assignments:
        warning = rest_warning(a.day, a.doctor_id, a.activity, periods, a.paid) or guard_warning(a.day, a.doctor_id, a.activity, assignments)
        if start <= a.day <= start + timedelta(days=6) and warning:
            issues.add(Issue(warning, a.doctor_id, a.day, "error" if warning == "error_night_off_unavailable" else "warning", activity=a.activity))
        if not start <= a.day <= start + timedelta(days=6) or a.activity not in AVAILABILITY_REQUIRED:
            continue
        day_error = activity_day_error(a.day, a.activity)
        if day_error:
            issues.add(Issue(day_error, a.doctor_id, a.day, "error", activity=a.activity))
        same = [b for b in assignments if b.day == a.day and b.doctor_id == a.doctor_id]
        if any(b.activity in ABSENCES for b in same):
            issues.add(Issue("error_unavailable", a.doctor_id, a.day, "error", activity=a.activity))
        if any(activities_conflict(a.activity, b.activity) for b in same):
            issues.add(Issue("error_time_conflict", a.doctor_id, a.day, "error", activity=a.activity))
        if a.activity in SINGLE_DOCTOR_ACTIVITIES and any(
            b.day == a.day and b.activity == a.activity and b.id != a.id for b in assignments
        ):
            issues.add(Issue("error_single_doctor", a.doctor_id, a.day, "error", activity=a.activity))
    return sorted(issues, key=lambda i: (i.day, i.doctor_id, i.key, i.activity or ""))
