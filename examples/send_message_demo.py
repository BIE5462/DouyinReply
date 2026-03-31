"""发送抖音私信案例。"""

import argparse
import asyncio

from playwright.async_api import async_playwright

from douyin_automation.config import DEFAULT_BROWSER_NAME, DEFAULT_CHAT_URL
from douyin_automation.send_message import send_message


def build_parser():
    parser = argparse.ArgumentParser(description="抖音私信发送案例")
    parser.add_argument(
        "--browser-name",
        default=DEFAULT_BROWSER_NAME,
        help="BitBrowser 窗口名称",
    )
    parser.add_argument(
        "--chat-url",
        default=DEFAULT_CHAT_URL,
        help="抖音私信页面地址",
    )
    parser.add_argument(
        "--target-user",
        required=True,
        help="目标会话用户名关键字",
    )
    parser.add_argument(
        "--message",
        required=True,
        help="要发送的消息内容",
    )
    return parser


async def run_demo(args):
    async with async_playwright() as playwright:
        result = await send_message(
            playwright=playwright,
            target_user=args.target_user,
            message=args.message,
            browser_name=args.browser_name,
            chat_url=args.chat_url,
        )
    print("发送成功" if result["success"] else "发送失败")


def main():
    args = build_parser().parse_args()
    asyncio.run(run_demo(args))


if __name__ == "__main__":
    main()
