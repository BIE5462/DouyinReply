"""桌面端主窗口。"""

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStyle,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..utils.paths import get_app_data_dir
from .accounts_tab import AccountsTab
from .ai_settings_tab import AISettingsTab
from .dashboard_tab import DashboardTab
from .debug_tab import DebugTab
from .logs_tab import LogsTab
from .rules_knowledge_tab import RulesKnowledgeTab


class MainWindow(QMainWindow):
    def __init__(self, orchestrator, show_onboarding=False, parent=None):
        super().__init__(parent)
        self.orchestrator = orchestrator
        self.repository = orchestrator.repository
        self.show_onboarding = show_onboarding
        self.allow_close = False
        self.has_minimize_tip = False
        self.tray_icon = None

        self._build_ui()
        self._connect_signals()
        self._setup_tray()
        self._setup_refresh_timer()
        self.refresh_all_views()

        app_data_dir = get_app_data_dir()
        self.statusBar().showMessage(f"数据目录：{app_data_dir}", 8000)
        if self.show_onboarding:
            QTimer.singleShot(300, self._show_onboarding_hint)

    def _build_ui(self):
        self.setWindowTitle("抖音消息自动回复系统")
        self.resize(1280, 860)
        self.setMinimumSize(1080, 720)

        self.dashboard_tab = DashboardTab(self)
        self.accounts_tab = AccountsTab(self.repository, self)
        self.rules_tab = RulesKnowledgeTab(self.repository, self)
        self.ai_tab = AISettingsTab(self.repository, self)
        self.logs_tab = LogsTab(self.repository, self)
        self.debug_tab = DebugTab(self.repository, self)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.dashboard_tab, "仪表盘")
        self.tabs.addTab(self.accounts_tab, "账号管理")
        self.tabs.addTab(self.rules_tab, "规则与知识")
        self.tabs.addTab(self.ai_tab, "AI 设置")
        self.tabs.addTab(self.logs_tab, "消息与日志")
        self.tabs.addTab(self.debug_tab, "调试")

        hint_label = QLabel(
            "建议顺序：先检查 AI 设置，再到账号管理绑定 BitBrowser 窗口并登录，"
            "最后补充 FAQ / 提示词并启动监控。关闭窗口后默认最小化到托盘继续运行。"
        )
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet(
            "padding: 10px 12px; background: #eef6ff; border: 1px solid #d5e5ff;"
            "border-radius: 8px; color: #24415e;"
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(hint_label)
        layout.addWidget(self.tabs)
        self.setCentralWidget(container)
        self.statusBar()

    def _connect_signals(self):
        self.tabs.currentChanged.connect(self._handle_tab_changed)

        self.dashboard_tab.start_all_clicked.connect(self.orchestrator.start_all)
        self.dashboard_tab.pause_all_clicked.connect(self.orchestrator.pause_all)
        self.dashboard_tab.refresh_clicked.connect(self.refresh_all_views)

        self.accounts_tab.refresh_requested.connect(self._handle_account_refresh)
        self.accounts_tab.open_login_requested.connect(self._open_login_for_account)
        self.accounts_tab.start_monitor_requested.connect(
            self._start_monitor_for_account
        )
        self.accounts_tab.pause_monitor_requested.connect(
            self._pause_monitor_for_account
        )

        self.ai_tab.save_requested.connect(self._handle_ai_config_saved)
        self.ai_tab.test_requested.connect(self.orchestrator.test_ai)

        self.rules_tab.refresh_requested.connect(self._handle_rules_saved)

        self.logs_tab.export_requested.connect(self._export_reply_records)

        self.debug_tab.poll_requested.connect(self.orchestrator.poll_account_once)
        self.debug_tab.prompt_preview_requested.connect(
            self.orchestrator.preview_prompt
        )

        self.orchestrator.data_changed.connect(self.refresh_runtime_views)
        self.orchestrator.event_emitted.connect(self._handle_event_emitted)
        self.orchestrator.notify_requested.connect(self._show_notification)
        self.orchestrator.ai_test_finished.connect(self._handle_ai_test_finished)
        self.orchestrator.prompt_preview_ready.connect(
            self.debug_tab.set_prompt_preview
        )

    def _setup_refresh_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(10000)
        self.refresh_timer.timeout.connect(self.refresh_runtime_views)
        self.refresh_timer.start()

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(
            self.style().standardIcon(QStyle.SP_ComputerIcon),
            self,
        )
        self.tray_icon.setToolTip("抖音消息自动回复系统")

        menu = QMenu(self)
        show_action = QAction("显示主窗口", self)
        start_action = QAction("启动全部监控", self)
        pause_action = QAction("暂停全部监控", self)
        refresh_action = QAction("刷新状态", self)
        quit_action = QAction("退出系统", self)

        show_action.triggered.connect(self._restore_from_tray)
        start_action.triggered.connect(self.orchestrator.start_all)
        pause_action.triggered.connect(self.orchestrator.pause_all)
        refresh_action.triggered.connect(self.refresh_all_views)
        quit_action.triggered.connect(self._quit_application)

        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(start_action)
        menu.addAction(pause_action)
        menu.addAction(refresh_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._handle_tray_activated)
        self.tray_icon.show()

    def refresh_runtime_views(self):
        stats = self.repository.dashboard_stats()
        events = self.repository.list_recent_event_logs(limit=20)
        self.dashboard_tab.refresh(stats, events)
        self.logs_tab.refresh()

    def refresh_all_views(self):
        self.refresh_runtime_views()
        self.accounts_tab.refresh()
        self.rules_tab.refresh_accounts()
        self.ai_tab.refresh()
        self.debug_tab.refresh_accounts()

    def _handle_tab_changed(self, _index):
        current_widget = self.tabs.currentWidget()
        if current_widget is self.accounts_tab:
            self.accounts_tab.refresh()
        elif current_widget is self.rules_tab:
            self.rules_tab.refresh_accounts()
        elif current_widget is self.ai_tab:
            self.ai_tab.refresh()
        elif current_widget is self.logs_tab:
            self.logs_tab.refresh()
        elif current_widget is self.debug_tab:
            self.debug_tab.refresh_accounts()
        else:
            self.refresh_runtime_views()

    def _handle_account_refresh(self):
        self.refresh_all_views()
        self.statusBar().showMessage("账号列表已刷新。", 4000)

    def _start_monitor_for_account(self, account_id):
        account = self.repository.get_account(account_id)
        if not account:
            QMessageBox.warning(self, "提示", "未找到对应账号配置。")
            return
        try:
            self.orchestrator.start_account(account_id)
        except Exception as exc:
            QMessageBox.warning(self, "启动失败", f"提交启动监控任务失败：{exc}")
            return
        self.statusBar().showMessage(
            f"已提交账号「{account.display_name}」的启动监控请求，正在尝试拉起 BitBrowser 并校验登录状态。",
            8000,
        )

    def _pause_monitor_for_account(self, account_id):
        account = self.repository.get_account(account_id)
        if not account:
            QMessageBox.warning(self, "提示", "未找到对应账号配置。")
            return
        try:
            self.orchestrator.pause_account(account_id)
        except Exception as exc:
            QMessageBox.warning(self, "暂停失败", f"提交暂停监控任务失败：{exc}")
            return
        self.statusBar().showMessage(
            f"已提交账号「{account.display_name}」的暂停监控请求。",
            5000,
        )

    def _handle_ai_config_saved(self):
        self.statusBar().showMessage("AI 配置已保存。", 4000)

    def _handle_rules_saved(self):
        self.statusBar().showMessage("规则与知识配置已保存。", 4000)
        self.refresh_runtime_views()

    def _open_login_for_account(self, account_id):
        account = self.repository.get_account(account_id)
        if not account:
            QMessageBox.warning(self, "提示", "未找到对应账号配置。")
            return
        self.orchestrator.open_login(account_id)
        self.statusBar().showMessage(
            f"正在打开账号「{account.display_name}」的 BitBrowser 窗口，请完成登录。",
            8000,
        )

    def _handle_event_emitted(self, level, event_type, account_id, message):
        account_prefix = f"[账号 {account_id}] " if account_id else ""
        timeout = 10000 if level in {"error", "warning"} else 5000
        self.statusBar().showMessage(
            f"{account_prefix}{event_type}: {message}",
            timeout,
        )

    def _handle_ai_test_finished(self, success, message):
        if success:
            QMessageBox.information(self, "AI 连通性测试", message)
        else:
            QMessageBox.warning(self, "AI 连通性测试失败", message)

    def _show_notification(self, title, message):
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)
            return
        self.statusBar().showMessage(f"{title}: {message}", 8000)

    def _show_onboarding_hint(self):
        QMessageBox.information(
            self,
            "首次使用提示",
            "建议按以下顺序完成首次配置：\n"
            "1. 在“AI 设置”页确认兼容接口与模型可用。\n"
            "2. 在“账号管理”页点击“登录/重登”打开对应 BitBrowser 窗口。\n"
            "3. 完成人工登录后，再启动监控。\n"
            "4. 在“规则与知识”页补充系统提示词、店铺资料和 FAQ。",
        )

    def _export_reply_records(self):
        default_path = get_app_data_dir() / "reply_records_export.csv"
        csv_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出回复日志",
            str(default_path),
            "CSV 文件 (*.csv)",
        )
        if not csv_path:
            return
        try:
            self.repository.export_reply_records_csv(csv_path)
        except Exception as exc:
            QMessageBox.warning(self, "导出失败", f"导出回复日志失败：{exc}")
            return
        QMessageBox.information(self, "导出成功", f"回复日志已导出到：\n{csv_path}")

    def _handle_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
        ):
            if self.isVisible():
                self.hide()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_application(self):
        self.allow_close = True
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.instance().quit()

    def closeEvent(self, event: QCloseEvent):
        if self.allow_close or not self.tray_icon or not self.tray_icon.isVisible():
            super().closeEvent(event)
            return

        self.hide()
        event.ignore()
        if not self.has_minimize_tip:
            self.has_minimize_tip = True
            self._show_notification(
                "系统仍在运行",
                "窗口已最小化到托盘，监控任务会继续执行。",
            )
