"""账号管理页。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import DEFAULT_CHAT_URL, DEFAULT_CONTEXT_MAX_CHARS, DEFAULT_CREATOR_URL
from ..models.entities import AccountConfig


class AccountsTab(QWidget):
    refresh_requested = Signal()
    open_login_requested = Signal(int)
    start_monitor_requested = Signal(int)
    pause_monitor_requested = Signal(int)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.current_account_id = None
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "账号名", "窗口名", "状态", "启用"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._load_selected_account)

        form_group = QGroupBox("账号配置")
        form = QFormLayout(form_group)
        self.display_name_edit = QLineEdit()
        self.browser_name_edit = QLineEdit()
        self.creator_url_edit = QLineEdit(DEFAULT_CREATOR_URL)
        self.chat_url_edit = QLineEdit(DEFAULT_CHAT_URL)
        self.enabled_checkbox = QCheckBox("启用账号")
        self.enabled_checkbox.setChecked(True)
        self.auto_reply_checkbox = QCheckBox("开启自动回复")
        self.auto_reply_checkbox.setChecked(True)
        self.manual_takeover_checkbox = QCheckBox("人工接管")
        self.context_max_chars_spin = QSpinBox()
        self.context_max_chars_spin.setRange(200, 5000)
        self.context_max_chars_spin.setValue(DEFAULT_CONTEXT_MAX_CHARS)
        self.status_label = QLabel("未配置")

        form.addRow("账号显示名", self.display_name_edit)
        form.addRow("BitBrowser 窗口名", self.browser_name_edit)
        form.addRow("创作者中心地址", self.creator_url_edit)
        form.addRow("私信页面地址", self.chat_url_edit)
        form.addRow("上下文最大字符数", self.context_max_chars_spin)
        form.addRow("状态", self.status_label)
        form.addRow("", self.enabled_checkbox)
        form.addRow("", self.auto_reply_checkbox)
        form.addRow("", self.manual_takeover_checkbox)

        button_row = QHBoxLayout()
        add_btn = QPushButton("新增账号")
        save_btn = QPushButton("保存账号")
        login_btn = QPushButton("登录/重登")
        start_btn = QPushButton("启动监控")
        pause_btn = QPushButton("暂停监控")
        refresh_btn = QPushButton("刷新")
        add_btn.clicked.connect(self._new_account)
        save_btn.clicked.connect(self._save_account)
        login_btn.clicked.connect(self._open_login)
        start_btn.clicked.connect(self._start_monitor)
        pause_btn.clicked.connect(self._pause_monitor)
        refresh_btn.clicked.connect(lambda: self.refresh_requested.emit())
        for button in [add_btn, save_btn, login_btn, start_btn, pause_btn, refresh_btn]:
            button_row.addWidget(button)

        right_layout = QVBoxLayout()
        right_layout.addWidget(form_group)
        right_layout.addLayout(button_row)
        right_layout.addStretch(1)

        layout.addWidget(self.table, 3)
        container = QWidget()
        container.setLayout(right_layout)
        layout.addWidget(container, 2)

    def refresh(self):
        accounts = self.repository.list_accounts()
        selected_account_id = self.current_account_id
        self.table.setRowCount(0)
        for row_index, account in enumerate(accounts):
            self.table.insertRow(row_index)
            self.table.setItem(row_index, 0, QTableWidgetItem(str(account.account_id)))
            self.table.setItem(row_index, 1, QTableWidgetItem(account.display_name))
            self.table.setItem(row_index, 2, QTableWidgetItem(account.browser_name))
            self.table.setItem(row_index, 3, QTableWidgetItem(account.status))
            self.table.setItem(row_index, 4, QTableWidgetItem("是" if account.enabled else "否"))
            if selected_account_id and account.account_id == selected_account_id:
                self.table.selectRow(row_index)
        if selected_account_id:
            self._load_selected_account()

    def _new_account(self):
        self.current_account_id = None
        self.display_name_edit.clear()
        self.browser_name_edit.clear()
        self.creator_url_edit.setText(DEFAULT_CREATOR_URL)
        self.chat_url_edit.setText(DEFAULT_CHAT_URL)
        self.enabled_checkbox.setChecked(True)
        self.auto_reply_checkbox.setChecked(True)
        self.manual_takeover_checkbox.setChecked(False)
        self.context_max_chars_spin.setValue(DEFAULT_CONTEXT_MAX_CHARS)
        self.status_label.setText("未配置")

    def _load_selected_account(self):
        items = self.table.selectedItems()
        if not items:
            return
        account_id = int(items[0].text())
        account = self.repository.get_account(account_id)
        if not account:
            return
        self.current_account_id = account.account_id
        self.display_name_edit.setText(account.display_name)
        self.browser_name_edit.setText(account.browser_name)
        self.creator_url_edit.setText(account.creator_url)
        self.chat_url_edit.setText(account.chat_url)
        self.enabled_checkbox.setChecked(account.enabled)
        self.auto_reply_checkbox.setChecked(account.auto_reply_enabled)
        self.manual_takeover_checkbox.setChecked(account.manual_takeover)
        self.context_max_chars_spin.setValue(account.context_max_chars)
        self.status_label.setText(account.status)

    def _save_account(self):
        if not self.display_name_edit.text().strip() or not self.browser_name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写账号显示名和窗口名。")
            return
        existing_account = (
            self.repository.get_account(self.current_account_id)
            if self.current_account_id
            else None
        )
        account = AccountConfig(
            account_id=self.current_account_id,
            display_name=self.display_name_edit.text().strip(),
            browser_name=self.browser_name_edit.text().strip(),
            creator_url=self.creator_url_edit.text().strip(),
            chat_url=self.chat_url_edit.text().strip(),
            enabled=self.enabled_checkbox.isChecked(),
            auto_reply_enabled=self.auto_reply_checkbox.isChecked(),
            manual_takeover=self.manual_takeover_checkbox.isChecked(),
            status=self.status_label.text() or "待登录",
            inherit_reply_policy=(
                existing_account.inherit_reply_policy if existing_account else True
            ),
            inherit_knowledge_profile=(
                existing_account.inherit_knowledge_profile if existing_account else True
            ),
            inherit_faq_items=(
                existing_account.inherit_faq_items if existing_account else True
            ),
            context_max_chars=self.context_max_chars_spin.value(),
        )
        saved_id = self.repository.save_account(account)
        self.current_account_id = saved_id
        self.refresh()
        self.refresh_requested.emit()

    def _open_login(self):
        if not self.current_account_id:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个账号。")
            return
        self.open_login_requested.emit(self.current_account_id)

    def _start_monitor(self):
        if not self.current_account_id:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个账号。")
            return
        self.start_monitor_requested.emit(self.current_account_id)

    def _pause_monitor(self):
        if not self.current_account_id:
            QMessageBox.warning(self, "提示", "请先在左侧选择一个账号。")
            return
        self.pause_monitor_requested.emit(self.current_account_id)
