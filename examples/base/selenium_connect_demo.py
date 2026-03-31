"""BitBrowser + Selenium 基础连接示例。"""

import argparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from douyin_automation.browser import open_browser_session


def build_parser():
    parser = argparse.ArgumentParser(description="BitBrowser Selenium 基础连接示例")
    parser.add_argument("--browser-id", required=True, help="BitBrowser 窗口 ID")
    parser.add_argument(
        "--url",
        default="https://www.baidu.com/",
        help="打开后的测试页面地址",
    )
    parser.add_argument(
        "--keyword",
        default="BitBrowser",
        help="输入的测试关键词",
    )
    return parser


def main():
    args = build_parser().parse_args()
    res = open_browser_session(args.browser_id)
    print(res)

    driver_path = res["data"]["driver"]
    debugger_address = res["data"]["http"]

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("debuggerAddress", debugger_address)

    chrome_service = Service(driver_path)
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    driver.get(args.url)
    input_box = driver.find_element(By.CLASS_NAME, "s_ipt")
    input_box.send_keys(args.keyword)
    print("before click...")
    btn = driver.find_element(By.CLASS_NAME, "s_btn")
    btn.click()
    print("after click")


if __name__ == "__main__":
    main()
