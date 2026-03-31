# 文件清点与映射

## 当前结构

| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `bit_api.py` | 核心底层 | BitBrowser 原始 API 封装 |
| `douyin_automation/` | 正式代码 | 新的共享逻辑包 |
| `examples/` | 正式入口 | 登录、抓取、发送与基础连接示例 |
| `research/` | 研究归档 | 调试、API 探测、历史脚本 |
| `research/artifacts/` | 历史产物 | 一次性分析结果与旧 JSON 输出 |
| `docs/` | 文档 | 快速开始、案例参考、二开说明等 |
| `chat_messages_output/` | 数据输出 | 抓取产物目录 |

## 新旧文件映射

| 旧文件 | 新位置 / 现状 | 说明 |
| --- | --- | --- |
| `douyin_login.py` | 保留为兼容入口 | 实际调用 `examples/login_demo.py` |
| `douyin_chat_extract_v2.py` | 保留为兼容入口 | 实际调用 `examples/chat_extract_demo.py` |
| `douyin_send_message_final.py` | 保留为兼容入口 | 实际调用 `examples/send_message_demo.py` |
| `bit_playwright.py` | 保留为兼容入口 | 实际调用 `examples/base/playwright_connect_demo.py` |
| `bit_selenium.py` | 保留为兼容入口 | 实际调用 `examples/base/selenium_connect_demo.py` |

## 研究脚本映射

| 分类 | 文件 | 说明 |
| --- | --- | --- |
| `research/debug/` | `douyin_chat_analyze.py` | 页面结构与聊天 DOM 分析 |
| `research/debug/` | `douyin_debug_iframe.py` | iframe 存在性与内容调试 |
| `research/debug/` | `douyin_iframe_debug.py` | iframe 内输入元素排查 |
| `research/api_probe/` | `douyin_analyze_send_api.py` | 发送消息 API 行为分析 |
| `research/api_probe/` | `douyin_find_send_api.py` | 请求拦截与发送链路探测 |
| `research/api_probe/` | `douyin_send_api_test.py` | IM token / API 直发试验 |
| `research/legacy/` | `douyin_creator.py` | 早期窗口创建与手工登录样例 |
| `research/legacy/` | `douyin_send_final_v2.py` | 历史发送实现版本 |
| `research/legacy/` | `douyin_send_message.py` | 历史发送实现版本 |
| `research/legacy/` | `douyin_send_message_keyboard.py` | 键盘模拟发送试验 |
| `research/legacy/` | `douyin_send_message_simple.py` | 简化版发送试验 |
| `research/legacy/` | `douyin_send_js_inject.py` | JS 注入发送试验 |
| `research/artifacts/` | `chat_api_analysis.json` | 历史聊天 API 抓包结果 |
| `research/artifacts/` | `chat_dom_analysis.json` | 历史 DOM 分析结果 |
| `research/artifacts/` | `parsed_messages.json` | 历史解析后的消息样本 |

## 历史文档

| 原文档 | 新位置 |
| --- | --- |
| `PROJECT_SUMMARY.md` | `docs/archive/PROJECT_SUMMARY.md` |
| `Douyin_Message_Extraction_Technical_Documentation.md` | `docs/archive/Douyin_Message_Extraction_Technical_Documentation.md` |
