"""SQLite persistence. Every edit is atomic and saved immediately."""
from __future__ import annotations

from datetime import date, timedelta
from dataclasses import replace
from pathlib import Path
import sqlite3
from uuid import uuid4

from .domain import (Activity, Assignment, Doctor, RuleError, effective_assignments,
                     monday, normalize_name, validate_assignment)


class Store:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS doctors (
                id TEXT PRIMARY KEY, name TEXT NOT NULL,
                name_key TEXT NOT NULL UNIQUE, active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS weeks (start TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY, day TEXT NOT NULL, activity TEXT NOT NULL,
                doctor_id TEXT NOT NULL REFERENCES doctors(id), paid INTEGER NOT NULL,
                associate_role TEXT NOT NULL DEFAULT '', associate_name TEXT NOT NULL DEFAULT '',
                UNIQUE(day, activity, doctor_id)
            );
            CREATE INDEX IF NOT EXISTS assignments_day ON assignments(day);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        self._migrate()

    def _migrate(self):
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 3:
            raise ValueError("Database created by a newer version of turniamo")
        if version < 2:
            # Removed legacy columns are discarded as requested. The app makes
            # a database backup before opening an older schema.
            with self.db:
                self.db.execute("""CREATE TABLE IF NOT EXISTS week_doctors (
                    week_start TEXT NOT NULL REFERENCES weeks(start),
                    doctor_id TEXT NOT NULL REFERENCES doctors(id), name TEXT NOT NULL,
                    PRIMARY KEY(week_start,doctor_id))""")
                self.db.execute("DELETE FROM assignments WHERE activity = 'ward_help'")
                self.db.execute("""INSERT OR IGNORE INTO week_doctors
                    SELECT w.start,d.id,d.name FROM weeks w CROSS JOIN doctors d
                    WHERE d.active=1 OR EXISTS (SELECT 1 FROM assignments a
                    WHERE a.doctor_id=d.id AND a.day BETWEEN date(w.start,'-1 day') AND date(w.start,'+6 days'))""")
                self.db.execute("PRAGMA user_version=2")
        if version < 3:
            self.db.execute("PRAGMA user_version=3")

    def close(self):
        self.db.close()

    def doctors(self, active_only: bool = False) -> list[Doctor]:
        query = "SELECT id, name, active FROM doctors"
        if active_only:
            query += " WHERE active=1"
        rows = self.db.execute(query).fetchall()
        return sorted((Doctor(r["id"], r["name"], bool(r["active"])) for r in rows),
                      key=lambda d: normalize_name(d.name))

    def save_doctor(self, name: str, doctor_id: str | None = None, active: bool = True) -> str:
        name = " ".join(name.split())
        if not name or len(name) > 80:
            raise RuleError("error_name")
        doctor_id = doctor_id or str(uuid4())
        try:
            with self.db:
                self.db.execute("""INSERT INTO doctors(id,name,name_key,active) VALUES(?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                    name_key=excluded.name_key, active=excluded.active""",
                                (doctor_id, name, normalize_name(name), int(active)))
        except sqlite3.IntegrityError as exc:
            raise RuleError("error_unique_name") from exc
        return doctor_id

    def weeks(self) -> list[date]:
        return [date.fromisoformat(r[0]) for r in self.db.execute("SELECT start FROM weeks ORDER BY start DESC")]

    def create_week(self, day: date) -> date:
        start = monday(day)
        with self.db:
            new = self.db.execute("INSERT OR IGNORE INTO weeks(start) VALUES(?)", (start.isoformat(),)).rowcount
            if new:
                self.db.execute("INSERT INTO week_doctors SELECT ?,id,name FROM doctors WHERE active=1", (start.isoformat(),))
        return start

    def week_doctors(self, start: date) -> list[Doctor]:
        rows = self.db.execute("""SELECT r.doctor_id,r.name,d.active FROM week_doctors r
            JOIN doctors d ON d.id=r.doctor_id WHERE r.week_start=?""", (start.isoformat(),))
        return sorted((Doctor(r[0], r[1], bool(r[2])) for r in rows), key=lambda d: normalize_name(d.name))

    def save_week_doctor(self, start: date, name: str, doctor_id: str | None = None) -> str:
        name = " ".join(name.split())
        if not name or len(name) > 80:
            raise RuleError("error_name")
        if any(normalize_name(d.name) == normalize_name(name) and d.id != doctor_id for d in self.week_doctors(start)):
            raise RuleError("error_unique_name")
        if doctor_id and not any(d.id == doctor_id for d in self.week_doctors(start)):
            raise RuleError("error_doctor")
        adding = doctor_id is None
        if adding:
            previous = self.db.execute("SELECT id FROM doctors WHERE name_key=?", (normalize_name(name),)).fetchone()
            doctor_id = previous[0] if previous else str(uuid4())
        try:
            with self.db:
                self.db.execute("""INSERT INTO doctors VALUES(?,?,?,1)
                    ON CONFLICT(id) DO UPDATE SET name=excluded.name,name_key=excluded.name_key""",
                                (doctor_id, name, normalize_name(name)))
                if adding:
                    self.db.execute("UPDATE doctors SET active=1 WHERE id=?", (doctor_id,))
                if adding:
                    self.db.execute("""INSERT INTO week_doctors SELECT start,?,? FROM weeks WHERE start>=?
                        ON CONFLICT(week_start,doctor_id) DO UPDATE SET name=excluded.name""",
                                    (doctor_id, name, start.isoformat()))
                else:
                    self.db.execute("UPDATE week_doctors SET name=? WHERE doctor_id=? AND week_start>=?",
                                    (name, doctor_id, start.isoformat()))
        except sqlite3.IntegrityError as exc:
            raise RuleError("error_unique_name") from exc
        return doctor_id

    def remove_week_doctor(self, start: date, doctor_id: str):
        if not any(d.id == doctor_id for d in self.week_doctors(start)):
            raise RuleError("error_doctor")
        with self.db:
            self.db.execute("UPDATE doctors SET active=0 WHERE id=?", (doctor_id,))
            self.db.execute("DELETE FROM assignments WHERE doctor_id=? AND day>=?", (doctor_id, start.isoformat()))
            self.db.execute("DELETE FROM week_doctors WHERE doctor_id=? AND week_start>=?", (doctor_id, start.isoformat()))
            for row in self.db.execute("""SELECT day,min(id) FROM assignments WHERE activity='ward_help'
                AND day>=? AND NOT EXISTS (SELECT 1 FROM assignments b WHERE b.day=assignments.day
                AND b.activity='ward') GROUP BY day""", (start.isoformat(),)).fetchall():
                self.db.execute("UPDATE assignments SET activity='ward' WHERE id=?", (row[1],))

    def raw_assignments(self, start: date | None = None, end: date | None = None) -> list[Assignment]:
        query, params = "SELECT * FROM assignments", []
        if start is not None and end is not None:
            query += " WHERE day BETWEEN ? AND ?"
            params = [start.isoformat(), end.isoformat()]
        return [Assignment(r["id"], date.fromisoformat(r["day"]), Activity(r["activity"]),
                           r["doctor_id"], bool(r["paid"]), r["associate_role"], r["associate_name"])
                for r in self.db.execute(query, params)]

    def week_context(self, start: date) -> list[Assignment]:
        # Two previous days are needed for the user's day-A night, day-B S.N.,
        # day-C warning rule, even when A/B belong to the preceding week.
        context = effective_assignments(self.raw_assignments(start - timedelta(days=2), start + timedelta(days=6)))
        roster = {d.id for d in self.week_doctors(start)}
        return [a for a in context if a.day < start or a.doctor_id in roster]

    def save_assignment(self, a: Assignment):
        self.create_week(a.day)
        doctor = self.db.execute("SELECT active FROM doctors WHERE id=?", (a.doctor_id,)).fetchone()
        old = self.db.execute("SELECT doctor_id FROM assignments WHERE id=?", (a.id,)).fetchone()
        roster = {d.id for d in self.week_doctors(monday(a.day))}
        if not doctor or a.doctor_id not in roster:
            raise RuleError("error_doctor")
        if a.source_id or a.id.startswith("night-off:"):
            raise RuleError("error_derived")
        validate_assignment(a, self.raw_assignments(a.day - timedelta(days=1), a.day + timedelta(days=1)))
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO weeks(start) VALUES(?)", (monday(a.day).isoformat(),))
            self.db.execute("""INSERT INTO assignments VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET day=excluded.day, activity=excluded.activity,
                doctor_id=excluded.doctor_id, paid=excluded.paid,
                associate_role=excluded.associate_role, associate_name=excluded.associate_name""",
                            (a.id, a.day.isoformat(), a.activity.value, a.doctor_id, int(a.paid),
                             a.associate_role, a.associate_name.strip()))
            if a.activity == Activity.NIGHT_DUTY:
                # Absorb a manual incoming S.N. once its source night is known.
                self.db.execute("DELETE FROM assignments WHERE day=? AND activity=? AND doctor_id=?",
                                ((a.day + timedelta(days=1)).isoformat(), Activity.NIGHT_OFF.value, a.doctor_id))

    def delete_assignment(self, assignment_id: str):
        if assignment_id.startswith("night-off:"):
            raise RuleError("error_derived")
        with self.db:
            self.db.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))

    def set_slot_doctors(self, day: date, activity: Activity, doctor_ids: list[str]):
        """Validate and save a complete multi-selection in one transaction."""
        if activity == Activity.WARD_HELP:
            raise RuleError("error_doctor")
        if len(doctor_ids) != len(set(doctor_ids)):
            raise RuleError("error_duplicate_assignment")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            roster = {d.id for d in self.week_doctors(monday(day))}
            if not set(doctor_ids) <= roster:
                raise RuleError("error_doctor")
            raw = self.raw_assignments(day - timedelta(days=1), day + timedelta(days=1))
            activities = (Activity.WARD, Activity.WARD_HELP) if activity == Activity.WARD else (activity,)
            current = [a for a in effective_assignments(raw) if a.day == day and a.activity in activities]
            if any(a.source_id and a.doctor_id not in doctor_ids for a in current):
                raise RuleError("error_derived")
            removed = {a.id for a in current if a.doctor_id not in doctor_ids}
            working = [a for a in raw if a.id not in removed]
            retained = [a for a in current if a.doctor_id in doctor_ids]
            changes = []
            if activity == Activity.WARD and retained and not any(a.activity == Activity.WARD for a in retained):
                promoted = replace(retained[0], activity=Activity.WARD)
                working = [promoted if a.id == promoted.id else a for a in working]
                changes.append(promoted)
            for doctor_id in doctor_ids:
                if any(a.doctor_id == doctor_id for a in retained):
                    continue
                kind = activity
                if activity == Activity.WARD and any(a.day == day and a.activity == Activity.WARD for a in working):
                    kind = Activity.WARD_HELP
                a = Assignment(str(uuid4()), day, kind, doctor_id)
                validate_assignment(a, working)
                working.append(a)
                changes.append(a)
            for assignment_id in removed:
                self.db.execute("DELETE FROM assignments WHERE id=?", (assignment_id,))
            for a in changes:
                self.db.execute("""INSERT INTO assignments VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET activity=excluded.activity""",
                    (a.id, a.day.isoformat(), a.activity.value, a.doctor_id, int(a.paid), a.associate_role, a.associate_name))
                if a.activity == Activity.NIGHT_DUTY:
                    self.db.execute("DELETE FROM assignments WHERE day=? AND activity=? AND doctor_id=?",
                                    ((day + timedelta(days=1)).isoformat(), Activity.NIGHT_OFF.value, a.doctor_id))

    def setting(self, key: str, default: str) -> str:
        row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        with self.db:
            self.db.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (key, value))

    def backup(self, path: str):
        if Path(path).resolve() == Path(self.path).resolve():
            raise RuleError("error_backup_path")
        target = sqlite3.connect(path)
        try:
            self.db.backup(target)
        finally:
            target.close()
