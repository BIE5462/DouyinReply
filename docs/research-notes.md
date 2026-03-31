# 研究脚本说明

## 为什么还保留 research

当前项目已经有一批很有价值的实验脚本，它们虽然不适合作为正式入口，但对定位问题、验证页面变化、分析 IM 通信机制非常有帮助，因此统一归档到 `research/`。

## 研究主题与归档位置

| 主题 | 目录 | 说明 |
| --- | --- | --- |
| iframe / DOM 调试 | `research/debug/` | 用来确认聊天输入区域是否仍在 iframe、页面结构如何变化 |
| 发送 API 探测 | `research/api_probe/` | 用来拦截、分析消息发送相关请求与凭证信息 |
| 历史实现与旧版本 | `research/legacy/` | 保存多轮发送脚本、旧流程尝试和早期样例 |
| 历史分析产物 | `research/artifacts/` | 保存 `chat_api_analysis.json`、`chat_dom_analysis.json`、`parsed_messages.json` 这类一次性分析结果 |

## 研究结论

| 结论 | 说明 |
| --- | --- |
| 正式发送方案应使用主页面输入框 | 当前可用实现已经回到主页面 `contenteditable` 输入框，不应默认走 iframe |
| 直接 IM API 发送暂不稳定 | 需要复杂签名、token、protobuf 请求体，不适合作为主流程 |
| protobuf 拦截依然有价值 | 适合抓取聊天原始响应与辅助定位消息结构 |

## 建议使用方式

| 目标 | 推荐动作 |
| --- | --- |
| 页面突然改版，主流程失效 | 先查看 `research/debug/` 下的脚本与历史思路 |
| 想分析发送接口或会话协议 | 查看 `research/api_probe/` |
| 想追溯旧方案差异 | 查看 `research/legacy/` 中的历史脚本 |
| 想查看旧分析结果样本 | 查看 `research/artifacts/` 中已归档的 JSON 产物 |
