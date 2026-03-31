"""BitBrowser 连接与窗口复用能力。"""

import json

import requests

from bit_api import closeBrowser, headers, openBrowser, url
from .config import DEFAULT_BROWSER_FINGERPRINT, DEFAULT_BROWSER_REMARK


def find_browser_by_name(name):
    """按窗口名查找 BitBrowser 窗口 ID。"""
    json_data = {"page": 0, "pageSize": 100}
    res = requests.post(
        f"{url}/browser/list",
        data=json.dumps(json_data),
        headers=headers,
    ).json()
    if not res.get("success"):
        return None

    for item in res.get("data", {}).get("list", []):
        if item.get("name") == name:
            return item.get("id")
    return None


def create_douyin_browser(
    browser_name,
    remark=DEFAULT_BROWSER_REMARK,
    fingerprint=None,
):
    """创建用于抖音创作者中心的 BitBrowser 窗口。"""
    json_data = {
        "name": browser_name,
        "remark": remark,
        "proxyMethod": 2,
        "proxyType": "noproxy",
        "syncCookies": True,
        "syncLocalStorage": True,
        "browserFingerPrint": fingerprint or DEFAULT_BROWSER_FINGERPRINT,
    }
    res = requests.post(
        f"{url}/browser/update",
        data=json.dumps(json_data),
        headers=headers,
    ).json()
    if res.get("success"):
        return res["data"]["id"]

    print(f"创建窗口失败: {res.get('msg')}")
    return None


def get_or_create_browser(browser_name, create_if_missing=True):
    """优先复用窗口，必要时创建新窗口。"""
    browser_id = find_browser_by_name(browser_name)
    if browser_id:
        print(f"复用已有窗口: {browser_name} (ID: {browser_id})")
        return browser_id

    if not create_if_missing:
        return None

    print(f"未找到窗口，正在创建: {browser_name}")
    browser_id = create_douyin_browser(browser_name)
    if browser_id:
        print(f"窗口已创建，ID: {browser_id}")
    return browser_id


def open_browser_session(browser_id):
    """打开窗口并返回 BitBrowser 的打开响应。"""
    res = openBrowser(browser_id)
    if not res.get("success"):
        raise RuntimeError(f"打开窗口失败: {res.get('msg')}")
    return res


async def attach_browser(playwright, browser_name, create_if_missing=False):
    """通过 Playwright 连接到 BitBrowser 已打开窗口。"""
    browser_id = get_or_create_browser(
        browser_name=browser_name,
        create_if_missing=create_if_missing,
    )
    if not browser_id:
        raise RuntimeError(f"未找到窗口 {browser_name}")

    res = open_browser_session(browser_id)
    ws = res["data"]["ws"]
    browser = await playwright.chromium.connect_over_cdp(ws)
    context = browser.contexts[0]
    return browser_id, browser, context


async def get_or_create_page(context):
    """优先复用现有页签，否则新建页面。"""
    if context.pages:
        return context.pages[0]
    return await context.new_page()


def close_browser_window(browser_id):
    """关闭 BitBrowser 窗口。"""
    closeBrowser(browser_id)
