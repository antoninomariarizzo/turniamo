"""Shared compact timetable geometry for the HTML UI and exports."""
from .domain import Activity as A

# Each column has vertically stacked slots, rather than extra activity columns.
COLUMNS = (
    ("surgery_urgent", (A.SURGERY_URGENT,)),
    ("surgery_2", (A.SURGERY_2,)),
    ("surgery_3", (A.SURGERY_3,)),
    ("ward", (A.WARD, A.WARD_HELP)),
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

TIMES = {
    A.SURGERY_URGENT: "07:45 - 15:00", A.SURGERY_2: "07:45 - 15:00",
    A.SURGERY_3: "07:45 - 15:00",
    A.WARD: "07:45 - 17:00", A.WEEK_SERVICE: "07:45 - 14:00",
    A.DAY_DUTY: "07:45 - 20:30", A.NIGHT_DUTY: "19:45 - 08:30",
    A.ON_CALL_AM: "07:45 - 14:00", A.ON_CALL_PM: "14:00 - 18:00",
    A.ON_CALL_NIGHT: "20:00 - 08:00",
    A.CLINIC_AM: "07:45 - 13:30", A.CLINIC_PM: "15:00 - 19:00",
}
