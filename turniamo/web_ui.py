"""Local HTML desktop UI. No server, network requests, or third-party assets."""
from __future__ import annotations

from contextlib import closing
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4

from PySide6.QtCore import QObject, QUrl, Signal, Slot, QStandardPaths, QTimer
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from .domain import (Activity, Assignment, RuleError, duration, issues_for_week,
                     minutes_for, monday, totals_for_week, validate_assignment)
from .exports import document_html, export_excel, export_pdf
from .i18n import TEXT, day_label, tr, week_label
from .layout import COLUMNS, SUBLABELS, TIMES
from .storage import Store
from .presentation import presentation_data


def default_export_path(filename):
    for location in (QStandardPaths.StandardLocation.DownloadLocation,
                     QStandardPaths.StandardLocation.DesktopLocation,
                     QStandardPaths.StandardLocation.HomeLocation):
        folder = QStandardPaths.writableLocation(location)
        if folder and Path(folder).is_dir():
            return str(Path(folder) / filename)
    return str(Path.home() / filename)


def backup_before_migration(path: Path):
    if not path.exists():
        return
    with closing(sqlite3.connect(path)) as source:
        version = source.execute("PRAGMA user_version").fetchone()[0]
        if version < 2:
            folder = path.parent / "backups"
            folder.mkdir(exist_ok=True)
            with closing(sqlite3.connect(folder / f"before-html-update-{datetime.now():%Y%m%d-%H%M%S}.sqlite3")) as target:
                source.backup(target)


def import_database(store: Store, source_path: str):
    """Validate a private copy, back up the live DB, then replace via SQLite backup."""
    if Path(source_path).resolve() == Path(store.path).resolve():
        raise RuleError("error_backup_path")
    with tempfile.TemporaryDirectory(prefix="turniamo-import-") as folder:
        candidate = Path(folder) / "candidate.sqlite3"
        try:
            with closing(sqlite3.connect(Path(source_path).resolve().as_uri() + "?mode=ro", uri=True)) as source:
                if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("integrity")
                version = source.execute("PRAGMA user_version").fetchone()[0]
                if version not in (1, 2):
                    raise ValueError("version")
                if source.execute("SELECT count(*) FROM sqlite_master WHERE type IN ('trigger','view')").fetchone()[0]:
                    raise ValueError("unexpected schema")
                for table, columns in {
                    "doctors": {"id", "name", "name_key", "active"}, "weeks": {"start"},
                    "assignments": {"id", "day", "activity", "doctor_id", "paid", "associate_role", "associate_name"},
                    "settings": {"key", "value"},
                }.items():
                    if {r[1] for r in source.execute(f"PRAGMA table_info({table})")} != columns:
                        raise ValueError("schema")
                if version == 2 and {r[1] for r in source.execute("PRAGMA table_info(week_doctors)")} != {"week_start", "doctor_id", "name"}:
                    raise ValueError("roster")
                with closing(sqlite3.connect(candidate)) as target:
                    source.backup(target)
            incoming = Store(candidate)
            try:
                if incoming.db.execute("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("foreign keys")
                for d in incoming.doctors():
                    if not d.name.strip() or len(d.name) > 80:
                        raise ValueError("name")
                for start in incoming.weeks():
                    if start != monday(start):
                        raise ValueError("week")
                for a in incoming.raw_assignments():
                    if a.associate_role not in ("", "training", "reference"):
                        raise ValueError("role")
                    if a.activity == Activity.SURGERY_3:
                        raise ValueError("obsolete activity")
                    if a.doctor_id not in {d.id for d in incoming.week_doctors(monday(a.day))}:
                        raise ValueError("assignment without weekly membership")
                for row in incoming.db.execute("SELECT week_start,doctor_id,name FROM week_doctors"):
                    if not row[2].strip() or len(row[2]) > 80:
                        raise ValueError("roster name")
                folder = Path(store.path).parent / "backups"
                folder.mkdir(parents=True, exist_ok=True)
                store.backup(str(folder / f"before-import-{datetime.now():%Y%m%d-%H%M%S-%f}.sqlite3"))
                incoming.db.backup(store.db)
            finally:
                incoming.close()
        except (sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            raise RuleError("invalid_database") from exc


class Bridge(QObject):
    updated = Signal(str)
    exportFinished = Signal(str)

    def __init__(self, store: Store, window=None):
        super().__init__(window)
        self.store, self.window = store, window
        self.language = store.setting("language", "it")
        if self.language not in ("it", "en"):
            self.language = "it"
        try:
            saved = date.fromisoformat(store.setting("last_week", ""))
        except ValueError:
            saved = date.today()
        self.start = store.create_week(saved)

    def t(self, key, **kwargs):
        return tr(key, self.language, **kwargs)

    def state(self):
        data = presentation_data(self.start, self.store.week_context(self.start), self.store.week_doctors(self.start), self.language)
        data["weeks"] = [{"start": s.isoformat(), "label": week_label(s)} for s in self.store.weeks()]
        return data

    def publish(self):
        self.updated.emit(json.dumps(self.state(), ensure_ascii=False))

    @Slot(str, str, result=str)
    def request(self, command, payload):
        try:
            args = json.loads(payload or "{}")
            if command == "export":
                # Leave the WebChannel callback before loading/printing another
                # Chromium page: nested rendering here blocks Chromium IPC.
                QTimer.singleShot(0, lambda: self.finish_export(args))
                return json.dumps({"ok": True, "result": None})
            result = self.dispatch(command, args)
            if command not in ("state", "choices"):
                self.publish()
            return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
        except RuleError as exc:
            return json.dumps({"ok": False, "error": self.t(exc.key)}, ensure_ascii=False)
        except (ValueError, KeyError, TypeError, sqlite3.Error, OSError) as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

    def selected_day(self, value):
        day = date.fromisoformat(value)
        if not self.start <= day <= self.start + timedelta(days=6):
            raise ValueError("Day outside selected week")
        return day

    def find_assignment(self, assignment_id):
        for a in self.store.week_context(self.start):
            if a.id == assignment_id and self.start <= a.day <= self.start + timedelta(days=6):
                return a
        raise ValueError("Assignment no longer exists")

    def slot_entries(self, day, activity):
        activities = (Activity.WARD, Activity.WARD_HELP) if activity == Activity.WARD else (activity,)
        return [a for a in self.store.week_context(self.start) if a.day == day and a.activity in activities]

    def chosen_activity(self, day, activity):
        if activity == Activity.SURGERY_3:
            raise ValueError("Removed activity")
        if activity == Activity.WARD and any(a.activity == Activity.WARD for a in self.slot_entries(day, activity)):
            return Activity.WARD_HELP
        return activity

    def choices(self, day, activity):
        existing = {a.doctor_id: a for a in self.slot_entries(day, activity)}
        raw = self.store.raw_assignments(day - timedelta(days=1), day + timedelta(days=1))
        result = []
        for doctor in self.store.week_doctors(self.start):
            entry = existing.get(doctor.id)
            error = self.t("error_derived") if entry and entry.source_id else ""
            if not entry:
                try:
                    validate_assignment(Assignment(str(uuid4()), day, self.chosen_activity(day, activity), doctor.id), raw)
                except RuleError as exc:
                    error = self.t(exc.key)
            result.append({"id": doctor.id, "name": doctor.name, "selected": bool(entry),
                           "assignment": entry.id if entry else None, "disabled": bool(error), "reason": error})
        return result

    def dispatch(self, command, args):
        if command == "state":
            return self.state()
        if command == "week":
            self.start = self.store.create_week(date.fromisoformat(args["date"]))
            self.store.set_setting("last_week", self.start.isoformat())
        elif command == "language":
            if args["language"] not in ("it", "en"):
                raise ValueError("Invalid language")
            self.language = args["language"]
            self.store.set_setting("language", self.language)
        elif command == "save_doctor":
            return self.store.save_week_doctor(self.start, args["name"], args.get("id"))
        elif command == "remove_doctor":
            self.store.remove_week_doctor(self.start, args["id"])
        elif command == "choices":
            return self.choices(self.selected_day(args["day"]), Activity(args["activity"]))
        elif command == "set_slot_doctors":
            self.store.set_slot_doctors(self.selected_day(args["day"]), Activity(args["activity"]), args["doctors"])
        elif command == "toggle":
            day, activity = self.selected_day(args["day"]), Activity(args["activity"])
            current = next((a for a in self.slot_entries(day, activity) if a.doctor_id == args["doctor"]), None)
            if current:
                self.store.delete_assignment(current.id)
                self.promote_ward(day)
            else:
                self.store.save_assignment(Assignment(str(uuid4()), day, self.chosen_activity(day, activity), args["doctor"]))
        elif command == "update_assignment":
            a = self.find_assignment(args["id"])
            self.store.save_assignment(replace(a, paid=bool(args["paid"]), associate_role=args["role"], associate_name=args["name"].strip()))
        elif command == "delete_assignment":
            a = self.find_assignment(args["id"])
            self.store.delete_assignment(a.id)
            self.promote_ward(a.day)
        elif command == "export":
            self.export(args["kind"])
        elif command == "export_database":
            path, _ = QFileDialog.getSaveFileName(self.window, self.t(command), default_export_path(f"turniamo-{date.today()}.sqlite3"), "SQLite (*.sqlite3)")
            if path:
                self.store.backup(path)
        elif command == "import_database":
            path, _ = QFileDialog.getOpenFileName(self.window, self.t(command), "", "SQLite (*.sqlite3 *.db)")
            if path:
                message = QMessageBox(self.window)
                message.setWindowTitle(self.t(command))
                message.setText(self.t("import_confirm"))
                accept = message.addButton(self.t(command), QMessageBox.ButtonRole.AcceptRole)
                message.addButton(self.t("cancel"), QMessageBox.ButtonRole.RejectRole)
                message.exec()
                if message.clickedButton() == accept:
                    import_database(self.store, path)
                    self.start = self.store.weeks()[0] if self.store.weeks() else self.store.create_week(date.today())
                    self.language = self.store.setting("language", "it")
                    if self.language not in ("it", "en"):
                        self.language = "it"
        else:
            raise ValueError("Unknown command")

    def promote_ward(self, day):
        entries = self.slot_entries(day, Activity.WARD)
        if entries and not any(a.activity == Activity.WARD for a in entries):
            self.store.save_assignment(replace(entries[0], activity=Activity.WARD))

    def finish_export(self, args):
        try:
            path = self.export(args["kind"])
            response = {"ok": True, "path": path,
                        "message": self.t("export_done", path=path) if path else ""}
        except (ValueError, KeyError, TypeError, OSError) as exc:
            response = {"ok": False, "message": str(exc)}
        self.exportFinished.emit(json.dumps(response, ensure_ascii=False))

    def export(self, kind):
        if kind not in ("pdf", "xlsx"):
            raise ValueError("Invalid format")
        path, _ = QFileDialog.getSaveFileName(self.window, self.t("export"), default_export_path(f"turniamo-{self.start}.{kind}"), f"{kind.upper()} (*.{kind})")
        if not path:
            return
        if not path.lower().endswith("." + kind):
            path += "." + kind
        assignments, doctors = self.store.week_context(self.start), self.store.week_doctors(self.start)
        if kind == "xlsx":
            export_excel(path, self.start, assignments, doctors, self.language)
        else:
            export_pdf(path, document_html(self.start, assignments, doctors, self.language))
        return path


class LocalPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        return url.scheme() in ("file", "qrc", "about")


class MainWindow(QMainWindow):
    def __init__(self, store: Store):
        super().__init__()
        self.setWindowTitle("turniamo")
        self.resize(1440, 880)
        self.setMinimumSize(960, 600)
        self.view = QWebEngineView(self)
        self.view.setPage(LocalPage(self.view))
        self.view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        self.bridge = Bridge(store, self)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject("turniamo", self.bridge)
        self.view.page().setWebChannel(self.channel)
        self.setCentralWidget(self.view)
        self.view.load(QUrl.fromLocalFile(str(Path(__file__).parent / "web" / "index.html")))
