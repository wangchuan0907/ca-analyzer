"""
ca-analyzer — M5 色度仪测试模块 (Tkinter + Pygame)
Main UI: tkinter (Python built-in) — avoids pygame multi-window conflict.
Display window: pygame (independent thread).
"""

import sys
import os

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
            try:
                import tkinter as tk
                import tkinter.messagebox as mb
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                mb.showwarning("提示", "软件已启动，请勿重复打开。")
                root.destroy()
            except Exception:
                pass
            sys.exit(1)
    except ImportError:
        pass

# ── App entry ─────────────────────────────────────────────────────────────────

def main() -> None:
    # Set Windows DPI awareness BEFORE tkinter root is created
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    import tkinter as tk
    root = tk.Tk()
    app = App(root)
    root.mainloop()


# ═══════════════════════════════════════════════════════════════════════════════
# TKINTER UI IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk
import math
from datetime import datetime
from typing import Optional, Callable, List, Tuple, Any
from functools import partial

# ── Theme colors ──────────────────────────────────────────────────────────────

DARK_THEME = {
    'bg':        "#1E5B9E",   # 深蓝色背景
    'surface':   "#1A4A82",   # 略深的面板背景
    'border':    "#2A6AB0",
    'accent':    "#FF9800",   # 橙色（启用按钮高亮）
    'accent_h':  "#FFB74D",
    'text':      "#FFFFFF",   # 白色字体
    'text_sec':  "#C0D8F0",
    'text_plh':  "#8AACCC",
    'success':   "#4CAF50",
    'error':     "#F44336",
    'warning':   "#FF9800",   # 橙色
    'divider':   "#2A6AB0",
    'log_bg':    "#164A80",
    'disabled':  "#4A7AAA",
    'disabled_tx':"#8AACCC",
    'progress_bg':"#1A4A82",
    'canvas_border': "#2A6AB0",
}

LIGHT_THEME = {
    'bg':        "#E8F4FD",   # 浅蓝色背景
    'surface':   "#FFFFFF",
    'border':    "#B0D0F0",
    'accent':    "#FF9800",   # 橙色（启用按钮高亮）
    'accent_h':  "#FFB74D",
    'text':      "#1A1A2E",
    'text_sec':  "#507090",
    'text_plh':  "#90B0C8",
    'success':   "#388E3C",
    'error':     "#D32F2F",
    'warning':   "#FF9800",
    'divider':   "#C0D8F0",
    'log_bg':    "#D8EAFC",
    'disabled':  "#C0D0D8",
    'disabled_tx':"#909090",
    'progress_bg':"#D0E0F0",
    'canvas_border': "#B0D0F0",
}

# ── Layout constants ──────────────────────────────────────────────────────────

WIN_W, WIN_H = 1024, 768
LEFT_W = 440
DIVIDER_X = LEFT_W
PAD = 16

# Color definitions
COLOR_MAP = [
    ("white", "白色", (255, 255, 255)),
    ("red",   "红色", (255,  60,  60)),
    ("green", "绿色", ( 60, 220,  60)),
    ("blue",  "蓝色", ( 60, 120, 255)),
]

FONT_NAME = "Microsoft YaHei UI"
FONT_MISC = "Arial"


# ── Helper: rgb tuple to hex string ───────────────────────────────────────────

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def brightness(r: int, g: int, b: int) -> float:
    return (r * 299 + g * 587 + b * 114) / 1000


# ── Custom ttk styles ─────────────────────────────────────────────────────────

def apply_ttk_theme(is_dark: bool, root: tk.Tk) -> None:
    theme = DARK_THEME if is_dark else LIGHT_THEME
    style = ttk.Style(root)

    # Try to load a modern theme, fall back to default
    available = style.theme_names()
    if 'clam' in available:
        style.theme_use('clam')
    elif 'vista' in available and sys.platform == 'win32':
        style.theme_use('vista')
    elif 'default' in available:
        style.theme_use('default')

    # Configure ttk elements
    bg = theme['bg']
    surface = theme['surface']
    accent = theme['accent']
    text = theme['text']
    text_sec = theme['text_sec']
    border = theme['border']

    style.configure('TFrame', background=bg)
    style.configure('Surface.TFrame', background=surface)
    style.configure('TLabel', background=bg, foreground=text, font=(FONT_NAME, 11))
    style.configure('Surface.TLabel', background=surface, foreground=text, font=(FONT_NAME, 11))
    style.configure('Accent.TLabel', background=bg, foreground=accent, font=(FONT_NAME, 12, 'bold'))
    style.configure('Sec.TLabel', background=bg, foreground=text_sec, font=(FONT_NAME, 10))
    style.configure('Big.TLabel', background=surface, foreground=text, font=(FONT_NAME, 14, 'bold'))

    style.configure('TButton', font=(FONT_NAME, 12, 'bold'), padding=(10, 6))
    style.map('Primary.TButton',
              background=[('active', theme['accent_h']), ('!active', accent)],
              foreground=[('active', text), ('!active', text)])
    style.configure('Primary.TButton', background=accent, foreground=text,
                    font=(FONT_NAME, 13, 'bold'), padding=(12, 8))
    style.configure('Danger.TButton', background=theme['error'], foreground=text,
                    font=(FONT_NAME, 13, 'bold'), padding=(12, 8))
    style.configure('TSpinbox', fieldbackground=surface, foreground=text,
                    insertcolor=text, bordercolor=border, darkcolor=surface,
                    lightcolor=surface, borderwidth=0, arrowsize=14)
    style.configure('TRadiobutton', background=surface, foreground=text,
                    indicatorcolor=accent, font=(FONT_NAME, 11))

    style.configure('Horizontal.TProgressbar', thickness=8, background=accent,
                    troughcolor=theme['progress_bg'])


# ── Main Application ──────────────────────────────────────────────────────────

class App:
    """Main tkinter application."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.is_dark = True
        self.theme = DARK_THEME.copy()

        # Measurement state
        self.meas_state = "IDLE"
        self.progress_val = 0
        self.progress_total = 256
        self.last_record: Optional[dict] = None

        # Parameters
        self.offset_x = 0
        self.offset_y = 0
        self.width = 512
        self.height = 512
        self.start_gray = 0
        self.end_gray = 255
        self.current_color = "white"
        self.current_gray = 255

        self._color_mix = {
            "white": lambda g: (g, g, g),
            "red":   lambda g: (g, 0, 0),
            "green": lambda g: (0, g, 0),
            "blue":  lambda g: (0, 0, g),
        }

        # Sub-systems (lazy init)
        self._display_window = None
        self._controller = None
        self._csv_exporter = None
        self._log_lines: List[str] = []

        # Build UI
        self._build_ui()
        self._center_window()

        # Init subsystems
        self._init_subsystems()

        # Bind close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initial preview
        self._update_preview_color()
        self._update_preview_info()
        self._log("系统就绪")
        self._log("参数已加载，默认显示白色 255 灰阶")

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.root
        root.title("CA-410测量Gamma色坐标")
        root.geometry(f"{WIN_W}x{WIN_H}")
        root.minsize(WIN_W, WIN_H)
        root.resizable(True, True)

        t = self.theme
        root.configure(bg=t['bg'])

        # Icon (if exists)
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "logo.ico")
        if os.path.exists(icon_path):
            try:
                root.iconbitmap(icon_path)
            except Exception:
                pass

        # ── Top-level: left + divider + right ─────────────────────────────
        self._main_frame = tk.Frame(root, bg=t['bg'], width=WIN_W, height=WIN_H)
        self._main_frame.pack(fill='both', expand=True)
        self._main_frame.pack_propagate(False)

        # Left panel
        self._left_frame = tk.Frame(self._main_frame, bg=t['surface'], width=LEFT_W)
        self._left_frame.pack(side='left', fill='both')
        self._left_frame.pack_propagate(False)

        # Divider
        self._divider = tk.Frame(self._main_frame, bg=t['divider'], width=2)
        self._divider.pack(side='left', fill='both')

        # Right panel
        self._right_frame = tk.Frame(self._main_frame, bg=t['bg'])
        self._right_frame.pack(side='left', fill='both', expand=True)

        # Build left panel sections
        self._build_header()
        self._build_params_section()
        self._build_gray_section()
        self._build_color_section()
        self._build_buttons_section()
        self._build_status_section()
        self._build_log_section()

        # Build right panel
        self._build_preview_section()

        # Apply ttk theme
        apply_ttk_theme(self.is_dark, root)

    def _build_header(self) -> None:
        t = self.theme
        frm = self._left_frame

        header = tk.Frame(frm, bg=t['surface'], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        # Title
        self._lbl_title = tk.Label(header, text="CA-410测量Gamma色坐标",
                                   font=(FONT_NAME, 14, 'bold'),
                                   bg=t['surface'], fg=t['text'])
        self._lbl_title.pack(side='left', padx=PAD, pady=10)

        # Subtitle
        self._lbl_sub = tk.Label(header, text="Gamma & Chromaticity Analyzer",
                                 font=(FONT_NAME, 9),
                                 bg=t['surface'], fg=t['text_sec'])
        self._lbl_sub.pack(side='left', padx=4, pady=14)

        # Theme toggle button
        self._btn_theme = tk.Button(header, text="浅色", font=(FONT_NAME, 10),
                                    bg=t['surface'], fg=t['text'],
                                    relief='flat', bd=0,
                                    activebackground=t['accent'],
                                    command=self._toggle_theme,
                                    cursor='hand2', padx=8, width=5)
        self._btn_theme.pack(side='right', padx=PAD, pady=8)

        # Bottom border
        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x')

    def _build_params_section(self) -> None:
        t = self.theme
        frm = self._left_frame

        sec = tk.Frame(frm, bg=t['surface'])
        sec.pack(fill='x', padx=PAD, pady=(10, 0))

        tk.Label(sec, text="📌 坐标参数", font=(FONT_NAME, 11, 'bold'),
                 bg=t['surface'], fg=t['accent']).pack(anchor='w', pady=(4, 6))

        # X, Y row
        row = tk.Frame(sec, bg=t['surface'])
        row.pack(fill='x')

        self._lbl_x = tk.Label(row, text="X", font=(FONT_NAME, 10),
                                bg=t['surface'], fg=t['text_sec'], width=8, anchor='w')
        self._lbl_x.pack(side='left')
        self._spin_x = self._make_spinbox(row, 0, 0, 9999, width=8)
        self._spin_x.pack(side='left', padx=(0, PAD))

        self._lbl_y = tk.Label(row, text="Y", font=(FONT_NAME, 10),
                                bg=t['surface'], fg=t['text_sec'], width=8, anchor='w')
        self._lbl_y.pack(side='left')
        self._spin_y = self._make_spinbox(row, 0, 0, 9999, width=8)
        self._spin_y.pack(side='left')

        row.pack(pady=(0, 4))

        # Width, Height row
        row2 = tk.Frame(sec, bg=t['surface'])
        row2.pack(fill='x')

        tk.Label(row2, text="宽度", font=(FONT_NAME, 10),
                 bg=t['surface'], fg=t['text_sec'], width=8, anchor='w').pack(side='left')
        self._spin_w = self._make_spinbox(row2, 512, 1, 9999, width=8)
        self._spin_w.pack(side='left', padx=(0, PAD))

        tk.Label(row2, text="高度", font=(FONT_NAME, 10),
                 bg=t['surface'], fg=t['text_sec'], width=8, anchor='w').pack(side='left')
        self._spin_h = self._make_spinbox(row2, 512, 1, 9999, width=8)
        self._spin_h.pack(side='left')

        row2.pack(pady=(0, 4))

        # Wire spinbox changes
        for sb, key in [(self._spin_x, 'x'), (self._spin_y, 'y'),
                        (self._spin_w, 'w'), (self._spin_h, 'h')]:
            sb.bind('<<Increment>>', lambda e, k=key: self._on_spin_changed(k))
            sb.bind('<<Decrement>>', lambda e, k=key: self._on_spin_changed(k))
            sb.bind('<FocusOut>', lambda e, k=key: self._on_spin_changed(k))
            sb.bind('<Return>', lambda e, k=key: self._on_spin_changed(k))

        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x', padx=PAD)

    def _make_spinbox(self, parent, default: int, minv: int, maxv: int,
                      width: int = 8) -> ttk.Spinbox:
        sb = ttk.Spinbox(parent, from_=minv, to=maxv,
                         increment=1, justify='center',
                         font=(FONT_NAME, 12),
                         width=width)
        sb.set(default)
        return sb

    def _build_gray_section(self) -> None:
        t = self.theme
        frm = self._left_frame

        sec = tk.Frame(frm, bg=t['surface'])
        sec.pack(fill='x', padx=PAD, pady=(8, 0))

        tk.Label(sec, text="📌 灰阶参数", font=(FONT_NAME, 11, 'bold'),
                 bg=t['surface'], fg=t['accent']).pack(anchor='w', pady=(4, 6))

        row = tk.Frame(sec, bg=t['surface'])
        row.pack(fill='x')

        tk.Label(row, text="开始", font=(FONT_NAME, 10),
                 bg=t['surface'], fg=t['text_sec'], width=8, anchor='w').pack(side='left')
        self._spin_start = self._make_spinbox(row, 0, 0, 255, width=8)
        self._spin_start.pack(side='left', padx=(0, PAD))

        tk.Label(row, text="结束", font=(FONT_NAME, 10),
                 bg=t['surface'], fg=t['text_sec'], width=8, anchor='w').pack(side='left')
        self._spin_end = self._make_spinbox(row, 255, 0, 255, width=8)
        self._spin_end.pack(side='left')

        row.pack(pady=(0, 4))

        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x', padx=PAD)

    def _build_color_section(self) -> None:
        t = self.theme
        frm = self._left_frame

        sec = tk.Frame(frm, bg=t['surface'])
        sec.pack(fill='x', padx=PAD, pady=(8, 0))

        tk.Label(sec, text="📌 颜色选择", font=(FONT_NAME, 11, 'bold'),
                 bg=t['surface'], fg=t['accent']).pack(anchor='w', pady=(4, 6))

        self._color_var = tk.StringVar(value="white")

        color_frame = tk.Frame(sec, bg=t['surface'])
        color_frame.pack(fill='x')

        n = len(COLOR_MAP)
        cell_w = (LEFT_W - PAD * 2) // n

        for key, name, color_rgb in COLOR_MAP:
            cell = tk.Frame(color_frame, bg=t['surface'], width=cell_w)
            cell.pack(side='left')
            cell.pack_propagate(False)

            rb = tk.Radiobutton(cell, text=name, variable=self._color_var,
                                value=key, font=(FONT_NAME, 11),
                                bg=t['surface'], fg=t['text'],
                                activebackground=t['surface'],
                                activeforeground=t['accent'],
                                selectcolor=t['surface'],
                                indicatoron=True,
                                command=partial(self._on_color_changed, key))
            rb.pack(pady=(0, 2))

            # Color swatch circle (using a canvas)
            sw = tk.Canvas(cell, width=40, height=40,
                           bg=t['surface'], highlightthickness=0)
            sw.create_oval(4, 4, 36, 36, fill=rgb_to_hex(*color_rgb),
                           outline=t['accent'], width=2)
            sw.pack(pady=(0, 4))

        # Ensure white is pre-selected
        self._color_var.set("white")

        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x', padx=PAD)

    def _build_buttons_section(self) -> None:
        t = self.theme
        frm = self._left_frame

        btn_row = tk.Frame(frm, bg=t['surface'], height=60)
        btn_row.pack(fill='x', padx=PAD, pady=(8, 4))
        btn_row.pack_propagate(False)

        btn_inner = tk.Frame(btn_row, bg=t['surface'])
        btn_inner.pack(expand=True)

        self._btn_start = tk.Button(btn_inner, text="▶  开始测量",
                                    font=(FONT_NAME, 13, 'bold'),
                                    bg=t['accent'], fg='white',
                                    relief='flat', cursor='hand2',
                                    command=self._on_start_clicked,
                                    padx=16, pady=6)
        self._btn_start.pack(side='left', padx=(0, 8))

        self._btn_abort = tk.Button(btn_inner, text="■  中止",
                                   font=(FONT_NAME, 13, 'bold'),
                                   bg=t['error'], fg='white',
                                   relief='flat', cursor='hand2',
                                   state='disabled',
                                   command=self._on_abort_clicked,
                                   padx=16, pady=6)
        self._btn_abort.pack(side='left')

        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x', padx=PAD)

    def _build_status_section(self) -> None:
        t = self.theme
        frm = self._left_frame

        sec = tk.Frame(frm, bg=t['surface'])
        sec.pack(fill='x', padx=PAD, pady=(6, 0))

        # Status label + badge
        status_row = tk.Frame(sec, bg=t['surface'])
        status_row.pack(fill='x')

        tk.Label(status_row, text="状态", font=(FONT_NAME, 11, 'bold'),
                 bg=t['surface'], fg=t['accent']).pack(side='left')

        self._lbl_status = tk.Label(status_row, text="就绪", font=(FONT_NAME, 11, 'bold'),
                                     bg=t['success'], fg='white',
                                     padx=10, pady=2)
        self._lbl_status.pack(side='right')

        status_row.pack(pady=(4, 4))

        # Progress bar
        self._progress = ttk.Progressbar(sec, orient='horizontal',
                                          length=LEFT_W - PAD * 2,
                                          mode='determinate', maximum=100)
        self._progress.pack(pady=(0, 4))

        # Progress text
        self._lbl_progress = tk.Label(sec, text="进度: 0% (0/256)",
                                      font=(FONT_NAME, 10),
                                      bg=t['surface'], fg=t['text_sec'], anchor='w')
        self._lbl_progress.pack(fill='x', pady=(0, 6))

        # Data display (x, y, Lv)
        data_row = tk.Frame(sec, bg=t['surface'])
        data_row.pack(fill='x', pady=(0, 6))

        self._lbl_xdata = self._data_label(data_row, "x 坐标", "--")
        self._lbl_xdata.pack(side='left', padx=(0, 6))
        self._lbl_ydata = self._data_label(data_row, "y 坐标", "--")
        self._lbl_ydata.pack(side='left', padx=(0, 6))
        self._lbl_lvdata = self._data_label(data_row, "亮度 Lv", "--")
        self._lbl_lvdata.pack(side='left')

        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x', padx=PAD)

    def _data_label(self, parent, label: str, value: str) -> tk.Label:
        t = self.theme
        frm = tk.Frame(parent, bg=t['surface'], relief='solid', bd=1)
        frm.pack(side='left', padx=(0, 6))

        tk.Label(frm, text=label, font=(FONT_NAME, 9),
                 bg=t['surface'], fg=t['text_sec']).pack(padx=8, pady=(2, 0))
        lbl = tk.Label(frm, text=value, font=(FONT_NAME, 13, 'bold'),
                       bg=t['surface'], fg=t['text'])
        lbl.pack(padx=8, pady=(0, 2))
        return lbl

    def _build_log_section(self) -> None:
        t = self.theme
        frm = self._left_frame

        sec = tk.Frame(frm, bg=t['surface'])
        sec.pack(fill='both', expand=True, padx=PAD, pady=(6, PAD))

        tk.Label(sec, text="📋 日志", font=(FONT_NAME, 11, 'bold'),
                 bg=t['surface'], fg=t['accent']).pack(anchor='w', pady=(0, 4))

        self._log_count_lbl = tk.Label(sec, text="0 条", font=(FONT_NAME, 9),
                                        bg=t['surface'], fg=t['text_sec'])
        self._log_count_lbl.pack(anchor='e', pady=(0, 2))

        log_win = tk.Frame(sec, bg=t['log_bg'], relief='solid', bd=1)
        log_win.pack(fill='both', expand=True)

        scroll_y = ttk.Scrollbar(log_win, orient='vertical')
        scroll_x = ttk.Scrollbar(log_win, orient='horizontal')
        self._log_text = tk.Text(log_win, font=(FONT_NAME, 10),
                                  bg=t['log_bg'], fg=t['text_sec'],
                                  relief='flat', bd=0,
                                  state='disabled', wrap='none',
                                  yscrollcommand=scroll_y.set,
                                  xscrollcommand=scroll_x.set,
                                  insertbackground=t['text'])
        self._log_text.pack(fill='both', expand=True, padx=4, pady=4)
        scroll_y.config(command=self._log_text.yview)
        scroll_y.pack(side='right', fill='y')
        scroll_x.config(command=self._log_text.xview)
        scroll_x.pack(side='bottom', fill='x')

        # Tag colors
        self._log_text.tag_configure('info', foreground=t['text_sec'])
        self._log_text.tag_configure('success', foreground=t['success'])
        self._log_text.tag_configure('error', foreground=t['error'])
        self._log_text.tag_configure('warning', foreground=t['warning'])
        self._log_text.tag_configure('step', foreground=t['accent'])

    def _build_preview_section(self) -> None:
        t = self.theme
        frm = self._right_frame

        # Header
        header = tk.Frame(frm, bg=t['surface'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="🖥️  打屏预览窗口",
                 font=(FONT_NAME, 13, 'bold'),
                 bg=t['surface'], fg=t['text']).pack(side='left', padx=PAD, pady=10)

        # AOT badge
        aot = tk.Label(header, text="Always on Top",
                        font=(FONT_NAME, 9),
                        bg=t['surface'], fg=t['text_sec'], padx=8, pady=2,
                        relief='solid', bd=1)
        aot.pack(side='right', padx=PAD, pady=10)

        sep = tk.Frame(frm, bg=t['divider'], height=1)
        sep.pack(fill='x')

        # Preview area
        preview_area = tk.Frame(frm, bg=t['bg'])
        preview_area.pack(fill='both', expand=True, padx=PAD, pady=PAD)

        # Color preview canvas
        self._preview_canvas = tk.Canvas(preview_area, width=320, height=180,
                                          bg='#FFFFFF', highlightbackground=t['canvas_border'],
                                          highlightthickness=2, relief='flat')
        self._preview_canvas.pack(pady=(0, 8))

        # Preview gray big text
        self._lbl_preview_gray = tk.Label(preview_area, text="255",
                                          font=(FONT_NAME, 28, 'bold'),
                                          bg=t['bg'], fg=t['text'])
        self._lbl_preview_gray.pack()

        # Preview info grid
        info_frame = tk.Frame(preview_area, bg=t['bg'])
        info_frame.pack(pady=(8, 0))

        self._lbl_pos = tk.Label(info_frame, text="位置: X=0, Y=0",
                                  font=(FONT_NAME, 11),
                                  bg=t['bg'], fg=t['text_sec'], anchor='w', width=22)
        self._lbl_pos.grid(row=0, column=0, padx=4, sticky='w')

        self._lbl_gray = tk.Label(info_frame, text="灰阶: 255",
                                   font=(FONT_NAME, 11),
                                   bg=t['bg'], fg=t['text_sec'], anchor='w', width=18)
        self._lbl_gray.grid(row=0, column=1, padx=4, sticky='w')

        self._lbl_size = tk.Label(info_frame, text="尺寸: 512×512",
                                   font=(FONT_NAME, 11),
                                   bg=t['bg'], fg=t['text_sec'], anchor='w', width=22)
        self._lbl_size.grid(row=1, column=0, padx=4, sticky='w', pady=(4, 0))

        self._lbl_rgb = tk.Label(info_frame, text="RGB: (255,255,255)",
                                  font=(FONT_NAME, 11),
                                  bg=t['bg'], fg=t['text_sec'], anchor='w', width=18)
        self._lbl_rgb.grid(row=1, column=1, padx=4, sticky='w', pady=(4, 0))

    # ── Subsystems ────────────────────────────────────────────────────────────

    def _init_subsystems(self) -> None:
        # Display window (pygame-based, runs in its own thread)
        try:
            from src.display_window import DisplayWindow
            self._display_window = DisplayWindow("打屏窗口")
            self._display_window.start()
            self._update_display_window()
        except Exception as e:
            self._log(f"[警告] 打屏窗口初始化失败: {e}")

        # CSV exporter (tkinter-based)
        try:
            from src.csv_exporter import CSVExporter
            self._csv_exporter = CSVExporter()
        except Exception as e:
            self._log(f"[警告] CSV导出器初始化失败: {e}")

        # Controller (threading-based)
        try:
            from src.measurement_controller import MeasurementController
            self._controller = MeasurementController()
            self._controller.on_state_changed   = self._on_state_changed
            self._controller.on_log_message    = self._on_log_message
            self._controller.on_data_ready     = self._on_data_ready
            self._controller.on_progress_updated = self._on_progress_updated
            self._controller.on_finished        = self._on_finished
        except Exception as e:
            self._log(f"[警告] 测量控制器初始化失败: {e}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center_window(self) -> None:
        try:
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = (sw - WIN_W) // 2
            y = (sh - WIN_H) // 2
            self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")
        except Exception:
            pass

    def _get_current_color_rgb(self) -> Tuple[int, int, int]:
        gray = self.current_gray
        return self._color_mix[self.current_color](gray)

    def _rgb_text_color(self, r: int, g: int, b: int) -> str:
        return "#1E1E2E" if brightness(r, g, b) > 128 else "#FFFFFF"

    def _on_spin_changed(self, key: str) -> None:
        try:
            if key == 'x':
                self.offset_x = int(self._spin_x.get())
            elif key == 'y':
                self.offset_y = int(self._spin_y.get())
            elif key == 'w':
                self.width = max(1, int(self._spin_w.get()))
            elif key == 'h':
                self.height = max(1, int(self._spin_h.get()))
        except ValueError:
            pass
        self._update_display_window()
        self._update_preview_info()

    def _on_color_changed(self, key: str) -> None:
        self.current_color = key
        self._update_display_window()
        self._update_preview_color()
        self._update_preview_info()

    def _update_display_window(self) -> None:
        if not self._display_window:
            return
        gray = self.current_gray
        mix_fn = self._color_mix[self.current_color]
        r, g, b = mix_fn(gray)
        self._display_window.set_color(r, g, b)
        self._display_window.set_size(self.width, self.height)
        self._display_window.set_position(self.offset_x, self.offset_y)

    def _update_preview_color(self) -> None:
        r, g, b = self._get_current_color_rgb()
        hex_color = rgb_to_hex(r, g, b)
        self._preview_canvas.configure(bg=hex_color)
        # Redraw swatch (canvas needs to be updated)
        self._preview_canvas.delete('all')
        self._preview_canvas.create_rectangle(0, 0, 320, 180, fill=hex_color, outline='')
        self._preview_canvas.create_text(160, 90, text=str(self.current_gray),
                                          font=(FONT_NAME, 28, 'bold'),
                                          fill=self._rgb_text_color(r, g, b))

    def _update_preview_info(self) -> None:
        gray = self.current_gray
        r, g, b = self._get_current_color_rgb()

        self._lbl_preview_gray.configure(text=str(gray))
        self._lbl_pos.configure(text=f"位置: X={self.offset_x}, Y={self.offset_y}")
        self._lbl_gray.configure(text=f"灰阶: {gray}")
        self._lbl_size.configure(text=f"尺寸: {self.width}×{self.height}")
        self._lbl_rgb.configure(text=f"RGB: ({r},{g},{b})")

    def _log(self, msg: str, level: str = 'info') -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self._log_lines.append((line, level))
        # Update log text widget
        self._log_text.configure(state='normal')
        tag = level if level in ('success', 'error', 'warning', 'step') else 'info'
        self._log_text.insert('end', line + '\n', tag)
        self._log_text.see('end')
        self._log_text.configure(state='disabled')
        self._log_count_lbl.configure(text=f"{len(self._log_lines)} 条")

    # ── Controls enable/disable ─────────────────────────────────────────────

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = 'normal' if enabled else 'disabled'
        for sb in [self._spin_x, self._spin_y, self._spin_w, self._spin_h,
                   self._spin_start, self._spin_end]:
            sb.configure(state=state)
        self._btn_start.configure(state='disabled' if not enabled else 'normal',
                                   bg=self.theme['accent'])
        self._btn_abort.configure(state='normal' if not enabled else 'disabled',
                                   bg=self.theme['error'])
        # Also update radio buttons
        for child in self._left_frame.winfo_children():
            self._recursive_disable(child, not enabled)

    def _recursive_disable(self, widget, disable: bool) -> None:
        try:
            if isinstance(widget, tk.Radiobutton):
                if disable:
                    widget.configure(state='disabled')
                else:
                    widget.configure(state='normal')
        except Exception:
            pass
        for child in getattr(widget, 'winfo_children', lambda: [])():
            self._recursive_disable(child, disable)

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        self.is_dark = not self.is_dark
        self.theme = DARK_THEME.copy() if self.is_dark else LIGHT_THEME.copy()
        t = self.theme

        # Update root and all frames
        self.root.configure(bg=t['bg'])
        self._main_frame.configure(bg=t['bg'])
        self._left_frame.configure(bg=t['surface'])
        self._divider.configure(bg=t['divider'])
        self._right_frame.configure(bg=t['bg'])
        self._btn_theme.configure(text="深色" if self.is_dark else "浅色",
                                   bg=t['surface'], fg=t['text'], width=5)

        # Rebuild all sections with new theme colors
        self._rebuild_surface_widgets()
        self._rebuild_preview_section()
        apply_ttk_theme(self.is_dark, self.root)

    def _rebuild_surface_widgets(self) -> None:
        """Reconfigure all widgets that use surface/bg colors after theme change."""
        t = self.theme

        def recolor_widget(w):
            try:
                cur_bg = str(w.cget('bg')) if hasattr(w, 'cget') else ''
                if cur_bg in (DARK_THEME.get('surface', ''), LIGHT_THEME.get('surface', '')):
                    w.configure(bg=t['surface'])
                elif cur_bg in (DARK_THEME.get('bg', ''), LIGHT_THEME.get('bg', '')):
                    w.configure(bg=t['bg'])
            except Exception:
                pass
            for child in getattr(w, 'winfo_children', lambda: [])():
                recolor_widget(child)

        recolor_widget(self._left_frame)

        # Update log
        self._log_text.configure(bg=t['log_bg'], fg=t['text_sec'])
        self._log_text.tag_configure('info', foreground=t['text_sec'])
        self._log_text.tag_configure('success', foreground=t['success'])
        self._log_text.tag_configure('error', foreground=t['error'])
        self._log_text.tag_configure('warning', foreground=t['warning'])
        self._log_text.tag_configure('step', foreground=t['accent'])

    def _rebuild_preview_section(self) -> None:
        t = self.theme
        self._preview_canvas.configure(highlightbackground=t['canvas_border'])
        self._lbl_preview_gray.configure(bg=t['bg'], fg=t['text'])
        for lbl in [self._lbl_pos, self._lbl_gray, self._lbl_size, self._lbl_rgb]:
            lbl.configure(bg=t['bg'], fg=t['text_sec'])

    # ── Button actions ──────────────────────────────────────────────────────

    def _on_start_clicked(self) -> None:
        try:
            start = int(self._spin_start.get())
            end   = int(self._spin_end.get())
        except ValueError:
            self._log("[错误] 灰阶参数无效", 'error')
            return

        if start > end:
            self._log("[错误] 开始灰阶不能大于结束灰阶", 'error')
            return

        if not self._controller:
            self._log("[错误] 测量控制器未初始化", 'error')
            return

        color_key_map = {"white": "W", "red": "R", "green": "G", "blue": "B"}
        color_name_map = {"white": "白", "red": "红", "green": "绿", "blue": "蓝"}

        params = {
            "offset_x":   self.offset_x,
            "offset_y":   self.offset_y,
            "width":      self.width,
            "height":     self.height,
            "start_gray": start,
            "end_gray":   end,
            "color":      color_key_map.get(self.current_color, "W"),
            "color_name": color_name_map.get(self.current_color, "白"),
        }
        self._controller.start(params, self._display_window, self._csv_exporter)

    def _on_abort_clicked(self) -> None:
        if self._controller:
            self._controller.abort()

    # ── Controller callbacks ─────────────────────────────────────────────────

    def _on_state_changed(self, state_name: str) -> None:
        self.meas_state = state_name
        badge_map = {
            "IDLE":        ("就绪", self.theme['success']),
            "SCANNING":    ("扫描中", self.theme['warning']),
            "CONNECTING":  ("连接中", self.theme['warning']),
            "CALIBRATING": ("校准中", self.theme['warning']),
            "MEASURING":   ("测量中", self.theme['warning']),
            "ABORTING":    ("中止中", self.theme['warning']),
            "EXPORTING":   ("导出中", self.theme['warning']),
            "ERROR":       ("错误", self.theme['error']),
        }
        text, color = badge_map.get(state_name, (state_name, self.theme['warning']))
        self._lbl_status.configure(text=text, bg=color)

        is_busy = state_name not in ("IDLE", "ERROR")
        self._set_controls_enabled(not is_busy)

    def _on_log_message(self, msg: str) -> None:
        level = 'info'
        if '错误' in msg or 'ERROR' in msg:
            level = 'error'
        elif '完成' in msg:
            level = 'success'
        elif '中止' in msg:
            level = 'warning'
        elif '[Step' in msg or '测量' in msg or '正在' in msg:
            level = 'step'
        self._log(msg, level)

    def _on_data_ready(self, record: dict) -> None:
        self.last_record = record
        gray = record.get('灰阶值', self.current_gray)
        self.current_gray = gray
        x_val = record.get('x')
        y_val = record.get('y')
        lv_val = record.get('亮度Lv')
        if x_val is not None:
            self._lbl_xdata.configure(text=f"{x_val:.4f}")
        if y_val is not None:
            self._lbl_ydata.configure(text=f"{y_val:.4f}")
        if lv_val is not None:
            self._lbl_lvdata.configure(text=f"{lv_val:.4f}")
        # Update preview with current gray
        self._update_preview_color()
        self._update_preview_info()

    def _on_progress_updated(self, current: int, total: int) -> None:
        self.progress_total = total
        pct = int(current / total * 100) if total > 0 else 0
        self._progress.configure(value=pct)
        self._lbl_progress.configure(text=f"进度: {pct}% ({current}/{total})")

    def _on_finished(self, message: str) -> None:
        if message.startswith("ERROR:"):
            err_msg = message[6:]
            self._log(f"[错误] {err_msg}", 'error')
            # 弹窗告知用户
            try:
                import tkinter.messagebox as mb
                mb.showerror("测量错误", err_msg)
            except Exception:
                pass
        elif message == "CSV export cancelled":
            self._log("CSV 导出已取消", 'warning')
            try:
                import tkinter.messagebox as mb
                mb.showwarning("已取消", "CSV 导出已取消")
            except Exception:
                pass
        else:
            self._log(f"[完成] CSV 已保存: {message}", 'success')
            try:
                import tkinter.messagebox as mb
                mb.showinfo("测量完成", f"CSV 已保存:\n{message}")
            except Exception:
                pass

    # ── Close ────────────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        if self._display_window:
            self._display_window.stop()
        self.root.destroy()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
