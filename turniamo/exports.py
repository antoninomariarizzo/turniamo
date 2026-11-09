"""Compact localized timetable and three-column summary exports."""
from datetime import timedelta
from pathlib import Path
import json

from .domain import activity_day_error, hidden_activities, Activity, issues_for_week, minutes_for
from .i18n import day_label, tr, week_label
from .layout import COLUMNS, TIMES
from .presentation import presentation_data
from .reports import ANNUAL_COLUMNS, period_reports


def visible_doctors(doctors, assignments, start):
    return doctors


def assignment_text(a, names, language, show_auto=False):
    text = names[a.doctor_id] + (" *" if a.paid else "")
    if a.associate_role:
        text += f"\n{tr(a.associate_role, language)}: {a.associate_name}"
    if show_auto and a.source_id:
        text += "\n" + tr("automatic", language)
    return text


def slot_text(day, activities, assignments, names, language):
    entries = [a for a in assignments if a.day == day and a.activity in activities and a.doctor_id in names]
    entries.sort(key=lambda a: names[a.doctor_id].casefold())
    return "\n\n".join(assignment_text(a, names, language) for a in entries)


def export_cells(start, assignments, doctors, language):
    """Physical cell coordinates shared by PDF and Excel; six physical rows per day for halves and thirds."""
    names = {d.id: d.name for d in doctors}
    flagged = issues_for_week(start, assignments)
    cells = []
    for n in range(7):
        day, row = start + timedelta(days=n), n * 6
        cells.append((row, 0, day_label(day, language), 6, False))
        for col, (key, activities) in enumerate(COLUMNS, start=1):
            activities = tuple(a for a in activities if a not in hidden_activities(day))
            slots = len(activities) if key in ("duty_group", "on_call_group", "clinic_group") else 1
            span = 6 // slots
            for half in range(slots):
                selected = (activities[half],) if slots > 1 else activities
                text = slot_text(day, selected, assignments, names, language)
                if selected[0] in TIMES:
                    text = TIMES[selected[0]] + ("\n" + text if text else "")
                warning = any(any(i.day == a.day and i.doctor_id == a.doctor_id and (i.activity is None or i.activity == a.activity) for i in flagged) for a in assignments if a.day == day and a.activity in selected)
                cells.append((row+half*span, col, text, span, warning))
    return sorted(cells)


def document_html(start, assignments, doctors, language, reports=None):
    web = Path(__file__).parent / "web"
    # Inline local assets so the export has exactly the same renderer/styles as
    # the desktop UI. Escape script delimiters in user-provided names and notes.
    state = presentation_data(start, assignments, doctors, language)
    state["reports"] = reports if reports is not None else period_reports(start.replace(day=1), assignments, doctors)
    data = json.dumps(state).replace("<", "\\u003c")
    html = "\n".join(line for line in (web / "index.html").read_text(encoding="utf-8").splitlines()
                     if not any(marker in line for marker in ('<script ', '<link ', 'Content-Security-Policy')))
    html = html.replace("</head>", "<style>" + (web / "style.css").read_text(encoding="utf-8") + "</style></head>")
    script = "<script>window.turniamoPrintState=" + data + ";\n" + (web / "app.js").read_text(encoding="utf-8") + "</script>"
    return html.replace("</body>", script + "</body>")


def make_printer():
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageLayout, QPageSize
    from PySide6.QtPrintSupport import QPrinter
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A3))
    printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
    printer.setDocName("turniamo")
    return printer


def print_document(printer, html):
    from PySide6.QtGui import QFont, QTextDocument
    document = QTextDocument()
    document.setDefaultFont(QFont("Arial", 8))
    document.setHtml(html)
    document.print_(printer)


def export_pdf(path, html):
    from PySide6.QtCore import QEventLoop, QTimer, QMarginsF
    from PySide6.QtGui import QPageLayout, QPageSize
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    page = QWebEnginePage()
    page.settings().setAttribute(QWebEngineSettings.WebAttribute.PrintElementBackgrounds, True)
    loop, timer, result = QEventLoop(), QTimer(), []
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A3), QPageLayout.Orientation.Landscape,
                         QMarginsF(10, 10, 10, 10))
    def received(data):
        result.append(bytes(data))
        loop.quit()
    def ready(value):
        if value:
            page.printToPdf(received, layout)
        elif timer.isActive():
            QTimer.singleShot(50, check)
    def check():
        if timer.isActive():
            page.runJavaScript("window.turniamoPrintReady === true", ready)
    page.loadFinished.connect(lambda ok: check() if ok else loop.quit())
    timer.start(20000)
    page.setHtml(html)
    loop.exec()
    timer.stop()
    page.deleteLater()
    if not result or not result[0].startswith(b"%PDF"):
        raise OSError("PDF rendering failed or timed out")
    Path(path).write_bytes(result[0])


def export_excel(path, start, assignments, doctors, language, reports=None):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.workbook.properties import CalcProperties
    from openpyxl.formatting.rule import FormulaRule
    t = lambda key: tr(key, language)
    workbook = Workbook()
    workbook.calculation = CalcProperties(calcId=0, fullCalcOnLoad=True)
    schedule = workbook.active
    schedule.title = t("schedule")
    summary = workbook.create_sheet(t("summary"))
    reports = reports if reports is not None else period_reports(start.replace(day=1), assignments, doctors)
    monthly = workbook.create_sheet(t("monthly"))
    annual = workbook.create_sheet(t("festivities"))
    detail = workbook.create_sheet(t("assignment"))
    detail.sheet_state = "hidden"
    names = {d.id: d.name for d in doctors}
    count = len(COLUMNS) + 1
    schedule.append(["turniamo · " + week_label(start)])
    schedule.merge_cells(start_row=1, start_column=1, end_row=1, end_column=count)
    schedule.append([t("day")] + [t(k) for k, _ in COLUMNS])
    for row, col, text, span, warning in export_cells(start, assignments, doctors, language):
        cell = schedule.cell(row+3, col+1, text)
        if col and all(activity_day_error(start + timedelta(days=row // 6), a) for a in COLUMNS[col-1][1]):
            cell.fill = PatternFill("solid", fgColor="EEF0F3")
        if warning:
            cell.fill = PatternFill("solid", fgColor="FFF0D7")
        if span > 1:
            schedule.merge_cells(start_row=row+3, start_column=col+1, end_row=row+2+span, end_column=col+1)
        height = max(12, ((text.count("\n") + 1) * 14 + 10) / span)
        for offset in range(span):
            schedule.row_dimensions[row+3+offset].height = max(schedule.row_dimensions[row+3+offset].height or 12, height)
    schedule.freeze_panes = "B3"
    schedule.print_title_rows = "1:2"
    schedule.print_area = f"A1:{get_column_letter(count)}44"
    for col in range(1, count+1):
        schedule.column_dimensions[get_column_letter(col)].width = 13 if col == 1 else 23
    detail.append([t(k) for k in ("date", "doctor", "activity", "paid", "associate", "associate_name", "minutes")]+["doctor_id", "category"])
    for a in assignments:
        if start <= a.day <= start + timedelta(days=6) and a.doctor_id in names:
            category = "paid" if a.paid else "holidays" if a.activity == Activity.HOLIDAY else "recovery" if a.activity == Activity.RECOVERY else "ordinary"
            detail.append([a.day, names[a.doctor_id], t(a.activity.value), t("yes" if a.paid else "no"),
                           t(a.associate_role) if a.associate_role else "", a.associate_name,
                           minutes_for(a, assignments), a.doctor_id, category])
    for row in detail.iter_rows(min_row=2):
        row[0].number_format = "dd/mm/yyyy"
    summary.append([t("summary") + " · " + week_label(start)]); summary.merge_cells("A1:D1")
    summary.append([t("decimal_hours")]); summary.merge_cells("A2:D2")
    summary.row_dimensions[2].height = 35
    summary.append([t("ordinary_tooltip")]); summary.merge_cells("A3:D3")
    summary.row_dimensions[3].height = 35
    summary.append([t(k) for k in ("doctor", "ordinary", "paid_hours", "status")])
    ref = "'" + detail.title.replace("'", "''") + "'"
    last = max(2, detail.max_row)
    for row, d in enumerate(doctors, start=5):
        summary.cell(row, 1, d.name)
        def sum_category(category):
            return f'SUMIFS({ref}!$G$2:$G${last},{ref}!$H$2:$H${last},"{d.id}",{ref}!$I$2:$I${last},"{category}")'
        summary.cell(row, 2, f'={sum_category("<>paid")}/60')
        summary.cell(row, 3, f'={sum_category("paid")}/60')
        threshold = f'({sum_category("ordinary")}+{sum_category("holidays")})'
        summary.cell(row, 4, f'=IF({threshold}>2400,"{t("above")}","{t("normal")}")')
        for col in (2, 3):
            summary.cell(row, col).number_format = '0.00" h";[Red]-0.00" h"'
    if summary.max_row >= 5:
        for status, color in (("above", "FFF0D7"),):
            summary.conditional_formatting.add(f"D5:D{summary.max_row}", FormulaRule(
                formula=[f'D5="{t(status)}"'], fill=PatternFill("solid", fgColor=color)))
    summary.freeze_panes = "B5"
    summary.print_title_rows = "1:4"
    for sheet, label, rows, columns, period in (
        (monthly, 'monthly', reports['monthly'], reports['columns'], reports['month']),
        (annual, 'festivities', reports['festivities'], ANNUAL_COLUMNS, str(reports['year']))):
        sheet.append([t(label) + ' · ' + period])
        sheet.merge_cells(start_row=1,start_column=1,end_row=1,end_column=len(columns)+1)
        sheet.append([t('report_person')] + [t(key) for key in columns])
        for entry in rows:
            sheet.append([entry['name']] + [entry['counts'][key] for key in columns])
        sheet.freeze_panes='B3'
        sheet.print_title_rows='1:2'
    for sheet, header in ((schedule, 2), (summary, 4), (monthly,2), (annual,2), (detail, 1)):
        sheet.sheet_view.showGridLines = False
        sheet.sheet_properties.pageSetUpPr.fitToPage = True
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A3 if sheet == schedule else sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth, sheet.page_setup.fitToHeight = 1, 0
        for cells in sheet:
            for cell in cells:
                cell.font = Font(name="Arial", size=11, color="25364A")
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.border = Border(bottom=Side(style="hair", color="E0E6ED"))
                if isinstance(cell.value, str) and cell.value.startswith("=") and not (sheet == summary and cell.row >= 5 and cell.column > 1):
                    cell.data_type = "s"
        for cell in sheet[header]:
            cell.fill = PatternFill("solid", fgColor="EEF3F7")
            cell.font = Font(name="Arial", size=11, bold=True, color="25364A")
        sheet.row_dimensions[header].height = 32
        if sheet != schedule:
            for col in range(1, sheet.max_column+1):
                sheet.column_dimensions[get_column_letter(col)].width = 30
        if sheet != detail:
            sheet["A1"].font = Font(name="Arial", size=16, bold=True, color="176B72")
            sheet.row_dimensions[1].height = 30
    workbook.save(path)
