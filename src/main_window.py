"""
Main Window — PySide6 control panel (1024×768) with a sci-fi dark theme.
Handles user input, binds the MeasurementController, and manages the DisplayWindow.
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QRadioButton, QPushButton,
    QTextEdit, QGroupBox, QMessageBox, QApplication,
)

from .measurement_controller import MeasurementController, State
from .display_window import DisplayWindow
from .csv_exporter import CSVExporter


# ── Sci-fi Dark Theme Palette ──────────────────────────────────────────────

COLOR_BG       = '#0d1117'
COLOR_SURFACE   = '#161b22'
COLOR_BORDER    = '#30363d'
COLOR_ACCENT    = '#238636'   # green (start button)
COLOR_ABORT     = '#da3633'   # red (abort button)
COLOR_TEXT      = '#c9d1d9'
COLOR_MUTED     = '#8b949e'
COLOR_HEADER    = '#1f6feb'   # blue accent for section headers


def _dark_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {COLOR_BG};
        color: {COLOR_TEXT};
        font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
        font-size: 13px;
    }}
    QGroupBox {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 10px 10px 10px 10px;
        margin-top: 8px;
        font-weight: bold;
        color: {COLOR_TEXT};
    }}
    QGroupBox::title {{
        color: {COLOR_HEADER};
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 6px;
    }}
    QSpinBox, QLineEdit {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        min-width: 80px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {COLOR_BORDER};
        border-radius: 2px;
    }}
    QRadioButton {{
        color: {COLOR_TEXT};
        spacing: 6px;
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border: 1px solid {COLOR_BORDER};
        border-radius: 7px;
        background-color: {COLOR_SURFACE};
    }}
    QRadioButton::indicator:checked {{
        background-color: {COLOR_HEADER};
        border-color: {COLOR_HEADER};
    }}
    QPushButton {{
        border-radius: 6px;
        padding: 8px 20px;
        font-weight: bold;
        font-size: 14px;
        min-width: 120px;
    }}
    QPushButton#btn_start {{
        background-color: {COLOR_ACCENT};
        color: white;
        border: none;
    }}
    QPushButton#btn_start:hover {{
        background-color: #2ea043;
    }}
    QPushButton#btn_start:disabled {{
        background-color: {COLOR_BORDER};
        color: {COLOR_MUTED};
    }}
    QPushButton#btn_abort {{
        background-color: {COLOR_ABORT};
        color: white;
        border: none;
    }}
    QPushButton#btn_abort:hover {{
        background-color: #f85149;
    }}
    QPushButton#btn_abort:disabled {{
        background-color: {COLOR_BORDER};
        color: {COLOR_MUTED};
    }}
    QTextEdit {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_MUTED};
        border: 1px solid {COLOR_BORDER};
        border-radius: 6px;
        padding: 8px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
    }}
    QLabel {{
        color: {COLOR_TEXT};
    }}
    """


class MainWindow(QWidget):
    """
    Main control panel for the CA-410 colorimeter measurement tool.

    Layout (1024×768):
      ┌────────────────────────────────────────────────────────┐
      │  🎯 CA-410 色度分析仪                                  │
      ├────────────────────────────────────────────────────────┤
      │  【打屏参数】  offset_x/y  width/height               │
      │  【灰阶参数】  start_gray  end_gray                   │
      │  【颜色选择】  R / G / B / White (radio)             │
      │  【操作】      [开始测量]  [中止]                      │
      │  【状态日志】  QTextEdit (read-only)                  │
      └────────────────────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CA-410 色度分析仪')
        self.setFixedSize(1024, 768)

        # ── Display window (independent, Always-on-Top) ─────────────────
        self.display_window = DisplayWindow()
        self.display_window.start()

        # ── CSV exporter ────────────────────────────────────────────────
        self.csv_exporter = CSVExporter(self)

        # ── Measurement controller ───────────────────────────────────────
        self.controller = MeasurementController(self)
        self.controller.state_changed.connect(self._on_state_changed)
        self.controller.log_message.connect(self._on_log_message)
        self.controller.data_ready.connect(self._on_data_ready)
        self.controller.progress_updated.connect(self._on_progress_updated)
        self.controller.finished.connect(self._on_finished)

        # ── Build UI ───────────────────────────────────────────────────
        self._setup_ui()
        self._apply_theme()

        # ── Preview timer (sync display window with param changes) ────────
        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._apply_display_preview)
        self._preview_timer.start(100)  # ~10fps

        # ── Initial log ─────────────────────────────────────────────────
        self._append_log("系统就绪")
        self._append_log("请配置参数后点击「开始测量」")

    # ── UI Setup ───────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Title
        title = QLabel('🎯  CA-410 色度分析仪')
        title.setStyleSheet('font-size: 18px; font-weight: bold; color: #1f6feb; padding: 4px;')
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # ── Display parameters ─────────────────────────────────────────
        param_group = QGroupBox('【打屏参数】')
        param_layout = QGridLayout(param_group)
        param_layout.setSpacing(8)

        def make_spin(label: str, minv: int, maxv: int, default: int) -> QSpinBox:
            row = param_layout.rowCount()
            param_layout.addWidget(QLabel(label), row, 0, Qt.AlignRight)
            sb = QSpinBox()
            sb.setRange(minv, maxv)
            sb.setValue(default)
            param_layout.addWidget(sb, row, 1)
            return sb

        self._sb_offset_x = make_spin('起始 X:', 0, 9999, 100)
        self._sb_offset_y = make_spin('起始 Y:', 0, 9999, 100)
        self._sb_width    = make_spin('宽度:', 1, 9999, 512)
        self._sb_height   = make_spin('高度:', 1, 9999, 512)

        main_layout.addWidget(param_group)

        # ── Gray-level parameters ───────────────────────────────────────
        gray_group = QGroupBox('【灰阶参数】')
        gray_layout = QGridLayout(gray_group)
        gray_layout.setSpacing(8)

        self._sb_start = make_spin('开始灰阶:', 0, 255, 0)
        self._sb_end   = make_spin('结束灰阶:', 0, 255, 255)

        main_layout.addWidget(gray_group)

        # ── Color selection ──────────────────────────────────────────────
        color_group = QGroupBox('【颜色选择】')
        color_layout = QHBoxLayout(color_group)
        color_layout.setSpacing(12)

        self._radio_red   = QRadioButton('红色')
        self._radio_green = QRadioButton('绿色')
        self._radio_blue  = QRadioButton('蓝色')
        self._radio_white = QRadioButton('白色')
        self._radio_white.setChecked(True)

        for r in (self._radio_red, self._radio_green, self._radio_blue, self._radio_white):
            color_layout.addWidget(r)
        color_layout.addStretch()

        main_layout.addWidget(color_group)

        # ── Buttons ─────────────────────────────────────────────────────
        btn_group = QGroupBox('【操作】')
        btn_layout = QHBoxLayout(btn_group)
        btn_layout.setSpacing(16)

        self._btn_start = QPushButton('▶  开始测量')
        self._btn_start.setObjectName('btn_start')
        self._btn_start.clicked.connect(self._on_start_clicked)

        self._btn_abort = QPushButton('■  中止')
        self._btn_abort.setObjectName('btn_abort')
        self._btn_abort.setEnabled(False)
        self._btn_abort.clicked.connect(self._on_abort_clicked)

        btn_layout.addWidget(self._btn_start)
        btn_layout.addWidget(self._btn_abort)
        btn_layout.addStretch()

        main_layout.addWidget(btn_group)

        # ── Log area ────────────────────────────────────────────────────
        log_group = QGroupBox('【状态日志】')
        log_layout = QVBoxLayout(log_group)

        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMinimumHeight(200)
        log_layout.addWidget(self._log_area)

        main_layout.addWidget(log_group)

        # ── Status bar ───────────────────────────────────────────────────
        self._status_label = QLabel('就绪')
        self._status_label.setStyleSheet('color: #8b949e; font-size: 12px; padding: 2px;')
        self._status_label.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self._status_label)

    def _apply_theme(self) -> None:
        self.setStyleSheet(_dark_stylesheet())

    # ── Display preview ────────────────────────────────────────────────────

    def _apply_display_preview(self) -> None:
        """Periodically sync display window with current parameters (only in IDLE state)."""
        if self.controller.get_state() != State.IDLE:
            return
        try:
            self.display_window.set_position(
                self._sb_offset_x.value(),
                self._sb_offset_y.value()
            )
            self.display_window.set_size(
                self._sb_width.value(),
                self._sb_height.value()
            )
            gray = self._sb_start.value()
            color = self._get_selected_color()
            if color == MeasurementController.COLOR_RED:
                r, g, b = gray, 0, 0
            elif color == MeasurementController.COLOR_GREEN:
                r, g, b = 0, gray, 0
            elif color == MeasurementController.COLOR_BLUE:
                r, g, b = 0, 0, gray
            else:  # white
                r = g = b = gray
            self.display_window.set_color(r, g, b)
        except Exception:
            pass

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_selected_color(self) -> str:
        if self._radio_red.isChecked():
            return MeasurementController.COLOR_RED
        if self._radio_green.isChecked():
            return MeasurementController.COLOR_GREEN
        if self._radio_blue.isChecked():
            return MeasurementController.COLOR_BLUE
        return MeasurementController.COLOR_WHITE

    # ── Button handlers ───────────────────────────────────────────────────

    def _on_start_clicked(self) -> None:
        start = self._sb_start.value()
        end   = self._sb_end.value()
        if start > end:
            QMessageBox.warning(self, "参数错误", "开始灰阶不能大于结束灰阶")
            return

        params = {
            'offset_x':   self._sb_offset_x.value(),
            'offset_y':   self._sb_offset_y.value(),
            'width':      self._sb_width.value(),
            'height':     self._sb_height.value(),
            'start_gray': start,
            'end_gray':   end,
            'color':      self._get_selected_color_code(),
            'color_name': self._get_selected_color(),
        }
        self.controller.start(
            params,
            display_window=self.display_window,
            csv_exporter=self.csv_exporter,
        )

    def _get_selected_color_code(self) -> str:
        if self._radio_red.isChecked():   return 'R'
        if self._radio_green.isChecked(): return 'G'
        if self._radio_blue.isChecked():  return 'B'
        return 'W'

    def _on_abort_clicked(self) -> None:
        self.controller.abort()

    # ── Controller signal handlers ─────────────────────────────────────────

    def _on_state_changed(self, state_name: str) -> None:
        state = State[state_name]
        self._status_label.setText(f"状态: {state_name}")

        if state == State.IDLE:
            self._set_controls_enabled(True)
            self._btn_abort.setEnabled(False)
            self._btn_start.setEnabled(True)
        elif state in (State.SCANNING, State.CONNECTING, State.CALIBRATING,
                        State.MEASURING, State.ABORTING, State.EXPORTING):
            self._set_controls_enabled(False)
            self._btn_abort.setEnabled(state in (State.MEASURING, State.ABORTING))
            self._btn_start.setEnabled(False)
        elif state == State.ERROR:
            self._set_controls_enabled(True)
            self._btn_abort.setEnabled(False)
            self._btn_start.setEnabled(True)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for sb in (self._sb_offset_x, self._sb_offset_y,
                   self._sb_width,   self._sb_height,
                   self._sb_start,   self._sb_end):
            sb.setEnabled(enabled)
        for r in (self._radio_red, self._radio_green,
                  self._radio_blue, self._radio_white):
            r.setEnabled(enabled)

    def _on_log_message(self, msg: str) -> None:
        self._append_log(msg)

    def _append_log(self, msg: str) -> None:
        ts = datetime.now().strftime('%H:%M:%S')
        self._log_area.append(f'<span style="color:#8b949e">[{ts}]</span> {msg}')
        cursor = self._log_area.textCursor()
        cursor.movePosition(cursor.End)
        self._log_area.setTextCursor(cursor)

    def _on_data_ready(self, record: dict) -> None:
        pass  # Data shown via log

    def _on_progress_updated(self, current: int, total: int) -> None:
        self._status_label.setText(f"进度: {current}/{total}")

    def _on_finished(self, message: str) -> None:
        if message.startswith('ERROR:'):
            QMessageBox.critical(self, "测量错误", message[6:])
        elif message == "CSV export cancelled":
            self._append_log("CSV 导出已取消")
        else:
            QMessageBox.information(
                self,
                "测量完成",
                f"测量完成，CSV 已保存：\n{message}"
            )
        self._append_log(f"[完成] {message}")

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self.display_window.stop()
        event.accept()
