"""仪表盘页。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DashboardTab(QWidget):
    start_all_clicked = Signal()
    pause_all_clicked = Signal()
    refresh_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        stats_group = QGroupBox("运行概览")
        grid = QGridLayout(stats_group)
        self.stats_labels = {}
        items = [
            ("账号总数", "account_total"),
            ("监控中账号", "monitor_total"),
            ("待登录账号", "pending_login_total"),
            ("异常账号", "error_total"),
            ("今日回复数", "today_reply_total"),
        ]
        for index, item in enumerate(items):
            title, stat_key = item
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(
                "font-size: 24px; font-weight: 700; padding: 16px; "
                "background: #f4f7fb; border: 1px solid #d9e2ef; border-radius: 8px;"
            )
            grid.addWidget(QLabel(title), index // 3 * 2, index % 3)
            grid.addWidget(value_label, index // 3 * 2 + 1, index % 3)
            self.stats_labels[stat_key] = value_label

        button_row = QHBoxLayout()
        start_btn = QPushButton("启动全部监控")
        pause_btn = QPushButton("暂停全部监控")
        refresh_btn = QPushButton("刷新概览")
        start_btn.clicked.connect(lambda: self.start_all_clicked.emit())
        pause_btn.clicked.connect(lambda: self.pause_all_clicked.emit())
        refresh_btn.clicked.connect(lambda: self.refresh_clicked.emit())
        button_row.addWidget(start_btn)
        button_row.addWidget(pause_btn)
        button_row.addWidget(refresh_btn)
        button_row.addStretch(1)

        self.error_table = QTableWidget(0, 4)
        self.error_table.setHorizontalHeaderLabels(["时间", "级别", "事件", "消息"])
        self.error_table.horizontalHeader().setStretchLastSection(True)
        self.error_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(stats_group)
        layout.addLayout(button_row)
        layout.addWidget(QLabel("最近事件"))
        layout.addWidget(self.error_table)

    def refresh(self, stats, logs):
        for key, label in self.stats_labels.items():
            label.setText(str(stats.get(key, 0)))
        self.error_table.setRowCount(0)
        for row_index, row in enumerate(logs[:20]):
            self.error_table.insertRow(row_index)
            self.error_table.setItem(row_index, 0, QTableWidgetItem(row["created_at"]))
            self.error_table.setItem(row_index, 1, QTableWidgetItem(row["level"]))
            self.error_table.setItem(row_index, 2, QTableWidgetItem(row["event_type"]))
            self.error_table.setItem(row_index, 3, QTableWidgetItem(row["message"]))
