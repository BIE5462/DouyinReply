# 抖音私信自动化与自动回复系统

## 项目概览

本项目在原有 BitBrowser + Playwright 自动化链路的基础上，整理出了两类能力：

| 能力 | 说明 | 入口 |
| --- | --- | --- |
| 桌面端自动回复系统 | 使用 `PySide6` 实现的本地控制台，支持多开 BitBrowser 窗口、首次登录提醒、持续监控、AI 自动回复、日志导出、系统托盘运行 | `python desktop_app.py` |
| 底层案例脚本 | 保留登录、聊天抓取、消息发送的独立案例，方便排障、验证选择器和做二次开发 | `examples/` |

桌面端系统默认坚持以下正式链路：

| 项目 | 约定 |
| --- | --- |
| 浏览器控制 | 继续复用当前项目稳定的 BitBrowser 本地接口 |
| 页面自动化 | 继续复用当前 Playwright DOM 自动化逻辑 |
| 消息监听 | 以 DOM 轮询为主，protobuf 只保留为调试辅助 |
| 消息发送 | 使用主页面 `contenteditable` 输入框 + 发送按钮 / Enter 回退 |
| AI 接口 | 使用 OpenAI 兼容的 `Chat Completions` 请求格式 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install
```

### 2. 启动 BitBrowser 本地服务

请先确保：

| 检查项 | 说明 |
| --- | --- |
| BitBrowser 已启动 | 本地窗口管理端必须已打开 |
| API 服务可用 | 项目默认通过本地 BitBrowser API 打开/复用窗口 |
| 已创建或准备好窗口名 | 每个抖音账号对应一个 BitBrowser 窗口名 |

### 3. 启动桌面端

```bash
python desktop_app.py
```

首次启动会进入轻量引导：

| 步骤 | 内容 |
| --- | --- |
| 1 | 填写全局 AI 配置：`Base URL`、`API Key`、`Model` 等 |
| 2 | 创建至少一个初始账号，并绑定 BitBrowser 窗口名 |
| 3 | 进入主界面后，在“账号管理”点击“登录/重登” |
| 4 | 完成人工登录后，再启动监控和自动回复 |

## 桌面端能力

### 核心页面

| 页面 | 主要用途 |
| --- | --- |
| 仪表盘 | 查看账号总数、监控中数量、异常数量、今日回复数，并可一键启动/暂停全部监控 |
| 账号管理 | 绑定窗口名、设置抖音页面地址、登录/重登、单账号启动或暂停监控 |
| 规则与知识 | 编辑系统提示词、店铺资料、语气要求、FAQ、黑白名单、冷却时间、每日上限 |
| AI 设置 | 维护全局 OpenAI 兼容接口配置，并测试连通性 |
| 消息与日志 | 查看回复记录、事件日志，并导出最近回复数据 CSV |
| 调试 | 手动轮询某账号一次，或预览某条消息最终拼装出来的 Prompt |

### 方便使用的补充功能

| 功能 | 当前实现 |
| --- | --- |
| 首次使用提醒 | 首次引导完成后会弹出登录与使用顺序提示 |
| 多账号多窗口 | 每个账号绑定一个独立 BitBrowser 窗口 |
| 全局启动 / 暂停 | 仪表盘和系统托盘都可快速控制 |
| 系统托盘驻留 | 关闭主窗口时默认最小化到托盘继续运行 |
| AI 连通性测试 | 在 AI 设置页直接验证接口是否可用 |
| Prompt 预览 | 在调试页查看系统提示词、FAQ、上下文拼装结果 |
| 回复日志导出 | 在日志页导出 CSV，便于复盘与运营分析 |

## 目录参考

| 路径 | 说明 |
| --- | --- |
| `desktop_app.py` | PySide6 桌面端入口 |
| `douyin_automation/gui/` | 主窗口、首次引导、各功能页 |
| `douyin_automation/services/` | 浏览器运行时、登录、监控、回复、规则引擎、后端调度 |
| `douyin_automation/storage/` | SQLite 持久化与仓储层 |
| `douyin_automation/ai/` | OpenAI 兼容 Chat Completions 客户端 |
| `douyin_automation/models/` | 账号、策略、知识、会话快照、回复任务等数据模型 |
| `examples/` | 登录、抓取聊天、发送消息的独立案例 |
| `research/` | 历史调试脚本、API 探测、DOM 分析、历史产物归档 |
| `docs/` | 快速开始、案例参考、二开说明、研究说明、文件映射 |

## 独立案例入口

如果你想先验证底层自动化能力，可以使用这些示例：

| 示例 | 作用 |
| --- | --- |
| `python examples/login_demo.py --browser-name <窗口名>` | 打开或复用 BitBrowser 窗口，并等待抖音登录 |
| `python examples/chat_extract_demo.py --browser-name <窗口名>` | 进入私信页并抓取会话/聊天记录 |
| `python examples/send_message_demo.py --browser-name <窗口名> --target-user <用户名> --message <内容>` | 打开发送链路并给指定会话发送文本消息 |

## 数据与日志位置

| 类型 | 位置 |
| --- | --- |
| SQLite 数据库 | `QStandardPaths.AppDataLocation/app.db` |
| 桌面端日志文件 | `QStandardPaths.AppDataLocation/logs/desktop_app.log` |
| 聊天抓取原始输出 | `chat_messages_output/` |
| 历史研究产物 | `research/` |

## 延伸文档

| 文档 | 用途 |
| --- | --- |
| `docs/quick-start.md` | 从依赖安装到首次运行的最短路径 |
| `docs/case-reference.md` | 登录、抓取、发送三条案例说明 |
| `docs/secondary-development.md` | 二次开发入口、可替换点和扩展建议 |
| `docs/research-notes.md` | 为什么某些脚本仍保留在研究区而未进入正式流程 |
| `docs/file-map.md` | 当前目录清点与新旧文件映射 |

## 注意事项

| 项目 | 说明 |
| --- | --- |
| 登录方式 | 仍然依赖人工首次登录或登录失效后的人工重登 |
| 自动回复范围 | 当前版本仅支持文本消息 |
| AI 配置粒度 | 当前为全局统一配置，不区分账号 |
| 正式监听能力 | 仍以 DOM 轮询为准，不把 IM 底层接口当正式依赖 |
