"""账号监控循环。"""

import asyncio

from ..models.entities import ConversationMessage, ConversationSnapshot
from ..utils.fingerprints import build_conversation_fingerprint
from ..utils.text import truncate_text
from ..utils.time_utils import now_iso
from .browser_runtime import LoginRequiredError


class MonitorService:
    def __init__(self, repository, browser_runtime, login_service, reply_service, event_handler=None):
        self.repository = repository
        self.browser_runtime = browser_runtime
        self.login_service = login_service
        self.reply_service = reply_service
        self.event_handler = event_handler
        self._tasks = {}
        self._session_bootstrap_pending = set()

    def _emit(self, level, event_type, message, account_id=None, notify=False):
        self.repository.add_event_log(level, event_type, message, account_id=account_id)
        if self.event_handler:
            self.event_handler(level, event_type, message, account_id, notify)

    async def start_all(self):
        for account in self.repository.list_accounts():
            if account.enabled:
                await self.start_account(account.account_id)

    async def pause_all(self):
        for account_id in list(self._tasks.keys()):
            await self.pause_account(account_id)

    async def start_account(self, account_id):
        if account_id in self._tasks and not self._tasks[account_id].done():
            self._emit("info", "monitor_start_skipped", "账号已在监控中。", account_id)
            return
        account = self.repository.get_account(account_id)
        if not account:
            raise RuntimeError("账号不存在")
        self.repository.update_account_fields(account_id, status="监控中", last_error="")
        self._session_bootstrap_pending.add(account_id)
        self._emit("info", "monitor_start", f"开始监控账号：{account.display_name}", account_id)
        self._tasks[account_id] = asyncio.create_task(self._monitor_loop(account_id))

    async def pause_account(self, account_id):
        task = self._tasks.pop(account_id, None)
        self._session_bootstrap_pending.discard(account_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.repository.update_account_fields(account_id, status="暂停")
        self._emit("info", "monitor_pause", "账号监控已暂停", account_id)

    async def poll_account_once(self, account_id):
        await self._poll_account(account_id)

    async def _monitor_loop(self, account_id):
        try:
            while True:
                account = self.repository.get_account(account_id)
                if not account or not account.enabled:
                    self.repository.update_account_fields(account_id, status="暂停")
                    return
                policy = self.repository.get_reply_policy(account_id)
                try:
                    await self._poll_account(account_id)
                except asyncio.CancelledError:
                    raise
                except LoginRequiredError as exc:
                    self.repository.update_account_fields(
                        account_id,
                        status="待登录",
                        last_error=str(exc),
                        last_monitor_at=now_iso(),
                    )
                    self._emit("warning", "login_required", str(exc), account_id, notify=True)
                    return
                except Exception as exc:
                    self.repository.update_account_fields(
                        account_id,
                        status="异常",
                        last_error=str(exc),
                        last_monitor_at=now_iso(),
                    )
                    self._emit("error", "monitor_error", f"监控异常：{exc}", account_id, notify=True)
                    return
                await asyncio.sleep(policy.monitor_interval_seconds)
        finally:
            self._session_bootstrap_pending.discard(account_id)

    async def _poll_account(self, account_id):
        account = self.repository.get_account(account_id)
        if not account:
            raise RuntimeError("账号不存在")

        logged_in = await self.login_service.ensure_account_login(account_id)
        if not logged_in:
            raise LoginRequiredError("账号登录已失效，请重新登录。")

        conversations = await self.browser_runtime.fetch_conversation_list(account)
        now_text = now_iso()
        changed_items = []
        for item in conversations:
            conversation_name = (item.get("name") or "").strip()
            last_message_text = (item.get("lastMsg") or "").strip()
            time_label = (item.get("time") or "").strip()
            if not conversation_name or not last_message_text:
                continue

            fingerprint = build_conversation_fingerprint(
                account_id,
                conversation_name,
                last_message_text,
                time_label,
            )
            snapshot = ConversationSnapshot(
                account_id=account_id,
                conversation_name=conversation_name,
                last_message_text=last_message_text,
                time_label=time_label,
                fingerprint=fingerprint,
                observed_at=now_text,
            )
            previous = self.repository.get_snapshot(account_id, conversation_name)
            self.repository.save_snapshot(snapshot)

            if not account.bootstrap_completed:
                continue

            previous_fingerprint = previous["fingerprint"] if previous else ""
            if previous_fingerprint == fingerprint:
                continue
            if account.last_outbound_text and last_message_text == account.last_outbound_text:
                continue
            if account.last_replied_fingerprint and fingerprint == account.last_replied_fingerprint:
                continue
            changed_items.append(snapshot)

        if account_id in self._session_bootstrap_pending:
            self._session_bootstrap_pending.discard(account_id)
            update_fields = {
                "status": "监控中",
                "last_error": "",
                "last_monitor_at": now_text,
            }
            if not account.bootstrap_completed:
                update_fields["bootstrap_completed"] = 1
            self.repository.update_account_fields(account_id, **update_fields)
            self._emit(
                "info",
                "monitor_session_bootstrap",
                "本次启动已建立消息基线，启动前的历史消息不会自动回复。",
                account_id,
            )
            return

        if not account.bootstrap_completed:
            self.repository.update_account_fields(
                account_id,
                bootstrap_completed=1,
                status="监控中",
                last_monitor_at=now_text,
            )
            self._emit(
                "info",
                "monitor_bootstrap",
                "首次监控已建立基线，不会对历史消息自动回复。",
                account_id,
            )
            return

        for snapshot in changed_items:
            raw_messages = await self.browser_runtime.fetch_conversation_messages(
                account,
                snapshot.conversation_name,
            )
            conversation_messages = [
                ConversationMessage(
                    account_id=account_id,
                    conversation_name=snapshot.conversation_name,
                    role=item.get("role", "user"),
                    message_text=item.get("message_text", ""),
                    observed_at=now_text,
                )
                for item in raw_messages
                if item.get("role") in {"user", "assistant"}
                and (item.get("message_text") or "").strip()
            ]
            if conversation_messages:
                self.repository.replace_conversation_messages(
                    account_id,
                    snapshot.conversation_name,
                    conversation_messages,
                )
            message_summary = truncate_text(snapshot.last_message_text, max_chars=80)
            self._emit(
                "info",
                "message_received",
                f"会话 {snapshot.conversation_name} 收到新消息：{message_summary}",
                account_id,
            )

            await self.reply_service.handle_new_message(
                account_id=account_id,
                conversation_name=snapshot.conversation_name,
                user_message=snapshot.last_message_text,
                conversation_messages=conversation_messages,
                fingerprint=snapshot.fingerprint,
            )

        last_seen = changed_items[-1].fingerprint if changed_items else account.last_seen_fingerprint
        self.repository.update_account_fields(
            account_id,
            status="监控中",
            last_error="",
            last_monitor_at=now_text,
            last_seen_fingerprint=last_seen,
        )
