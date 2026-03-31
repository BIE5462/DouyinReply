# 快速开始

## 1. 环境前置

| 项目 | 要求 |
| --- | --- |
| Python | 建议 3.9 及以上 |
| BitBrowser | 本地客户端已启动，并开启本地服务 |
| 本地 API 地址 | `http://127.0.0.1:54345` |
| 浏览器驱动 | Playwright Chromium 已安装 |

## 2. 安装依赖

| 步骤 | 命令 |
| --- | --- |
| 安装 Python 依赖 | `pip install -r requirements.txt` |
| 安装 Playwright 浏览器 | `playwright install chromium` |

## 3. 首次登录

首次使用建议先运行登录案例，让 BitBrowser 保存 Cookie 与 localStorage：

```bash
python examples/login_demo.py
```

脚本默认会：

| 动作 | 说明 |
| --- | --- |
| 查找窗口 | 优先复用名为 `douyin_creator` 的 BitBrowser 窗口 |
| 创建窗口 | 若不存在则自动创建一个用于抖音创作者中心的窗口 |
| 打开创作者中心 | 访问 `https://creator.douyin.com/` |
| 检测登录态 | 已登录则直接复用，未登录则等待人工扫码或手动登录 |

## 4. 抓取聊天记录

```bash
python examples/chat_extract_demo.py
```

默认输出：

| 文件/目录 | 说明 |
| --- | --- |
| `chat_messages_output/extraction_result.json` | 汇总结果 |
| `chat_messages_output/pb_*.bin` | 原始 protobuf 响应 |

## 5. 发送消息

```bash
python examples/send_message_demo.py --target-user 蓝熙 --message "hello"
```

关键说明：

| 项目 | 说明 |
| --- | --- |
| 目标用户 | 使用会话名称关键字匹配 |
| 发送位置 | 主页面 `contenteditable` 输入框 |
| 发送方式 | 优先点击发送按钮，失败时回退到 Enter |

## 6. 推荐运行顺序

| 顺序 | 场景 |
| --- | --- |
| 1 | `python examples/login_demo.py` |
| 2 | 人工确认抖音创作者中心已登录 |
| 3 | `python examples/chat_extract_demo.py` |
| 4 | `python examples/send_message_demo.py --target-user xxx --message "..."` |

## 7. 常见问题

| 问题 | 处理建议 |
| --- | --- |
| 找不到 BitBrowser 窗口 | 先启动 BitBrowser，并确认本地 API 服务可用 |
| 打开后跳转登录页 | 重新执行登录案例，确保窗口已保存 Cookie |
| 找不到目标会话 | 确认用户已出现在当前会话列表中，必要时先人工打开对应会话 |
| 找不到输入框或发送按钮 | 抖音页面 DOM 可能变更，优先检查 `douyin_automation/selectors.py` |
