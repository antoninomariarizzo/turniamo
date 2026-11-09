"""Shared compact timetable geometry for the HTML UI and exports."""
from .domain import Activity as A, ACTIVITY_INTERVALS

# Each column has vertically stacked slots, rather than extra activity columns.
COLUMNS = (
    ("surgery_urgent", (A.SURGERY_URGENT,)),
    ("surgery_2", (A.SURGERY_2,)),
    ("surgery_3", (A.SURGERY_3,)),
    ("ward", (A.WARD,)),
    ("week_service", (A.WEEK_SERVICE,)),
    ("duty_group", (A.DAY_DUTY, A.NIGHT_DUTY)),
    ("on_call_group", (A.ON_CALL_AM, A.ON_CALL_PM, A.ON_CALL_NIGHT)),
    ("clinic_group", (A.CLINIC_AM, A.CLINIC_PM)),
    ("multidisciplinary", (A.MULTIDISCIPLINARY,)),
    ("night_off", (A.NIGHT_OFF,)),
    ("absence", (A.ABSENCE,)),
    ("holiday", (A.HOLIDAY,)),
    ("recovery", (A.RECOVERY,)),
)

SUBLABELS = {
    A.DAY_DUTY: "day_shift", A.NIGHT_DUTY: "night_shift",
    A.ON_CALL_AM: "morning", A.ON_CALL_PM: "afternoon",
    A.CLINIC_AM: "morning", A.CLINIC_PM: "afternoon",
}

def clock_label(minutes):
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


TIMES = {activity: f"{clock_label(start)} - {clock_label(end)}"
         for activity, (start, end) in ACTIVITY_INTERVALS.items()}
