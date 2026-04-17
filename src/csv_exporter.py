"""
CSV Exporter — handles measurement record export with a system Save-As dialog.
Refactored to remove PySide6 dependency; uses tkinter (built-in).
"""

import csv
import os
import sys
from typing import List, Optional


# ── Tkinter-based dialogs (no PySide6 needed) ─────────────────────────────────

def _get_tk_root():
    """Lazily create a hidden Tk root for file dialogs."""
    try:
        import tkinter as tk
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()  # hide the Tk window
    root.attributes('-topmost', True)  # bring dialog to front
    return root


def ask_save_filename(default_name: str) -> Optional[str]:
    """Show a system Save-As dialog and return the chosen path, or None if cancelled."""
    try:
        import tkinter.filedialog as fd
    except ImportError:
        return None

    root = _get_tk_root()
    if root is None:
        return None

    # Always append .csv
    if not default_name.endswith('.csv'):
        default_name += '.csv'

    file_path = fd.asksaveasfilename(
        title="保存测量数据",
        initialfile=default_name,
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        defaultextension=".csv",
    )
    try:
        root.destroy()
    except Exception:
        pass

    return file_path if file_path else None


def show_warning(title: str, message: str) -> None:
    """Show a warning message box."""
    try:
        import tkinter as tk
        import tkinter.messagebox as mb
    except ImportError:
        return

    root = _get_tk_root()
    if root:
        mb.showwarning(title, message)
        try:
            root.destroy()
        except Exception:
            pass


def show_error(title: str, message: str) -> None:
    """Show an error message box."""
    try:
        import tkinter.messagebox as mb
    except ImportError:
        return

    root = _get_tk_root()
    if root:
        mb.showerror(title, message)
        try:
            root.destroy()
        except Exception:
            pass


def show_info(title: str, message: str) -> None:
    """Show an info message box."""
    try:
        import tkinter.messagebox as mb
    except ImportError:
        return

    root = _get_tk_root()
    if root:
        mb.showinfo(title, message)
        try:
            root.destroy()
        except Exception:
            pass


# ── CSVExporter ───────────────────────────────────────────────────────────────

class CSVExporter:
    """Handles exporting measurement records to CSV via a save dialog."""

    FIELDNAMES = ['序号', '灰阶值', '通道', '颜色', 'x', 'y', '亮度Lv', '测量时间']

    def __init__(self):
        pass

    def export(self, records: List[dict], default_name: str) -> Optional[str]:
        """
        Export measurement records to CSV via a Save-As dialog.

        Args:
            records: List of measurement record dicts
            default_name: Default filename suggestion

        Returns:
            The chosen file path, or None if cancelled / failed
        """
        if not records:
            show_warning("导出警告", "没有测量数据可导出。")
            return None

        file_path = ask_save_filename(default_name)
        if not file_path:
            return None

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(records)
            return file_path
        except Exception as e:
            show_error("导出失败", f"写入 CSV 文件失败：\n{e}")
            return None
