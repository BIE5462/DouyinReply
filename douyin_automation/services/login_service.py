"""登录相关服务。"""

from ..config import DEFAULT_LOGIN_TIMEOUT
from ..utils.time_utils import now_iso
from .browser_runtime import LoginRequiredError


class LoginService:
    def __init__(self, repository, browser_runtime, event_handler):
        self.repository = repository
        self.browser_runtime = browser_runtime
        self.event_handler = event_handler

    def _emit(self, level, event_type, message, account_id=None, notify=False):
        self.repository.add_event_log(level, event_type, message, account_id=account_id)
        if self.event_handler:
            self.event_handler(level, event_type, message, account_id, notify)

    async def login_account(self, account_id, timeout=DEFAULT_LOGIN_TIMEOUT):
        account = self.repository.get_account(account_id)
        if not account:
            raise RuntimeError("账号不存在")

        self.repository.update_account_fields(
            account_id,
            status="待登录",
            last_error="",
            last_login_check_at=now_iso(),
        )
        self._emit("info", "login_start", f"开始登录账号：{account.display_name}", account_id)

        result = await self.browser_runtime.open_login(account, timeout)
        new_status = "就绪" if result["logged_in"] else "待登录"
        self.repository.update_account_fields(
            account_id,
            status=new_status,
            last_error="" if result["logged_in"] else "登录超时，请重新登录",
            last_browser_id=result["browser_id"],
            last_login_check_at=now_iso(),
        )
        self._emit(
            "info" if result["logged_in"] else "warning",
            "login_done",
            "登录成功，账号已就绪" if result["logged_in"] else "登录未完成，仍需人工登录",
            account_id,
            notify=not result["logged_in"],
        )
        return result["logged_in"]

    async def ensure_account_login(self, account_id):
        account = self.repository.get_account(account_id)
        if not account:
            raise RuntimeError("账号不存在")
        try:
            self._emit(
                "info",
                "login_check_start",
                "正在校验登录状态，并尝试拉起 BitBrowser 窗口。",
                account_id,
            )
            await self.browser_runtime.ensure_chat_page(account, create_if_missing=True)
            self.repository.update_account_fields(
                account_id,
                status="就绪",
                last_error="",
                last_login_check_at=now_iso(),
            )
            return True
        except LoginRequiredError as exc:
            self.repository.update_account_fields(
                account_id,
                status="待登录",
                last_error=str(exc),
                last_login_check_at=now_iso(),
            )
            self._emit(
                "warning",
                "login_required",
                "已打开账号窗口，但检测到登录未完成，请先在浏览器中登录后再启动监控。",
                account_id,
                notify=True,
            )
            return False
