"""
ca-analyzer — M5 色度仪测试模块
Program entry point.

Features:
  - Single-instance detection (Windows named mutex)
  - Console window hidden (pythonw / --noconsole)

Usage (development):
    python main.py

Usage (production / packaged):
    pyinstaller --noconsole --onefile --name ca-analyzer --icon resources/icons/logo.ico main.py
    ./dist/ca-analyzer.exe
"""

import sys

# ── Single-instance detection (Windows) ─────────────────────────────────────
if sys.platform == "win32":
    import win32event
    import win32api
    import winerror

    _mutex_name = "ca-analyzer-single-instance-mutex"
    _mutex = win32event.CreateMutex(None, False, _mutex_name)
    _last_error = win32api.GetLastError()

    if _last_error == winerror.ERROR_ALREADY_EXISTS:
        # Another instance is already running — show warning and exit
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            _app = QApplication(sys.argv)
            QMessageBox.warning(
                None,
                "提示",
                "软件已启动，请勿重复打开。",
            )
        except Exception:
            pass
        sys.exit(1)

# ── App entry ─────────────────────────────────────────────────────────────────
from PySide6.QtWidgets import QApplication
from src.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("CA-410 色度分析仪")
    app.setApplicationVersion("2.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
