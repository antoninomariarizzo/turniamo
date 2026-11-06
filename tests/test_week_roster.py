from datetime import timedelta
import sqlite3

import pytest

from turniamo.domain import Activity as A, Assignment, RuleError
from turniamo.storage import Store
from turniamo.web_ui import backup_before_migration, import_database
from test_domain import MONDAY


def test_delete_preserves_earlier_week_names_and_removes_future_shifts(tmp_path):
    store=Store(tmp_path/'live.sqlite3')
    doctor=store.save_doctor('Rossi')
    store.create_week(MONDAY)
    next_week=store.create_week(MONDAY+timedelta(days=7))
    later=store.create_week(MONDAY+timedelta(days=14))
    for index,start in enumerate((MONDAY,next_week,later)):
        store.save_assignment(Assignment(str(index),start,A.CLINIC_AM,doctor))
    store.save_week_doctor(next_week,'Rossi M.',doctor)
    assert store.week_doctors(MONDAY)[0].name=='Rossi'
    assert store.week_doctors(next_week)[0].name=='Rossi M.'
    store.remove_week_doctor(next_week,doctor)
    assert store.week_doctors(next_week)==store.week_doctors(later)==[]
    assert not store.week_doctors(MONDAY)[0].active
    assert len(store.week_context(MONDAY))==1
    assert store.week_context(next_week)==[]
    store.save_week_doctor(MONDAY,'Rossi old',doctor)
    assert store.week_doctors(later)==[]  # Renaming history cannot restore deleted members.
    newest=store.create_week(MONDAY+timedelta(days=21))
    assert store.week_doctors(newest)==[]
    store.close()
    reopened=Store(tmp_path/'live.sqlite3')
    assert reopened.week_doctors(MONDAY)[0].name=='Rossi old'
    assert reopened.week_doctors(next_week)==[]


def test_add_is_week_scoped_and_removed_doctor_can_be_readded():
    store=Store(':memory:')
    store.create_week(MONDAY)
    later=store.create_week(MONDAY+timedelta(days=7))
    d=store.save_week_doctor(later,'Alpha')
    assert store.week_doctors(MONDAY)==[]
    store.remove_week_doctor(later,d)
    assert store.save_week_doctor(later,'Alpha')==d
    assert store.week_doctors(later)[0].active


def test_removal_suppresses_incoming_night_off_without_deleting_previous_night():
    store=Store(':memory:')
    d=store.save_doctor('Alpha')
    store.save_assignment(Assignment('sun',MONDAY-timedelta(days=1),A.NIGHT_DUTY,d,True))
    store.create_week(MONDAY)
    assert any(a.activity==A.NIGHT_OFF for a in store.week_context(MONDAY))
    store.remove_week_doctor(MONDAY,d)
    assert not any(a.day==MONDAY for a in store.week_context(MONDAY))
    assert store.raw_assignments()[0].id=='sun'


def legacy_database(path):
    db=sqlite3.connect(path)
    db.executescript('''
        CREATE TABLE doctors(id TEXT PRIMARY KEY,name TEXT NOT NULL,name_key TEXT NOT NULL UNIQUE,active INTEGER NOT NULL);
        CREATE TABLE weeks(start TEXT PRIMARY KEY);
        CREATE TABLE assignments(id TEXT PRIMARY KEY,day TEXT NOT NULL,activity TEXT NOT NULL,
          doctor_id TEXT NOT NULL REFERENCES doctors(id),paid INTEGER NOT NULL,
          associate_role TEXT NOT NULL DEFAULT '',associate_name TEXT NOT NULL DEFAULT '',UNIQUE(day,activity,doctor_id));
        CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        INSERT INTO doctors VALUES('a','Alpha','alpha',1);
        INSERT INTO weeks VALUES('2026-12-07');
        INSERT INTO assignments VALUES('room','2026-12-07','surgery_3','a',0,'','');
        INSERT INTO assignments VALUES('helper','2026-12-08','ward_help','a',0,'','');
        INSERT INTO assignments VALUES('valid','2026-12-09','clinic_am','a',0,'','');
        PRAGMA user_version=1;
    ''')
    db.close()


def test_migration_backs_up_and_removes_only_requested_legacy_duties(tmp_path):
    path=tmp_path/'legacy.sqlite3'
    legacy_database(path)
    backup_before_migration(path)
    store=Store(path)
    assert {a.id for a in store.raw_assignments()}=={'room','valid'}
    assert store.week_doctors(MONDAY)[0].name=='Alpha'
    backup=next((tmp_path/'backups').glob('*.sqlite3'))
    with sqlite3.connect(backup) as db:
        assert db.execute('SELECT count(*) FROM assignments').fetchone()[0]==3


def test_import_replaces_valid_archive_and_backs_up_current_one(tmp_path):
    store=Store(tmp_path/'live.sqlite3')
    store.save_doctor('Current')
    source=Store(tmp_path/'source.sqlite3')
    d=source.save_doctor('Imported')
    source.save_assignment(Assignment('shift',MONDAY,A.DAY_DUTY,d))
    source.set_setting('language','en');source.close()
    import_database(store,str(tmp_path/'source.sqlite3'))
    assert store.week_doctors(MONDAY)[0].name=='Imported'
    assert store.setting('language','it')=='en'
    assert len(store.raw_assignments())==1
    backup=next((tmp_path/'backups').glob('*.sqlite3'))
    with sqlite3.connect(backup) as db:
        assert db.execute('SELECT name FROM doctors').fetchone()[0]=='Current'


@pytest.mark.parametrize('kind',['random','wrong_schema','future','bad_reference'])
def test_rejected_import_never_changes_live_data(tmp_path,kind):
    store=Store(tmp_path/'live.sqlite3');store.save_doctor('Keep me')
    path=tmp_path/'bad.sqlite3'
    if kind=='random':
        path.write_text('not a database')
    elif kind=='wrong_schema':
        with sqlite3.connect(path) as db:
            db.executescript('CREATE TABLE other(x); PRAGMA user_version=2;')
    else:
        other=Store(path);other.close()
        with sqlite3.connect(path) as db:
            if kind=='future':db.execute('PRAGMA user_version=99')
            else:db.execute("INSERT INTO assignments VALUES('bad','2026-12-07','ward','missing',0,'','')")
    with pytest.raises(RuleError,match='invalid_database'):
        import_database(store,str(path))
    assert store.doctors()[0].name=='Keep me'


@pytest.mark.parametrize('valid', [True, False])
def test_import_closes_temporary_database_connections(tmp_path, monkeypatch, valid):
    store = Store(tmp_path / 'live.sqlite3')
    source = Store(tmp_path / 'source.sqlite3')
    if not valid:
        source.db.execute('PRAGMA foreign_keys=OFF')
        with source.db:
            source.db.execute("INSERT INTO assignments VALUES('bad','2026-12-07','ward','missing',0,'','')")
    source.close()
    original_connect = sqlite3.connect
    opened = []

    def tracking_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, 'connect', tracking_connect)
    if valid:
        import_database(store, str(tmp_path / 'source.sqlite3'))
    else:
        with pytest.raises(RuleError, match='invalid_database'):
            import_database(store, str(tmp_path / 'source.sqlite3'))
    assert opened
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError, match='closed'):
            connection.execute('PRAGMA user_version')
    store.close()
