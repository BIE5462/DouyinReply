"""调试页。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DebugTab(QWidget):
    poll_requested = Signal(int)
    prompt_preview_requested = Signal(int, str, str)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        top_row = QHBoxLayout()
        self.account_combo = QComboBox()
        poll_btn = QPushButton("手动轮询一次")
        preview_btn = QPushButton("预览提示词")
        poll_btn.clicked.connect(self._poll)
        preview_btn.clicked.connect(self._preview)
        top_row.addWidget(QLabel("账号"))
        top_row.addWidget(self.account_combo, 1)
        top_row.addWidget(poll_btn)
        top_row.addWidget(preview_btn)

        self.user_message_edit = QTextEdit()
        self.conversation_name_edit = QLineEdit()
        self.prompt_preview_edit = QTextEdit()
        self.prompt_preview_edit.setReadOnly(True)
        self.user_message_edit.setPlaceholderText("输入一条测试消息")
        self.conversation_name_edit.setPlaceholderText("输入会话名称，用于读取最近10条历史")

        layout.addLayout(top_row)
        layout.addWidget(QLabel("测试消息"))
        layout.addWidget(self.user_message_edit)
        layout.addWidget(QLabel("会话名称"))
        layout.addWidget(self.conversation_name_edit)
        layout.addWidget(QLabel("提示词预览"))
        layout.addWidget(self.prompt_preview_edit)

    def refresh_accounts(self):
        current_id = self.account_combo.currentData()
        self.account_combo.clear()
        for account in self.repository.list_accounts():
            self.account_combo.addItem(account.display_name, account.account_id)
        if current_id:
            index = self.account_combo.findData(current_id)
            if index >= 0:
                self.account_combo.setCurrentIndex(index)

    def set_prompt_preview(self, preview_text):
        self.prompt_preview_edit.setPlainText(preview_text)

    def _poll(self):
        account_id = self.account_combo.currentData()
        if account_id:
            self.poll_requested.emit(account_id)

    def _preview(self):
        account_id = self.account_combo.currentData()
        if account_id:
            self.prompt_preview_requested.emit(
                account_id,
                self.user_message_edit.toPlainText(),
                self.conversation_name_edit.text().strip(),
            )
