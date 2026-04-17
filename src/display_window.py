"""
Display Window — Pygame-based screen color window running in an independent thread.
Always on Top (Windows HWND_TOPMOST) and can be positioned/resized.
"""

import ctypes
import threading
import time
from typing import Optional

import pygame

user32 = ctypes.windll.user32


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

        # Target display parameters (written from main thread, read in pygame thread)
        self._target_r = 128
        self._target_g = 128
        self._target_b = 128
        self._target_x = 100
        self._target_y = 100
        self._target_w = 512
        self._target_h = 512

        # pygame objects (created in the pygame thread)
        self._screen: Optional[pygame.Surface] = None
        self._clock: Optional[pygame.time.Clock] = None

        # Lock for shared parameters
        self._lock = threading.Lock()

    # ── Public API (call from main thread) ──────────────────────────────────

    def set_color(self, r: int, g: int, b: int) -> None:
        """Set the target RGB fill color."""
        with self._lock:
            self._target_r = max(0, min(255, r))
            self._target_g = max(0, min(255, g))
            self._target_b = max(0, min(255, b))

    def set_position(self, x: int, y: int) -> None:
        """Set the window top-left position (in screen coordinates)."""
        with self._lock:
            self._target_x = x
            self._target_y = y

    def set_size(self, w: int, h: int) -> None:
        """Set the window size."""
        with self._lock:
            self._target_w = max(1, w)
            self._target_h = max(1, h)

    def start(self) -> None:
        """Start the pygame thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="DisplayThread")
        self._thread.start()

    def stop(self) -> None:
        """Stop the pygame thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    # ── Pygame thread ───────────────────────────────────────────────────────

    def _run(self) -> None:
        """Pygame event loop (runs in background thread)."""
        pygame.init()
        self._clock = pygame.time.Clock()

        # Create window — initially small, position will be set after init
        self._screen = pygame.display.set_mode(
            (self._target_w, self._target_h),
            pygame.NOFRAME
        )

        # Set Always on Top via Windows SetWindowPos
        self._apply_always_on_top()
        self._apply_position()

        pygame.display.set_caption(self.title)

        # Main loop
        while self._running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                    break

            # Read target parameters under lock
            with self._lock:
                r, g, b = self._target_r, self._target_g, self._target_b
                x, y = self._target_x, self._target_y
                w, h = self._target_w, self._target_h

            # Resize window if size changed
            current_w, current_h = self._screen.get_size()
            if current_w != w or current_h != h:
                self._screen = pygame.display.set_mode(
                    (w, h), pygame.NOFRAME
                )
                self._apply_always_on_top()

            # Apply position
            self._apply_position()

            # Fill with target color
            self._screen.fill((r, g, b))
            pygame.display.flip()

            self._clock.tick(30)  # ~30 fps is enough for color updates

        pygame.quit()

    def _apply_position(self) -> None:
        """Move the pygame window to the target position using Windows API."""
        try:
            hwnd = pygame.display.get_wm_info()['window']
            with self._lock:
                tx, ty = self._target_x, self._target_y
            user32.SetWindowPos(
                hwnd,           # hWnd
                -1,             # hWndInsertAfter: HWND_TOPMOST (-1)
                tx,             # X
                ty,             # Y
                0, 0,            # cx, cy (use existing)
                0x0001 | 0x0004  # flags: SWP_NOSIZE | SWP_NOZORDER
            )
        except Exception:
            pass  # Non-critical on non-Windows platforms

    def _apply_always_on_top(self) -> None:
        """Ensure the window stays on top using Windows SetWindowPos."""
        try:
            hwnd = pygame.display.get_wm_info()['window']
            user32.SetWindowPos(
                hwnd,
                -1,  # HWND_TOPMOST
                0, 0, 0, 0,
                0x0001 | 0x0002  # SWP_NOMOVE | SWP_NOSIZE
            )
        except Exception:
            pass
