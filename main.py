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
    try:
        import win32event
        import win32api
        import winerror

        _mutex_name = "ca-analyzer-single-instance-mutex"
        _mutex = win32event.CreateMutex(None, False, _mutex_name)
        _last_error = win32api.GetLastError()

        if _last_error == winerror.ERROR_ALREADY_EXISTS:
            from PySide6.QtWidgets import QApplication, QMessageBox
            _app = QApplication(sys.argv)
            QMessageBox.warning(
                None,
                "提示",
                "软件已启动，请勿重复打开。",
            )
            sys.exit(1)
    except ImportError:
        # pywin32 not installed — skip single-instance check
        pass

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
