"""Run with the project environment on the target OS: python scripts/build.py."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
           "--name", "turniamo", "--distpath", str(ROOT / "dist"),
           "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build")]
if sys.platform == "win32":
    command += ["--onefile", "--icon", str(ROOT / "turniamo" / "assets" / "turniamo.ico")]
else:
    command += ["--onedir"]
if sys.platform == "darwin":
    command += ["--osx-bundle-identifier", "local.turniamo.desktop",
                "--icon", str(ROOT / "turniamo" / "assets" / "turniamo.icns")]
command += ["--add-data", str(ROOT / "turniamo" / "assets") + ":turniamo/assets"]
command += ["--add-data", str(ROOT / "turniamo" / "web") + ":turniamo/web", str(ROOT / "run.py")]
subprocess.run(command, cwd=ROOT, check=True)
