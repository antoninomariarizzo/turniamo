"""Publication checks use synthetic files in an isolated Git repository."""
import subprocess

import pytest

from scripts import check_public_files


@pytest.mark.parametrize('name,data', [
    ('doctors.sqlite3', b'private data'),
    ('exports/roster.csv', b'private data'),
    ('turniamo/assets/turniamo.png', b'SQLite format 3\0database'),
    ('run.py', b'token = "' + b'ghp_' + b'x' * 36 + b'"'),
])
def test_publication_rejects_data_and_credentials(tmp_path, monkeypatch, name, data):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    subprocess.run(['git', 'add', name], cwd=tmp_path, check=True)
    monkeypatch.setattr(check_public_files, 'ROOT', tmp_path)
    assert check_public_files.main() == 1


def test_publication_accepts_source(tmp_path, monkeypatch):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path / 'run.py').write_text('print("turniamo")\n')
    subprocess.run(['git', 'add', 'run.py'], cwd=tmp_path, check=True)
    monkeypatch.setattr(check_public_files, 'ROOT', tmp_path)
    assert check_public_files.main() == 0
