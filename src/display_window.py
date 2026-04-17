"""
Display Window — Pygame-based screen color window running in an independent thread.
Always on Top (Windows HWND_TOPMOST) and can be positioned/resized.
Gracefully skips display if no screen is available (e.g., headless Windows VM).
"""

import ctypes
import threading
import time
from typing import Optional

# Lazy import pygame — only loaded when display is actually started
pygame = None
user32 = None
win32gui = None


class DisplayWindow:
    """
    Independent Pygame window for rendering solid-color screen patches.
    Runs its own pygame event loop in a background thread.
    Call set_color(), set_position(), set_size() from any thread.
    """

    def __init__(self, title: str = "ca-analyzer"):
        self.title = title
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._display_available = False

        # Target display parameters
        self._target_r = 255
        self._target_g = 255
        self._target_b = 255
        self._target_x = 0
        self._target_y = 0
        self._target_w = 512
        self._target_h = 512

        # pygame objects
        self._screen: Optional[object] = None
        self._clock: Optional[object] = None
        self._hwnd: Optional[int] = None

        self._lock = threading.Lock()

    @property
    def is_display_available(self) -> bool:
        return self._display_available

    # ── Public API ──────────────────────────────────────────────────────────

    def set_color(self, r: int, g: int, b: int) -> None:
        with self._lock:
            self._target_r = max(0, min(255, r))
            self._target_g = max(0, min(255, g))
            self._target_b = max(0, min(255, b))

    def set_position(self, x: int, y: int) -> None:
        with self._lock:
            self._target_x = x
            self._target_y = y

    def set_size(self, w: int, h: int) -> None:
        with self._lock:
            self._target_w = max(1, w)
            self._target_h = max(1, h)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="DisplayThread")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    # ── Pygame thread ───────────────────────────────────────────────────────

    def _run(self) -> None:
        """Pygame event loop — runs in background thread."""
        global pygame, user32, win32gui

        # ── 1. Lazy import pygame ───────────────────────────────────────────
        try:
            import pygame as _pg
            pygame = _pg
        except Exception as e:
            print(f"[打屏窗口] pygame 导入失败: {e}")
            return

        # ── 2. Test display availability ──────────────────────────────────
        try:
            pygame.display.init()
            test = pygame.display.set_mode((1, 1), pygame.HWSURFACE | pygame.DOUBLEBUF)
            if test is None:
                raise RuntimeError("set_mode returned None")
            pygame.display.quit()
            pygame.display.init()
        except Exception as e:
            print(f"[打屏窗口] 无法初始化显示器: {e}")
            print("[打屏窗口] 打屏功能已禁用，主程序继续运行")
            self._display_available = False
            return

        self._display_available = True

        # ── 3. Load Windows API ─────────────────────────────────────────────
        try:
            user32 = ctypes.windll.user32
        except Exception as e:
            print(f"[打屏窗口] 无法加载 user32: {e}")
            self._display_available = False
            return

        try:
            import win32gui
        except ImportError:
            win32gui = None

        # ── 4. Create the actual pygame window ──────────────────────────────
        try:
            self._clock = pygame.time.Clock()
            self._screen = pygame.display.set_mode(
                (self._target_w, self._target_h),
                pygame.HWSURFACE | pygame.DOUBLEBUF
            )
            pygame.display.set_caption(self.title)
        except Exception as e:
            print(f"[打屏窗口] 无法创建窗口: {e}")
            self._display_available = False
            return

        # ── 5. Get and verify HWND ──────────────────────────────────────────
        try:
            wm_info = pygame.display.get_wm_info()
            self._hwnd = wm_info.get('window')
            if self._hwnd is None or self._hwnd == 0:
                # Try alternative keys
                for key in ('window', 'hwnd', 'HWND'):
                    try:
                        self._hwnd = wm_info[key]
                        if self._hwnd:
                            break
                    except KeyError:
                        continue
            if self._hwnd is None or self._hwnd == 0:
                print(f"[打屏窗口] 无法获取 HWND，wm_info={wm_info}")
                # Try win32gui as fallback
                if win32gui:
                    hwnd = win32gui.GetForegroundWindow()
                    if hwnd:
                        self._hwnd = hwnd
        except Exception as e:
            print(f"[打屏窗口] HWND 获取失败: {e}")

        print(f"[打屏窗口] 已创建，HWND={self._hwnd}")

        # ── 6. Apply Always on Top ──────────────────────────────────────────
        if self._hwnd:
            self._set_always_on_top(self._hwnd)

        # ── 7. Apply initial position ───────────────────────────────────────
        self._apply_position()

        # ── 8. Main render loop ─────────────────────────────────────────────
        while self._running:
            try:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                        break

                with self._lock:
                    r, g, b = self._target_r, self._target_g, self._target_b
                    w, h = self._target_w, self._target_h

                # Recreate window if size changed
                if self._screen.get_size() != (w, h):
                    try:
                        self._screen = pygame.display.set_mode(
                            (w, h), pygame.HWSURFACE | pygame.DOUBLEBUF
                        )
                        # Get fresh HWND after resize
                        try:
                            wm_info = pygame.display.get_wm_info()
                            self._hwnd = wm_info.get('window')
                        except Exception:
                            pass
                        if self._hwnd:
                            self._set_always_on_top(self._hwnd)
                    except Exception as e:
                        print(f"[打屏窗口] 窗口resize失败: {e}")

                # Apply position every frame (robust: try both APIs)
                if self._hwnd:
                    self._apply_position()
                    self._set_always_on_top(self._hwnd)

                # Render
                self._screen.fill((r, g, b))
                pygame.display.flip()
                self._clock.tick(30)

            except Exception as e:
                print(f"[打屏窗口] 渲染异常: {e}")
                time.sleep(0.1)

        pygame.quit()

    def _apply_position(self) -> None:
        """Move pygame window to target position via Windows SetWindowPos."""
        if not self._display_available or not self._hwnd:
            return
        try:
            with self._lock:
                tx, ty = self._target_x, self._target_y
            user32.SetWindowPos(
                self._hwnd, -1,  # HWND_TOPMOST
                tx, ty, 0, 0,
                0x0001 | 0x0004  # SWP_NOSIZE | SWP_NOZORDER
            )
        except Exception as e:
            # Fallback: try win32gui
            if win32gui and self._hwnd:
                try:
                    win32gui.SetWindowPos(
                        self._hwnd, win32gui.HWND_TOPMOST,
                        int(self._target_x), int(self._target_y), 0, 0,
                        0x0001 | 0x0004
                    )
                except Exception:
                    pass

    def _set_always_on_top(self, hwnd: int) -> None:
        """Keep window always on top via SetWindowPos."""
        if not user32 or not hwnd:
            return
        try:
            user32.SetWindowPos(
                hwnd, -1,  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0001 | 0x0002  # SWP_NOMOVE | SWP_NOSIZE
            )
        except Exception:
            # Fallback: try win32gui
            if win32gui and hwnd:
                try:
                    win32gui.SetWindowPos(
                        hwnd, win32gui.HWND_TOPMOST,
                        0, 0, 0, 0,
                        0x0001 | 0x0002
                    )
                except Exception:
                    pass
