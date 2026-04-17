"""
Measurement Controller — State machine + worker thread for CA-410 measurement flow.
Coordinates serial_protocol, display_window, and csv_exporter.
All serial I/O happens in the worker thread; results dispatched to GUI via Qt Signals.
"""

import time
import threading
from datetime import datetime
from enum import IntEnum
from typing import Optional

from PySide6.QtCore import QObject, Signal, QThread


class State(IntEnum):
    """Measurement state machine states."""
    IDLE        = 0
    SCANNING    = 1
    CONNECTING  = 2
    CALIBRATING = 3
    MEASURING   = 4
    ABORTING    = 5
    EXPORTING   = 6
    ERROR       = 99


class MeasurementController(QObject):
    """
    Orchestrates the CA-410 measurement workflow:
      1. Scan serial ports
      2. Connect & probe (COM,1)
      3. Calibrate (ZRC)
      4. Loop: set display color → measure (MES,1) → record
      5. Close (COM,0)
      6. Export CSV

    Qt Signals (emitted from worker thread → delivered to GUI thread):
      state_changed    -> str  (state name)
      log_message      -> str  (human-readable message)
      data_ready       -> dict (single measurement record)
      progress_updated -> (int current, int total)
      finished         -> str  (file path or error message)
    """

    state_changed    = Signal(str)
    log_message      = Signal(str)
    data_ready       = Signal(dict)
    progress_updated = Signal(int, int)
    finished         = Signal(str)

    # Color mode constants
    COLOR_WHITE = '白'
    COLOR_RED   = '红'
    COLOR_GREEN = '绿'
    COLOR_BLUE  = '蓝'

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = State.IDLE
        self._thread: Optional[QThread] = None
        self._worker: Optional['MeasurementWorker'] = None

    # ── Public API (call from GUI main thread) ───────────────────────────────

    def start(self, params: dict,
                display_window=None,
                csv_exporter=None) -> None:
        """
        Begin the measurement workflow.

        Args:
            params: dict with keys:
              offset_x, offset_y, width, height,
              start_gray, end_gray,
              color (R/G/B/白)
            display_window: DisplayWindow instance (optional)
            csv_exporter: CSVExporter instance (optional)
        """
        if self._state != State.IDLE:
            self.log_message.emit("[警告] 测量已在进行中，忽略本次请求")
            return

        self._worker = MeasurementWorker(params)
        self._worker.display_window = display_window
        self._worker.csv_exporter = csv_exporter
        self._worker.state_changed.connect(self._on_state_changed)
        self._worker.log_message.connect(self.log_message)
        self._worker.data_ready.connect(self.data_ready)
        self._worker.progress_updated.connect(self.progress_updated)
        self._worker.finished.connect(self._on_finished)

        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._thread.start()

    def abort(self) -> None:
        """Request abort of the current measurement (from GUI main thread)."""
        if self._worker and self._state in (State.MEASURING, State.ABORTING):
            self._worker.abort()
            self.log_message.emit("[用户] 中止请求已发送")

    def get_state(self) -> State:
        return self._state

    # ── Internal slots ─────────────────────────────────────────────────────

    def _on_state_changed(self, state_name: str) -> None:
        self._state = State[state_name]
        self.state_changed.emit(state_name)

    def _on_finished(self, message: str) -> None:
        self._state = State.IDLE
        self.finished.emit(message)
        if self._thread:
            self._thread.quit()
            self._thread.wait(timeout=3000)
            self._thread = None
        self._worker = None


class MeasurementWorker(QObject):
    """
    Actual measurement logic running inside a QThread.
    Emits Qt Signals back to the controller (and ultimately the GUI).
    """

    state_changed    = Signal(str)
    log_message      = Signal(str)
    data_ready       = Signal(dict)
    progress_updated = Signal(int, int)
    finished         = Signal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

        # Abort event — thread-safe, can be set from GUI main thread
        self._abort = threading.Event()

        # Reference to display window set by main_window
        self.display_window = None
        # Reference to csv_exporter set by main_window
        self.csv_exporter = None

        self._records: list[dict] = []

    def abort(self) -> None:
        """Signal the worker to abort (call from main thread)."""
        self._abort.set()

    # ── Entry point (called in worker thread) ───────────────────────────────

    def run(self) -> None:
        """Execute the full measurement workflow."""
        self._abort.clear()
        self._records = []

        try:
            self._do_work()
        except Exception as e:
            self._set_state(State.ERROR)
            err_msg = f"[异常] {type(e).__name__}: {e}"
            self.log_message.emit(err_msg)
            self.finished.emit(f"ERROR: {err_msg}")

    def _do_work(self) -> None:
        from .serial_protocol import CA410Protocol

        p = self.params
        color_name = p.get('color_name', '白')
        start_gray = int(p['start_gray'])
        end_gray   = int(p['end_gray'])
        total = end_gray - start_gray + 1

        # ── 1. Scan ports ──────────────────────────────────────────────────
        self._set_state(State.SCANNING)
        self.log_message.emit("[Step 1] 正在扫描串口...")
        ports = CA410Protocol.scan_ports()
        if not ports:
            self.log_message.emit("[错误] 未找到色度仪设备，请检查连接")
            self.finished.emit("ERROR: 色度仪未连接")
            self._set_state(State.ERROR)
            return

        port = ports[0]
        self.log_message.emit(f"[Step 1] 找到设备: {port}")

        # ── 2. Connect & probe ─────────────────────────────────────────────
        self._set_state(State.CONNECTING)
        self.log_message.emit(f"[Step 2] 连接色度仪 {port}...")
        protocol = CA410Protocol(port)
        try:
            protocol.open()
            if not protocol.expect_ok('COM,1'):
                self.log_message.emit("[错误] 色度仪通讯失败（COM,1 未返回 OK00）")
                self.finished.emit("ERROR: 色度仪通讯失败")
                self._set_state(State.ERROR)
                return
            self.log_message.emit("[Step 2] 通讯建立成功")
        except Exception as e:
            self.log_message.emit(f"[错误] 连接异常: {e}")
            self.finished.emit(f"ERROR: 连接异常: {e}")
            self._set_state(State.ERROR)
            return

        # ── 3. Calibrate ───────────────────────────────────────────────────
        self._set_state(State.CALIBRATING)
        self.log_message.emit("[Step 3] 正在校准...")
        if not protocol.expect_ok('ZRC'):
            self.log_message.emit("[错误] 色度仪校准失败（ZRC 未返回 OK00）")
            self.finished.emit("ERROR: 色度仪校准失败")
            protocol.close()
            self._set_state(State.ERROR)
            return
        self.log_message.emit("[Step 3] 校准完成")

        # ── 4. Measurement loop ────────────────────────────────────────────
        self._set_state(State.MEASURING)
        self.log_message.emit(f"[Step 4] 开始测量，灰阶 {start_gray} ~ {end_gray}，颜色: {color_name}")
        self.progress_updated.emit(0, total)

        index = 0
        for gray in range(start_gray, end_gray + 1):
            # Check abort flag (max delay: 100ms since we sleep 0.1s per iteration)
            if self._abort.is_set():
                self.log_message.emit("[中止] 测量已中止，正在退出循环...")
                self._set_state(State.ABORTING)
                break

            # Set display color: white = RGB same value; single-color = RGB same value
            r = g = b = gray
            if self.display_window:
                self.display_window.set_color(r, g, b)

            time.sleep(0.1)  # 100ms settle time

            # Check abort again after sleep
            if self._abort.is_set():
                self.log_message.emit("[中止] 测量已中止，正在退出循环...")
                self._set_state(State.ABORTING)
                break

            # Measure
            self.log_message.emit(f"  灰阶 {gray}: 发送 MES,1...")
            try:
                reply = protocol.send_command('MES,1')
                result = protocol.parse_measurement(reply)
                if result is None:
                    self.log_message.emit(f"[错误] 灰阶 {gray} 测量解析失败: {reply}")
                    self.finished.emit(f"ERROR: 第 {gray} 灰阶测量失败")
                    self._set_state(State.ERROR)
                    protocol.close()
                    return
            except Exception as e:
                self.log_message.emit(f"[错误] 灰阶 {gray} 测量异常: {e}")
                self.finished.emit(f"ERROR: 第 {gray} 灰阶测量异常: {e}")
                self._set_state(State.ERROR)
                protocol.close()
                return

            # Record
            index += 1
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record = {
                '序号': index,
                '灰阶值': gray,
                '通道': '单色',  # white mode: single RGB value
                '颜色': color_name,
                'x': result['x'],
                'y': result['y'],
                '亮度Lv': result['lv'],
                '测量时间': ts,
            }
            self._records.append(record)
            self.data_ready.emit(record)
            self.progress_updated.emit(index, total)
            self.log_message.emit(f"  灰阶 {gray}: x={result['x']:.4f} y={result['y']:.4f} Lv={result['lv']:.4f}")

        # ── 5. Close ──────────────────────────────────────────────────────
        try:
            protocol.expect_ok('COM,0')
            self.log_message.emit("[Step 5] 色度仪已关闭")
        except Exception:
            self.log_message.emit("[警告] 色度仪关闭指令失败（已忽略）")
        finally:
            protocol.close()

        # ── 6. Export CSV ─────────────────────────────────────────────────
        self._set_state(State.EXPORTING)
        self.log_message.emit("[Step 6] 正在导出 CSV...")

        # Build default filename: 色度测量-{start}-{end}-{timestamp}.csv
        ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"色度测量-{start_gray}-{end_gray}-{ts_str}"

        if self.csv_exporter:
            file_path = self.csv_exporter.export(self._records, default_name)
        else:
            # Fallback: export to current directory
            import os
            fallback_path = os.path.join(os.getcwd(), default_name + '.csv')
            try:
                import csv
                with open(fallback_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        '序号', '灰阶值', '通道', '颜色', 'x', 'y', '亮度Lv', '测量时间'
                    ])
                    writer.writeheader()
                    writer.writerows(self._records)
                file_path = fallback_path
            except Exception as e:
                file_path = None
                self.log_message.emit(f"[错误] CSV 写入失败: {e}")

        if file_path:
            self.log_message.emit(f"[完成] CSV 已保存: {file_path}")
            self.finished.emit(file_path)
        else:
            self.log_message.emit("[完成] CSV 导出已取消")
            self.finished.emit("CSV export cancelled")

        self._set_state(State.IDLE)

    def _set_state(self, state: State) -> None:
        """Emit state change signal."""
        self.state_changed.emit(state.name)
