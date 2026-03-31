"""聊天记录抓取与 protobuf 落盘逻辑。"""

import asyncio
import json
import os
import time

from .browser import attach_browser, get_or_create_page
from .config import (
    DEFAULT_BROWSER_NAME,
    DEFAULT_CHAT_URL,
    DEFAULT_MEMORY_MESSAGE_LIMIT,
    DEFAULT_OUTPUT_DIR,
)
from .selectors import (
    CHAT_FALLBACK_CONTAINER_SELECTOR,
    CHAT_LIST_CONTAINER_SELECTOR,
    CHAT_PANEL_SELECTOR,
    CONVERSATION_ITEM_SELECTOR,
    CONVERSATION_LAST_MESSAGE_SELECTOR,
    CONVERSATION_NAME_SELECTOR,
    CONVERSATION_TIME_SELECTOR,
)
from .utils.text import normalize_text


class ProtobufCaptureStore:
    """保存 protobuf 响应摘要与原始文件。"""

    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.data = {}

    async def intercept_protobuf(self, response):
        req = response.request
        req_url = req.url
        if "imapi.snssdk.com" in req_url and "message" in req_url:
            try:
                body = await response.body()
                if len(body) <= 200:
                    return

                try:
                    post_data = req.post_data_buffer
                    post_hex = post_data[:100].hex() if post_data else ""
                except Exception:
                    post_hex = ""

                entry = {
                    "url": req_url,
                    "method": req.method,
                    "body_size": len(body),
                    "body_path": "",
                    "request_body_hex_prefix": post_hex,
                }

                fname = f"pb_{int(time.time() * 1000)}_{len(body)}.bin"
                fpath = os.path.join(self.output_dir, fname)
                with open(fpath, "wb") as file_obj:
                    file_obj.write(body)
                entry["body_path"] = fpath

                readable_parts = []
                index = 0
                while index < len(body) and len(readable_parts) < 100:
                    if 0x20 <= body[index] < 0x7F:
                        start = index
                        while index < len(body) and 0x20 <= body[index] < 0x7F:
                            index += 1
                        text = body[start:index].decode("ascii", errors="replace")
                        if len(text) >= 2:
                            readable_parts.append(text)
                    else:
                        index += 1

                entry["extracted_strings"] = readable_parts[:50]
                self.data[f"{req.method}_{req_url}_{len(body)}"] = entry

                print(f"\n[IM API] {req.method} {req_url[:80]}...")
                print(f"  大小: {len(body)} bytes, 提取文本片段: {len(readable_parts)}")
                for text in readable_parts[:10]:
                    print(f"  >> {text[:200]}")
            except Exception as exc:
                print(f"  处理失败: {exc}")


async def extract_conversation_list(page):
    """从 DOM 中抓取当前可见会话列表。"""
    return await page.evaluate(
        f"""() => {{
        const items = document.querySelectorAll('{CONVERSATION_ITEM_SELECTOR}');
        const results = [];
        items.forEach((item, i) => {{
            const nameEl = item.querySelector('{CONVERSATION_NAME_SELECTOR}');
            const msgEl = item.querySelector('{CONVERSATION_LAST_MESSAGE_SELECTOR}');
            const timeEl = item.querySelector('{CONVERSATION_TIME_SELECTOR}');
            results.push({{
                index: i,
                name: nameEl ? nameEl.textContent.trim() : '',
                lastMsg: msgEl ? msgEl.textContent.trim() : '',
                time: timeEl ? timeEl.textContent.trim() : ''
            }});
        }});
        return results;
    }}"""
    )


async def open_conversation_by_name(page, target_user, timeout=5000):
    """在当前会话列表中按名称关键字打开目标会话。"""
    items = await page.query_selector_all(CONVERSATION_ITEM_SELECTOR)
    for item in items:
        try:
            name = await item.query_selector(CONVERSATION_NAME_SELECTOR)
            if name and target_user in await name.inner_text():
                await item.click(timeout=timeout)
                await asyncio.sleep(2)
                return True
        except Exception:
            pass
    return False


async def get_message_panel_text(page, max_chars=2000):
    """获取当前聊天面板中可见的文本摘要。"""
    return await page.evaluate(
        f"""() => {{
        const panels = document.querySelectorAll('{CHAT_PANEL_SELECTOR}');
        for (const panel of panels) {{
            const text = panel.textContent.trim();
            if (text.length > 20) {{
                return text.substring(0, {max_chars});
            }}
        }}
        return '';
    }}"""
    )


async def extract_recent_conversation_messages(
    page,
    limit=DEFAULT_MEMORY_MESSAGE_LIMIT,
):
    """从当前聊天面板中提取最近的结构化消息。"""
    raw_messages = await page.evaluate(
        f"""(limit) => {{
        const normalizeText = (value) => (value || '').replace(/\\s+/g, ' ').trim();
        const selectors = [
            '[data-message-id]',
            '[class*="bubble"]',
            '[class*="message"]',
            '[class*="msg"]',
            '[class*="item"]',
            '[class*="content"]',
            '[class*="text"]'
        ];
        const panels = Array.from(document.querySelectorAll('{CHAT_PANEL_SELECTOR}'));
        let targetPanel = null;
        let maxTextLength = 0;
        for (const panel of panels) {{
            const text = normalizeText(panel.innerText || panel.textContent || '');
            if (text.length > maxTextLength) {{
                targetPanel = panel;
                maxTextLength = text.length;
            }}
        }}
        if (!targetPanel) {{
            return [];
        }}

        const panelRect = targetPanel.getBoundingClientRect();
        const seen = new Set();
        const candidates = [];

        const detectRole = (element, rect) => {{
            const classNames = [
                element.className || '',
                element.parentElement ? (element.parentElement.className || '') : '',
                element.getAttribute('data-testid') || '',
                element.getAttribute('data-role') || '',
            ].join(' ').toLowerCase();

            if (/(self|mine|me|owner|send|sender|outgoing|reply-right|message-right|right)/.test(classNames)) {{
                return 'assistant';
            }}
            if (/(other|user|customer|incoming|receive|receiver|reply-left|message-left|left)/.test(classNames)) {{
                return 'user';
            }}

            const centerX = rect.left + rect.width / 2;
            if (panelRect.width > 0) {{
                const ratio = (centerX - panelRect.left) / panelRect.width;
                if (ratio >= 0.58) {{
                    return 'assistant';
                }}
                if (ratio <= 0.42) {{
                    return 'user';
                }}
            }}
            return '';
        }};

        const addCandidate = (element) => {{
            if (!(element instanceof HTMLElement)) {{
                return;
            }}

            const text = normalizeText(element.innerText || element.textContent || '');
            if (!text || text.length > 500) {{
                return;
            }}
            if (element.tagName === 'BUTTON') {{
                return;
            }}

            const rect = element.getBoundingClientRect();
            if (!rect.width || !rect.height) {{
                return;
            }}
            if (rect.top < panelRect.top + 40) {{
                return;
            }}
            if (rect.height > panelRect.height * 0.8) {{
                return;
            }}

            const childTexts = Array.from(element.children || [])
                .map((child) => normalizeText(child.innerText || child.textContent || ''))
                .filter(Boolean);
            if (childTexts.some((childText) => childText === text)) {{
                return;
            }}
            if (childTexts.length > 1 && normalizeText(childTexts.join(' ')) === text) {{
                return;
            }}

            const role = detectRole(element, rect);
            if (!role) {{
                return;
            }}

            const key = `${{Math.round(rect.top)}}|${{Math.round(rect.left)}}|${{role}}|${{text}}`;
            if (seen.has(key)) {{
                return;
            }}
            seen.add(key);
            candidates.push({{
                role,
                message_text: text,
                top: rect.top,
                left: rect.left,
            }});
        }};

        for (const selector of selectors) {{
            const elements = targetPanel.querySelectorAll(selector);
            elements.forEach((element) => addCandidate(element));
        }}

        candidates.sort((a, b) => {{
            if (a.top === b.top) {{
                return a.left - b.left;
            }}
            return a.top - b.top;
        }});

        const deduped = [];
        for (const item of candidates) {{
            const previous = deduped[deduped.length - 1];
            if (previous && previous.role === item.role && previous.message_text === item.message_text) {{
                continue;
            }}
            deduped.push(item);
        }}

        return deduped.slice(-limit).map((item) => ({{
            role: item.role,
            message_text: item.message_text,
        }}));
    }}""",
        limit,
    )

    messages = []
    for item in raw_messages:
        role = (item.get("role") or "").strip()
        message_text = normalize_text(item.get("message_text") or "")
        if role not in {"user", "assistant"} or not message_text:
            continue
        messages.append(
            {
                "role": role,
                "message_text": message_text,
            }
        )
    return messages[-limit:]


async def extract_chat_history(
    playwright,
    browser_name=DEFAULT_BROWSER_NAME,
    chat_url=DEFAULT_CHAT_URL,
    output_dir=DEFAULT_OUTPUT_DIR,
):
    """进入私信页并抓取当前可访问的聊天概览与 protobuf 数据。"""
    os.makedirs(output_dir, exist_ok=True)

    browser_id, browser, context = await attach_browser(
        playwright=playwright,
        browser_name=browser_name,
        create_if_missing=False,
    )
    page = await get_or_create_page(context)
    protobuf_store = ProtobufCaptureStore(output_dir)
    page.on("response", protobuf_store.intercept_protobuf)

    print(f"窗口: {browser_name} ({browser_id})")
    print(f"访问: {chat_url}")
    await page.goto(chat_url, wait_until="domcontentloaded")
    await asyncio.sleep(12)

    print("\n\n" + "=" * 60)
    print("方法1: 从DOM提取会话列表概览")
    print("=" * 60)

    conversation_list = await extract_conversation_list(page)
    print(f"共找到 {len(conversation_list)} 个会话:")
    for conversation in conversation_list:
        print(
            f"  [{conversation['index']}] {conversation['name']} | "
            f"{conversation['lastMsg'][:50]} | {conversation['time']}"
        )

    print("\n\n" + "=" * 60)
    print("方法2: 点击每个会话，拦截protobuf中的消息数据")
    print("=" * 60)

    all_chat_data = {}
    for idx in range(len(conversation_list)):
        try:
            items = await page.query_selector_all(CONVERSATION_ITEM_SELECTOR)
            if idx >= len(items):
                break

            item = items[idx]
            name_el = await item.query_selector(CONVERSATION_NAME_SELECTOR)
            conv_name = await name_el.inner_text() if name_el else f"会话_{idx}"
            conv_name = conv_name.strip()

            print(f"\n--- [{idx + 1}/{len(conversation_list)}] 点击: {conv_name} ---")
            before_keys = set(protobuf_store.data.keys())

            try:
                await item.click(timeout=5000)
            except Exception:
                print("  点击失败，尝试force click")
                try:
                    await item.click(force=True, timeout=3000)
                except Exception as exc:
                    print(f"  force click也失败: {exc}")
                    continue

            await asyncio.sleep(3)

            after_keys = set(protobuf_store.data.keys())
            new_keys = after_keys - before_keys
            conv_strings = []
            for key in new_keys:
                entry = protobuf_store.data[key]
                if "get_by_conversation" in entry["url"] or entry["body_size"] > 500:
                    conv_strings.extend(entry.get("extracted_strings", []))

            if not conv_strings:
                msg_panel = await page.evaluate(
                    f"""() => {{
                    const panels = document.querySelectorAll('{CHAT_PANEL_SELECTOR}');
                    for (const panel of panels) {{
                        const text = panel.textContent.trim();
                        if (text.length > 20) {{
                            return text.substring(0, 2000);
                        }}
                    }}
                    return '';
                }}"""
                )
                if msg_panel:
                    conv_strings.append(msg_panel)

            all_chat_data[conv_name] = {
                "index": idx,
                "extracted_strings": conv_strings,
                "new_api_calls": len(new_keys),
            }
            print(f"  新API调用: {len(new_keys)}, 提取文本: {len(conv_strings)}")
            for text in conv_strings[:10]:
                print(f"  >> {text[:150]}")
        except Exception as exc:
            print(f"  错误: {exc}")

    print("\n\n" + "=" * 60)
    print("方法3: 滚动加载全部会话列表")
    print("=" * 60)

    list_container = await page.query_selector(CHAT_LIST_CONTAINER_SELECTOR)
    if not list_container:
        list_container = await page.query_selector(CHAT_FALLBACK_CONTAINER_SELECTOR)

    final_conversations = []
    if list_container:
        prev_count = 0
        for scroll_round in range(10):
            await list_container.evaluate("el => el.scrollTop = el.scrollHeight")
            await asyncio.sleep(2)
            current_items = await page.query_selector_all(CONVERSATION_ITEM_SELECTOR)
            current_count = len(current_items)
            print(f"  滚动轮次 {scroll_round + 1}: 当前 {current_count} 个会话")
            if current_count == prev_count:
                break
            prev_count = current_count

        final_conversations = await extract_conversation_list(page)
        print(f"\n滚动后共 {len(final_conversations)} 个会话:")
        for conversation in final_conversations:
            print(
                f"  [{conversation['index']}] {conversation['name']} | "
                f"{conversation['lastMsg'][:60]} | {conversation['time']}"
            )

    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "conversation_list": conversation_list,
        "all_chat_data": all_chat_data,
        "final_conversations": final_conversations,
        "protobuf_api_summary": {
            key: {
                "url": value["url"][:100],
                "size": value["body_size"],
                "strings": value.get("extracted_strings", [])[:20],
            }
            for key, value in protobuf_store.data.items()
        },
    }

    result_file = os.path.join(output_dir, "extraction_result.json")
    with open(result_file, "w", encoding="utf-8") as file_obj:
        json.dump(result, file_obj, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到 {result_file}")
    print(f"Protobuf原始数据保存在 {output_dir}/ 目录")

    return {
        "browser_id": browser_id,
        "browser": browser,
        "context": context,
        "page": page,
        "result": result,
        "result_file": result_file,
        "output_dir": output_dir,
    }
