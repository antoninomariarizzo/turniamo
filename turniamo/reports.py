"""Calendar-based assignment counts; independent from credited hours."""
from datetime import date, timedelta
from .domain import Activity as A, WORK, effective_assignments

MONTH_COLUMNS = ('surgery_urgent', 'surgery_2', 'surgery_3', 'day_duty', 'night_duty',
                 'on_call_group', 'clinic_group', 'saturday_day', 'saturday_night',
                 'sunday_day', 'sunday_night')


ANNUAL_COLUMNS = ('festive', 'special', 'paid_clinic', 'paid_nights', 'recovery_total')

def easter(year):
    """Gregorian Easter, Meeus/Jones/Butcher algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    month, day = divmod(h + l - 7*m + 114, 31)
    return date(year, month, day + 1)


def holiday_dates(year):
    regular = {date(year, m, d) for m, d in [(4,25),(5,1),(6,2),(10,4),(11,1),(12,8),(12,26)]}
    special = {date(year, m, d) for m, d in [(1,1),(1,6),(8,15),(12,25)]}
    special |= {easter(year), easter(year) + timedelta(days=1)}
    # A date that overlaps categories counts only once, in the special group.
    return regular - special, special


def holiday_catalog(year):
    regular, special = holiday_dates(year)
    names = {(4,25): 'liberation_day', (5,1): 'labour_day', (6,2): 'republic_day',
             (10,4): 'saint_francis', (11,1): 'all_saints', (12,8): 'immaculate_conception',
             (12,26): 'saint_stephen', (1,1): 'new_year', (1,6): 'epiphany',
             (8,15): 'assumption', (12,25): 'christmas'}
    def name(day):
        if day == easter(year): return 'easter'
        if day == easter(year) + timedelta(days=1): return 'easter_monday'
        return names[(day.month, day.day)]
    return {key: [{'date': day.isoformat(), 'holiday': name(day)} for day in sorted(days)]
            for key, days in [('festive', regular), ('special', special)]}


def period_reports(month, assignments, doctors):
    regular, special = holiday_dates(month.year)
    monthly = {d.id: {key: [] for key in MONTH_COLUMNS} for d in doctors}
    catalog = holiday_catalog(month.year)
    names = {item['date']: item['holiday'] for items in catalog.values() for item in items}
    annual = {d.id: {'paid_clinic': [], 'paid_nights': [], 'recovery_total': []} for d in doctors}
    festive = {d.id: {'festive': {}, 'special': {}} for d in doctors}
    for a in effective_assignments(assignments):
        if a.doctor_id not in monthly:
            continue
        if a.day.year == month.year and a.paid:
            category = 'paid_clinic' if a.activity in (A.CLINIC_AM, A.CLINIC_PM) else 'paid_nights' if a.activity == A.NIGHT_DUTY else None
            if category:
                annual[a.doctor_id][category].append({'date': a.day.isoformat(), 'holiday': '', 'assignments': [{'activity': a.activity.value, 'paid': True}]})
        if a.day.year == month.year and a.activity == A.RECOVERY:
            annual[a.doctor_id]['recovery_total'].append({'date': a.day.isoformat(), 'holiday': '', 'assignments': [{'activity': a.activity.value, 'paid': a.paid}]})
        if a.day.year == month.year and a.activity in WORK | {A.NIGHT_OFF}:
            group = 'special' if a.day in special else 'festive' if a.day in regular else None
            if group:
                festive[a.doctor_id][group].setdefault(a.day, []).append({'activity': a.activity.value, 'paid': a.paid})
        if (a.day.year, a.day.month) != (month.year, month.month):
            continue
        category = None
        if a.activity in (A.SURGERY_URGENT, A.SURGERY_2, A.SURGERY_3):
            category = a.activity.value
        elif a.day.weekday() < 5:
            if a.activity in (A.DAY_DUTY, A.NIGHT_DUTY):
                category = a.activity.value
            elif a.activity in (A.ON_CALL_AM, A.ON_CALL_PM):
                category = 'on_call_group'
            elif a.activity in (A.CLINIC_AM, A.CLINIC_PM):
                category = 'clinic_group'
        elif a.activity in (A.DAY_DUTY, A.NIGHT_DUTY):
            category = ('saturday_' if a.day.weekday() == 5 else 'sunday_') + ('day' if a.activity == A.DAY_DUTY else 'night')
        if category:
            monthly[a.doctor_id][category].append({'date': a.day.isoformat(), 'assignments': [{'activity': a.activity.value, 'paid': a.paid}]})
    return {'month': month.strftime('%Y-%m'), 'year': month.year, 'columns': MONTH_COLUMNS, 'annual_columns': ANNUAL_COLUMNS, 'holiday_catalog': catalog,
            'monthly': [{'id': d.id, 'name': d.name, 'counts': {key: len(entries) for key, entries in monthly[d.id].items()}, 'details': monthly[d.id]} for d in doctors],
            'festivities': [{'id': d.id, 'name': d.name, 'counts': {k: len(v) for k,v in (festive[d.id] | annual[d.id]).items()},
                             'details': {k: [{'date': day.isoformat(), 'holiday': names[day.isoformat()], 'assignments': entries}
                                             for day, entries in sorted(v.items())] for k,v in festive[d.id].items()} | annual[d.id]} for d in doctors]}
