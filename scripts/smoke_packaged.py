"""Check that the packaged executable starts with its own bundled dependencies."""
from contextlib import closing
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
    print(f"Started packaged app (PID {process.pid}); waiting for an empty database.", flush=True)
    ready = False
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"Packaged app exited early: {process.communicate()}")
            if database.exists():
                try:
                    with closing(sqlite3.connect(database)) as connection:
                        ready = connection.execute("SELECT count(*) FROM weeks").fetchone()[0] > 0
                except sqlite3.Error:
                    pass
                if ready:
                    with closing(sqlite3.connect(database)) as connection:
                        for table in ('doctors', 'assignments', 'week_doctors'):
                            assert connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 0, f'Packaged app contains unexpected {table} data'
                    print("Empty database initialized; checking process stays alive.", flush=True)
                    time.sleep(1)
                    assert process.poll() is None, "App exited during startup"
                    break
            time.sleep(0.1)
        assert ready, "Packaged app did not initialize its local database"
    finally:
        if sys.platform == "win32":
            # A one-file bundle has a bootloader parent and an application child.
            # Terminating only the parent leaves the child holding files and pipes.
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        else:
            process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=10)
    assert b"Traceback" not in stderr, stderr.decode(errors="replace")
    print("Packaged turniamo started and initialized its database successfully.")
