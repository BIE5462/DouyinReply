"""日志页。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..utils.text import truncate_text


class LogsTab(QWidget):
    export_requested = Signal()

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        button_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新日志")
        export_btn = QPushButton("导出回复 CSV")
        refresh_btn.clicked.connect(self.refresh)
        export_btn.clicked.connect(lambda: self.export_requested.emit())
        button_row.addWidget(refresh_btn)
        button_row.addWidget(export_btn)
        button_row.addStretch(1)

        splitter = QSplitter(Qt.Vertical)
        self.reply_table = QTableWidget(0, 6)
        self.reply_table.setHorizontalHeaderLabels(
            ["时间", "账号", "会话", "收到消息", "处理结果", "AI回复/错误"]
        )
        self.reply_table.horizontalHeader().setStretchLastSection(True)
        self.reply_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.event_table = QTableWidget(0, 5)
        self.event_table.setHorizontalHeaderLabels(["时间", "级别", "事件", "账号ID", "消息"])
        self.event_table.horizontalHeader().setStretchLastSection(True)
        self.event_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        splitter.addWidget(self.reply_table)
        splitter.addWidget(self.event_table)
        splitter.setSizes([260, 260])

        layout.addLayout(button_row)
        layout.addWidget(splitter)

    def _build_text_item(self, value, max_chars=120):
        text = str(value or "")
        item = QTableWidgetItem(truncate_text(text, max_chars=max_chars))
        if text:
            item.setToolTip(text)
        return item

    def _build_result_text(self, row):
        send_status = str(row["send_status"] or "").strip()
        task_status = str(row["task_status"] or "").strip()
        return send_status or task_status

    def _build_detail_text(self, row):
        error_message = str(row["error_message"] or "").strip()
        ai_reply_text = str(row["ai_reply_text"] or "").strip()
        return error_message or ai_reply_text

    def refresh(self):
        message_logs = self.repository.list_recent_message_logs()
        events = self.repository.list_recent_event_logs()

        self.reply_table.setRowCount(0)
        for row_index, row in enumerate(message_logs):
            self.reply_table.insertRow(row_index)
            self.reply_table.setItem(row_index, 0, self._build_text_item(row["created_at"], max_chars=32))
            self.reply_table.setItem(row_index, 1, self._build_text_item(row["account_id"], max_chars=16))
            self.reply_table.setItem(
                row_index,
                2,
                self._build_text_item(row["conversation_name"], max_chars=32),
            )
            self.reply_table.setItem(
                row_index,
                3,
                self._build_text_item(row["user_message"], max_chars=80),
            )
            self.reply_table.setItem(
                row_index,
                4,
                self._build_text_item(self._build_result_text(row), max_chars=24),
            )
            self.reply_table.setItem(
                row_index,
                5,
                self._build_text_item(self._build_detail_text(row), max_chars=120),
            )

        self.event_table.setRowCount(0)
        for row_index, row in enumerate(events):
            self.event_table.insertRow(row_index)
            self.event_table.setItem(row_index, 0, self._build_text_item(row["created_at"], max_chars=32))
            self.event_table.setItem(row_index, 1, self._build_text_item(row["level"], max_chars=16))
            self.event_table.setItem(row_index, 2, self._build_text_item(row["event_type"], max_chars=32))
            self.event_table.setItem(
                row_index,
                3,
                self._build_text_item(row["account_id"] or "", max_chars=16),
            )
            self.event_table.setItem(
                row_index,
                4,
                self._build_text_item(row["message"], max_chars=120),
            )
