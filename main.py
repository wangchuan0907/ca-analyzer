"""
ca-analyzer — M5 色度仪测试模块 (Pure Pygame)
Program entry point — no PySide6 dependency.
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
            # Show a simple tkinter message box since we don't have PySide6
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
    import pygame
    pygame.init()

    app = PygameApp()
    app.run()

    pygame.quit()


# ═══════════════════════════════════════════════════════════════════════════════
# PUREPYGAME UI IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

import pygame
import math
from datetime import datetime
from typing import Optional, Callable, List, Tuple, Any

# ── Theme colors ──────────────────────────────────────────────────────────────

class Theme:
    DARK = dict(
        bg              = (30,  30,  46 ),
        surface         = (45,  45,  68 ),
        border          = (61,  61,  92 ),
        accent          = (108, 126, 225),
        accent_hover    = (124, 142, 241),
        accent_pressed  = (94,  116, 201),
        text            = (255, 255, 255),
        text_sec        = (160, 160, 184),
        text_placeholder= (107, 107, 128),
        success         = (76,  175, 80 ),
        error           = (244, 67,  54 ),
        warning         = (255, 152,  0 ),
        divider         = (42,  42,  62 ),
        log_bg          = (22,  22,  42 ),
        btn_disabled    = (61,  61,  92 ),
        btn_disabled_txt= (120, 120, 140),
        progress_bg     = (45,  45,  68 ),
        status_ready_bg = (76,  175, 80 ),
        status_busy_bg  = (255, 152,  0 ),
        status_err_bg   = (244, 67,  54 ),
    )
    LIGHT = dict(
        bg              = (245, 245, 247),
        surface         = (255, 255, 255),
        border          = (224, 224, 232),
        accent          = (74,  86,  226),
        accent_hover    = (90,  102, 242),
        accent_pressed  = (64,  76,  206),
        text            = (26,  26,  46 ),
        text_sec        = (107, 107, 128),
        text_placeholder= (160, 160, 184),
        success         = (56,  142,  60),
        error           = (211, 47,   47),
        warning         = (245, 124,   0),
        divider         = (232, 232, 240),
        log_bg          = (235, 235, 240),
        btn_disabled    = (224, 224, 232),
        btn_disabled_txt= (160, 160, 180),
        progress_bg     = (224, 224, 232),
        status_ready_bg = (56,  142,  60),
        status_busy_bg  = (245, 124,   0),
        status_err_bg   = (211,  47,  47),
    )


# ── Layout constants ──────────────────────────────────────────────────────────

WIN_W, WIN_H = 1024, 768
LEFT_W = 460          # Control panel width
DIVIDER_X = LEFT_W
RIGHT_X = LEFT_W + 1

FONT_NAME = "Microsoft YaHei UI"
FONT_MISC = "Arial"

# Left panel sections
HEADER_H = 60
SECTION_START_Y = HEADER_H + 8
SECTION_GAP = 10
SECTION_PADDING = 16


# ── Helper drawing functions ──────────────────────────────────────────────────

def draw_rounded_rect(surf: pygame.Surface, rect: pygame.Rect,
                      color: Tuple[int, int, int], radius: int = 6) -> None:
    """Draw a filled rounded rectangle."""
    if radius <= 0:
        surf.fill(color, rect)
        return
    x, y, w, h = rect
    radius = min(radius, w // 2, h // 2)
    # Main rect
    surf.fill(color, (x + radius, y, w - radius * 2, h))
    surf.fill(color, (x, y + radius, w, h - radius * 2))
    # Corner circles
    for cx, cy in [(x + radius, y + radius),
                   (x + w - radius, y + radius),
                   (x + radius, y + h - radius),
                   (x + w - radius, y + h - radius)]:
        for dy in range(-radius + 1, radius):
            for dx in range(-radius + 1, radius):
                if dx * dx + dy * dy <= radius * radius:
                    px, py = cx + dx, cy + dy
                    if x <= px < x + w and y <= py < y + h:
                        surf.set_at((px, py), color)


def draw_rounded_rect_outline(surf: pygame.Surface, rect: pygame.Rect,
                              color: Tuple[int, int, int],
                              radius: int = 6, width: int = 1) -> None:
    """Draw a rounded rectangle outline."""
    x, y, w, h = rect
    radius = min(radius, w // 2, h // 2)
    if w <= 0 or h <= 0:
        return
    pts = []
    # Top-left arc
    for angle in range(90, 180):
        rad = math.radians(angle)
        pts.append((x + radius + math.cos(rad) * radius,
                    y + radius + math.sin(rad) * radius))
    # Top-right arc
    for angle in range(180, 270):
        rad = math.radians(angle)
        pts.append((x + w - radius + math.cos(rad) * radius,
                    y + radius + math.sin(rad) * radius))
    # Bottom-right arc
    for angle in range(270, 360):
        rad = math.radians(angle)
        pts.append((x + w - radius + math.cos(rad) * radius,
                    y + h - radius + math.sin(rad) * radius))
    # Bottom-left arc
    for angle in range(0, 90):
        rad = math.radians(angle)
        pts.append((x + radius + math.cos(rad) * radius,
                    y + h - radius + math.sin(rad) * radius))
    if len(pts) >= 2:
        pygame.draw.lines(surf, color, False, pts, width)


def get_font(size: int, bold: bool = False) -> pygame.Font:
    """Get a font, falling back to system defaults."""
    try:
        return pygame.font.SysFont(FONT_NAME, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


def render_text(text: str, font: pygame.Font,
                color: Tuple[int, int, int],
                antialias: bool = True) -> pygame.Surface:
    return font.render(text, antialias, color)


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL to RGB (h: 0-360, s,l: 0-1)."""
    if s == 0:
        v = round(l * 255)
        return (v, v, v)
    def hue2rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    r = hue2rgb(p, q, h / 360 + 1/3)
    g = hue2rgb(p, q, h / 360)
    b = hue2rgb(p, q, h / 360 - 1/3)
    return (round(r * 255), round(g * 255), round(b * 255))


# ── UI Widgets ─────────────────────────────────────────────────────────────────

class Widget:
    """Base widget class."""
    def __init__(self, rect: pygame.Rect):
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.disabled = False
        self._hovered = False

    def contains(self, x: int, y: int) -> bool:
        return self.rect.collidepoint(x, y)

    def update(self, events: list) -> None:
        pass

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        pass

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if event was consumed."""
        return False


class Label:
    """Simple text label."""
    def __init__(self, rect: pygame.Rect, text: str = "",
                 font_size: int = 13, color_key: str = "text",
                 align: str = "left", bold: bool = False,
                 bg_key: Optional[str] = None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font_size = font_size
        self.color_key = color_key
        self.align = align
        self.bold = bold
        self.bg_key = bg_key
        self._surf: Optional[pygame.Surface] = None

    def set_text(self, text: str) -> None:
        if self.text != text:
            self.text = text
            self._surf = None

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        if not self.visible:
            return
        if self.bg_key:
            surf.fill(theme[self.bg_key], self.rect)
        if not self.text:
            return
        font = get_font(self.font_size, self.bold)
        color = theme.get(self.color_key, theme['text'])
        lines = self.text.split('\n')
        line_h = font.get_height()
        total_h = line_h * len(lines)
        y_start = self.rect.y + (self.rect.height - total_h) // 2
        for i, line in enumerate(lines):
            ts = font.render(line, True, color)
            if self.align == "center":
                x = self.rect.x + (self.rect.width - ts.get_width()) // 2
            elif self.align == "right":
                x = self.rect.x + self.rect.width - ts.get_width()
            else:
                x = self.rect.x + 4
            surf.blit(ts, (x, y_start + i * line_h))


class SpinBox(Widget):
    """Integer spin box with +/- buttons."""

    def __init__(self, rect: pygame.Rect,
                 value: int = 0, min_val: int = 0, max_val: int = 9999,
                 step: int = 1, font_size: int = 13):
        super().__init__(rect)
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.font_size = font_size
        self._hovered = False
        self.focused = False

        btn_w = max(24, rect.height - 4)
        self._btn_minus = pygame.Rect(rect.x, rect.y, btn_w, rect.height)
        self._btn_plus  = pygame.Rect(rect.right - btn_w, rect.y, btn_w, rect.height)
        self._value_rect = pygame.Rect(
            self._btn_minus.right, rect.y,
            self._btn_plus.left - self._btn_minus.right, rect.height
        )
        self._drag_value: Optional[int] = None
        self._last_mouse_y: Optional[int] = None

    def set_value(self, v: int) -> None:
        self.value = max(self.min_val, min(self.max_val, v))

    def contains(self, x: int, y: int) -> bool:
        return self.rect.collidepoint(x, y)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.disabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if self._btn_minus.collidepoint(x, y):
                self.set_value(self.value - self.step)
                return True
            if self._btn_plus.collidepoint(x, y):
                self.set_value(self.value + self.step)
                return True
            if self.rect.collidepoint(x, y):
                self.focused = True
                # drag by mouse y
                if event.button == 1:
                    self._drag_value = self.value
                    self._last_mouse_y = y
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self._drag_value = None
            self._last_mouse_y = None
            self.focused = False
        elif event.type == pygame.MOUSEMOTION and self.focused:
            x, y = event.pos
            if self._last_mouse_y is not None and event.buttons[0]:
                dy = self._last_mouse_y - y
                if abs(dy) > 4:
                    delta = int(dy / 4) * self.step
                    self.set_value(self.value + delta)
                    self._last_mouse_y = y
                return True
        elif event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(event.pos):
            self.set_value(self.value + event.y * self.step)
            return True
        elif event.type == pygame.KEYDOWN and self.focused:
            if event.key in (pygame.K_UP, pygame.K_RIGHT):
                self.set_value(self.value + self.step)
                return True
            elif event.key in (pygame.K_DOWN, pygame.K_LEFT):
                self.set_value(self.value - self.step)
                return True
            elif event.key in (pygame.K_PAGEUP,):
                self.set_value(self.value + self.step * 10)
                return True
            elif event.key in (pygame.K_PAGEDOWN,):
                self.set_value(self.value - self.step * 10)
                return True
            elif event.key in (pygame.K_HOME,):
                self.set_value(self.max_val)
                return True
            elif event.key in (pygame.K_END,):
                self.set_value(self.min_val)
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self._drag_value = None
            self._last_mouse_y = None
            self.focused = False
        return False

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        if not self.visible:
            return
        bg = theme['bg']
        border = theme['border']
        accent = theme['accent']
        text_c = theme['text']
        sec_c  = theme['text_sec']

        # Background
        draw_rounded_rect(surf, self.rect, bg, radius=6)
        # Border
        draw_rounded_rect_outline(surf, self.rect,
                                  accent if self.focused else border,
                                  radius=6, width=1)

        # Value text
        font = get_font(self.font_size)
        val_str = str(self.value)
        ts = font.render(val_str, True, text_c if not self.disabled else sec_c)
        tx = self._value_rect.x + (self._value_rect.width - ts.get_width()) // 2
        ty = self._value_rect.y + (self._value_rect.height - ts.get_height()) // 2
        surf.blit(ts, (tx, ty))

        # Minus button
        btn_bg = theme['surface']
        mrect = self._btn_minus
        draw_rounded_rect(surf, mrect, btn_bg, radius=4)
        # Draw minus sign
        cx, cy = mrect.centerx, mrect.centery
        minus_color = theme['accent'] if not self.disabled else theme['btn_disabled_txt']
        pygame.draw.line(surf, minus_color, (cx - 4, cy), (cx + 4, cy), 2)

        # Plus button
        prect = self._btn_plus
        draw_rounded_rect(surf, prect, btn_bg, radius=4)
        cx, cy = prect.centerx, prect.centery
        plus_color = theme['accent'] if not self.disabled else theme['btn_disabled_txt']
        pygame.draw.line(surf, plus_color, (cx - 4, cy), (cx + 4, cy), 2)
        pygame.draw.line(surf, plus_color, (cx, cy - 4), (cx, cy + 4), 2)


class Button(Widget):
    """Push button widget."""

    def __init__(self, rect: pygame.Rect, text: str = "",
                 font_size: int = 14, bold: bool = True,
                 variant: str = "primary"):  # primary | danger | secondary
        super().__init__(rect)
        self.text = text
        self.font_size = font_size
        self.bold = bold
        self.variant = variant  # primary | danger | secondary
        self._pressed = False

    def set_text(self, text: str) -> None:
        self.text = text

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.disabled:
            return False
        mx, my = event.pos
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mx, my):
                self._pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self.rect.collidepoint(mx, my):
                return True
        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[0] and self._pressed:
                return True
        return False

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        if not self.visible:
            return
        if self.variant == "primary":
            bg = theme['accent']
        elif self.variant == "danger":
            bg = theme['error']
        else:
            bg = theme['surface']

        if self.disabled:
            bg = theme['btn_disabled']

        draw_rounded_rect(surf, self.rect, bg, radius=8)

        font = get_font(self.font_size, self.bold)
        ts = font.render(self.text, True,
                         theme['text'] if not self.disabled else theme['btn_disabled_txt'])
        tx = self.rect.x + (self.rect.width - ts.get_width()) // 2
        ty = self.rect.y + (self.rect.height - ts.get_height()) // 2
        surf.blit(ts, (tx, ty))


class ColorRadio(Widget):
    """Color selection radio button (white/red/green/blue)."""

    COLORS = [
        ("white", "白色", (255, 255, 255)),
        ("red",   "红色", (255,  60,  60)),
        ("green", "绿色", ( 60, 220,  60)),
        ("blue",  "蓝色", ( 60, 120, 255)),
    ]

    def __init__(self, rect: pygame.Rect,
                 on_change: Callable[[str], None]):
        super().__init__(rect)
        self.on_change = on_change
        self.selected: str = "white"
        self._hovered_key: Optional[str] = None

        n = len(self.COLORS)
        spacing = rect.width // n
        self._radios: List[pygame.Rect] = [
            pygame.Rect(rect.x + i * spacing, rect.y,
                        spacing - 4, rect.height)
            for i in range(n)
        ]
        self._swatch_size = 16
        self._swatch_radii = [
            pygame.Rect(r.x + (r.width - self._swatch_size) // 2,
                        r.y + (r.height - self._swatch_size) // 2,
                        self._swatch_size, self._swatch_size)
            for r in self._radios
        ]

    def set_selected(self, key: str) -> None:
        if self.selected != key:
            self.selected = key

    def contains(self, x: int, y: int) -> bool:
        return self.rect.collidepoint(x, y)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.disabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            for i, r in enumerate(self._radios):
                if r.collidepoint(x, y):
                    key = self.COLORS[i][0]
                    if key != self.selected:
                        self.selected = key
                        if self.on_change:
                            self.on_change(key)
                    return True
        return False

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        if not self.visible:
            return
        accent = theme['accent']
        text_c = theme['text']
        sec_c  = theme['text_sec']
        font = get_font(13)

        for i, (key, name, color) in enumerate(self.COLORS):
            r = self._radios[i]
            sw = self._swatch_radii[i]
            is_selected = (key == self.selected)

            # Background
            draw_rounded_rect(surf, r,
                              theme['surface'] if not self.disabled else theme['btn_disabled'],
                              radius=6)

            # Swatch circle
            circle_r = 8
            cx, cy = sw.centerx, sw.centery
            border_c = accent if is_selected else sec_c
            pygame.draw.circle(surf, border_c, (cx, cy), circle_r + 2)
            pygame.draw.circle(surf, color, (cx, cy), circle_r)

            # Label
            ts = font.render(name, True,
                             text_c if not self.disabled else sec_c)
            label_x = r.x + r.width // 2 - ts.get_width() // 2
            label_y = sw.bottom + 4
            if label_y + ts.get_height() <= r.bottom - 4:
                surf.blit(ts, (label_x, label_y))


class ThemeToggle(Widget):
    """Theme toggle button (sun/moon icon)."""

    def __init__(self, rect: pygame.Rect, is_dark: bool = True,
                 on_toggle: Callable[[bool], None] = None):
        super().__init__(rect)
        self.is_dark = is_dark
        self.on_toggle = on_toggle

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(*event.pos):
                self.is_dark = not self.is_dark
                if self.on_toggle:
                    self.on_toggle(self.is_dark)
                return True
        return False

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        if not self.visible:
            return
        # Icon button background
        draw_rounded_rect(surf, self.rect, (0, 0, 0, 0), radius=8)  # transparent-ish
        draw_rounded_rect_outline(surf, self.rect, theme['border'], radius=8, width=1)
        # Draw sun/moon symbol
        font = get_font(18)
        symbol = "☀️" if not self.is_dark else "🌙"
        ts = font.render(symbol, True, theme['text'])
        tx = self.rect.centerx - ts.get_width() // 2
        ty = self.rect.centery - ts.get_height() // 2
        surf.blit(ts, (tx, ty))


# ── Progress Bar widget ────────────────────────────────────────────────────────

class ProgressBar(Widget):
    def __init__(self, rect: pygame.Rect):
        super().__init__(rect)
        self.value = 0  # 0..100
        self._surf: Optional[pygame.Surface] = None

    def set_value(self, v: int) -> None:
        self.value = max(0, min(100, v))

    def draw(self, surf: pygame.Surface, theme: dict) -> None:
        if not self.visible:
            return
        bg_rect = pygame.Rect(self.rect.x, self.rect.y,
                              self.rect.width, self.rect.height)
        draw_rounded_rect(surf, bg_rect, theme['progress_bg'], radius=3)
        if self.value > 0:
            fill_w = int(self.rect.width * self.value / 100)
            if fill_w > 0:
                fill_rect = pygame.Rect(self.rect.x, self.rect.y,
                                        fill_w, self.rect.height)
                draw_rounded_rect(surf, fill_rect, theme['accent'], radius=3)


# ── Log Buffer ────────────────────────────────────────────────────────────────

class LogBuffer:
    def __init__(self, max_lines: int = 200):
        self.max_lines = max_lines
        self.lines: List[Tuple[str, str]] = []  # (timestamp, message)
        self._unread_count = 0

    def append(self, msg: str, level: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.lines.append((ts, msg))
        if len(self.lines) > self.max_lines:
            self.lines.pop(0)
        self._unread_count += 1

    def draw(self, surf: pygame.Surface, rect: pygame.Rect,
             theme: dict, font_size: int = 12) -> None:
        """Draw the log area."""
        # Background
        draw_rounded_rect(surf, rect, theme['log_bg'], radius=6)

        # Border
        draw_rounded_rect_outline(surf, rect, theme['border'], radius=6, width=1)

        font = get_font(font_size)
        line_h = font.get_height() + 2
        visible_lines = rect.height // line_h
        start_y = rect.bottom - line_h

        # Draw visible lines from end
        offset = len(self.lines) - visible_lines
        if offset < 0:
            offset = 0

        for i in range(visible_lines):
            idx = offset + i
            if idx >= len(self.lines):
                break
            ts, msg = self.lines[idx]
            y = start_y - (visible_lines - 1 - i) * line_h
            if y < rect.y:
                break
            # Timestamp
            ts_surf = font.render(f"[{ts}]", True, theme['text_placeholder'])
            surf.blit(ts_surf, (rect.x + 6, y))
            # Message — color by level
            color = theme['text_sec']
            if '错误' in msg or 'ERROR' in msg or '异常' in msg:
                color = theme['error']
            elif '完成' in msg or '成功' in msg or 'OK' in msg.upper():
                color = theme['success']
            elif '[中止' in msg or 'warning' in msg.lower():
                color = theme['warning']
            elif '[Step' in msg or '测量' in msg:
                color = theme['accent']

            msg_surf = font.render(msg[:80], True, color)
            surf.blit(msg_surf, (rect.x + 52, y))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

class PygameApp:
    """Main pygame application."""

    def __init__(self):
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("CA-410测量Gamma色坐标")
        self.clock = pygame.time.Clock()

        # State
        self.is_dark = True
        self.theme = Theme.DARK
        self.running = True

        # Measurement state
        self.meas_state = "IDLE"   # IDLE | SCANNING | CONNECTING | CALIBRATING | MEASURING | ABORTING | EXPORTING | ERROR
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
        self.current_gray = 255  # default preview gray

        # Color gray mix
        self._color_mix = {
            "white": lambda g: (g, g, g),
            "red":   lambda g: (g, 0, 0),
            "green": lambda g: (0, g, 0),
            "blue":  lambda g: (0, 0, g),
        }

        # Build widgets
        self._build_widgets()

        # Sub-systems
        self._display_window = None
        self._controller = None
        self._csv_exporter = None
        self._init_subsystems()

        # Log
        self.log = LogBuffer()
        self.log.append("系统就绪", "info")
        self.log.append("参数已加载，默认显示白色 255 灰阶", "info")

        # Focus tracking
        self._focused_widget: Optional[Widget] = None

        # Window position for centering
        self._center_window()

    def _center_window(self) -> None:
        """Center the window on screen."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            hwnd = pygame.display.get_wm_info()['window']
            user32.SetWindowPos(hwnd, 0,
                                 (sw - WIN_W) // 2, (sh - WIN_H) // 2,
                                 0, 0, 0x0001 | 0x0004)  # SWP_NOSIZE | SWP_NOZORDER
        except Exception:
            pass

    def _init_subsystems(self) -> None:
        """Initialize display window, controller, csv_exporter."""
        # Display window (pygame-based, runs in its own thread)
        try:
            from src.display_window import DisplayWindow
            self._display_window = DisplayWindow("打屏窗口")
            self._display_window.start()
            # Apply initial state
            self._update_display_window()
        except Exception as e:
            self.log.append(f"[警告] 打屏窗口初始化失败: {e}", "warning")
            self._display_window = None

        # CSV exporter (tkinter-based)
        try:
            from src.csv_exporter import CSVExporter
            self._csv_exporter = CSVExporter()
        except Exception as e:
            self.log.append(f"[警告] CSV导出器初始化失败: {e}", "warning")
            self._csv_exporter = None

        # Controller (threading-based)
        try:
            from src.measurement_controller import MeasurementController
            self._controller = MeasurementController()
            self._controller.on_state_changed = self._on_state_changed
            self._controller.on_log_message   = self._on_log_message
            self._controller.on_data_ready   = self._on_data_ready
            self._controller.on_progress_updated = self._on_progress_updated
            self._controller.on_finished     = self._on_finished
        except Exception as e:
            self.log.append(f"[警告] 测量控制器初始化失败: {e}", "warning")
            self._controller = None

    def _build_widgets(self) -> None:
        """Build all UI widgets."""
        self.widgets: List[Widget] = []

        # ── Header ──────────────────────────────────────────────────────────
        # Title
        self.lbl_title = Label(
            pygame.Rect(16, 16, 360, 28),
            "CA-410测量Gamma色坐标",
            font_size=15, color_key="text", bold=True
        )
        # Subtitle
        self.lbl_subtitle = Label(
            pygame.Rect(16, 38, 200, 16),
            "Gamma & Chromaticity Analyzer",
            font_size=10, color_key="text_sec"
        )
        # Theme toggle
        self.btn_theme = ThemeToggle(
            pygame.Rect(LEFT_W - 52, 14, 36, 36),
            is_dark=True,
            on_toggle=self._on_theme_toggled
        )
        self.widgets.append(self.btn_theme)

        # ── Section: 打屏参数 ───────────────────────────────────────────────
        sy = SECTION_START_Y

        # Section label
        self.lbl_sec1 = Label(
            pygame.Rect(SECTION_PADDING, sy, 120, 18),
            "📌 打屏参数",
            font_size=12, color_key="accent", bold=True
        )
        sy += 20

        def make_input(label_text: str, x: int, y: int,
                       default_val: int, min_v: int, max_v: int,
                       on_change: Callable) -> Tuple[Label, SpinBox]:
            lbl = Label(pygame.Rect(x, y, 50, 16),
                       label_text, font_size=11, color_key="text_sec")
            sb = SpinBox(pygame.Rect(x, y + 16, 190, 36),
                        value=default_val, min_val=min_v, max_val=max_v,
                        font_size=13)
            sb.on_change_handler = on_change
            self.widgets.append(sb)
            return lbl, sb

        row_gap = 58

        # Row 1: offset X, offset Y
        self.lbl_offx, self.sb_offset_x = make_input(
            "起始 X", SECTION_PADDING, sy, 0, 0, 9999,
            lambda v: self._on_offset_changed('x', v))
        self.lbl_offy, self.sb_offset_y = make_input(
            "起始 Y", SECTION_PADDING + 200, sy, 0, 0, 9999,
            lambda v: self._on_offset_changed('y', v))
        sy += row_gap

        # Row 2: width, height
        self.lbl_w, self.sb_width = make_input(
            "宽度", SECTION_PADDING, sy, 512, 1, 9999,
            self._on_display_params_changed)
        self.lbl_h, self.sb_height = make_input(
            "高度", SECTION_PADDING + 200, sy, 512, 1, 9999,
            self._on_display_params_changed)
        sy += row_gap + 6

        # ── Section: 灰阶参数 ───────────────────────────────────────────────
        self.lbl_sec2 = Label(
            pygame.Rect(SECTION_PADDING, sy, 120, 18),
            "📌 灰阶参数",
            font_size=12, color_key="accent", bold=True
        )
        sy += 20

        self.lbl_start_gray, self.sb_start_gray = make_input(
            "开始灰阶", SECTION_PADDING, sy, 0, 0, 255,
            lambda v: None)
        self.lbl_end_gray, self.sb_end_gray = make_input(
            "结束灰阶", SECTION_PADDING + 200, sy, 255, 0, 255,
            lambda v: None)
        sy += row_gap + 6

        # ── Section: 颜色选择 ───────────────────────────────────────────────
        self.lbl_sec3 = Label(
            pygame.Rect(SECTION_PADDING, sy, 120, 18),
            "📌 颜色选择",
            font_size=12, color_key="accent", bold=True
        )
        sy += 20

        self.color_radio = ColorRadio(
            pygame.Rect(SECTION_PADDING, sy, LEFT_W - SECTION_PADDING * 2, 56),
            on_change=self._on_color_changed
        )
        self.widgets.append(self.color_radio)
        sy += 60 + 10

        # ── Buttons ──────────────────────────────────────────────────────────
        self.btn_start = Button(
            pygame.Rect(SECTION_PADDING, sy, 196, 44),
            "▶  开始测量", font_size=14, variant="primary"
        )
        self.btn_abort = Button(
            pygame.Rect(SECTION_PADDING + 206, sy, 196, 44),
            "■  中止", font_size=14, variant="danger"
        )
        self.btn_abort.disabled = True
        self.widgets.append(self.btn_start)
        self.widgets.append(self.btn_abort)
        sy += 48 + 10

        # ── Status section ───────────────────────────────────────────────────
        self.lbl_status_title = Label(
            pygame.Rect(SECTION_PADDING, sy, 60, 18),
            "状态", font_size=12, color_key="accent", bold=True
        )
        self.lbl_status_badge = Label(
            pygame.Rect(LEFT_W - SECTION_PADDING - 60, sy, 60, 22),
            "就绪", font_size=11, bold=True
        )
        sy += 22 + 6

        self.progress_bar = ProgressBar(pygame.Rect(SECTION_PADDING, sy, LEFT_W - SECTION_PADDING * 2, 8))
        self.widgets.append(self.progress_bar)
        sy += 12 + 4

        self.lbl_progress = Label(
            pygame.Rect(SECTION_PADDING, sy, 300, 16),
            "进度: 0% (0/256)", font_size=12, color_key="text_sec"
        )
        sy += 20 + 4

        # Data display row
        self._data_labels: dict = {}
        data_items = [("x 坐标", "x"), ("y 坐标", "y"), ("亮度 Lv", "lv")]
        data_y = sy
        for label_text, key in data_items:
            lbl = Label(pygame.Rect(SECTION_PADDING, data_y, 136, 36),
                       "", font_size=13, bold=True)
            self._data_labels[key] = lbl
            self.widgets.append(lbl)
            SECTION_PADDING  # using existing
        sy += 40

        # ── Log section ───────────────────────────────────────────────────────
        log_y = sy + 4
        self.lbl_log_title = Label(
            pygame.Rect(SECTION_PADDING, log_y, 60, 18),
            "日志", font_size=12, color_key="accent", bold=True
        )
        self.lbl_log_count = Label(
            pygame.Rect(LEFT_W - SECTION_PADDING - 50, log_y, 50, 18),
            "0 条", font_size=11, color_key="text_sec", align="right"
        )
        log_y += 20
        self.log_rect = pygame.Rect(
            SECTION_PADDING, log_y,
            LEFT_W - SECTION_PADDING * 2,
            WIN_H - log_y - 8
        )

        # Right panel labels
        rx = RIGHT_X + 16
        rw = WIN_W - RIGHT_X - 16

        self.lbl_right_title = Label(
            pygame.Rect(rx, 12, rw, 28),
            "🖥️  打屏预览窗口",
            font_size=14, color_key="text", bold=True
        )
        self.lbl_aot_badge = Label(
            pygame.Rect(WIN_W - 16 - 90, 14, 90, 22),
            "Always on Top", font_size=10, color_key="text_sec",
            align="center",
            bg_key="surface"
        )

        # Preview color box (centered in right panel)
        preview_cx = RIGHT_X + (WIN_W - RIGHT_X) // 2
        preview_box_w, preview_box_h = 320, 200
        self.preview_rect = pygame.Rect(
            preview_cx - preview_box_w // 2, 60,
            preview_box_w, preview_box_h
        )

        # Preview info
        self.lbl_preview_gray = Label(
            pygame.Rect(preview_cx - 80, self.preview_rect.bottom + 8, 160, 30),
            "255", font_size=24, bold=True, align="center"
        )
        self.lbl_preview_size = Label(
            pygame.Rect(preview_cx - 80, self.preview_rect.bottom + 38, 160, 18),
            "512 × 512", font_size=12, color_key="text_sec", align="center"
        )

        # Info grid on right panel
        info_y = self.preview_rect.bottom + 68
        info_items = [
            ("位置", self._make_info_label(rx, info_y, rw // 2 - 4, "position")),
            ("灰阶", self._make_info_label(rx + rw // 2 + 4, info_y, rw // 2 - 8, "gray")),
            ("尺寸", self._make_info_label(rx, info_y + 40, rw // 2 - 4, "size")),
            ("RGB",  self._make_info_label(rx + rw // 2 + 4, info_y + 40, rw // 2 - 8, "rgb")),
        ]
        self._right_info: dict = {key: lbl for key, lbl in info_items}
        for _, lbl in info_items:
            self.widgets.append(lbl)

    def _make_info_label(self, x: int, y: int, w: int, key: str) -> Label:
        lbl = Label(pygame.Rect(x, y, w, 36), "",
                   font_size=12, bg_key="surface")
        return lbl

    def _on_theme_toggled(self, is_dark: bool) -> None:
        self.is_dark = is_dark
        self.theme = Theme.DARK if is_dark else Theme.LIGHT
        # Update theme toggle icon
        self._update_preview_color()

    def _on_offset_changed(self, axis: str, value: int) -> None:
        if axis == 'x':
            self.offset_x = value
        else:
            self.offset_y = value
        if self._display_window:
            self._display_window.set_position(self.offset_x, self.offset_y)
        self._update_preview_info()

    def _on_display_params_changed(self, value: int) -> None:
        self.width  = self.sb_width.value
        self.height = self.sb_height.value
        if self._display_window:
            self._display_window.set_size(self.width, self.height)
        self._update_preview_color()
        self._update_preview_info()

    def _on_color_changed(self, color_key: str) -> None:
        self.current_color = color_key
        self._update_display_window()
        self._update_preview_color()
        self._update_preview_info()

    def _update_display_window(self) -> None:
        """Update the display window color, size, and position."""
        if not self._display_window:
            return
        gray = self.current_gray
        mix_fn = self._color_mix[self.current_color]
        r, g, b = mix_fn(gray)
        self._display_window.set_color(r, g, b)
        self._display_window.set_size(self.width, self.height)
        self._display_window.set_position(self.offset_x, self.offset_y)

    def _update_preview_color(self) -> None:
        """Update the right-panel preview color (just redraw, actual color in draw)."""
        pass  # color computed in draw()

    def _update_preview_info(self) -> None:
        """Update right panel info labels."""
        gray = self.current_gray
        mix_fn = self._color_mix[self.current_color]
        r, g, b = mix_fn(gray)

        self.lbl_preview_gray.set_text(str(gray))
        self.lbl_preview_size.set_text(f"{self.width} × {self.height}")

        pos_text = f"位置: <b>({self.offset_x}, {self.offset_y})</b>"
        gray_text = f"灰阶: <b>{gray}</b>"
        size_text = f"尺寸: <b>{self.width}×{self.height}</b>"
        rgb_text = f"RGB: <b>{r}, {g}, {b}</b>"

        self._right_info["position"].set_text(pos_text)
        self._right_info["gray"].set_text(gray_text)
        self._right_info["size"].set_text(size_text)
        self._right_info["rgb"].set_text(rgb_text)

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable/disable controls during measurement."""
        for w in self.widgets:
            if not isinstance(w, (SpinBox, ColorRadio)):
                continue
            w.disabled = not enabled
        self.btn_start.disabled = enabled
        self.btn_abort.disabled = not enabled
        # Also disable spinboxes that aren't SpinBox class
        for w in self.widgets:
            if isinstance(w, SpinBox):
                w.disabled = not enabled

    # ── Button actions ────────────────────────────────────────────────────────

    def _on_start_clicked(self) -> None:
        start = self.sb_start_gray.value
        end   = self.sb_end_gray.value
        if start > end:
            self.log.append("[错误] 开始灰阶不能大于结束灰阶", "error")
            return

        if not self._controller:
            self.log.append("[错误] 测量控制器未初始化", "error")
            return

        params = {
            "offset_x":   self.offset_x,
            "offset_y":   self.offset_y,
            "width":      self.width,
            "height":     self.height,
            "start_gray": start,
            "end_gray":   end,
            "color":      {"white": "W", "red": "R", "green": "G", "blue": "B"}.get(self.current_color, "W"),
            "color_name": {"white": "白", "red": "红", "green": "绿", "blue": "蓝"}.get(self.current_color, "白"),
        }
        self._controller.start(params, self._display_window, self._csv_exporter)

    def _on_abort_clicked(self) -> None:
        if self._controller:
            self._controller.abort()

    # ── Controller callbacks ─────────────────────────────────────────────────

    def _on_state_changed(self, state_name: str) -> None:
        self.meas_state = state_name
        badge_text = {
            "IDLE":        "就绪",
            "SCANNING":    "扫描中",
            "CONNECTING":  "连接中",
            "CALIBRATING": "校准中",
            "MEASURING":   "测量中",
            "ABORTING":    "中止中",
            "EXPORTING":   "导出中",
            "ERROR":       "错误",
        }.get(state_name, state_name)

        self.lbl_status_badge.set_text(badge_text)

        is_busy = state_name not in ("IDLE", "ERROR")
        self._set_controls_enabled(not is_busy)

    def _on_log_message(self, msg: str) -> None:
        level = "info"
        if "错误" in msg or "ERROR" in msg:
            level = "error"
        elif "完成" in msg:
            level = "success"
        elif "中止" in msg:
            level = "warning"
        self.log.append(msg, level)
        self.lbl_log_count.set_text(f"{len(self.log.lines)} 条")

    def _on_data_ready(self, record: dict) -> None:
        self.last_record = record
        gray = record.get('灰阶值', self.current_gray)
        self.current_gray = gray
        # Update data display labels
        x_val = record.get('x', None)
        y_val = record.get('y', None)
        lv_val = record.get('亮度Lv', None)
        if x_val is not None:
            self._data_labels.get('x',  Label(pygame.Rect(0,0,0,0))).set_text(f"x 坐标: {x_val:.4f}")
        # Re-draw will be handled in main loop

    def _on_progress_updated(self, current: int, total: int) -> None:
        self.progress_total = total
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.set_value(pct)
        self.lbl_progress.set_text(f"进度: {pct}% ({current}/{total})")

    def _on_finished(self, message: str) -> None:
        if message.startswith("ERROR:"):
            self.log.append(f"[完成] {message}", "error")
            self._show_message("error", "测量错误", message[6:])
        elif message == "CSV export cancelled":
            self.log.append("CSV 导出已取消", "warning")
        else:
            self.log.append(f"[完成] 测量完成", "success")
            self._show_message("info", "测量完成", f"CSV 已保存：\n{message}")

    def _show_message(self, kind: str, title: str, msg: str) -> None:
        """Show a simple overlay message box in pygame."""
        self._pending_message = (kind, title, msg)

    # ── SpinBox update helpers ───────────────────────────────────────────────

    def _update_spinbox_handlers(self) -> None:
        """Wire up spinbox on_change to internal state updates."""
        for w in self.widgets:
            if isinstance(w, SpinBox):
                if w is self.sb_offset_x:
                    orig = w.value
                    # We store value in self.offset_x
                    pass
                elif w is self.sb_offset_y:
                    pass
                elif w is self.sb_width:
                    pass
                elif w is self.sb_height:
                    pass

    # ── Event handling ────────────────────────────────────────────────────────

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._shutdown()
                return

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._shutdown()
                    return
                # Focus management
                if event.key == pygame.K_TAB:
                    self._cycle_focus()
                    continue
                # Pass to focused widget
                if self._focused_widget and not self._focused_widget.disabled:
                    consumed = self._focused_widget.handle_event(event)

            elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP,
                                  pygame.MOUSEMOTION):
                x, y = event.pos if hasattr(event, 'pos') else (0, 0)

                # Track hover
                for w in self.widgets:
                    if isinstance(w, (Button, ThemeToggle)):
                        w._hovered = w.rect.collidepoint(x, y) if hasattr(event, 'pos') else False

                # Button clicks
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Check buttons first
                    if self.btn_start.rect.collidepoint(x, y) and not self.btn_start.disabled:
                        self._on_start_clicked()
                        continue
                    if self.btn_abort.rect.collidepoint(x, y) and not self.btn_abort.disabled:
                        self._on_abort_clicked()
                        continue

                # Spinbox / radio clicks (in widget list)
                for w in self.widgets:
                    if not w.disabled and w.contains(x, y):
                        consumed = w.handle_event(event)
                        # Update state from spinboxes
                        if isinstance(w, SpinBox):
                            if w is self.sb_offset_x:
                                self.offset_x = w.value
                                self._on_offset_changed('x', w.value)
                            elif w is self.sb_offset_y:
                                self.offset_y = w.value
                                self._on_offset_changed('y', w.value)
                            elif w is self.sb_width:
                                self.width = w.value
                                self._on_display_params_changed(w.value)
                            elif w is self.sb_height:
                                self.height = w.value
                                self._on_display_params_changed(w.value)
                        if consumed:
                            self._focused_widget = w
                            break
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        # Unfocus if clicking outside
                        if self._focused_widget is w:
                            self._focused_widget = None

    def _cycle_focus(self) -> None:
        """Cycle focus through spinboxes."""
        spinboxes = [w for w in self.widgets if isinstance(w, SpinBox)]
        if not spinboxes:
            return
        if self._focused_widget not in spinboxes:
            self._focused_widget = spinboxes[0]
        else:
            idx = spinboxes.index(self._focused_widget)
            self._focused_widget = spinboxes[(idx + 1) % len(spinboxes)]

    def _shutdown(self) -> None:
        self.running = False
        if self._display_window:
            self._display_window.stop()

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _draw(self) -> None:
        t = self.theme

        # Main background
        self.screen.fill(t['bg'])

        # Left panel background
        self.screen.fill(t['surface'], (0, 0, LEFT_W, WIN_H))

        # Divider
        self.screen.fill(t['divider'], (DIVIDER_X, 0, 1, WIN_H))

        # Right panel header bar
        self.screen.fill(t['surface'], (RIGHT_X, 0, WIN_W - RIGHT_X, 44))
        self.screen.fill(t['divider'], (RIGHT_X, 43, WIN_W - RIGHT_X, 1))

        # Left header bottom border
        self.screen.fill(t['divider'], (0, HEADER_H, LEFT_W, 1))

        # ── Draw left panel content ───────────────────────────────────────────
        # Title
        self.lbl_title.draw(self.screen, t)
        self.lbl_subtitle.draw(self.screen, t)
        self.btn_theme.draw(self.screen, t)

        # Section titles
        self.lbl_sec1.draw(self.screen, t)
        self.lbl_sec2.draw(self.screen, t)
        self.lbl_sec3.draw(self.screen, t)

        # Input labels
        for lbl in [self.lbl_offx, self.lbl_offy,
                    self.lbl_w, self.lbl_h,
                    self.lbl_start_gray, self.lbl_end_gray]:
            lbl.draw(self.screen, t)

        # Buttons
        self.btn_start.draw(self.screen, t)
        self.btn_abort.draw(self.screen, t)

        # Status
        self.lbl_status_title.draw(self.screen, t)

        # Status badge
        badge_bg = t['success']
        if self.meas_state in ("SCANNING", "CONNECTING", "CALIBRATING",
                                 "MEASURING", "ABORTING", "EXPORTING"):
            badge_bg = t['warning']
        elif self.meas_state == "ERROR":
            badge_bg = t['error']

        badge_rect = pygame.Rect(LEFT_W - SECTION_PADDING - 60,
                                  self.lbl_status_title.rect.y, 60, 22)
        draw_rounded_rect(self.screen, badge_rect, badge_bg, radius=11)
        # Badge text
        font = get_font(11, True)
        badge_text = self.lbl_status_badge.text
        ts = font.render(badge_text, True, (255, 255, 255))
        tx = badge_rect.centerx - ts.get_width() // 2
        ty = badge_rect.centery - ts.get_height() // 2
        self.screen.blit(ts, (tx, ty))

        # Progress bar
        self.progress_bar.draw(self.screen, t)

        # Progress label
        self.lbl_progress.draw(self.screen, t)

        # Data labels
        if self.last_record:
            x_val = self.last_record.get('x')
            y_val = self.last_record.get('y')
            lv_val = self.last_record.get('亮度Lv')
            # Draw data boxes
            data_items = [
                ("x 坐标", f"{x_val:.4f}" if x_val is not None else "--"),
                ("y 坐标", f"{y_val:.4f}" if y_val is not None else "--"),
                ("亮度 Lv", f"{lv_val:.4f}" if lv_val is not None else "--"),
            ]
            dx = SECTION_PADDING
            dy = self.lbl_progress.rect.y + 20
            for label_text, value_text in data_items:
                dr = pygame.Rect(dx, dy, 136, 36)
                draw_rounded_rect(self.screen, dr, t['surface'], radius=6)
                draw_rounded_rect_outline(self.screen, dr, t['border'], radius=6, width=1)
                f_lbl = get_font(10)
                f_val = get_font(13, True)
                ts_lbl = f_lbl.render(label_text, True, t['text_sec'])
                ts_val = f_val.render(value_text, True, t['text'])
                self.screen.blit(ts_lbl, (dr.x + 8, dr.y + 4))
                self.screen.blit(ts_val, (dr.x + 8, dr.y + 16))
                dx += 140
        else:
            # Draw placeholder data boxes
            data_items = [("x 坐标", "--"), ("y 坐标", "--"), ("亮度 Lv", "--")]
            dx = SECTION_PADDING
            dy = self.lbl_progress.rect.y + 20
            for label_text, value_text in data_items:
                dr = pygame.Rect(dx, dy, 136, 36)
                draw_rounded_rect(self.screen, dr, t['surface'], radius=6)
                draw_rounded_rect_outline(self.screen, dr, t['border'], radius=6, width=1)
                f_lbl = get_font(10)
                f_val = get_font(13, True)
                ts_lbl = f_lbl.render(label_text, True, t['text_sec'])
                ts_val = f_val.render(value_text, True, t['text_sec'])
                self.screen.blit(ts_lbl, (dr.x + 8, dr.y + 4))
                self.screen.blit(ts_val, (dr.x + 8, dr.y + 16))
                dx += 140

        # Log section
        self.lbl_log_title.draw(self.screen, t)
        self.lbl_log_count.draw(self.screen, t)
        self.log.draw(self.screen, self.log_rect, t)

        # ── Draw right panel ─────────────────────────────────────────────────
        self.lbl_right_title.draw(self.screen, t)

        # AOT badge
        badge_rect2 = pygame.Rect(WIN_W - 16 - 90, 14, 90, 22)
        draw_rounded_rect(self.screen, badge_rect2, t['surface'], radius=11)
        draw_rounded_rect_outline(self.screen, badge_rect2, t['border'], radius=11, width=1)
        f_badge = get_font(10)
        ts_b = f_badge.render("Always on Top", True, t['text_sec'])
        self.screen.blit(ts_b, (badge_rect2.centerx - ts_b.get_width() // 2,
                                badge_rect2.centery - ts_b.get_height() // 2))

        # Preview color box
        gray = self.current_gray
        mix_fn = self._color_mix[self.current_color]
        r, g, b = mix_fn(gray)
        preview_c = (r, g, b)

        draw_rounded_rect(self.screen, self.preview_rect, preview_c, radius=4)
        draw_rounded_rect_outline(self.screen, self.preview_rect, t['border'], radius=4, width=1)

        # Preview gray text (on top of color)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = (30, 30, 30) if brightness > 128 else (255, 255, 255)
        f_big = get_font(24, True)
        ts_big = f_big.render(str(gray), True, text_color)
        self.screen.blit(ts_big,
                        (self.preview_rect.centerx - ts_big.get_width() // 2,
                         self.preview_rect.centery - ts_big.get_height() // 2 - 8))

        # Info labels on right panel
        self.lbl_preview_gray.draw(self.screen, t)
        self.lbl_preview_size.draw(self.screen, t)
        for key, lbl in self._right_info.items():
            lbl.draw(self.screen, t)

        # Pending message overlay
        if hasattr(self, '_pending_message') and self._pending_message:
            self._draw_message_overlay(*self._pending_message)

        pygame.display.flip()

    def _draw_message_overlay(self, kind: str, title: str, msg: str) -> None:
        """Draw a modal message box overlay."""
        t = self.theme
        bw, bh = 420, 200
        bx = (WIN_W - bw) // 2
        by = (WIN_H - bh) // 2
        overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        # Box
        box_rect = pygame.Rect(bx, by, bw, bh)
        draw_rounded_rect(self.screen, box_rect, t['surface'], radius=12)
        draw_rounded_rect_outline(self.screen, box_rect, t['border'], radius=12, width=2)

        # Title
        f_title = get_font(15, True)
        ts = f_title.render(title, True, t['text'])
        self.screen.blit(ts, (bx + 20, by + 16))

        # Icon
        icon = "ℹ️" if kind == "info" else "✅" if kind == "success" else "❌"
        f_icon = get_font(24)
        ti = f_icon.render(icon, True, t['accent'])
        self.screen.blit(ti, (bx + 20, by + 50))

        # Message (multi-line)
        f_msg = get_font(13)
        lines = msg.split('\n')
        my = by + 54
        for line in lines:
            tl = f_msg.render(line, True, t['text_sec'])
            self.screen.blit(tl, (bx + 56, my))
            my += f_msg.get_height() + 4

        # OK button
        btn_w, btn_h = 100, 36
        btn_rect = pygame.Rect(bx + bw // 2 - btn_w // 2, by + bh - 50, btn_w, btn_h)
        draw_rounded_rect(self.screen, btn_rect, t['accent'], radius=8)
        f_btn = get_font(13, True)
        ts_btn = f_btn.render("确定", True, (255, 255, 255))
        self.screen.blit(ts_btn, (btn_rect.centerx - ts_btn.get_width() // 2,
                                   btn_rect.centery - ts_btn.get_height() // 2))

        # Store button rect for click detection
        self._msg_ok_btn = btn_rect

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60)  # ~60 fps

            self._handle_events()

            # Update widgets
            for w in self.widgets:
                w.update(pygame.event.get())

            # Draw
            self._draw()

        # Cleanup
        if self._display_window:
            self._display_window.stop()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
