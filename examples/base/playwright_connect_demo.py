"""BitBrowser + Playwright 基础连接示例。"""

import argparse
import asyncio
import time

from playwright.async_api import async_playwright

from bit_api import closeBrowser
from douyin_automation.browser import open_browser_session


def build_parser():
    parser = argparse.ArgumentParser(description="BitBrowser Playwright 基础连接示例")
    parser.add_argument("--browser-id", required=True, help="BitBrowser 窗口 ID")
    parser.add_argument(
        "--url",
        default="https://baidu.com",
        help="打开后的测试页面地址",
    )
    return parser


async def run_demo(args):
    res = open_browser_session(args.browser_id)
    ws = res["data"]["ws"]
    print("ws address ==>>> ", ws)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.connect_over_cdp(ws)
        context = browser.contexts[0]
        page = await context.new_page()
        print("new page and goto target url")
        await page.goto(args.url)
        time.sleep(2)
        print("close page and browser window")
        await page.close()

    time.sleep(2)
    closeBrowser(args.browser_id)


def main():
    args = build_parser().parse_args()
    asyncio.run(run_demo(args))


if __name__ == "__main__":
    main()
