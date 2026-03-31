"""后台调度器与 QThread 异步桥接。"""

import asyncio
import threading
from concurrent.futures import Future

from PySide6.QtCore import QObject, QThread, Signal

from ..storage.database import AppRepository, DatabaseManager
from ..utils.paths import get_db_path
from .browser_runtime import BrowserRuntimeService
from .login_service import LoginService
from .monitor_service import MonitorService
from .reply_service import ReplyService


class BackendLoopThread(QThread):
    def __init__(self):
        super().__init__()
        self.loop = None
        self.loop_ready = threading.Event()

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop_ready.set()
        self.loop.run_forever()
        pending_tasks = asyncio.all_tasks(self.loop)
        for task in pending_tasks:
            task.cancel()
        if pending_tasks:
            self.loop.run_until_complete(
                asyncio.gather(*pending_tasks, return_exceptions=True)
            )
        asyncio.set_event_loop(None)
        self.loop.close()
        self.loop = None
        self.loop_ready.clear()

    def wait_until_ready(self, timeout=5.0):
        return self.loop_ready.wait(timeout)

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait(2000)


class BackendOrchestrator(QObject):
    data_changed = Signal()
    account_status_changed = Signal(int, str, str)
    event_emitted = Signal(str, str, int, str)
    notify_requested = Signal(str, str)
    ai_test_finished = Signal(bool, str)
    prompt_preview_ready = Signal(str)

    def __init__(self, db_path=None):
        super().__init__()
        self.db_manager = DatabaseManager(db_path or get_db_path())
        self.repository = AppRepository(self.db_manager)
        self.thread = BackendLoopThread()
        self.thread.start()
        if not self.thread.wait_until_ready():
            raise RuntimeError("后台事件循环初始化失败。")
        self._shutdown_started = False

        self.browser_runtime = BrowserRuntimeService(
            self.repository,
            event_handler=self._handle_event,
        )
        self.reply_service = ReplyService(
            self.repository,
            self.browser_runtime,
            event_handler=self._handle_event,
        )
        self.login_service = LoginService(
            self.repository,
            self.browser_runtime,
            event_handler=self._handle_event,
        )
        self.monitor_service = MonitorService(
            self.repository,
            self.browser_runtime,
            self.login_service,
            self.reply_service,
            event_handler=self._handle_event,
        )

    def _handle_event(self, level, event_type, message, account_id=None, notify=False):
        safe_account_id = int(account_id or 0)
        self.event_emitted.emit(level, event_type, safe_account_id, message)
        if safe_account_id:
            account = self.repository.get_account(safe_account_id)
            if account:
                self.account_status_changed.emit(
                    safe_account_id,
                    account.status,
                    account.last_error,
                )
        self.data_changed.emit()
        if notify:
            self.notify_requested.emit(event_type, message)

    def submit_coroutine(self, coro, on_success=None, on_error=None) -> Future:
        if self._shutdown_started:
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("后台服务已停止，无法提交新任务。")
        if not self.thread.loop or not self.thread.isRunning():
            if hasattr(coro, "close"):
                coro.close()
            raise RuntimeError("后台事件循环未就绪。")
        future = asyncio.run_coroutine_threadsafe(coro, self.thread.loop)

        def _done_callback(done_future):
            try:
                result = done_future.result()
                if on_success:
                    on_success(result)
            except Exception as exc:
                if on_error:
                    on_error(exc)
                else:
                    self._handle_event("error", "backend_error", str(exc), None, True)

        future.add_done_callback(_done_callback)
        return future

    def start_all(self):
        self.submit_coroutine(self.monitor_service.start_all())

    def pause_all(self):
        self.submit_coroutine(self.monitor_service.pause_all())

    def start_account(self, account_id):
        self.submit_coroutine(self.monitor_service.start_account(account_id))

    def pause_account(self, account_id):
        self.submit_coroutine(self.monitor_service.pause_account(account_id))

    def open_login(self, account_id):
        self.submit_coroutine(self.login_service.login_account(account_id))

    def poll_account_once(self, account_id):
        self.submit_coroutine(self.monitor_service.poll_account_once(account_id))

    def test_ai(self, prompt_text):
        self.submit_coroutine(
            self.reply_service.test_ai(prompt_text),
            on_success=lambda result: self.ai_test_finished.emit(True, result),
            on_error=lambda exc: self.ai_test_finished.emit(False, str(exc)),
        )

    def preview_prompt(self, account_id, user_message, conversation_name):
        self.submit_coroutine(
            self.reply_service.preview_prompt(
                account_id,
                user_message,
                conversation_name,
            ),
            on_success=lambda result: self.prompt_preview_ready.emit(result),
            on_error=lambda exc: self.prompt_preview_ready.emit(f"提示词预览失败：{exc}"),
        )

    def shutdown(self):
        if self._shutdown_started:
            return
        self._shutdown_started = True

        try:
            if self.thread.loop and self.thread.isRunning():
                async def _shutdown():
                    await self.monitor_service.pause_all()
                    await self.browser_runtime.close()

                future = asyncio.run_coroutine_threadsafe(
                    _shutdown(),
                    self.thread.loop,
                )
                try:
                    future.result(timeout=15)
                except Exception as exc:
                    self._handle_event(
                        "warning",
                        "shutdown_warning",
                        f"后台关闭阶段出现异常：{exc}",
                        None,
                        False,
                    )
        finally:
            self.thread.stop()
