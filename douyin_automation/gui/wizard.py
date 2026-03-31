"""首次启动引导。"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from ..config import (
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MAX_TOKENS,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_TEMPERATURE,
    DEFAULT_AI_TIMEOUT_SECONDS,
    DEFAULT_BROWSER_NAME,
    DEFAULT_CHAT_URL,
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_CREATOR_URL,
)
from ..models.entities import AccountConfig, GlobalAIConfig


class FirstRunDialog(QDialog):
    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.setWindowTitle("首次启动引导")
        self.resize(520, 360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.base_url_edit = QLineEdit(DEFAULT_AI_BASE_URL)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.model_edit = QLineEdit(DEFAULT_AI_MODEL)
        self.temperature_edit = QLineEdit(str(DEFAULT_AI_TEMPERATURE))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 32000)
        self.max_tokens_spin.setValue(DEFAULT_AI_MAX_TOKENS)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(DEFAULT_AI_TIMEOUT_SECONDS)

        self.account_name_edit = QLineEdit("默认账号")
        self.browser_name_edit = QLineEdit(DEFAULT_BROWSER_NAME)
        self.creator_url_edit = QLineEdit(DEFAULT_CREATOR_URL)
        self.chat_url_edit = QLineEdit(DEFAULT_CHAT_URL)
        self.context_max_chars_spin = QSpinBox()
        self.context_max_chars_spin.setRange(200, 5000)
        self.context_max_chars_spin.setValue(DEFAULT_CONTEXT_MAX_CHARS)
        self.enabled_checkbox = QCheckBox("启用账号")
        self.enabled_checkbox.setChecked(True)

        form.addRow("AI Base URL", self.base_url_edit)
        form.addRow("AI API Key", self.api_key_edit)
        form.addRow("AI 模型", self.model_edit)
        form.addRow("Temperature", self.temperature_edit)
        form.addRow("Max Tokens", self.max_tokens_spin)
        form.addRow("超时时间（秒）", self.timeout_spin)
        form.addRow("账号显示名", self.account_name_edit)
        form.addRow("BitBrowser 窗口名", self.browser_name_edit)
        form.addRow("创作者中心地址", self.creator_url_edit)
        form.addRow("私信页面地址", self.chat_url_edit)
        form.addRow("上下文最大字符数", self.context_max_chars_spin)
        form.addRow("", self.enabled_checkbox)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._handle_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _handle_accept(self):
        if not self.api_key_edit.text().strip():
            QMessageBox.warning(self, "提示", "请先填写 AI API Key。")
            return
        if not self.base_url_edit.text().strip() or not self.model_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写完整的 AI 配置。")
            return
        if not self.account_name_edit.text().strip() or not self.browser_name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请至少填写一个初始账号。")
            return

        ai_config = GlobalAIConfig(
            base_url=self.base_url_edit.text().strip(),
            api_key=self.api_key_edit.text().strip(),
            model=self.model_edit.text().strip(),
            temperature=float(self.temperature_edit.text().strip() or "0.7"),
            max_tokens=self.max_tokens_spin.value(),
            timeout_seconds=self.timeout_spin.value(),
        )
        self.repository.save_global_ai_config(ai_config)

        account = AccountConfig(
            display_name=self.account_name_edit.text().strip(),
            browser_name=self.browser_name_edit.text().strip(),
            creator_url=self.creator_url_edit.text().strip(),
            chat_url=self.chat_url_edit.text().strip(),
            enabled=self.enabled_checkbox.isChecked(),
            auto_reply_enabled=True,
            status="待登录",
            context_max_chars=self.context_max_chars_spin.value(),
        )
        self.repository.save_account(account)
        self.accept()
