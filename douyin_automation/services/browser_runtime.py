"""浏览器运行时与页面复用。"""

import asyncio

from playwright.async_api import async_playwright

from ..browser import attach_browser, get_or_create_page
from ..chat_extract import (
    extract_conversation_list,
    extract_recent_conversation_messages,
    get_message_panel_text,
    open_conversation_by_name,
)
from ..config import DEFAULT_MEMORY_MESSAGE_LIMIT
from ..login import check_logged_in, ensure_login
from ..send_message import send_message_to_current_conversation


class LoginRequiredError(RuntimeError):
    pass


class BrowserRuntimeService:
    def __init__(self, repository, event_handler=None):
        self.repository = repository
        self.event_handler = event_handler
        self._playwright = None
        self._sessions = {}
        self._lock = asyncio.Lock()

    async def ensure_playwright(self):
        async with self._lock:
            if self._playwright is None:
                self._playwright = await async_playwright().start()
        return self._playwright

    async def _attach_account(self, account, create_if_missing=False):
        playwright = await self.ensure_playwright()
        browser_id, browser, context = await attach_browser(
            playwright=playwright,
            browser_name=account.browser_name,
            create_if_missing=create_if_missing,
        )
        page = await get_or_create_page(context)
        self._sessions[account.account_id] = {
            "browser_id": browser_id,
            "browser": browser,
            "context": context,
            "page": page,
        }
        self.repository.update_account_fields(
            account.account_id,
            last_browser_id=browser_id,
            last_error="",
        )
        return self._sessions[account.account_id]

    async def get_session(self, account, create_if_missing=False, force_reconnect=False):
        if force_reconnect:
            self._sessions.pop(account.account_id, None)
        session = self._sessions.get(account.account_id)
        if session:
            page = session["page"]
            try:
                if page.is_closed():
                    raise RuntimeError("页面已关闭")
                return session
            except Exception:
                self._sessions.pop(account.account_id, None)
        return await self._attach_account(account, create_if_missing=create_if_missing)

    async def open_login(self, account, timeout):
        playwright = await self.ensure_playwright()
        result = await ensure_login(
            playwright=playwright,
            browser_name=account.browser_name,
            target_url=account.creator_url,
            create_if_missing=True,
            timeout=timeout,
            keep_alive=False,
        )
        self._sessions[account.account_id] = {
            "browser_id": result["browser_id"],
            "browser": result["browser"],
            "context": result["context"],
            "page": result["page"],
        }
        return result

    async def ensure_chat_page(self, account, create_if_missing=False):
        session = await self.get_session(account, create_if_missing=create_if_missing)
        page = session["page"]
        try:
            if account.chat_url not in page.url:
                await page.goto(account.chat_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)
        except Exception:
            session = await self.get_session(
                account,
                create_if_missing=create_if_missing,
                force_reconnect=True,
            )
            page = session["page"]
            await page.goto(account.chat_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

        logged_in = await check_logged_in(page)
        if not logged_in:
            raise LoginRequiredError("账号登录已失效，请重新登录。")
        return page

    async def fetch_conversation_list(self, account):
        page = await self.ensure_chat_page(account, create_if_missing=False)
        return await extract_conversation_list(page)

    async def fetch_conversation_context(self, account, conversation_name, max_chars):
        page = await self.ensure_chat_page(account, create_if_missing=False)
        opened = await open_conversation_by_name(page, conversation_name)
        if not opened:
            return ""
        return await get_message_panel_text(page, max_chars=max_chars)

    async def fetch_conversation_messages(
        self,
        account,
        conversation_name,
        limit=DEFAULT_MEMORY_MESSAGE_LIMIT,
    ):
        page = await self.ensure_chat_page(account, create_if_missing=False)
        opened = await open_conversation_by_name(page, conversation_name)
        if not opened:
            return []
        return await extract_recent_conversation_messages(page, limit=limit)

    async def send_reply(self, account, conversation_name, reply_text):
        page = await self.ensure_chat_page(account, create_if_missing=False)
        opened = await open_conversation_by_name(page, conversation_name)
        if not opened:
            return {"success": False, "reason": "target_not_found"}
        return await send_message_to_current_conversation(page, reply_text)

    async def close(self):
        for session in self._sessions.values():
            try:
                await session["browser"].close()
            except Exception:
                pass
        self._sessions.clear()
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
