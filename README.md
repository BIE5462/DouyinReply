# 抖音私信自动化项目

## 项目概览

本项目围绕 BitBrowser（比特浏览器）+ Playwright/Selenium 的自动化能力，整理出一套适合后续二次开发的抖音创作者中心私信参考工程。

当前正式支持的 3 条主能力链路如下：

| 能力 | 正式入口 | 说明 |
| --- | --- | --- |
| 登录与登录态复用 | `examples/login_demo.py` | 创建或复用 BitBrowser 窗口，打开抖音创作者中心并等待人工登录 |
| 聊天记录抓取 | `examples/chat_extract_demo.py` | 进入私信页，抓取会话概览、拦截 protobuf 响应并输出结果 |
| 发送私信 | `examples/send_message_demo.py` | 定位目标会话，在主页面输入框中输入并发送消息 |

## 目录结构

| 路径 | 作用 |
| --- | --- |
| `bit_api.py` | BitBrowser 本地 API 原始封装，作为底层事实来源 |
| `douyin_automation/` | 新增的正式公共包，承接登录、抓取、发送等共享逻辑 |
| `examples/` | 新的正式案例入口，适合作为后续扩展起点 |
| `research/` | 实验脚本、调试脚本、API 探针脚本归档区 |
| `docs/` | 新的项目文档体系 |
| `chat_messages_output/` | 聊天抓取输出目录，保留原语义 |
| `research/artifacts/` | 历史分析 JSON、一次性解析结果归档区 |

## 最短跑通步骤

| 步骤 | 命令 / 动作 |
| --- | --- |
| 安装依赖 | `pip install -r requirements.txt` |
| 安装 Playwright 浏览器 | `playwright install chromium` |
| 启动 BitBrowser | 启动客户端，并确保本地服务地址为 `http://127.0.0.1:54345` |
| 首次登录 | `python examples/login_demo.py` |
| 抓取聊天记录 | `python examples/chat_extract_demo.py` |
| 发送消息 | `python examples/send_message_demo.py --target-user 蓝熙 --message "hello"` |

## 推荐阅读顺序

| 文档 | 适用场景 |
| --- | --- |
| `docs/quick-start.md` | 首次运行、环境准备、登录前置说明 |
| `docs/case-reference.md` | 看三条主案例如何调用 |
| `docs/secondary-development.md` | 想改目标用户、选择器、输出结构时使用 |
| `docs/research-notes.md` | 想了解 iframe、IM API、调试结论时查看 |
| `docs/file-map.md` | 想快速定位新旧文件关系时查看 |

## 兼容入口

为了降低迁移成本，以下历史主入口仍可继续运行，但现在仅作为对新结构的薄封装：

| 旧入口 | 新入口 |
| --- | --- |
| `douyin_login.py` | `examples/login_demo.py` |
| `douyin_chat_extract_v2.py` | `examples/chat_extract_demo.py` |
| `douyin_send_message_final.py` | `examples/send_message_demo.py` |
| `bit_playwright.py` | `examples/base/playwright_connect_demo.py` |
| `bit_selenium.py` | `examples/base/selenium_connect_demo.py` |
