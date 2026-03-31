"""登录态检测与登录流程封装。"""

import asyncio
import time

from .browser import attach_browser, get_or_create_page, close_browser_window
from .config import (
    DEFAULT_BROWSER_NAME,
    DEFAULT_CREATOR_URL,
    DEFAULT_LOGIN_TIMEOUT,
)
from .selectors import LOGIN_BUTTON_SELECTOR, USER_AVATAR_SELECTOR


async def check_logged_in(page):
    """检查当前页面是否已处于登录状态。"""
    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    if "login" in page.url:
        return False

    try:
        login_btn = await page.query_selector(LOGIN_BUTTON_SELECTOR)
        if login_btn and await login_btn.is_visible():
            return False
    except Exception:
        pass

    try:
        avatar = await page.query_selector(USER_AVATAR_SELECTOR)
        if avatar and await avatar.is_visible():
            return True
    except Exception:
        pass

    page_content = await page.content()
    for indicator in ["请登录", "扫码登录", "登录后查看", "登录头条号"]:
        if indicator in page_content:
            return False

    return True


async def wait_for_login(page, timeout=DEFAULT_LOGIN_TIMEOUT):
    """等待用户在浏览器内完成登录。"""
    print(f"请在浏览器中完成登录（超时 {timeout} 秒）...")
    start = time.time()
    while time.time() - start < timeout:
        if await check_logged_in(page):
            return True
        await asyncio.sleep(2)
    return False


async def ensure_login(
    playwright,
    browser_name=DEFAULT_BROWSER_NAME,
    target_url=DEFAULT_CREATOR_URL,
    create_if_missing=True,
    timeout=DEFAULT_LOGIN_TIMEOUT,
    keep_alive=False,
):
    """确保指定浏览器窗口已登录抖音创作者中心。"""
    browser_id, browser, context = await attach_browser(
        playwright=playwright,
        browser_name=browser_name,
        create_if_missing=create_if_missing,
    )
    page = await get_or_create_page(context)

    print(f"正在访问 {target_url} ...")
    await page.goto(target_url, wait_until="domcontentloaded")
    print(f"页面标题: {await page.title()}")

    logged_in = await check_logged_in(page)
    if logged_in:
        print("检测到已登录状态，直接使用")
    else:
        print("未登录，请在浏览器中手动登录抖音账号")
        logged_in = await wait_for_login(page, timeout=timeout)
        if logged_in:
            print("登录成功！Cookie 将自动保存在浏览器窗口中")
        else:
            print("登录超时，请重新运行脚本")

    if keep_alive:
        print("浏览器保持打开，按 Ctrl+C 退出")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("正在关闭...")
            await page.close()
            await browser.close()
            close_browser_window(browser_id)
            print("窗口已关闭，下次打开将自动复用已保存的 Cookie")

    return {
        "browser_id": browser_id,
        "browser": browser,
        "context": context,
        "page": page,
        "logged_in": logged_in,
    }
