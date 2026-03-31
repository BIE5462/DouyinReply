"""AI 设置页。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class AISettingsTab(QWidget):
    save_requested = Signal()
    test_requested = Signal(str)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form_group = QGroupBox("AI 设置")
        form = QFormLayout(form_group)

        self.base_url_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.model_edit = QLineEdit()
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 32000)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.test_prompt_edit = QLineEdit("请回复：配置测试成功")

        form.addRow("Base URL", self.base_url_edit)
        form.addRow("API Key", self.api_key_edit)
        form.addRow("模型", self.model_edit)
        form.addRow("Temperature", self.temperature_spin)
        form.addRow("Max Tokens", self.max_tokens_spin)
        form.addRow("超时时间（秒）", self.timeout_spin)
        form.addRow("测试提示词", self.test_prompt_edit)

        button_row = QHBoxLayout()
        save_btn = QPushButton("保存 AI 设置")
        test_btn = QPushButton("测试连通性")
        save_btn.clicked.connect(self._save)
        test_btn.clicked.connect(self._test)
        button_row.addWidget(save_btn)
        button_row.addWidget(test_btn)
        button_row.addStretch(1)

        layout.addWidget(form_group)
        layout.addLayout(button_row)
        layout.addStretch(1)

    def refresh(self):
        config = self.repository.get_global_ai_config()
        self.base_url_edit.setText(config.base_url)
        self.api_key_edit.setText(config.api_key)
        self.model_edit.setText(config.model)
        self.temperature_spin.setValue(config.temperature)
        self.max_tokens_spin.setValue(config.max_tokens)
        self.timeout_spin.setValue(config.timeout_seconds)

    def _save(self):
        config = self.repository.get_global_ai_config()
        config.base_url = self.base_url_edit.text().strip()
        config.api_key = self.api_key_edit.text().strip()
        config.model = self.model_edit.text().strip()
        config.temperature = self.temperature_spin.value()
        config.max_tokens = self.max_tokens_spin.value()
        config.timeout_seconds = self.timeout_spin.value()
        self.repository.save_global_ai_config(config)
        self.save_requested.emit()

    def _test(self):
        self.test_requested.emit(self.test_prompt_edit.text().strip() or "请回复：测试成功")
