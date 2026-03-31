"""规则与知识页。"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ..models.entities import FAQItem, KnowledgeProfile, ReplyPolicy
from ..utils.time_utils import parse_hhmm

GLOBAL_TEMPLATE_SCOPE = "__global_template__"


class RulesKnowledgeTab(QWidget):
    refresh_requested = Signal()

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._loading = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        account_row = QHBoxLayout()
        self.account_combo = QComboBox()
        self.account_combo.currentIndexChanged.connect(
            lambda _index: self._load_selected_account()
        )
        save_btn = QPushButton("保存规则与知识")
        save_btn.clicked.connect(self._save_current)
        account_row.addWidget(QLabel("编辑范围"))
        account_row.addWidget(self.account_combo, 1)
        account_row.addWidget(save_btn)

        self.scope_hint_label = QLabel()
        self.scope_hint_label.setWordWrap(True)

        inherit_group = QGroupBox("账号覆盖策略")
        inherit_layout = QVBoxLayout(inherit_group)
        self.inherit_policy_checkbox = QCheckBox("当前账号继承全局规则")
        self.inherit_knowledge_checkbox = QCheckBox("当前账号继承全局知识")
        self.inherit_faq_checkbox = QCheckBox("当前账号继承全局 FAQ")
        for checkbox in (
            self.inherit_policy_checkbox,
            self.inherit_knowledge_checkbox,
            self.inherit_faq_checkbox,
        ):
            checkbox.toggled.connect(lambda _checked: self._handle_override_toggle())
            inherit_layout.addWidget(checkbox)
        self.inherit_group = inherit_group

        form_group = QGroupBox("规则与知识")
        form = QFormLayout(form_group)
        self.system_prompt_edit = QTextEdit()
        self.business_summary_edit = QTextEdit()
        self.tone_style_edit = QLineEdit()
        self.work_start_edit = QTimeEdit()
        self.work_end_edit = QTimeEdit()
        self.cooldown_spin = QSpinBox()
        self.cooldown_spin.setRange(0, 86400)
        self.daily_limit_spin = QSpinBox()
        self.daily_limit_spin.setRange(1, 100000)
        self.blacklist_edit = QPlainTextEdit()
        self.whitelist_edit = QPlainTextEdit()
        self.policy_manual_checkbox = QCheckBox("规则层人工接管")

        form.addRow("系统提示词", self.system_prompt_edit)
        form.addRow("店铺/业务信息", self.business_summary_edit)
        form.addRow("语气要求", self.tone_style_edit)
        form.addRow("工作开始时间", self.work_start_edit)
        form.addRow("工作结束时间", self.work_end_edit)
        form.addRow("冷却时间（秒）", self.cooldown_spin)
        form.addRow("每日上限", self.daily_limit_spin)
        form.addRow("黑名单关键词（每行或逗号分隔）", self.blacklist_edit)
        form.addRow("白名单关键词（每行或逗号分隔）", self.whitelist_edit)
        form.addRow("", self.policy_manual_checkbox)

        faq_group = QGroupBox("FAQ 列表")
        faq_layout = QVBoxLayout(faq_group)
        self.faq_table = QTableWidget(0, 4)
        self.faq_table.setHorizontalHeaderLabels(
            ["问题", "标准答案", "触发关键词", "启用"]
        )
        self.faq_table.horizontalHeader().setStretchLastSection(True)
        faq_buttons = QHBoxLayout()
        self.add_faq_btn = QPushButton("新增 FAQ")
        self.remove_faq_btn = QPushButton("删除 FAQ")
        self.add_faq_btn.clicked.connect(lambda: self._add_faq_row())
        self.remove_faq_btn.clicked.connect(lambda: self._remove_faq_row())
        faq_buttons.addWidget(self.add_faq_btn)
        faq_buttons.addWidget(self.remove_faq_btn)
        faq_buttons.addStretch(1)
        faq_layout.addWidget(self.faq_table)
        faq_layout.addLayout(faq_buttons)

        layout.addLayout(account_row)
        layout.addWidget(self.scope_hint_label)
        layout.addWidget(self.inherit_group)
        layout.addWidget(form_group)
        layout.addWidget(faq_group)

    def refresh_accounts(self):
        current_scope = self.account_combo.currentData()
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        self.account_combo.addItem("全局模板", GLOBAL_TEMPLATE_SCOPE)
        for account in self.repository.list_accounts():
            self.account_combo.addItem(account.display_name, account.account_id)
        self.account_combo.blockSignals(False)
        index = self.account_combo.findData(current_scope)
        if index < 0:
            index = 0
        if self.account_combo.count() > 0:
            self.account_combo.setCurrentIndex(index)
            self._load_selected_account()

    def _selected_account_id(self):
        scope = self.account_combo.currentData()
        if scope == GLOBAL_TEMPLATE_SCOPE:
            return None
        return scope

    def _set_knowledge_form(self, knowledge):
        self.system_prompt_edit.setPlainText(knowledge.system_prompt)
        self.business_summary_edit.setPlainText(knowledge.business_summary)
        self.tone_style_edit.setText(knowledge.tone_style)

    def _set_policy_form(self, policy):
        self.work_start_edit.setTime(parse_hhmm(policy.work_start))
        self.work_end_edit.setTime(parse_hhmm(policy.work_end))
        self.cooldown_spin.setValue(policy.cooldown_seconds)
        self.daily_limit_spin.setValue(policy.daily_limit)
        self.blacklist_edit.setPlainText(policy.blacklist_keywords)
        self.whitelist_edit.setPlainText(policy.whitelist_keywords)
        self.policy_manual_checkbox.setChecked(policy.manual_takeover)

    def _set_faq_rows(self, faqs):
        self.faq_table.setRowCount(0)
        for faq in faqs:
            self._add_faq_row(faq)

    def _load_selected_account(self):
        if self.account_combo.count() == 0:
            return
        account_id = self._selected_account_id()
        is_global_scope = account_id is None
        self._loading = True
        if is_global_scope:
            knowledge = self.repository.get_global_knowledge_profile()
            policy = self.repository.get_global_reply_policy()
            faqs = self.repository.list_global_faq_items()
            self.inherit_policy_checkbox.setChecked(False)
            self.inherit_knowledge_checkbox.setChecked(False)
            self.inherit_faq_checkbox.setChecked(False)
        else:
            account = self.repository.get_account(account_id)
            if not account:
                self._loading = False
                return
            self.inherit_policy_checkbox.setChecked(account.inherit_reply_policy)
            self.inherit_knowledge_checkbox.setChecked(
                account.inherit_knowledge_profile
            )
            self.inherit_faq_checkbox.setChecked(account.inherit_faq_items)

            if account.inherit_knowledge_profile:
                knowledge = self.repository.get_global_knowledge_profile()
            else:
                knowledge = (
                    self.repository.get_knowledge_profile_override(account_id)
                    or self.repository.get_global_knowledge_profile()
                )

            if account.inherit_reply_policy:
                policy = self.repository.get_global_reply_policy()
            else:
                policy = (
                    self.repository.get_reply_policy_override(account_id)
                    or self.repository.get_global_reply_policy()
                )

            if account.inherit_faq_items:
                faqs = self.repository.list_global_faq_items()
            else:
                faqs = self.repository.list_faq_items_override(account_id)

        self._set_knowledge_form(knowledge)
        self._set_policy_form(policy)
        self._set_faq_rows(faqs)
        self._loading = False
        self._apply_override_state()

    def _apply_override_state(self):
        account_id = self._selected_account_id()
        is_global_scope = account_id is None
        self.inherit_group.setVisible(not is_global_scope)

        if is_global_scope:
            self.scope_hint_label.setText(
                "正在编辑全局模板。所有开启继承的账号都会使用这里的规则、知识和 FAQ。"
            )
        else:
            self.scope_hint_label.setText(
                "当前账号可按规则、知识、FAQ 三个部分分别继承全局模板，或关闭继承后保存自己的覆盖配置。"
            )

        knowledge_editable = is_global_scope or not self.inherit_knowledge_checkbox.isChecked()
        for widget in (
            self.system_prompt_edit,
            self.business_summary_edit,
            self.tone_style_edit,
        ):
            widget.setEnabled(knowledge_editable)

        policy_editable = is_global_scope or not self.inherit_policy_checkbox.isChecked()
        for widget in (
            self.work_start_edit,
            self.work_end_edit,
            self.cooldown_spin,
            self.daily_limit_spin,
            self.blacklist_edit,
            self.whitelist_edit,
            self.policy_manual_checkbox,
        ):
            widget.setEnabled(policy_editable)

        faq_editable = is_global_scope or not self.inherit_faq_checkbox.isChecked()
        self.faq_table.setEnabled(faq_editable)
        self.add_faq_btn.setEnabled(faq_editable)
        self.remove_faq_btn.setEnabled(faq_editable)

    def _handle_override_toggle(self):
        if self._loading:
            return
        account_id = self._selected_account_id()
        if account_id is None:
            self._apply_override_state()
            return

        self._loading = True
        account = self.repository.get_account(account_id)
        if self.inherit_knowledge_checkbox.isChecked():
            self._set_knowledge_form(self.repository.get_global_knowledge_profile())
        else:
            self._set_knowledge_form(
                self.repository.get_knowledge_profile_override(account_id)
                or self.repository.get_global_knowledge_profile()
            )

        if self.inherit_policy_checkbox.isChecked():
            self._set_policy_form(self.repository.get_global_reply_policy())
        else:
            self._set_policy_form(
                self.repository.get_reply_policy_override(account_id)
                or self.repository.get_global_reply_policy()
            )

        if self.inherit_faq_checkbox.isChecked():
            self._set_faq_rows(self.repository.list_global_faq_items())
        else:
            raw_faq_items = self.repository.list_faq_items_override(account_id)
            if raw_faq_items or (account and not account.inherit_faq_items):
                self._set_faq_rows(raw_faq_items)
        self._loading = False
        self._apply_override_state()

    def _add_faq_row(self, faq=None):
        row = self.faq_table.rowCount()
        self.faq_table.insertRow(row)
        values = [
            faq.question if faq else "",
            faq.answer if faq else "",
            faq.keywords if faq else "",
            "1" if (faq.enabled if faq else True) else "0",
        ]
        for column, value in enumerate(values):
            self.faq_table.setItem(row, column, QTableWidgetItem(value))

    def _remove_faq_row(self):
        row = self.faq_table.currentRow()
        if row >= 0:
            self.faq_table.removeRow(row)

    def _build_policy_from_form(self, account_id):
        return ReplyPolicy(
            account_id=account_id,
            work_start=self.work_start_edit.time().toString("HH:mm"),
            work_end=self.work_end_edit.time().toString("HH:mm"),
            cooldown_seconds=self.cooldown_spin.value(),
            daily_limit=self.daily_limit_spin.value(),
            blacklist_keywords=self.blacklist_edit.toPlainText(),
            whitelist_keywords=self.whitelist_edit.toPlainText(),
            manual_takeover=self.policy_manual_checkbox.isChecked(),
        )

    def _build_knowledge_from_form(self, account_id):
        return KnowledgeProfile(
            account_id=account_id,
            system_prompt=self.system_prompt_edit.toPlainText(),
            business_summary=self.business_summary_edit.toPlainText(),
            tone_style=self.tone_style_edit.text().strip(),
        )

    def _build_faq_items_from_form(self, account_id):
        faq_items = []
        for row in range(self.faq_table.rowCount()):
            faq_items.append(
                FAQItem(
                    account_id=account_id,
                    question=(
                        self.faq_table.item(row, 0).text()
                        if self.faq_table.item(row, 0)
                        else ""
                    ),
                    answer=(
                        self.faq_table.item(row, 1).text()
                        if self.faq_table.item(row, 1)
                        else ""
                    ),
                    keywords=(
                        self.faq_table.item(row, 2).text()
                        if self.faq_table.item(row, 2)
                        else ""
                    ),
                    enabled=(
                        self.faq_table.item(row, 3).text().strip() != "0"
                        if self.faq_table.item(row, 3)
                        else True
                    ),
                )
            )
        return faq_items

    def _save_current(self):
        if self.account_combo.count() == 0:
            return
        account_id = self._selected_account_id()
        if account_id is None:
            self.repository.save_global_reply_policy(
                self._build_policy_from_form(account_id=None)
            )
            self.repository.save_global_knowledge_profile(
                self._build_knowledge_from_form(account_id=None)
            )
            self.repository.replace_global_faq_items(
                self._build_faq_items_from_form(account_id=None)
            )
        else:
            inherit_policy = self.inherit_policy_checkbox.isChecked()
            inherit_knowledge = self.inherit_knowledge_checkbox.isChecked()
            inherit_faq = self.inherit_faq_checkbox.isChecked()
            self.repository.update_account_fields(
                account_id,
                inherit_reply_policy=int(inherit_policy),
                inherit_knowledge_profile=int(inherit_knowledge),
                inherit_faq_items=int(inherit_faq),
            )

            if inherit_policy:
                self.repository.delete_reply_policy_override(account_id)
            else:
                self.repository.save_reply_policy(
                    self._build_policy_from_form(account_id=account_id)
                )

            if inherit_knowledge:
                self.repository.delete_knowledge_profile_override(account_id)
            else:
                self.repository.save_knowledge_profile(
                    self._build_knowledge_from_form(account_id=account_id)
                )

            if inherit_faq:
                self.repository.delete_faq_items_override(account_id)
            else:
                self.repository.replace_faq_items(
                    account_id,
                    self._build_faq_items_from_form(account_id=account_id),
                )

        self._load_selected_account()
        self.refresh_requested.emit()
