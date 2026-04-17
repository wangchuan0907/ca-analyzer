"""
CA-410 Colorimeter - DearPyGui UI
Main entry point using GPU-accelerated DearPyGui instead of tkinter.
Display window still uses pygame (runs in its own thread).
"""

import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dearpygui.dearpygui as dpg
from datetime import datetime
from typing import Optional, Tuple

# ── Single-instance detection (Windows) ─────────────────────────────────────

if sys.platform == "win32":
    try:
        import win32event
        import win32api
        import winerror

        _mutex_name = "ca-analyzer-dpg-single-instance"
        _mutex = win32event.CreateMutex(None, False, _mutex_name)
        _last_error = win32api.GetLastError()
        if _last_error == winerror.ERROR_ALREADY_EXISTS:
            print("软件已启动，请勿重复打开。")
            sys.exit(1)
    except ImportError:
        pass

# ── Color / Gray mix helpers ──────────────────────────────────────────────────

COLOR_ORDER = ["white", "red", "green", "blue"]
COLOR_NAMES_SHORT = {"white": "白", "red": "红", "green": "绿", "blue": "蓝"}

COLOR_GRAY_MIX = {
    "white": lambda g: (g, g, g),
    "red":   lambda g: (g, 0, 0),
    "green": lambda g: (0, g, 0),
    "blue":  lambda g: (0, 0, g),
}

STATE_NAMES = {
    "IDLE":        "就绪",
    "SCANNING":    "扫描中",
    "CONNECTING":  "连接中",
    "CALIBRATING": "校准中",
    "MEASURING":   "测量中",
    "ABORTING":    "中止中",
    "EXPORTING":   "导出中",
    "ERROR":       "错误",
}


def brightness(r: int, g: int, b: int) -> float:
    return (r * 299 + g * 587 + b * 114) / 1000


# ── App State ─────────────────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.offset_x = 0
        self.offset_y = 0
        self.width = 512
        self.height = 512
        self.start_gray = 0
        self.end_gray = 255
        self.current_color = "white"
        self.current_gray = 255
        self.is_dark = True

        # Subsystems (lazy init)
        self._display_window = None
        self._controller = None
        self._csv_exporter = None

        # Log
        self.log_lines: list[str] = []

    def _get_rgb(self) -> Tuple[int, int, int]:
        mix_fn = COLOR_GRAY_MIX[self.current_color]
        return mix_fn(self.current_gray)

    # ── Subsystem init ────────────────────────────────────────────────────────

    def init_subsystems(self) -> None:
        try:
            from src.display_window import DisplayWindow
            self._display_window = DisplayWindow("打屏窗口")
            self._display_window.start()
            self._update_display_window()
        except Exception as e:
            print(f"[警告] 打屏窗口初始化失败: {e}")

        try:
            from src.csv_exporter import CSVExporter
            self._csv_exporter = CSVExporter()
        except Exception as e:
            print(f"[警告] CSV导出器初始化失败: {e}")

        try:
            from src.measurement_controller import MeasurementController
            self._controller = MeasurementController()
            self._controller.on_state_changed     = self._on_state_changed
            self._controller.on_log_message        = self._on_log_message
            self._controller.on_data_ready         = self._on_data_ready
            self._controller.on_progress_updated   = self._on_progress_updated
            self._controller.on_finished            = self._on_finished
        except Exception as e:
            print(f"[警告] 测量控制器初始化失败: {e}")

    def _update_display_window(self) -> None:
        if not self._display_window:
            return
        r, g, b = self._get_rgb()
        self._display_window.set_color(r, g, b)
        self._display_window.set_size(self.width, self.height)
        self._display_window.set_position(self.offset_x, self.offset_y)

    # ── UI Update callbacks ───────────────────────────────────────────────────

    def _on_state_changed(self, state_name: str) -> None:
        display_name = STATE_NAMES.get(state_name, state_name)
        dpg.set_value("lbl_status", f"状态: {display_name}")

        if state_name in ("MEASURING", "SCANNING", "CONNECTING", "CALIBRATING", "EXPORTING"):
            dpg.configure_item("lbl_status", color=(255, 200, 80))
        elif state_name == "ERROR":
            dpg.configure_item("lbl_status", color=(255, 80, 80))
        elif state_name == "IDLE":
            dpg.configure_item("lbl_status", color=(200, 255, 200))
        else:
            dpg.configure_item("lbl_status", color=(255, 220, 120))

        busy = state_name not in ("IDLE", "ERROR")
        dpg.configure_item("btn_start", show=not busy)
        dpg.configure_item("btn_abort", show=busy)
        for tag in ["spin_x", "spin_y", "spin_w", "spin_h", "spin_start", "spin_end"]:
            dpg.configure_item(tag, enabled=not busy)

    def _on_log_message(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        if len(self.log_lines) > 500:
            self.log_lines = self.log_lines[-500:]
        dpg.set_value("log_area", "\n".join(self.log_lines))
        dpg.set_y_scroll("log_area", dpg.get_y_scroll_max("log_area"))

    def _on_data_ready(self, record: dict) -> None:
        self.current_gray = record.get('灰阶值', self.current_gray)
        x_val = record.get('x')
        y_val = record.get('y')
        lv_val = record.get('亮度Lv')
        if x_val is not None:
            dpg.set_value("lbl_xdata", f"{x_val:.4f}")
        if y_val is not None:
            dpg.set_value("lbl_ydata", f"{y_val:.4f}")
        if lv_val is not None:
            dpg.set_value("lbl_lvdata", f"{lv_val:.4f}")
        if x_val is not None and y_val is not None and lv_val is not None:
            dpg.set_value("lbl_latest", f"最新: x={x_val:.4f} y={y_val:.4f} Lv={lv_val:.2f}")
        self._update_preview()

    def _on_progress_updated(self, current: int, total: int) -> None:
        pct = current / total if total > 0 else 0.0
        dpg.set_value("progress_bar", pct)
        pct_int = int(pct * 100)
        dpg.set_value("lbl_progress", f"进度: {pct_int}% ({current}/{total})")

    def _on_finished(self, message: str) -> None:
        if message.startswith("ERROR:"):
            dpg.configure_item("btn_start", show=True)
            dpg.configure_item("btn_abort", show=False)
            dpg.show_item("error_dialog")
        elif message == "CSV export cancelled":
            dpg.configure_item("btn_start", show=True)
            dpg.configure_item("btn_abort", show=False)
            dpg.show_item("cancel_dialog")
        else:
            dpg.configure_item("btn_start", show=True)
            dpg.configure_item("btn_abort", show=False)
            dpg.show_item("success_dialog")

    def _update_preview(self) -> None:
        r, g, b = self._get_rgb()
        gray = self.current_gray

        # Update preview rectangle
        dpg.configure_item("preview_rect", fill=[r, g, b])

        # Update text (delete and recreate since draw_text doesn't support configure text)
        if dpg.does_item_exist("preview_text"):
            dpg.delete_item("preview_text")
        text_color = [26, 26, 46] if brightness(r, g, b) > 128 else [220, 220, 220]
        dpg.draw_text([120, 75], str(gray), size=24, color=text_color,
                      parent="preview_drawlist", tag="preview_text")

        # Update info labels
        dpg.set_value("lbl_preview_gray", str(gray))
        dpg.set_value("lbl_info_pos",  f"位置: X={self.offset_x}, Y={self.offset_y}")
        dpg.set_value("lbl_info_size", f"尺寸: {self.width}×{self.height}")
        dpg.set_value("lbl_info_rgb",  f"RGB: ({r},{g},{b})")
        dpg.set_value("lbl_info_gray", f"灰阶: {gray}")


# ── Global state ──────────────────────────────────────────────────────────────

state = AppState()


# ── DPG Callbacks ─────────────────────────────────────────────────────────────

def on_offset_changed(sender, app_data):
    if sender == "spin_x":
        state.offset_x = app_data
    elif sender == "spin_y":
        state.offset_y = app_data
    elif sender == "spin_w":
        state.width = max(1, app_data)
    elif sender == "spin_h":
        state.height = max(1, app_data)
    state._update_display_window()
    state._update_preview()


def on_gray_changed(sender, app_data):
    if sender == "spin_start":
        state.start_gray = app_data
    elif sender == "spin_end":
        state.end_gray = app_data


def on_color_changed(sender, app_data):
    state.current_color = app_data
    state._update_display_window()
    state._update_preview()


def on_start(sender, app_data):
    if state.start_gray > state.end_gray:
        dpg.show_item("param_error_dialog")
        return

    color_key_map = {"white": "W", "red": "R", "green": "G", "blue": "B"}
    color_name_map = {"white": "白", "red": "红", "green": "绿", "blue": "蓝"}

    params = {
        "offset_x":   state.offset_x,
        "offset_y":   state.offset_y,
        "width":      state.width,
        "height":     state.height,
        "start_gray": state.start_gray,
        "end_gray":   state.end_gray,
        "color":      color_key_map.get(state.current_color, "W"),
        "color_name": color_name_map.get(state.current_color, "白"),
    }
    dpg.configure_item("btn_start", show=False)
    dpg.configure_item("btn_abort", show=True)
    for tag in ["spin_x", "spin_y", "spin_w", "spin_h", "spin_start", "spin_end"]:
        dpg.configure_item(tag, enabled=False)
    state._controller.start(params, state._display_window, state._csv_exporter)


def on_abort(sender, app_data):
    state._controller.abort()


def on_close():
    if state._display_window:
        state._display_window.stop()
    dpg.stop_dearpygui()


def on_theme_toggle(sender, app_data):
    state.is_dark = not state.is_dark
    if state.is_dark:
        dpg.bind_theme("dark_theme")
        dpg.configure_item("btn_theme", label="☀️")
    else:
        dpg.bind_theme("light_theme")
        dpg.configure_item("btn_theme", label="🌙")


# ── Themes ───────────────────────────────────────────────────────────────────

def setup_themes():
    # Dark theme (deep blue + orange)
    with dpg.theme(tag="dark_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,         (30, 91, 158))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,         (26, 74, 130))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,         (26, 74, 130))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,  (40, 107, 174))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,  (50, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_Button,         (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,  (255, 183, 77))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,    (230, 130, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Text,             (255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,     (128, 160, 192))
            dpg.add_theme_color(dpg.mvThemeCol_Header,          (40, 107, 174))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,  (50, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,    (60, 130, 200))
            dpg.add_theme_color(dpg.mvThemeCol_Tab,             (30, 91, 158))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,      (40, 107, 174))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,       (50, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,         (20, 60, 120))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,   (30, 91, 158))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    (26, 74, 130))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,   (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (255, 183, 77))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (230, 130, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Separator,       (50, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_Border,          (50, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        (26, 74, 130))
            dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg,  (40, 107, 174))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,       (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,      (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (230, 130, 0))

    # Light theme (light blue + orange)
    with dpg.theme(tag="light_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,         (232, 244, 253))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,         (245, 250, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,          (220, 235, 250))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,  (200, 220, 245))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,   (180, 210, 240))
            dpg.add_theme_color(dpg.mvThemeCol_Button,          (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,   (255, 183, 77))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,    (230, 130, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Text,             (26, 26, 46))
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,    (100, 130, 160))
            dpg.add_theme_color(dpg.mvThemeCol_Header,          (200, 220, 245))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,   (180, 210, 240))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,    (160, 200, 230))
            dpg.add_theme_color(dpg.mvThemeCol_Tab,             (220, 235, 250))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,      (200, 220, 245))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,       (180, 210, 240))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,         (200, 220, 245))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,   (220, 235, 250))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,    (220, 235, 250))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,   (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, (255, 183, 77))
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, (230, 130, 0))
            dpg.add_theme_color(dpg.mvThemeCol_Separator,      (176, 208, 240))
            dpg.add_theme_color(dpg.mvThemeCol_Border,         (176, 208, 240))
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,        (245, 250, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TextSelectedBg, (180, 210, 240))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,       (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,     (255, 152, 0))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (230, 130, 0))


# ── Build UI ──────────────────────────────────────────────────────────────────

def build_ui():
    WIN_W, WIN_H = 1024, 768

    dpg.create_context()
    dpg.create_viewport(
        title="CA-410测量Gamma色坐标",
        width=WIN_W,
        height=WIN_H,
        decorated=True,
        resizable=True,
        min_width=WIN_W,
        min_height=WIN_H,
    )

    setup_themes()
    dpg.bind_theme("dark_theme")

    # ── Main window ─────────────────────────────────────────────────────────
    with dpg.window(tag="main_window", label="CA-410测量Gamma色坐标",
                    width=WIN_W, height=WIN_H,
                    no_resize=True, no_close=False):

        # ── Header ─────────────────────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("CA-410 色度分析仪", color=(255, 255, 255))
            dpg.add_text("  Gamma & Chromaticity Analyzer", color=(128, 160, 192))
            dpg.add_spacer(width=20)
            dpg.add_button(label="☀️", callback=on_theme_toggle, tag="btn_theme",
                           width=40, height=40)

        dpg.add_separator()

        # ── Two-column layout ─────────────────────────────────────────────
        with dpg.group(horizontal=True):

            # ── LEFT PANEL ────────────────────────────────────────────────
            with dpg.child_window(width=430, height=WIN_H - 120, autosize_x=False):

                # Section: 坐标参数
                dpg.add_text("📌 坐标参数", color=(255, 152, 0))
                dpg.add_spacer(height=4)
                with dpg.group(horizontal=True):
                    dpg.add_text("X")
                    dpg.add_input_int(tag="spin_x", default_value=0,
                                      min_value=0, max_value=9999,
                                      width=100, callback=on_offset_changed,
                                      on_enter=True)
                    dpg.add_text("  Y")
                    dpg.add_input_int(tag="spin_y", default_value=0,
                                      min_value=0, max_value=9999,
                                      width=100, callback=on_offset_changed,
                                      on_enter=True)

                with dpg.group(horizontal=True):
                    dpg.add_text("宽")
                    dpg.add_input_int(tag="spin_w", default_value=512,
                                      min_value=1, max_value=9999,
                                      width=100, callback=on_offset_changed,
                                      on_enter=True)
                    dpg.add_text("  高")
                    dpg.add_input_int(tag="spin_h", default_value=512,
                                      min_value=1, max_value=9999,
                                      width=100, callback=on_offset_changed,
                                      on_enter=True)

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # Section: 灰阶参数
                dpg.add_text("📌 灰阶参数", color=(255, 152, 0))
                dpg.add_spacer(height=4)
                with dpg.group(horizontal=True):
                    dpg.add_text("开始")
                    dpg.add_input_int(tag="spin_start", default_value=0,
                                      min_value=0, max_value=255,
                                      width=100, callback=on_gray_changed,
                                      on_enter=True)
                    dpg.add_text("  结束")
                    dpg.add_input_int(tag="spin_end", default_value=255,
                                      min_value=0, max_value=255,
                                      width=100, callback=on_gray_changed,
                                      on_enter=True)

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # Section: 颜色选择
                dpg.add_text("📌 颜色选择", color=(255, 152, 0))
                dpg.add_spacer(height=4)

                # Use simple button group for color selection
                with dpg.group(horizontal=True):
                    for color_key in COLOR_ORDER:
                        color_rgb = COLOR_GRAY_MIX[color_key](128)
                        dpg.add_button(
                            label=f"● {COLOR_NAMES_SHORT[color_key]}",
                            callback=lambda s, a, ck=color_key: on_color_changed(None, ck),
                            tag=f"btn_color_{color_key}",
                            width=90, height=30,
                            small=True,
                        )

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # Buttons
                with dpg.group(horizontal=True):
                    dpg.add_button(label="▶  开始测量",
                                   callback=on_start,
                                   tag="btn_start",
                                   width=180, height=40)
                    dpg.add_spacer(width=10)
                    dpg.add_button(label="■  中止",
                                   callback=on_abort,
                                   tag="btn_abort",
                                   width=180, height=40,
                                   show=False)

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # Status section
                dpg.add_text("状态: 就绪", tag="lbl_status", color=(200, 255, 200))
                dpg.add_spacer(height=4)
                dpg.add_progress_bar(default_value=0.0, tag="progress_bar",
                                     width=-1, height=12)
                dpg.add_text("进度: 0% (0/256)", tag="lbl_progress",
                             color=(128, 160, 192))

                # Data display
                with dpg.group(horizontal=True):
                    dpg.add_text("x: ", color=(128, 160, 192))
                    dpg.add_text("--", tag="lbl_xdata", color=(255, 255, 255))
                    dpg.add_text("  y: ", color=(128, 160, 192))
                    dpg.add_text("--", tag="lbl_ydata", color=(255, 255, 255))
                    dpg.add_text("  Lv: ", color=(128, 160, 192))
                    dpg.add_text("--", tag="lbl_lvdata", color=(255, 255, 255))

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # Log section
                dpg.add_text("📋 日志", color=(255, 152, 0))
                dpg.add_spacer(height=4)
                dpg.add_input_text(
                    tag="log_area",
                    multiline=True,
                    readonly=True,
                    height=180,
                    width=-1,
                    default_value="[系统] 系统就绪\n",
                    tracked=False,
                )

            # Vertical spacer between panels
            dpg.add_spacer(width=4)

            # ── RIGHT PANEL ────────────────────────────────────────────────
            with dpg.child_window(width=-1, height=WIN_H - 120, autosize_x=False):

                # Header
                dpg.add_text("🖥️  打屏预览窗口", color=(255, 255, 255))
                dpg.add_spacer(width=5)
                dpg.add_text("Always on Top", color=(128, 160, 192))

                dpg.add_spacer(height=8)

                # Preview color block (drawlist)
                dpg.add_drawlist(width=320, height=180, tag="preview_drawlist")
                dpg.draw_rectangle([0, 0], [320, 180], color=[60, 60, 60],
                                   fill=[255, 255, 255], parent="preview_drawlist",
                                   tag="preview_rect")
                dpg.draw_text([120, 75], "255", size=24, color=[26, 26, 46],
                              parent="preview_drawlist", tag="preview_text")

                dpg.add_spacer(height=4)
                dpg.add_text("255", tag="lbl_preview_gray",
                             color=(255, 255, 255))

                dpg.add_spacer(height=8)

                # Info grid
                dpg.add_text("位置: X=0, Y=0",   tag="lbl_info_pos",  color=(200, 220, 240))
                dpg.add_text("尺寸: 512×512",     tag="lbl_info_size", color=(200, 220, 240))
                dpg.add_text("灰阶: 255",         tag="lbl_info_gray", color=(200, 220, 240))
                dpg.add_text("RGB: (255,255,255)", tag="lbl_info_rgb", color=(200, 220, 240))

                dpg.add_spacer(height=8)
                dpg.add_separator()
                dpg.add_spacer(height=8)

                # Latest data
                dpg.add_text("最新: x=-- y=-- Lv=--", tag="lbl_latest", color=(255, 152, 0))

    # ── Dialogs ─────────────────────────────────────────────────────────────

    # Param error
    with dpg.window(tag="param_error_dialog", modal=True, no_move=True,
                    width=320, height=120, no_resize=True,
                    label="参数错误"):
        dpg.add_text("开始灰阶不能大于结束灰阶", wrap=300)
        dpg.add_spacer(height=10)
        dpg.add_button(label="确定",
                       callback=lambda s, a: dpg.hide_item("param_error_dialog"),
                       width=100, pos=[110, 85])

    # Success
    with dpg.window(tag="success_dialog", modal=True, no_move=True,
                    width=420, height=150, no_resize=True,
                    label="测量完成"):
        dpg.add_text("测量完成，CSV 已保存", wrap=400)
        dpg.add_spacer(height=10)
        dpg.add_button(label="确定",
                       callback=lambda s, a: dpg.hide_item("success_dialog"),
                       width=100, pos=[160, 115])

    # Error
    with dpg.window(tag="error_dialog", modal=True, no_move=True,
                    width=420, height=150, no_resize=True,
                    label="测量错误"):
        dpg.add_text("测量过程中发生错误", wrap=400, color=(255, 80, 80))
        dpg.add_spacer(height=10)
        dpg.add_button(label="确定",
                       callback=lambda s, a: dpg.hide_item("error_dialog"),
                       width=100, pos=[160, 115])

    # Cancel
    with dpg.window(tag="cancel_dialog", modal=True, no_move=True,
                    width=400, height=130, no_resize=True,
                    label="已取消"):
        dpg.add_text("CSV 导出已取消", wrap=380)
        dpg.add_spacer(height=10)
        dpg.add_button(label="确定",
                       callback=lambda s, a: dpg.hide_item("cancel_dialog"),
                       width=100, pos=[150, 95])



# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        build_ui()
        state.init_subsystems()
        state._update_preview()
        dpg.setup_dearpygui()
        if not dpg.is_viewport_ok():
            print("[错误] 无法创建窗口，请确保在有图形界面的环境中运行")
            dpg.destroy_context()
            return
        dpg.show_viewport()
        dpg.start_dearpygui()
    except Exception as e:
        print(f"[错误] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            if state._display_window:
                state._display_window.stop()
        except Exception:
            pass
        try:
            dpg.destroy_context()
        except Exception:
            pass


if __name__ == "__main__":
    main()
