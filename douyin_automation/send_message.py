"""抖音私信发送逻辑封装。"""

import asyncio

from .browser import attach_browser, get_or_create_page
from .chat_extract import open_conversation_by_name
from .config import DEFAULT_BROWSER_NAME, DEFAULT_CHAT_URL
from .selectors import CHAT_INPUT_SELECTOR, CHAT_SEND_BUTTON_SELECTOR


async def send_message_to_current_conversation(page, message):
    """向当前已打开的会话发送消息。"""
    try:
        input_box = await page.wait_for_selector(CHAT_INPUT_SELECTOR, timeout=8000)
        await page.wait_for_selector(CHAT_SEND_BUTTON_SELECTOR, timeout=8000)
    except Exception as exc:
        print(f"未找到主页面聊天输入区: {exc}")
        return {"success": False, "reason": "input_not_found"}

    print("在主页面输入消息...")
    await input_box.click()
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(message, delay=30)
    await asyncio.sleep(1)

    send_btn = await page.query_selector(CHAT_SEND_BUTTON_SELECTOR)
    if not send_btn:
        print("未找到发送按钮")
        return {"success": False, "reason": "send_button_not_found"}

    if await send_btn.is_disabled():
        print("发送按钮不可用，尝试回车发送...")
        await page.keyboard.press("Enter")
    else:
        print("点击发送按钮...")
        await send_btn.click()

    try:
        await page.wait_for_function(
            """(selector) => {
                const el = document.querySelector(selector);
                return !!el && el.innerText.trim() === "";
            }""",
            CHAT_INPUT_SELECTOR,
            timeout=5000,
        )
        print("消息已发送!")
        await asyncio.sleep(1)
        return {"success": True}
    except Exception:
        current_text = await input_box.inner_text()
        success = current_text.strip() == ""
        print("消息已发送!" if success else "发送失败")
        return {"success": success, "reason": "send_failed" if not success else ""}


async def send_message_on_page(page, target_user, message):
    """在当前页面查找目标会话并发送消息。"""
    print(f"查找用户: {target_user}")
    opened = await open_conversation_by_name(page, target_user)
    if not opened:
        print("未找到用户!")
        return {"success": False, "reason": "target_not_found"}
    await asyncio.sleep(1)
    return await send_message_to_current_conversation(page, message)


async def send_message(
    playwright,
    target_user,
    message,
    browser_name=DEFAULT_BROWSER_NAME,
    chat_url=DEFAULT_CHAT_URL,
):
    """进入目标会话并发送消息。"""
    browser_id, browser, context = await attach_browser(
        playwright=playwright,
        browser_name=browser_name,
        create_if_missing=False,
    )
    page = await get_or_create_page(context)

    print(f"窗口: {browser_name} ({browser_id})")
    print("访问私信页面...")
    await page.goto(chat_url, wait_until="domcontentloaded")
    await asyncio.sleep(5)
    result = await send_message_on_page(page, target_user, message)

    return {
        "browser_id": browser_id,
        "browser": browser,
        "context": context,
        "page": page,
        "success": result["success"],
        "target_user": target_user,
        "message": message,
        "reason": result.get("reason", ""),
    }
