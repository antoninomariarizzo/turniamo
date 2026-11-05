"""Check that the packaged executable starts with its own bundled dependencies."""
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
executable = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (
    root / "dist" / "turniamo.exe" if sys.platform == "win32"
    else root / "dist" / "turniamo.app" / "Contents" / "MacOS" / "turniamo"
)
with tempfile.TemporaryDirectory(prefix="turniamo-smoke-") as data_dir:
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    process = subprocess.Popen([str(executable), "--data-dir", data_dir], env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    database = Path(data_dir) / "turniamo.sqlite3"
    ready = False
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Packaged app exited early: {process.communicate()}")
            if database.exists():
                try:
                    with sqlite3.connect(database) as connection:
                        ready = connection.execute("SELECT count(*) FROM weeks").fetchone()[0] > 0
                except sqlite3.Error:
                    pass
                if ready:
                    with sqlite3.connect(database) as connection:
                        for table in ('doctors', 'assignments', 'week_doctors'):
                            assert connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0, f'Packaged app contains unexpected {table} data'
                    time.sleep(1)
                    assert process.poll() is None, "App exited during startup"
                    break
            time.sleep(0.1)
        assert ready, "Packaged app did not initialize its local database"
    finally:
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    assert b"Traceback" not in stderr, stderr.decode(errors="replace")
    print("Packaged turniamo started and initialized its database successfully.")
