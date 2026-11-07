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


ACTIVITIES = tuple(Activity)
SURGERIES = frozenset((Activity.SURGERY_URGENT, Activity.SURGERY_2, Activity.SURGERY_3))
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


def validate_assignment(proposal: Assignment, raw: list[Assignment]) -> None:
    if proposal.activity == Activity.ON_CALL_AM and proposal.day.weekday() != 5:
        raise RuleError("error_saturday_only")
    if proposal.paid and proposal.activity in ABSENCES | {Activity.MULTIDISCIPLINARY, Activity.ON_CALL_NIGHT}:
        raise RuleError("error_paid_absence")
    if proposal.associate_role not in ("", "training", "reference"):
        raise RuleError("error_associate")
    if bool(proposal.associate_role) != bool(proposal.associate_name.strip()):
        raise RuleError("error_associate")
    others = [a for a in effective_assignments(raw) if a.id != proposal.id]
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
    # Night-off counts a previous night's work. Leave on that calendar day does
    # not introduce a new work assignment and is therefore allowed.
    if proposal.activity in ABSENCES:
        if any(a.activity in AVAILABILITY_REQUIRED | ABSENCES for a in same):
            raise RuleError("error_unavailable")
    elif proposal.activity in AVAILABILITY_REQUIRED and any(a.activity in ABSENCES for a in same):
        raise RuleError("error_unavailable")


MORNING_WORK = SURGERIES | {Activity.WARD, Activity.WEEK_SERVICE, Activity.DAY_DUTY, Activity.ON_CALL_AM, Activity.CLINIC_AM}


# Scheduling bands are explicit product rules, not parsed display labels.
# In particular surgery + a PM clinic/on-call remains a valid combination.
AFTERNOON_WORK = frozenset((Activity.WARD, Activity.DAY_DUTY, Activity.ON_CALL_PM, Activity.CLINIC_PM))
NIGHT_WORK = frozenset((Activity.NIGHT_DUTY, Activity.ON_CALL_NIGHT))


def activities_conflict(first: Activity, second: Activity) -> bool:
    if first == second:
        return False  # Duplicate assignments have a dedicated validation error.
    return any(first in band and second in band for band in (MORNING_WORK, AFTERNOON_WORK, NIGHT_WORK)) or {
        first, second
    } == {Activity.DAY_DUTY, Activity.NIGHT_DUTY}


def rest_periods(assignments):
    full_days = {(a.day, a.doctor_id) for a in effective_assignments(assignments) if a.activity == Activity.NIGHT_OFF}
    mornings = {(a.day + timedelta(days=1), a.doctor_id) for a in assignments if a.activity == Activity.ON_CALL_NIGHT}
    return full_days, mornings


def rest_warning(day, doctor_id, activity, periods):
    full_days, mornings = periods
    if (day, doctor_id) in full_days and activity not in ABSENCES | {Activity.NIGHT_OFF}:
        return "warning_after_night_off"
    if (day, doctor_id) in mornings and activity in MORNING_WORK:
        return "warning_after_on_call_night"
    return ""


def issues_for_week(start: date, assignments: list[Assignment]) -> list[Issue]:
    issues: set[Issue] = set()
    periods = rest_periods(assignments)
    for a in assignments:
        warning = rest_warning(a.day, a.doctor_id, a.activity, periods)
        if start <= a.day <= start + timedelta(days=6) and warning:
            issues.add(Issue(warning, a.doctor_id, a.day, activity=a.activity))
        if not start <= a.day <= start + timedelta(days=6) or a.activity not in AVAILABILITY_REQUIRED:
            continue
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
