"""Desktop entry point. --data-dir allows a portable or explicitly chosen archive."""
import argparse
from pathlib import Path
import sys

from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .storage import Store
from .appearance import TurniamoStyle
from .web_ui import MainWindow, backup_before_migration


def main():
    parser = argparse.ArgumentParser(description="turniamo · Turni ospedalieri / Hospital shifts")
    parser.add_argument("--data-dir", type=Path, help="Directory for the local SQLite database")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("turniamo")
    app.setOrganizationName("turniamo")
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "assets" / "turniamo.png")))
    app.setStyle(TurniamoStyle())
    data_dir = args.data_dir or Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation))
    try:
        path = data_dir / "turniamo.sqlite3"
        backup_before_migration(path)
        store = Store(path)
        window = MainWindow(store)
    except Exception as exc:
        QMessageBox.critical(None, "turniamo", f"Impossibile aprire l’archivio / Cannot open database:\n{exc}")
        return 1
    window.show()
    result = app.exec()
    store.close()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
