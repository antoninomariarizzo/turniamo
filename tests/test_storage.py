from datetime import timedelta

import pytest

from turniamo.domain import Activity as A, Assignment, RuleError, issues_for_week
from turniamo.storage import Store
from test_domain import MONDAY


def test_save_reopen_language_and_backup(tmp_path):
    path = tmp_path / "archive.sqlite3"
    store = Store(path)
    doctor = store.save_doctor("Rossi M.")
    store.create_week(MONDAY)
    store.save_assignment(Assignment("one", MONDAY, A.CLINIC_PM, doctor, associate_role="training", associate_name="Young"))
    store.set_setting("language", "en")
    backup = tmp_path / "backup.sqlite3"
    store.backup(str(backup))
    store.close()
    for p in (path, backup):
        reopened = Store(p)
        assert reopened.setting("language", "it") == "en"
        assert reopened.doctors()[0].name == "Rossi M."
        assert reopened.raw_assignments()[0].associate_name == "Young"
        assert reopened.weeks() == [MONDAY]
        reopened.close()


def test_names_normalized_and_archive_keeps_history():
    store = Store(":memory:")
    doctor = store.save_doctor("  Rossi   M. ")
    with pytest.raises(RuleError, match="error_unique_name"):
        store.save_doctor("rossi m.")
    store.save_assignment(Assignment("one", MONDAY, A.SURGERY_2, doctor))
    store.create_week(MONDAY + timedelta(days=7))
    store.remove_week_doctor(MONDAY + timedelta(days=7), doctor)
    assert store.doctors(active_only=True) == []
    assert len(store.raw_assignments()) == 1
    with pytest.raises(RuleError, match="error_doctor"):
        store.save_assignment(Assignment("two", MONDAY + timedelta(days=7), A.CLINIC_AM, doctor))


def test_cross_week_night_updates_deletes_and_absorbs_manual():
    store = Store(":memory:")
    d = store.save_doctor("Alpha")
    sunday = MONDAY - timedelta(days=1)
    store.save_assignment(Assignment("manual", MONDAY, A.NIGHT_OFF, d))
    store.save_assignment(Assignment("night", sunday, A.NIGHT_DUTY, d, True))
    context = store.week_context(MONDAY)
    assert len([a for a in context if a.activity == A.NIGHT_OFF]) == 1
    assert next(a for a in context if a.activity == A.NIGHT_OFF).paid
    assert all(a.id != "manual" for a in store.raw_assignments())
    store.save_assignment(Assignment("night", sunday, A.NIGHT_DUTY, d, False))
    assert not next(a for a in store.week_context(MONDAY) if a.activity == A.NIGHT_OFF).paid
    store.delete_assignment("night")
    assert store.week_context(MONDAY) == []


def test_saturday_night_does_not_warn_on_monday():
    store = Store(":memory:")
    d = store.save_doctor("Alpha")
    store.save_assignment(Assignment("night", MONDAY - timedelta(days=2), A.NIGHT_DUTY, d))
    store.save_assignment(Assignment("work", MONDAY, A.CLINIC_AM, d))
    assert issues_for_week(MONDAY, store.week_context(MONDAY)) == []


def test_rejected_edit_keeps_original_and_does_not_duplicate_week():
    store = Store(":memory:")
    d = store.save_doctor("Alpha")
    store.save_assignment(Assignment("leave", MONDAY, A.HOLIDAY, d))
    with pytest.raises(RuleError):
        store.save_assignment(Assignment("work", MONDAY, A.CLINIC_AM, d))
    assert len(store.raw_assignments()) == 1
    assert store.create_week(MONDAY + timedelta(days=2)) == MONDAY
    assert store.weeks() == [MONDAY]
