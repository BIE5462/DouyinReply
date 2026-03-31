# 二次开发说明

## 建议从哪里开始改

| 场景 | 推荐位置 |
| --- | --- |
| 改窗口名、页面地址、默认输出目录 | `douyin_automation/config.py` |
| 改 DOM 选择器 | `douyin_automation/selectors.py` |
| 改 BitBrowser 查找/创建逻辑 | `douyin_automation/browser.py` |
| 改登录态判断 | `douyin_automation/login.py` |
| 改聊天记录抓取流程 | `douyin_automation/chat_extract.py` |
| 改消息发送流程 | `douyin_automation/send_message.py` |

## 常见二开入口

| 需求 | 修改建议 |
| --- | --- |
| 更换默认浏览器名 | 修改 `DEFAULT_BROWSER_NAME`，或从 CLI 传入 `--browser-name` |
| 更换聊天输出目录 | 在案例脚本中传入 `--output-dir` |
| 改目标用户 | 在发送案例里通过 `--target-user` 指定，不建议继续硬编码 |
| 改消息内容 | 在发送案例里通过 `--message` 指定 |
| 替换页面选择器 | 优先统一修改 `selectors.py`，避免散落到多个脚本中 |

## 推荐扩展方式

| 扩展方向 | 实现建议 |
| --- | --- |
| 增加命令行参数 | 直接在 `examples/*.py` 中扩展 `argparse` |
| 增加新的业务动作 | 在 `douyin_automation/` 下新建模块，并复用 `browser.py` |
| 输出更多字段 | 在 `chat_extract.py` 的 `result` 中补充，不要直接改落盘路径语义 |
| 支持更多发送校验 | 在 `send_message.py` 中新增页面断言，但保留当前输入框清空判定 |

## 不建议直接升格为正式能力的方向

| 方向 | 原因 |
| --- | --- |
| 直接调用 IM 发送 API | 当前仍依赖复杂签名、protobuf 请求体和会话上下文，稳定性不足 |
| iframe 注入式发送 | 已有实验结论显示当前主输入区回到了主页面，iframe 方案不应作为默认实现 |
| 大量散落脚本继续复制逻辑 | 会继续放大维护成本，建议统一走 `douyin_automation/` |
