"""One presentation model for the live HTML interface and its PDF export."""
from dataclasses import asdict
from datetime import timedelta
from .domain import duration, issues_for_week, minutes_for, totals_for_week
from .i18n import TEXT, day_label, tr, week_label
from .layout import COLUMNS, TIMES


def presentation_data(start, context, doctors, language):
    assignments = [a for a in context if start <= a.day <= start + timedelta(days=6)]
    totals = totals_for_week(start, context, doctors)
    return {
        "start": start.isoformat(), "weekLabel": week_label(start), "language": language,
        "days": [{"date": (start + timedelta(days=n)).isoformat(), "label": day_label(start + timedelta(days=n), language), "weekday": n} for n in range(7)],
        "columns": [{"key": key, "activities": [a.value for a in activities]} for key, activities in COLUMNS],
        "sublabels": {a.value: value for a, value in TIMES.items()},
        "doctors": [asdict(d) for d in doctors],
        "assignments": [{**asdict(a), "day": a.day.isoformat(), "minutes": minutes_for(a, context)} for a in assignments],
        "totals": {d.id: {"ordinary": duration(totals[d.id].net), "paid": duration(totals[d.id].paid),
                          "status": "above" if totals[d.id].status == "above" else "normal"} for d in doctors},
        "issues": [{**asdict(i), "day": i.day.isoformat()} for i in issues_for_week(start, context)],
        "text": {key: tr(key, language) for key in TEXT if "{" not in TEXT[key][0]},
    }
