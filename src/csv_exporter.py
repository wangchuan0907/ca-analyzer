"""
CSV Exporter
Handles measurement record export with a system Save-As dialog.
"""

import csv
from datetime import datetime
from typing import List
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QObject


class CSVExporter(QObject):
    """Handles exporting measurement records to CSV via a save dialog."""

    FIELDNAMES = ['序号', '灰阶值', '通道', '颜色', 'x', 'y', '亮度Lv', '测量时间']

    def __init__(self, parent=None):
        super().__init__(parent)

    def export(self, records: List[dict], default_name: str) -> str | None:
        """
        Export measurement records to CSV via a Save-As dialog.

        Args:
            records: List of measurement record dicts
            default_name: Default filename suggestion

        Returns:
            The chosen file path, or None if cancelled
        """
        if not records:
            QMessageBox.warning(
                self.parent() if self.parent() else None,
                "导出警告",
                "没有测量数据可导出。"
            )
            return None

        # Always append .csv if not present
        if not default_name.endswith('.csv'):
            default_name += '.csv'

        file_path, _ = QFileDialog.getSaveFileName(
            self.parent() if self.parent() else None,
            "保存测量数据",
            default_name,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return None

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
                writer.writerows(records)
            return file_path
        except Exception as e:
            QMessageBox.critical(
                self.parent() if self.parent() else None,
                "导出失败",
                f"写入 CSV 文件失败：\n{e}"
            )
            return None
