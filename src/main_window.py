"""
Main Window — PySide6 control panel (1024×768).
New UI design per M5.ui-design.md with dark/light theme support,
two-column parameter layout, and real-time display window sync.
"""

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QRadioButton, QPushButton,
    QTextEdit, QGroupBox, QMessageBox, QButtonGroup,
    QFrame, QProgressBar, QApplication,
)

from .measurement_controller import MeasurementController, State
from .display_window import DisplayWindow
from .csv_exporter import CSVExporter


# ── Theme Color Palettes ─────────────────────────────────────────────────────

class ThemeColors:
    """Color palettes for dark and light themes."""
    DARK = {
        "bg":            "#1E1E2E",
        "surface":       "#2D2D44",
        "border":        "#3D3D5C",
        "accent":        "#6C7EE1",
        "accent_hover":  "#7C8EF1",
        "text":          "#FFFFFF",
        "text_sec":      "#A0A0B8",
        "text_placeholder": "#6B6B80",
        "success":       "#4CAF50",
        "error":         "#F44336",
        "warning":       "#FF9800",
        "divider":       "#2A2A3E",
        "log_bg":        "#16162A",
        "btn_disabled":  "#3D3D5C",
        "btn_disabled_txt": "rgba(255,255,255,0.4)",
    }
    LIGHT = {
        "bg":            "#F5F5F7",
        "surface":       "#FFFFFF",
        "border":        "#E0E0E8",
        "accent":        "#4A56E2",
        "accent_hover":  "#5A66F2",
        "text":          "#1A1A2E",
        "text_sec":      "#6B6B80",
        "text_placeholder": "#A0A0B8",
        "success":       "#388E3C",
        "error":         "#D32F2F",
        "warning":       "#F57C00",
        "divider":       "#E8E8F0",
        "log_bg":        "#EBEBF0",
        "btn_disabled":  "#E0E0E8",
        "btn_disabled_txt": "rgba(26,26,46,0.4)",
    }


# ── Stylesheet Builder ────────────────────────────────────────────────────────

def make_stylesheet(c: dict) -> str:
    font = "'Microsoft YaHei UI', 'Segoe UI', sans-serif"
    mono = "'Consolas', 'Courier New', monospace"

    return f"""
    QWidget {{
        background-color: {c['bg']};
        color: {c['text']};
        font-family: {font};
        font-size: 13px;
    }}
    QGroupBox {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 10px;
        padding: 12px 14px 14px 14px;
        margin-top: 4px;
        font-weight: 600;
        font-size: 12px;
        color: {c['accent']};
    }}
    QGroupBox::title {{
        color: {c['accent']};
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 4px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    /* Section title bar (custom) */
    .section-title {{
        font-size: 12px;
        font-weight: 600;
        color: {c['accent']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0 4px;
        background: transparent;
    }}
    /* SpinBox */
    QSpinBox {{
        background-color: {c['bg']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 7px 10px;
        min-width: 60px;
    }}
    QSpinBox:focus {{
        border: 1px solid {c['accent']};
    }}
    QSpinBox:disabled {{
        opacity: 0.5;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background-color: {c['border']};
        border-radius: 2px;
        width: 16px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: {c['accent']};
    }}
    /* RadioButton */
    QRadioButton {{
        color: {c['text']};
        spacing: 6px;
        font-size: 13px;
        padding: 4px 6px;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c['text_sec']};
        border-radius: 8px;
        background-color: transparent;
    }}
    QRadioButton::indicator:checked {{
        border-color: {c['accent']};
        background-color: {c['accent']};
    }}
    QRadioButton:disabled {{
        opacity: 0.5;
    }}
    /* PushButton — primary (start) */
    QPushButton#btn_start {{
        background-color: {c['accent']};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 11px 20px;
        font-size: 14px;
        font-weight: 600;
        min-width: 140px;
    }}
    QPushButton#btn_start:hover {{
        background-color: {c['accent_hover']};
    }}
    QPushButton#btn_start:disabled {{
        background-color: {c['btn_disabled']};
        color: {c['btn_disabled_txt']};
    }}
    /* PushButton — danger (abort) */
    QPushButton#btn_abort {{
        background-color: {c['error']};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 11px 20px;
        font-size: 14px;
        font-weight: 600;
        min-width: 140px;
    }}
    QPushButton#btn_abort:hover {{
        background-color: #E53935;
    }}
    QPushButton#btn_abort:disabled {{
        background-color: {c['btn_disabled']};
        color: {c['btn_disabled_txt']};
    }}
    /* Theme toggle button */
    QPushButton#btn_theme {{
        background-color: transparent;
        border: 1px solid {c['border']};
        border-radius: 8px;
        color: {c['text']};
        font-size: 16px;
        padding: 6px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
    }}
    QPushButton#btn_theme:hover {{
        background-color: {c['accent']};
        border-color: {c['accent']};
    }}
    /* Log area */
    QTextEdit#log_area {{
        background-color: {c['log_bg']};
        color: {c['text_sec']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 8px;
        font-family: {mono};
        font-size: 12px;
        line-height: 1.7;
    }}
    /* Progress bar */
    QProgressBar {{
        background-color: {c['bg']};
        border: none;
        border-radius: 3px;
        height: 6px;
        text-align: right;
        font-size: 10px;
        color: {c['text_sec']};
    }}
    QProgressBar::chunk {{
        background-color: {c['accent']};
        border-radius: 3px;
    }}
    /* Status badge */
    QLabel#status_badge {{
        background-color: rgba(76, 175, 80, 0.15);
        color: {c['success']};
        border: 1px solid rgba(76, 175, 80, 0.3);
        border-radius: 12px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 600;
    }}
    QLabel#status_badge.measuring {{
        background-color: rgba(255, 152, 0, 0.15);
        color: {c['warning']};
        border-color: rgba(255, 152, 0, 0.3);
    }}
    QLabel#status_badge.error {{
        background-color: rgba(244, 67, 54, 0.15);
        color: {c['error']};
        border-color: rgba(244, 67, 54, 0.3);
    }}
    QLabel#status_badge.aborted {{
        background-color: rgba(160, 160, 184, 0.15);
        color: {c['text_sec']};
        border-color: rgba(160, 160, 184, 0.3);
    }}
    /* Preview panel */
    QLabel#preview_color {{
        border-radius: 4px;
        border: 1px solid {c['border']};
    }}
    /* Divider */
    QFrame#divider {{
        background-color: {c['divider']};
        border: none;
    }}
    /* Mini data display */
    QLabel.mini_data_label {{
        font-family: {mono};
        font-size: 12px;
        color: {c['accent']};
        font-weight: 600;
    }}
    /* Footer */
    QLabel.footer {{
        font-size: 11px;
        color: {c['text_sec']};
    }}
    """


# ── Color configuration ──────────────────────────────────────────────────────

COLOR_ORDER = ["white", "red", "green", "blue"]
COLOR_NAMES = {"white": "白色", "red": "红色", "green": "绿色", "blue": "蓝色"}
COLOR_RGB = {
    "white": (255, 255, 255),
    "red":   (255, 0,   0  ),
    "green": (0,   255, 0  ),
    "blue":  (0,   0,   255),
}
# When gray is applied: white = all channels, red = R channel, etc.
COLOR_GRAY_MIX = {
    "white": lambda g: (g, g, g),
    "red":   lambda g: (g, 0, 0),
    "green": lambda g: (0, g, 0),
    "blue":  lambda g: (0, 0, g),
}


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QWidget):
    """
    Main control panel — new UI design (M5).
    Left panel: controls. Right panel: display window info + mini preview.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CA-410 色度分析仪")
        self.setFixedSize(1024, 768)

        # ── State ──────────────────────────────────────────────────────────
        self._is_dark = True
        self._current_color = "white"
        self._current_gray = 255  # default to max gray (white)

        # ── Display window ────────────────────────────────────────────────
        self.display_window = DisplayWindow()
        self.display_window.start()

        # Apply initial state to display window (white, 255)
        self._update_display_window()

        # ── CSV exporter ──────────────────────────────────────────────────
        self.csv_exporter = CSVExporter(self)

        # ── Measurement controller ─────────────────────────────────────────
        self.controller = MeasurementController(self)
        self.controller.state_changed.connect(self._on_state_changed)
        self.controller.log_message.connect(self._on_log_message)
        self.controller.data_ready.connect(self._on_data_ready)
        self.controller.progress_updated.connect(self._on_progress_updated)
        self.controller.finished.connect(self._on_finished)

        # ── Build UI ───────────────────────────────────────────────────────
        self._setup_ui()
        self._apply_theme()
        self._update_preview_color()  # show initial white 255

        # ── Startup log ───────────────────────────────────────────────────
        self._append_log("系统就绪", "info")
        self._append_log("参数已加载，默认显示白色 255 灰阶", "info")

    # ── UI Setup ─────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── LEFT: Control Panel ─────────────────────────────────────────────
        left_widget = QWidget()
        left_widget.setFixedWidth(460)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 12, 16, 12)
        left_layout.setSpacing(10)

        # Header
        header = self._build_header()
        left_layout.addWidget(header)

        # Scrollable content
        content = self._build_content()
        left_layout.addWidget(content, stretch=1)

        # Footer
        footer = self._build_footer()
        left_layout.addWidget(footer)

        main_layout.addWidget(left_widget)

        # Divider
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedWidth(1)
        main_layout.addWidget(divider)

        # ── RIGHT: Display Info Panel ────────────────────────────────────────
        right_widget = self._build_right_panel()
        main_layout.addWidget(right_widget, stretch=1)

    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(56)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        # Icon + title
        icon_label = QLabel("🎯")
        icon_label.setStyleSheet("font-size: 22px; background: transparent;")

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_main = QLabel("CA-410 色度分析仪")
        title_main.setStyleSheet("font-size: 15px; font-weight: 600; color: palette(text); background: transparent;")
        title_sub = QLabel("Chromaticity Analyzer v2.0")
        title_sub.setStyleSheet("font-size: 10px; color: palette(window-text); opacity: 0.6; background: transparent;")

        title_col.addWidget(title_main)
        title_col.addWidget(title_sub)

        layout.addWidget(icon_label)
        layout.addWidget(title_col)
        layout.addStretch()

        # Theme toggle button
        self._btn_theme = QPushButton("☀️")
        self._btn_theme.setObjectName("btn_theme")
        self._btn_theme.setToolTip("切换主题")
        self._btn_theme.clicked.connect(self._toggle_theme)
        layout.addWidget(self._btn_theme)

        # Style header background
        w.setStyleSheet("""
            QWidget { background-color: palette(window); border-bottom: 1px solid palette(dark); }
        """)
        return w

    def _build_content(self) -> QWidget:
        scroll = QWidget()  # No QScrollArea for simplicity (fixed layout)
        layout = QVBoxLayout(scroll)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(10)

        # ── Display Parameters ─────────────────────────────────────────────
        layout.addWidget(self._make_param_group(
            "📌 打屏参数",
            self._build_display_params(),
        ))

        # ── Gray Parameters ────────────────────────────────────────────────
        layout.addWidget(self._make_param_group(
            "📌 灰阶参数",
            self._build_gray_params(),
        ))

        # ── Color Selection ─────────────────────────────────────────────────
        layout.addWidget(self._make_param_group(
            "📌 颜色选择",
            self._build_color_selection(),
        ))

        # ── Buttons ─────────────────────────────────────────────────────────
        layout.addWidget(self._build_buttons())

        # ── Status ─────────────────────────────────────────────────────────
        layout.addWidget(self._build_status())

        # ── Log ─────────────────────────────────────────────────────────────
        layout.addWidget(self._build_log(), stretch=1)

        return scroll

    def _make_param_group(self, title: str, content_widget: QWidget) -> QGroupBox:
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(4, 14, 4, 4)
        group_layout.addWidget(content_widget)
        return group

    def _two_col_layout(self, left: QWidget, right: QWidget, gap: int = 10) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(gap)
        layout.addWidget(left, stretch=1)
        layout.addWidget(right, stretch=1)
        return layout

    def _input_row(self, label: str, spin: QSpinBox) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; color: palette(window-text); opacity: 0.7;")
        layout.addWidget(lbl)
        layout.addWidget(spin)
        return w

    def _build_display_params(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 1: offset_x, offset_y
        self._sb_offset_x = QSpinBox()
        self._sb_offset_x.setRange(0, 9999)
        self._sb_offset_x.setValue(0)
        self._sb_offset_x.valueChanged.connect(self._on_offset_changed)

        self._sb_offset_y = QSpinBox()
        self._sb_offset_y.setRange(0, 9999)
        self._sb_offset_y.setValue(0)
        self._sb_offset_y.valueChanged.connect(self._on_offset_changed)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(self._input_row("起始 X", self._sb_offset_x), stretch=1)
        row1.addWidget(self._input_row("起始 Y", self._sb_offset_y), stretch=1)

        # Row 2: width, height
        self._sb_width = QSpinBox()
        self._sb_width.setRange(1, 9999)
        self._sb_width.setValue(512)
        self._sb_width.valueChanged.connect(self._on_display_params_changed)

        self._sb_height = QSpinBox()
        self._sb_height.setRange(1, 9999)
        self._sb_height.setValue(512)
        self._sb_height.valueChanged.connect(self._on_display_params_changed)

        row2 = QHBoxLayout()
        row2.setSpacing(10)
        row2.addWidget(self._input_row("宽度", self._sb_width), stretch=1)
        row2.addWidget(self._input_row("高度", self._sb_height), stretch=1)

        layout.addLayout(row1)
        layout.addLayout(row2)
        return container

    def _build_gray_params(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        self._sb_start_gray = QSpinBox()
        self._sb_start_gray.setRange(0, 255)
        self._sb_start_gray.setValue(0)

        self._sb_end_gray = QSpinBox()
        self._sb_end_gray.setRange(0, 255)
        self._sb_end_gray.setValue(255)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(self._input_row("开始灰阶", self._sb_start_gray), stretch=1)
        row.addWidget(self._input_row("结束灰阶", self._sb_end_gray), stretch=1)
        layout.addLayout(row)
        return container

    def _build_color_selection(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        self._color_group = QButtonGroup()
        self._color_radios = {}

        swatches = {
            "white": "#FFFFFF",
            "red":   "#FF0000",
            "green": "#00FF00",
            "blue":  "#0066FF",
        }

        for i, color_key in enumerate(COLOR_ORDER):
            radio = QRadioButton(f"{COLOR_NAMES[color_key]}")
            radio.setCheckable(True)
            radio.setChecked(i == 0)  # white = first, default
            self._color_group.addButton(radio)
            self._color_radios[color_key] = radio
            layout.addWidget(radio, stretch=1)

        self._color_group.idClicked.connect(self._on_color_changed)
        return container

    def _build_buttons(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 4, 0, 4)

        self._btn_start = QPushButton("▶  开始测量")
        self._btn_start.setObjectName("btn_start")
        self._btn_start.clicked.connect(self._on_start_clicked)

        self._btn_abort = QPushButton("■  中止")
        self._btn_abort.setObjectName("btn_abort")
        self._btn_abort.setEnabled(False)
        self._btn_abort.clicked.connect(self._on_abort_clicked)

        layout.addWidget(self._btn_start)
        layout.addWidget(self._btn_abort)
        layout.addStretch()
        return container

    def _build_status(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header row: label + badge
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("状态"))
        header_row.addStretch()

        self._status_badge = QLabel("就绪")
        self._status_badge.setObjectName("status_badge")
        header_row.addWidget(self._status_badge)
        layout.addLayout(header_row)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        layout.addWidget(self._progress_bar)

        # Progress text
        self._progress_label = QLabel("进度: 0% (0/256)")
        self._progress_label.setStyleSheet("font-size: 12px; opacity: 0.7;")
        layout.addWidget(self._progress_label)

        # Latest measurement data (x, y, Lv)
        data_row = QHBoxLayout()
        data_row.setSpacing(8)
        for lbl_text in ["x 坐标", "y 坐标", "亮度 Lv"]:
            item = QWidget()
            item.setStyleSheet("background-color: palette(window); border-radius: 6px; padding: 4px 8px;")
            il = QVBoxLayout(item)
            il.setContentsMargins(4, 4, 4, 4)
            il.setSpacing(2)
            ml = QLabel(lbl_text)
            ml.setStyleSheet("font-size: 10px; opacity: 0.6;")
            vl = QLabel("--")
            vl.setObjectName(f"data_{lbl_text}")
            vl.setStyleSheet("font-size: 13px; font-weight: 600; color: palette(text);")
            il.addWidget(ml)
            il.addWidget(vl)
            data_row.addWidget(item, stretch=1)

        layout.addLayout(data_row)
        return container

    def _build_log(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("日志"))
        header_row.addStretch()
        self._log_count = QLabel("0 条")
        self._log_count.setStyleSheet("font-size: 11px; opacity: 0.6;")
        header_row.addWidget(self._log_count)
        layout.addLayout(header_row)

        self._log_area = QTextEdit()
        self._log_area.setObjectName("log_area")
        self._log_area.setReadOnly(True)
        self._log_area.setMinimumHeight(120)
        layout.addWidget(self._log_area, stretch=1)
        return container

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(32)
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("v2.0.0 · CA-Analyzer"))
        layout.addStretch()
        self._footer_status = QLabel("● 串口未连接")
        self._footer_status.setStyleSheet("font-size: 11px; opacity: 0.6;")
        layout.addWidget(self._footer_status)
        w.setStyleSheet("background-color: palette(window); border-top: 1px solid palette(dark);")
        return w

    def _build_right_panel(self) -> QWidget:
        """Right panel: display window info + mini preview."""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(44)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.addWidget(QLabel("🖥️  打屏预览窗口"))
        hl.addStretch()
        badge = QLabel("Always on Top")
        badge.setStyleSheet("font-size: 10px; background: palette(window); border: 1px solid palette(dark); border-radius: 10px; padding: 2px 8px;")
        hl.addWidget(badge)
        header.setStyleSheet("background-color: palette(window); border-bottom: 1px solid palette(dark);")
        layout.addWidget(header)

        # Content
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(16)
        cl.addStretch()

        # Color preview box
        preview_container = QWidget()
        preview_container.setFixedSize(300, 200)
        pl = QVBoxLayout(preview_container)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setAlignment(Qt.AlignCenter)

        self._preview_color = QLabel()
        self._preview_color.setObjectName("preview_color")
        self._preview_color.setFixedSize(280, 160)
        self._preview_color.setAlignment(Qt.AlignCenter)
        pl.addWidget(self._preview_color)

        preview_info = QHBoxLayout()
        preview_info.setSpacing(8)
        self._preview_gray_label = QLabel("255")
        self._preview_gray_label.setStyleSheet("font-size: 24px; font-weight: 700; color: #333; background: transparent;")
        self._preview_size_label = QLabel("512 × 512")
        self._preview_size_label.setStyleSheet("font-size: 12px; color: #666; background: transparent;")
        preview_info.addWidget(self._preview_gray_label)
        preview_info.addWidget(self._preview_size_label)
        preview_info.addStretch()
        pl.addLayout(preview_info)
        cl.addWidget(preview_container, alignment=Qt.AlignHCenter)

        # Info grid
        info_grid = QGridLayout()
        info_grid.setSpacing(8)

        def info_item(label: str, value: str, highlight: bool = False) -> tuple:
            lbl = QLabel(f"{label}: <b>{value}</b>")
            lbl.setStyleSheet(f"font-size: 12px; background: palette(window); border-radius: 6px; padding: 6px 12px;")
            return lbl

        self._info_pos   = info_item("位置",   "(0, 0)")
        self._info_gray  = info_item("灰阶",    "255",    highlight=True)
        self._info_size  = info_item("尺寸",    "512×512")
        self._info_rgb   = info_item("RGB",    "255, 255, 255")

        for i, lbl in enumerate([self._info_pos, self._info_gray, self._info_size, self._info_rgb]):
            info_grid.addWidget(lbl, i // 2, i % 2)
        cl.addLayout(info_grid)

        cl.addStretch()
        layout.addWidget(content, stretch=1)
        return w

    # ── Theme ────────────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        self._is_dark = not self._is_dark
        self._btn_theme.setText("🌙" if self._is_dark else "☀️")
        self._apply_theme()

    def _apply_theme(self) -> None:
        colors = ThemeColors.DARK if self._is_dark else ThemeColors.LIGHT
        self.setStyleSheet(make_stylesheet(colors))
        self._update_preview_color()

    # ── Display window sync ─────────────────────────────────────────────────

    def _on_offset_changed(self, _value: int) -> None:
        """Immediately update display window position when offset changes."""
        if self.controller.get_state() != State.IDLE:
            return
        self._update_display_position()
        self._update_preview_info()

    def _on_display_params_changed(self, _value: int) -> None:
        """Update display window when size changes."""
        if self.controller.get_state() != State.IDLE:
            return
        self.display_window.set_size(self._sb_width.value(), self._sb_height.value())
        self._update_preview_info()

    def _on_color_changed(self, radio_id: int) -> None:
        """Update display window when color selection changes."""
        # Map button IDs to color keys
        id_to_color = {id(r): k for k, r in self._color_radios.items()}
        sender = self.sender()
        if sender is None:
            return
        for btn_id in self._color_group.buttons():
            if btn_id is sender:
                color_key = id_to_color.get(id(btn_id), "white")
                self._current_color = color_key
                self._update_display_window()
                self._update_preview_color()
                break

    def _update_display_position(self) -> None:
        """Immediately move the display window to the target position."""
        self.display_window.set_position(
            self._sb_offset_x.value(),
            self._sb_offset_y.value()
        )

    def _update_display_window(self) -> None:
        """Update display window color, size, and position."""
        gray = self._current_gray
        mix_fn = COLOR_GRAY_MIX[self._current_color]
        r, g, b = mix_fn(gray)
        self.display_window.set_color(r, g, b)
        self.display_window.set_size(self._sb_width.value(), self._sb_height.value())
        self.display_window.set_position(self._sb_offset_x.value(), self._sb_offset_y.value())

    def _update_preview_color(self) -> None:
        """Update the right-panel mini preview color."""
        gray = self._current_gray
        mix_fn = COLOR_GRAY_MIX[self._current_color]
        r, g, b = mix_fn(gray)
        hex_color = f"#{r:02X}{g:02X}{b:02X}"

        self._preview_color.setStyleSheet(
            f"background-color: {hex_color}; "
            f"border-radius: 4px; "
            f"border: 1px solid palette(dark);"
        )

        # Text color based on brightness
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "#333" if brightness > 128 else "#FFF"
        self._preview_gray_label.setStyleSheet(
            f"font-size: 24px; font-weight: 700; color: {text_color}; background: transparent;"
        )
        self._preview_size_label.setStyleSheet(
            f"font-size: 12px; color: {text_color}; opacity: 0.7; background: transparent;"
        )

    def _update_preview_info(self) -> None:
        """Update right-panel info labels."""
        gray = self._current_gray
        mix_fn = COLOR_GRAY_MIX[self._current_color]
        r, g, b = mix_fn(gray)

        self._preview_gray_label.setText(str(gray))
        self._info_pos.setText(f"位置: <b>({self._sb_offset_x.value()}, {self._sb_offset_y.value()})</b>")
        self._info_gray.setText(f"灰阶: <b>{gray}</b>")
        self._info_size.setText(f"尺寸: <b>{self._sb_width.value()}×{self._sb_height.value()}</b>")
        self._info_rgb.setText(f"RGB: <b>{r}, {g}, {b}</b>")

    # ── Button handlers ──────────────────────────────────────────────────────

    def _on_start_clicked(self) -> None:
        start = self._sb_start_gray.value()
        end   = self._sb_end_gray.value()
        if start > end:
            QMessageBox.warning(self, "参数错误", "开始灰阶不能大于结束灰阶")
            return

        params = {
            "offset_x":   self._sb_offset_x.value(),
            "offset_y":   self._sb_offset_y.value(),
            "width":      self._sb_width.value(),
            "height":     self._sb_height.value(),
            "start_gray": start,
            "end_gray":   end,
            "color":      self._get_color_code(),
            "color_name": self._current_color,
        }
        self.controller.start(
            params,
            display_window=self.display_window,
            csv_exporter=self.csv_exporter,
        )

    def _get_color_code(self) -> str:
        return {"white": "W", "red": "R", "green": "G", "blue": "B"}.get(self._current_color, "W")

    def _on_abort_clicked(self) -> None:
        self.controller.abort()

    # ── Controller signal handlers ──────────────────────────────────────────

    def _on_state_changed(self, state_name: str) -> None:
        state = State[state_name]

        badge = self._status_badge
        badge.setProperty("class", "")
        if state == State.IDLE:
            badge.setText("就绪")
            self._set_controls_enabled(True)
            self._btn_abort.setEnabled(False)
            self._btn_start.setEnabled(True)
        elif state in (State.SCANNING, State.CONNECTING, State.CALIBRATING,
                        State.MEASURING, State.ABORTING, State.EXPORTING):
            badge.setText("测量中")
            badge.setProperty("class", "measuring")
            self._set_controls_enabled(False)
            self._btn_abort.setEnabled(state in (State.MEASURING, State.ABORTING))
            self._btn_start.setEnabled(False)
        elif state == State.ERROR:
            badge.setText("错误")
            badge.setProperty("class", "error")
            self._set_controls_enabled(True)
            self._btn_abort.setEnabled(False)
            self._btn_start.setEnabled(True)

        badge.style().unpolish(badge)
        badge.style().polish(badge)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for sb in (self._sb_offset_x, self._sb_offset_y,
                   self._sb_width,   self._sb_height,
                   self._sb_start_gray, self._sb_end_gray):
            sb.setEnabled(enabled)
        for radio in self._color_radios.values():
            radio.setEnabled(enabled)

    def _on_log_message(self, msg: str) -> None:
        self._append_log(msg, "info")

    def _append_log(self, msg: str, level: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        color_map = {
            "info":    "palette(window-text)",
            "success": "#4CAF50" if self._is_dark else "#388E3C",
            "error":   "#F44336" if self._is_dark else "#D32F2F",
            "warning": "#FF9800" if self._is_dark else "#F57C00",
            "measure": "#6C7EE1" if self._is_dark else "#4A56E2",
        }
        color = color_map.get(level, "palette(window-text)")
        self._log_area.append(
            f'<span style="color:#6B6B80">[{ts}]</span> '
            f'<span style="color:{color}">{msg}</span>'
        )
        cursor = self._log_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._log_area.setTextCursor(cursor)

        # Update log count
        line_count = self._log_area.document().blockCount()
        self._log_count.setText(f"{line_count} 条")

    def _on_data_ready(self, record: dict) -> None:
        """Update latest measurement data display."""
        x = record.get("x", "--")
        y = record.get("y", "--")
        lv = record.get("Lv", "--")
        for key, val in [("x 坐标", x), ("y 坐标", y), ("亮度 Lv", lv)]:
            lbl = self.findChild(QLabel, f"data_{key}")
            if lbl:
                lbl.setText(str(val) if val else "--")

        # Also update preview color for the measured gray
        gray = record.get("gray", self._current_gray)
        self._current_gray = gray
        self._update_preview_color()
        self._update_preview_info()

    def _on_progress_updated(self, current: int, total: int) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self._progress_bar.setValue(pct)
        self._progress_label.setText(f"进度: {pct}% ({current}/{total})")

    def _on_finished(self, message: str) -> None:
        if message.startswith("ERROR:"):
            QMessageBox.critical(self, "测量错误", message[6:])
        elif message == "CSV export cancelled":
            self._append_log("CSV 导出已取消", "warning")
        else:
            QMessageBox.information(
                self,
                "测量完成",
                f"测量完成，CSV 已保存：\n{message}"
            )
        self._append_log(f"[完成] {message}", "success")

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self.display_window.stop()
        event.accept()
