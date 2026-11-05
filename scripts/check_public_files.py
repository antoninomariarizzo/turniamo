"""Reject private data and credentials in the Git-tracked publication files."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {"LICENSE", ".gitignore", "README.md", "pyproject.toml", "run.py"}
ASSETS = {"turniamo.png", "turniamo.ico", "turniamo.icns"}
SECRET = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    rb"|gh[pousr]_[A-Za-z0-9]{30,}"
    rb"|github_pat_[A-Za-z0-9_]{40,}"
    rb"|sk-(?:proj-)?[A-Za-z0-9_-]{40,}"
)


def allowed(name):
    path = PurePosixPath(name)
    parent = str(path.parent)
    if name in ROOT_FILES:
        return True
    if parent in {"scripts", "tests", "turniamo"}:
        return path.suffix == ".py"
    if parent == "turniamo/web":
        return path.name in {"index.html", "style.css", "app.js"}
    if parent == "turniamo/assets":
        return path.name in ASSETS
    return name in {".github/workflows/build.yml", ".github/RELEASE_NOTES.md"}


def main():
    names = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).decode().strip("\0").split("\0")
    rejected = []
    for name in filter(None, names):
        path = ROOT / name
        if not allowed(name) or path.is_symlink():
            rejected.append(name)
            continue
        data = path.read_bytes()
        if data.startswith(b"SQLite format 3\0") or SECRET.search(data):
            rejected.append(name)
    if rejected:
        print("Publication blocked; review these files:", file=sys.stderr)
        print("\n".join(rejected), file=sys.stderr)
        return 1
    print(f"Publication check passed: {len(names)} tracked source and asset files; no database or detected credentials.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
