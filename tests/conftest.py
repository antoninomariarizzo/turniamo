import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    from turniamo.appearance import TurniamoStyle
    application = QApplication.instance() or QApplication([])
    application.setStyle(TurniamoStyle())
    yield application
