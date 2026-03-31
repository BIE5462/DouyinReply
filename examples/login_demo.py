"""抖音创作者中心登录案例。"""

import argparse
import asyncio

from playwright.async_api import async_playwright

from douyin_automation.config import (
    DEFAULT_BROWSER_NAME,
    DEFAULT_CREATOR_URL,
    DEFAULT_LOGIN_TIMEOUT,
)
from douyin_automation.login import ensure_login


def build_parser():
    parser = argparse.ArgumentParser(description="抖音创作者中心登录案例")
    parser.add_argument(
        "--browser-name",
        default=DEFAULT_BROWSER_NAME,
        help="BitBrowser 窗口名称",
    )
    parser.add_argument(
        "--target-url",
        default=DEFAULT_CREATOR_URL,
        help="登录检测页面地址",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_LOGIN_TIMEOUT,
        help="等待人工登录超时时间（秒）",
    )
    return parser


async def run_demo(args):
    async with async_playwright() as playwright:
        await ensure_login(
            playwright=playwright,
            browser_name=args.browser_name,
            target_url=args.target_url,
            timeout=args.timeout,
            keep_alive=True,
        )


def main():
    args = build_parser().parse_args()
    asyncio.run(run_demo(args))


if __name__ == "__main__":
    main()
