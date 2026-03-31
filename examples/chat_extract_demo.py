"""聊天记录抓取案例。"""

import argparse
import asyncio

from playwright.async_api import async_playwright

from douyin_automation.chat_extract import extract_chat_history
from douyin_automation.config import (
    DEFAULT_BROWSER_NAME,
    DEFAULT_CHAT_URL,
    DEFAULT_OUTPUT_DIR,
)


def build_parser():
    parser = argparse.ArgumentParser(description="抖音聊天记录抓取案例")
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
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="抓取结果输出目录",
    )
    return parser


async def run_demo(args):
    async with async_playwright() as playwright:
        result = await extract_chat_history(
            playwright=playwright,
            browser_name=args.browser_name,
            chat_url=args.chat_url,
            output_dir=args.output_dir,
        )
    print(f"抓取完成，结果文件: {result['result_file']}")


def main():
    args = build_parser().parse_args()
    asyncio.run(run_demo(args))


if __name__ == "__main__":
    main()
