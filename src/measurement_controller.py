"""
Measurement Controller — State machine + worker thread for CA-410 measurement flow.
Refactored to remove PySide6 dependency. Uses threading + callback pattern.
"""

import time
import threading
from datetime import datetime
from enum import IntEnum
from typing import Optional, Callable


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


class MeasurementController:
    """
    Orchestrates the CA-410 measurement workflow using threading + callbacks.

    Callbacks (set these before calling start()):
      on_state_changed:   callable(str)   — state name changed
      on_log_message:      callable(str)   — log message
      on_data_ready:      callable(dict) — single measurement record
      on_progress_updated: callable(int, int) — current, total
      on_finished:        callable(str)   — file path or error message
    """

    COLOR_WHITE = '白'
    COLOR_RED   = '红'
    COLOR_GREEN = '绿'
    COLOR_BLUE  = '蓝'

    def __init__(self):
        self._state = State.IDLE
        self._thread: Optional[threading.Thread] = None
        self._worker: Optional['MeasurementWorker'] = None

        # Callbacks (set by GUI)
        self.on_state_changed:   Optional[Callable[[str], None]]   = None
        self.on_log_message:      Optional[Callable[[str], None]]   = None
        self.on_data_ready:       Optional[Callable[[dict], None]]  = None
        self.on_progress_updated: Optional[Callable[[int, int], None]] = None
        self.on_finished:         Optional[Callable[[str], None]]   = None

    # ── Public API ──────────────────────────────────────────────────────────

    def start(self, params: dict,
              display_window=None,
              csv_exporter=None) -> None:
        """
        Begin the measurement workflow.

        Args:
            params: dict with keys:
              offset_x, offset_y, width, height,
              start_gray, end_gray,
              color_name (白/红/绿/蓝)
            display_window: DisplayWindow instance (optional)
            csv_exporter: CSVExporter instance (optional)
        """
        if self._state != State.IDLE:
            self._emit_log("[警告] 测量已在进行中，忽略本次请求")
            return

        self._worker = MeasurementWorker(params)
        self._worker.display_window = display_window
        self._worker.csv_exporter = csv_exporter

        # Wire up callbacks
        self._worker._state_changed_cb = self._on_worker_state
        self._worker._log_cb           = self._emit_log
        self._worker._data_cb          = self._emit_data
        self._worker._progress_cb      = self._emit_progress
        self._worker._finished_cb      = self._on_worker_finished

        self._thread = threading.Thread(
            target=self._worker.run,
            daemon=True,
            name="MeasurementThread"
        )
        self._thread.start()

    def abort(self) -> None:
        """Request abort of the current measurement."""
        if self._worker and self._state in (State.MEASURING, State.ABORTING):
            self._worker.abort()
            self._emit_log("[用户] 中止请求已发送")

    def get_state(self) -> State:
        return self._state

    # ── Internal callbacks ─────────────────────────────────────────────────

    def _on_worker_state(self, state_name: str) -> None:
        self._state = State[state_name]
        if self.on_state_changed:
            self.on_state_changed(state_name)

    def _emit_log(self, msg: str) -> None:
        if self.on_log_message:
            self.on_log_message(msg)

    def _emit_data(self, record: dict) -> None:
        if self.on_data_ready:
            self.on_data_ready(record)

    def _emit_progress(self, current: int, total: int) -> None:
        if self.on_progress_updated:
            self.on_progress_updated(current, total)

    def _on_worker_finished(self, message: str) -> None:
        self._state = State.IDLE
        if self.on_finished:
            self.on_finished(message)
        self._thread = None
        self._worker = None


class MeasurementWorker:
    """
    Actual measurement logic running inside a background thread.
    Uses plain callbacks instead of Qt Signals.
    """

    def __init__(self, params: dict):
        self.params = params

        # Callbacks set by MeasurementController
        self._state_changed_cb:   Optional[Callable[[str], None]]   = None
        self._log_cb:             Optional[Callable[[str], None]]    = None
        self._data_cb:            Optional[Callable[[dict], None]]   = None
        self._progress_cb:        Optional[Callable[[int, int], None]] = None
        self._finished_cb:        Optional[Callable[[str], None]]    = None

        # Abort event — thread-safe
        self._abort = threading.Event()

        # References set by main_window
        self.display_window = None
        self.csv_exporter = None

        self._records: list[dict] = []

    def abort(self) -> None:
        """Signal the worker to abort (call from main thread)."""
        self._abort.set()

    # ── Entry point (called in worker thread) ─────────────────────────────

    def run(self) -> None:
        """Execute the full measurement workflow."""
        self._abort.clear()
        self._records = []

        try:
            self._do_work()
        except Exception as e:
            self._set_state(State.ERROR)
            err_msg = f"[异常] {type(e).__name__}: {e}"
            self._emit_log(err_msg)
            self._finished("ERROR: " + err_msg)

    def _do_work(self) -> None:
        from .serial_protocol import CA410Protocol

        p = self.params
        color_name = p.get('color_name', '白')
        start_gray = int(p['start_gray'])
        end_gray   = int(p['end_gray'])
        total = end_gray - start_gray + 1

        # ── 1. Scan ports ──────────────────────────────────────────────────
        self._set_state(State.SCANNING)
        self._emit_log("[Step 1] 正在扫描串口...")
        ports = CA410Protocol.scan_ports()
        if not ports:
            self._emit_log("[错误] 未找到色度仪设备，请检查连接")
            self._finished("ERROR: 色度仪未连接")
            self._set_state(State.ERROR)
            return

        port = ports[0]
        self._emit_log(f"[Step 1] 找到设备: {port}")

        # ── 2. Connect & probe ─────────────────────────────────────────────
        self._set_state(State.CONNECTING)
        self._emit_log(f"[Step 2] 连接色度仪 {port}...")
        protocol = CA410Protocol(port)
        try:
            protocol.open()
            if not protocol.expect_ok('COM,1'):
                self._emit_log("[错误] 色度仪通讯失败（COM,1 未返回 OK00）")
                self._finished("ERROR: 色度仪通讯失败")
                self._set_state(State.ERROR)
                return
            self._emit_log("[Step 2] 通讯建立成功")
        except Exception as e:
            self._emit_log(f"[错误] 连接异常: {e}")
            self._finished(f"ERROR: 连接异常: {e}")
            self._set_state(State.ERROR)
            return

        # ── 3. Calibrate ───────────────────────────────────────────────────
        self._set_state(State.CALIBRATING)
        self._emit_log("[Step 3] 正在校准...")
        if not protocol.expect_ok('ZRC'):
            self._emit_log("[错误] 色度仪校准失败（ZRC 未返回 OK00）")
            self._finished("ERROR: 色度仪校准失败")
            protocol.close()
            self._set_state(State.ERROR)
            return
        self._emit_log("[Step 3] 校准完成")

        # ── 4. Measurement loop ────────────────────────────────────────────
        self._set_state(State.MEASURING)
        self._emit_log(f"[Step 4] 开始测量，灰阶 {start_gray} ~ {end_gray}，颜色: {color_name}")
        self._emit_progress(0, total)

        index = 0
        for gray in range(start_gray, end_gray + 1):
            # Check abort flag
            if self._abort.is_set():
                self._emit_log("[中止] 测量已中止，正在退出循环...")
                self._set_state(State.ABORTING)
                break

            # Set display color: white = RGB same value; single-color = RGB same value
            r = g = b = gray
            if self.display_window:
                self.display_window.set_color(r, g, b)

            time.sleep(0.1)  # 100ms settle time

            # Check abort again after sleep
            if self._abort.is_set():
                self._emit_log("[中止] 测量已中止，正在退出循环...")
                self._set_state(State.ABORTING)
                break

            # Measure
            self._emit_log(f"  灰阶 {gray}: 发送 MES,1...")
            try:
                reply = protocol.send_command('MES,1')
                result = protocol.parse_measurement(reply)
                if result is None:
                    self._emit_log(f"[错误] 灰阶 {gray} 测量解析失败: {reply}")
                    self._finished(f"ERROR: 第 {gray} 灰阶测量失败")
                    self._set_state(State.ERROR)
                    protocol.close()
                    return
            except Exception as e:
                self._emit_log(f"[错误] 灰阶 {gray} 测量异常: {e}")
                self._finished(f"ERROR: 第 {gray} 灰阶测量异常: {e}")
                self._set_state(State.ERROR)
                protocol.close()
                return

            # Record
            index += 1
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record = {
                '序号': index,
                '灰阶值': gray,
                '通道': '单色',
                '颜色': color_name,
                'x': result['x'],
                'y': result['y'],
                '亮度Lv': result['lv'],
                '测量时间': ts,
            }
            self._records.append(record)
            self._emit_data(record)
            self._emit_progress(index, total)
            self._emit_log(f"  灰阶 {gray}: x={result['x']:.4f} y={result['y']:.4f} Lv={result['lv']:.4f}")

        # ── 5. Close ──────────────────────────────────────────────────────
        try:
            protocol.expect_ok('COM,0')
            self._emit_log("[Step 5] 色度仪已关闭")
        except Exception:
            self._emit_log("[警告] 色度仪关闭指令失败（已忽略）")
        finally:
            protocol.close()

        # ── 6. Export CSV ─────────────────────────────────────────────────
        self._set_state(State.EXPORTING)
        self._emit_log("[Step 6] 正在导出 CSV...")

        ts_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"色度测量-{start_gray}-{end_gray}-{ts_str}"

        if self.csv_exporter:
            file_path = self.csv_exporter.export(self._records, default_name)
        else:
            import os, csv
            fallback_path = os.path.join(os.getcwd(), default_name + '.csv')
            try:
                with open(fallback_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=[
                        '序号', '灰阶值', '通道', '颜色', 'x', 'y', '亮度Lv', '测量时间'
                    ])
                    writer.writeheader()
                    writer.writerows(self._records)
                file_path = fallback_path
            except Exception as e:
                file_path = None
                self._emit_log(f"[错误] CSV 写入失败: {e}")

        if file_path:
            self._emit_log(f"[完成] CSV 已保存: {file_path}")
            self._finished(file_path)
        else:
            self._emit_log("[完成] CSV 导出已取消")
            self._finished("CSV export cancelled")

        self._set_state(State.IDLE)

    def _set_state(self, state: State) -> None:
        if self._state_changed_cb:
            self._state_changed_cb(state.name)

    def _emit_log(self, msg: str) -> None:
        if self._log_cb:
            self._log_cb(msg)

    def _emit_data(self, record: dict) -> None:
        if self._data_cb:
            self._data_cb(record)

    def _emit_progress(self, current: int, total: int) -> None:
        if self._progress_cb:
            self._progress_cb(current, total)

    def _finished(self, message: str) -> None:
        if self._finished_cb:
            self._finished_cb(message)
