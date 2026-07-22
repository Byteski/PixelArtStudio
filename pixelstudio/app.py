from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pixelstudio.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pixel Art Studio")
    app.setOrganizationName("Brianski")

    window = MainWindow()
    window.show()
    return app.exec()
