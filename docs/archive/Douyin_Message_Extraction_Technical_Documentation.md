# 抖音创作者中心私信消息获取技术文档

## 目录

1. [概述](#1-概述)
2. [环境准备](#2-环境准备)
3. [比特浏览器连接](#3-比特浏览器连接)
4. [页面架构分析](#4-页面架构分析)
5. [核心API接口](#5-核心api接口)
6. [消息数据提取实现](#6-消息数据提取实现)
7. [完整代码示例](#7-完整代码示例)
8. [Protobuf数据解析](#8-protobuf数据解析)
9. [常见问题与解决方案](#9-常见问题与解决方案)
10. [扩展与优化建议](#10-扩展与优化建议)

---

## 1. 概述

本文档详细介绍如何通过比特浏览器（BitBrowser）自动化访问抖音创作者中心私信页面，并获取当前账号接收的全部用户发送的消息内容。

**目标页面**: `https://creator.douyin.com/creator-micro/data/following/chat`

**核心挑战**:
- 私信数据通过 Protobuf 二进制格式传输，无法直接解析
- 页面采用 iframe 嵌套架构，实际IM通信在 iframe 内完成
- 需要处理登录态维持和反爬机制

---

## 2. 环境准备

### 2.1 依赖安装

```bash
pip install requests playwright
playwright install chromium
```

### 2.2 项目结构

```
python-demo/
├── bit_api.py                  # 比特浏览器API封装
├── bit_playwright.py           # Playwright连接示例
├── douyin_login.py             # 登录脚本（复用已保存Cookie）
├── douyin_chat_analyze.py      # 页面分析脚本
├── douyin_chat_extract.py      # 消息提取脚本v1
├── douyin_chat_extract_v2.py   # 消息提取脚本v2（推荐）
└── chat_messages_output/       # 输出目录
    ├── pb_*.bin                # 原始protobuf数据
    └── parsed_messages.json   # 解析后的消息
```

### 2.3 比特浏览器配置

1. 打开比特浏览器客户端
2. 创建名为 `douyin_creator` 的浏览器窗口
3. 手动登录抖音创作者中心（首次）
4. 窗口Cookie会自动保存，后续运行可直接复用

---

## 3. 比特浏览器连接

### 3.1 API 封装 (bit_api.py)

```python
import requests
import json

url = "http://127.0.0.1:54345"
headers = {'Content-Type': 'application/json'}

def findBrowserByName(name):
    json_data = {"page": 0, "pageSize": 100}
    res = requests.post(f"{url}/browser/list", data=json.dumps(json_data), headers=headers).json()
    for item in res.get("data", {}).get("list", []):
        if item["name"] == name:
            return item["id"]
    return None

def openBrowser(browser_id):
    json_data = {"id": browser_id}
    res = requests.post(f"{url}/browser/open", data=json.dumps(json_data), headers=headers).json()
    return res  # 返回 ws 地址等连接信息

def closeBrowser(browser_id):
    requests.post(f"{url}/browser/close", data=json.dumps({"id": browser_id}), headers=headers)
```

### 3.2 Playwright 连接

```python
import asyncio
from playwright.async_api import async_playwright

async def connect_browser(playwright, browser_id):
    res = openBrowser(browser_id)
    ws = res["data"]["ws"]  # WebSocket地址
    browser = await playwright.chromium.connect_over_cdp(ws)
    return browser
```

---

## 4. 页面架构分析

### 4.1 双层架构

抖音创作者中心私信页面采用**双层iframe嵌套架构**：

```
┌─────────────────────────────────────────────────────────────┐
│  creator.douyin.com (外层 - 页面框架)                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ iframe: summon.bytedance.com/web/ (IM SDK)              ││
│  │  - 实际的IM通信在这里完成                                ││
│  │  - 消息收发通过 imapi.snssdk.com 接口                   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 4.2 关键发现

1. **会话列表**: 在外层页面展示，通过DOM可直接获取
2. **消息内容**: 需要通过点击会话触发API请求获取
3. **IM接口**: 使用 `imapi.snssdk.com` 域名，全部为 Protobuf 格式
4. **响应格式**: `Content-Type: application/x-protobuf`

### 4.3 页面元素定位

```javascript
// 会话列表项
'[class*="item-fWZowv"]'

// 用户名称
'[class*="header-name"]'

// 最后一条消息
'[class*="item-content"]'

// 时间戳
'[class*="item-time"]'
```

---

## 5. 核心API接口

### 5.1 获取IM Token

```
POST https://creator.douyin.com/web/api/v1/im/token/
参数: channel=24, app_id=10001, is_visitor=false
返回: {"code":200,"data":{"token":"xxx"}}
```

### 5.2 获取用户IM Token

```
GET https://creator.douyin.com/aweme/v1/creator/im/user_token/
返回: 用户ID和IM Token
```

### 5.3 获取会话列表和消息（核心）

```
POST https://imapi.snssdk.com/v2/message/get_by_user_init
Content-Type: application/x-protobuf
返回: Protobuf二进制数据，包含全部会话和消息
响应大小: 约300KB-600KB
```

### 5.4 获取指定会话消息

```
POST https://imapi.snssdk.com/v1/message/get_by_conversation
Content-Type: application/x-protobuf
参数: conversation_id (会话唯一标识)
返回: Protobuf二进制数据，该会话的全部历史消息
响应大小: 约20KB-40KB
```

### 5.5 用户详情批量获取

```
POST https://creator.douyin.com/aweme/v1/creator/im/user_detail/
参数: user_ids (用户ID数组)
返回: 用户头像、昵称、抖音号等信息
```

---

## 6. 消息数据提取实现

### 6.1 拦截策略

由于Protobuf是二进制格式，直接解析难度较大。采用以下策略：

1. **拦截HTTP响应**：捕获所有 `imapi.snssdk.com` 的请求响应
2. **保存原始二进制**：将响应body保存为`.bin`文件
3. **正则提取文本**：从二进制数据中用正则提取JSON片段

### 6.2 消息类型识别

从Protobuf数据中发现的消息类型（aweType字段）：

| aweType | 含义 |
|---------|------|
| 0 | 系统消息/推送消息 |
| 700 | 普通文字消息 |
| 774 | 回复类消息 |
| 507 | 表情消息（点赞等） |
| 516 | 特效表情 |
| 248 | 分享卡片等 |

### 6.3 数据提取流程

```python
async def extract_messages(page):
    # 1. 访问私信页面
    await page.goto("https://creator.douyin.com/creator-micro/data/following/chat")
    await asyncio.sleep(10)
    
    # 2. 拦截所有IM API响应
    page.on("response", intercept_protobuf)
    
    # 3. 获取会话列表
    conversations = await page.evaluate("""() => {
        const items = document.querySelectorAll('[class*="item-fWZowv"]');
        return Array.from(items).map(item => ({
            name: item.querySelector('[class*="header-name"]')?.textContent,
            lastMsg: item.querySelector('[class*="item-content"]')?.textContent,
            time: item.querySelector('[class*="item-time"]')?.textContent
        }));
    }""")
    
    # 4. 点击每个会话触发API获取消息
    for idx in range(len(conversations)):
        await page.click(f'[class*="item-fWZowv"]:nth-child({idx+1})')
        await asyncio.sleep(2)
```

---

## 7. 完整代码示例

### 7.1 消息提取主脚本 (douyin_chat_extract_v2.py)

```python
from bit_api import *
import json
import time
import asyncio
import os
from playwright.async_api import async_playwright

CHAT_URL = "https://creator.douyin.com/creator-micro/data/following/chat"
BROWSER_NAME = "douyin_creator"
OUTPUT_DIR = "chat_messages_output"

protobuf_data = {}

async def intercept_protobuf(response):
    """拦截IM API的Protobuf响应并保存"""
    req_url = response.request.url
    if "imapi.snssdk.com" in req_url and "message" in req_url:
        try:
            body = await response.body()
            if len(body) > 200:
                # 保存原始二进制
                fname = f"pb_{int(time.time()*1000)}_{len(body)}.bin"
                fpath = os.path.join(OUTPUT_DIR, fname)
                with open(fpath, "wb") as f:
                    f.write(body)
                print(f"[IM API] {req_url[:60]}... 大小: {len(body)} bytes")
        except Exception as e:
            print(f"处理失败: {e}")

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    async with async_playwright() as playwright:
        # 1. 连接比特浏览器
        browser_id = findBrowserByName(BROWSER_NAME)
        res = openBrowser(browser_id)
        ws = res["data"]["ws"]
        
        browser = await playwright.chromium.connect_over_cdp(ws)
        page = browser.contexts[0].pages[0]
        
        # 2. 设置拦截
        page.on("response", intercept_protobuf)
        
        # 3. 访问页面
        await page.goto(CHAT_URL, wait_until="domcontentloaded")
        await asyncio.sleep(12)
        
        # 4. 获取会话列表
        conversation_list = await page.evaluate("""() => {
            const items = document.querySelectorAll('[class*="item-fWZowv"]');
            return Array.from(items).map(item => ({
                name: item.querySelector('[class*="header-name"]')?.textContent.trim(),
                lastMsg: item.querySelector('[class*="item-content"]')?.textContent.trim(),
                time: item.querySelector('[class*="item-time"]')?.textContent.trim()
            }));
        }""")
        
        print(f"找到 {len(conversation_list)} 个会话")
        for conv in conversation_list:
            print(f"  - {conv['name']}: {conv['lastMsg'][:50]}")
        
        # 5. 点击会话触发消息加载
        for idx in range(min(len(conversation_list), 5)):
            items = await page.query_selector_all('[class*="item-fWZowv"]')
            if idx < len(items):
                try:
                    await items[idx].click(timeout=3000)
                except:
                    await items[idx].click(force=True, timeout=2000)
                await asyncio.sleep(2)
        
        print(f"\n提取完成，原始数据保存在 {OUTPUT_DIR}/")

asyncio.run(main())
```

### 7.2 Protobuf数据解析脚本

```python
import re
import json
import os

def parse_protobuf_messages(bin_path):
    """从Protobuf二进制中提取消息文本"""
    with open(bin_path, 'rb') as f:
        data = f.read()
    
    results = []
    
    # 方法1: 提取 {"text": "xxx", ...} 格式
    for m in re.finditer(rb'\{"text":\s*"([^"]+)"', data):
        text = m.group(1).decode('utf-8', errors='replace')
        if text:
            results.append(text)
    
    # 方法2: 提取完整JSON对象
    for m in re.finditer(rb'\{[^{}]*"text"[^{}]*\}', data):
        try:
            s = m.group(0).decode('utf-8', errors='replace')
            if s not in results:
                results.append(s)
        except:
            pass
    
    return results

# 解析所有保存的protobuf文件
all_messages = {}
for fname in os.listdir('chat_messages_output'):
    if fname.endswith('.bin'):
        fpath = os.path.join('chat_messages_output', fname)
        messages = parse_protobuf_messages(fpath)
        all_messages[fname] = messages
        print(f"{fname}: {len(messages)} 条消息")

# 保存解析结果
with open('chat_messages_output/parsed_messages.json', 'w', encoding='utf-8') as f:
    json.dump(all_messages, f, ensure_ascii=False, indent=2)
```

---

## 8. Protobuf数据解析

### 8.1 数据结构

Protobuf响应是序列化的二进制数据，包含多个会话的消息。每个会话的消息以以下格式组织：

```
[会话ID消息头][消息1][消息2][消息3]...
```

消息ID格式: `0:1:当前用户ID:对方用户ID`

### 8.2 关键字段

```json
{
  "aweType": 700,           // 消息类型
  "text": "消息内容",        // 文字内容
  "createdAt": 时间戳,      // 创建时间
  "is_card": false,         // 是否卡片消息
  "msgHint": "",            // 消息提示
  "richTextInfos": []       // 富文本信息
}
```

### 8.3 文本提取算法

```python
import re

def extract_text_from_protobuf(data: bytes) -> list:
    """从二进制数据中提取可读文本"""
    results = []
    
    # 提取 {"text": "内容", ...} 格式的JSON
    pattern1 = rb'\{"text":\s*"([^"]+)"'
    for m in re.finditer(pattern1, data):
        text = m.group(1).decode('utf-8', errors='replace')
        if text and len(text) > 0:
            results.append(text)
    
    # 提取 aweType 相关的JSON对象
    pattern2 = rb'\{"aweType":\d+[^}]*\}'
    for m in re.finditer(pattern2, data):
        try:
            obj = m.group(0).decode('utf-8', errors='replace')
            results.append(obj)
        except:
            pass
    
    return results
```

---

## 9. 常见问题与解决方案

### 9.1 会话点击失败

**问题**: 点击会话时提示 "Element is not visible"

**原因**: 会话列表采用虚拟滚动，只有可见区域的元素才能点击

**解决方案**:
```python
# 方法1: 使用 force 点击
await item.click(force=True, timeout=2000)

# 方法2: 先滚动到目标位置
await item.scroll_into_view_if_needed()
await item.click(timeout=3000)

# 方法3: 多次重试
for retry in range(3):
    try:
        await item.click(timeout=3000)
        break
    except:
        await asyncio.sleep(1)
```

### 9.2 Protobuf解析乱码

**问题**: 直接用UTF-8解析出现乱码

**原因**: Protobuf是二进制格式，部分字节不是有效的UTF-8

**解决方案**:
```python
# 使用 errors='replace' 忽略无效字符
text = data.decode('utf-8', errors='replace')

# 或者只提取有效的文本片段
for byte in data:
    if 0x20 <= byte < 0x7F:  # 可打印ASCII
        # 处理
```

### 9.3 消息内容显示"请打开抖音app查看"

**原因**: 部分特殊消息类型（如语音、礼物等）只能在APP查看

**说明**: 这是抖音的限制，非技术问题，无法通过网页获取这部分内容

### 9.4 Cookie过期

**问题**: 打开窗口后跳转登录页

**解决方案**:
- 比特浏览器开启 `syncCookies: True`
- 复用已有窗口而非创建新窗口
- 定期手动登录刷新Cookie

---

## 10. 扩展与优化建议

### 10.1 直接调用API（需要解决签名）

如果能获取到有效的 `msToken` 和 `a_bogus` 参数，可以直接调用API：

```python
import requests

def get_messages(msToken, a_bogus, user_id):
    url = "https://imapi.snssdk.com/v2/message/get_by_user_init"
    headers = {
        "Content-Type": "application/x-protobuf",
        "msToken": msToken,
        "a_bogus": a_bogus
    }
    # 需要构造Protobuf请求体
    response = requests.post(url, headers=headers, data=request_body)
    return response.content
```

**注意**: `a_bogus` 是防爬参数，需要从浏览器中提取或逆向工程

### 10.2 定时任务

```python
import schedule
import time

def job():
    print("开始获取消息...")
    asyncio.run(main())

schedule.every().hour.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 10.3 数据存储

可以将提取的消息存储到数据库：

```python
import sqlite3

def save_messages(messages):
    conn = sqlite3.connect('messages.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS messages
        (id INTEGER PRIMARY KEY, conversation_id TEXT, 
         text TEXT, aweType INTEGER, createdAt INTEGER)''')
    for msg in messages:
        conn.execute("INSERT INTO messages VALUES (?,?,?,?,?)",
                     (msg['id'], msg['conversation_id'], msg['text'], 
                      msg['aweType'], msg['createdAt']))
    conn.commit()
    conn.close()
```

### 10.4 完整消息获取优化

1. **分页加载**: 会话列表向下滚动加载更多会话
2. **历史消息**: 每个会话需要翻页获取更早的消息
3. **实时推送**: 使用WebSocket获取实时新消息（需要IM SDK支持）

---

## 附录：文件清单

| 文件 | 说明 |
|------|------|
| `bit_api.py` | 比特浏览器API封装 |
| `douyin_login.py` | 登录脚本 |
| `douyin_chat_extract_v2.py` | 消息提取主脚本 |
| `chat_messages_output/` | 提取的原始数据目录 |
| `pb_*.bin` | Protobuf原始响应 |
| `parsed_messages.json` | 解析后的消息 |

---

*文档更新时间: 2025年*
*适用于比特浏览器 + Playwright 环境*