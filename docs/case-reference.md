# 案例参考

## 正式案例总览

| 案例 | 文件 | 适用场景 | 核心函数 |
| --- | --- | --- | --- |
| 登录案例 | `examples/login_demo.py` | 首次登录、登录态检查、Cookie 复用 | `douyin_automation.login.ensure_login` |
| 聊天抓取案例 | `examples/chat_extract_demo.py` | 拉取会话概览、落盘 protobuf、生成结果 JSON | `douyin_automation.chat_extract.extract_chat_history` |
| 发送消息案例 | `examples/send_message_demo.py` | 向已有会话发送文本消息 | `douyin_automation.send_message.send_message` |

## 登录案例

| 项目 | 内容 |
| --- | --- |
| 入口命令 | `python examples/login_demo.py` |
| 可选参数 | `--browser-name` `--target-url` `--timeout` |
| 默认窗口名 | `douyin_creator` |
| 默认页面 | `https://creator.douyin.com/` |
| 主要能力 | 复用窗口、创建窗口、打开页面、检测登录、等待人工登录 |

## 聊天抓取案例

| 项目 | 内容 |
| --- | --- |
| 入口命令 | `python examples/chat_extract_demo.py` |
| 可选参数 | `--browser-name` `--chat-url` `--output-dir` |
| 抓取策略 | DOM 会话列表 + 点击会话 + 拦截 protobuf |
| 输出文件 | `extraction_result.json` 与 `pb_*.bin` |
| 结果字段 | `conversation_list`、`all_chat_data`、`protobuf_api_summary` |

## 发送消息案例

| 项目 | 内容 |
| --- | --- |
| 入口命令 | `python examples/send_message_demo.py --target-user 用户名 --message "内容"` |
| 必填参数 | `--target-user` `--message` |
| 可选参数 | `--browser-name` `--chat-url` |
| 发送策略 | 定位会话 -> 输入框输入 -> 点击发送按钮或 Enter 回退 |
| 成功判定 | 输入框被清空，或页面状态显示发送成功 |

## 基础连接案例

| 案例 | 文件 | 用途 |
| --- | --- | --- |
| Playwright 基础连接 | `examples/base/playwright_connect_demo.py` | 演示如何用 CDP 连接 BitBrowser |
| Selenium 基础连接 | `examples/base/selenium_connect_demo.py` | 演示如何用 debuggerAddress + driver 连接 BitBrowser |
