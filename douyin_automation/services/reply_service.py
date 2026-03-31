"""自动回复服务。"""

from ..ai.chat_client import ChatCompletionClient
from ..config import DEFAULT_MEMORY_MESSAGE_LIMIT
from ..models.entities import ConversationMessage, FAQItem
from ..utils.text import (
    contains_any_keyword,
    normalize_text,
    split_keywords,
    truncate_text,
)
from ..utils.time_utils import now_iso
from .rule_engine import RuleEngine


class ReplyService:
    def __init__(self, repository, browser_runtime, event_handler=None):
        self.repository = repository
        self.browser_runtime = browser_runtime
        self.event_handler = event_handler
        self.rule_engine = RuleEngine()
        self.ai_client = ChatCompletionClient()

    def _emit(self, level, event_type, message, account_id=None, notify=False):
        self.repository.add_event_log(level, event_type, message, account_id=account_id)
        if self.event_handler:
            self.event_handler(level, event_type, message, account_id, notify)

    def _match_faq_items(self, user_message, faq_items):
        matched = []
        for item in faq_items:
            if not item.enabled:
                continue
            keywords = split_keywords(item.keywords or item.question)
            if not keywords:
                continue
            if contains_any_keyword(user_message, keywords):
                matched.append(item)
        return matched[:5]

    def _serialize_history_text(self, conversation_messages):
        lines = []
        for message in conversation_messages[-DEFAULT_MEMORY_MESSAGE_LIMIT:]:
            role_value = (
                message.get("role")
                if isinstance(message, dict)
                else getattr(message, "role", "")
            )
            message_text = (
                message.get("message_text")
                if isinstance(message, dict)
                else getattr(message, "message_text", "")
            )
            role = "用户" if role_value == "user" else "助手"
            text = normalize_text(message_text)
            if text:
                lines.append(f"[{role}] {text}")
        return "\n".join(lines)

    def _prepare_conversation_messages(self, conversation_messages, user_message):
        normalized_history = []
        for message in list(conversation_messages or [])[-DEFAULT_MEMORY_MESSAGE_LIMIT:]:
            role = (
                message.get("role")
                if isinstance(message, dict)
                else getattr(message, "role", "")
            )
            text = (
                message.get("message_text")
                if isinstance(message, dict)
                else getattr(message, "message_text", "")
            )
            role = (role or "").strip()
            text = normalize_text(text)
            if role not in {"user", "assistant"} or not text:
                continue
            normalized_history.append(
                ConversationMessage(
                    role=role,
                    message_text=text,
                )
            )

        latest_user_message = normalize_text(user_message)
        if latest_user_message:
            has_latest_user_message = bool(
                normalized_history
                and normalized_history[-1].role == "user"
                and normalized_history[-1].message_text == latest_user_message
            )
            if not has_latest_user_message:
                normalized_history.append(
                    ConversationMessage(
                        role="user",
                        message_text=latest_user_message,
                    )
                )

        return normalized_history[-DEFAULT_MEMORY_MESSAGE_LIMIT:]

    def build_prompt_messages(
        self,
        account,
        knowledge,
        faq_items,
        user_message,
        conversation_messages,
    ):
        matched_faqs = self._match_faq_items(user_message, faq_items)
        faq_text = ""
        if matched_faqs:
            faq_text = "\n\n".join(
                [
                    f"FAQ问题：{item.question}\nFAQ标准答案：{item.answer}"
                    for item in matched_faqs
                    if isinstance(item, FAQItem)
                ]
            )

        system_blocks = [
            "你是一个抖音私信自动回复助手，请只输出适合直接发送给用户的中文回复，不要解释推理过程。",
            f"当前账号名称：{account.display_name}",
            "请结合最近10条会话历史与最后一条用户消息，生成自然、简洁、适合直接发送的中文回复。",
        ]
        if knowledge.system_prompt.strip():
            system_blocks.append(f"系统提示词：{knowledge.system_prompt.strip()}")
        if knowledge.business_summary.strip():
            system_blocks.append(f"店铺/业务信息：{knowledge.business_summary.strip()}")
        if knowledge.tone_style.strip():
            system_blocks.append(f"回复语气要求：{knowledge.tone_style.strip()}")
        if faq_text:
            system_blocks.append(f"可参考FAQ：\n{faq_text}")

        prepared_history = self._prepare_conversation_messages(
            conversation_messages,
            user_message,
        )
        messages = [{"role": "system", "content": "\n\n".join(system_blocks)}]
        for message in prepared_history:
            messages.append(
                {
                    "role": message.role,
                    "content": message.message_text,
                }
            )

        history_preview = self._serialize_history_text(prepared_history) or "暂无历史消息"
        prompt_preview = (
            f"[System]\n{messages[0]['content']}\n\n"
            f"[History]\n{history_preview}\n\n"
            "请结合以上历史消息与最后一条用户消息生成回复。"
        )
        return messages, prompt_preview

    async def preview_prompt(self, account_id, user_message, conversation_name):
        account = self.repository.get_account(account_id)
        if not account:
            raise RuntimeError("账号不存在")
        knowledge = self.repository.get_knowledge_profile(account_id)
        faq_items = self.repository.list_faq_items(account_id)
        conversation_messages = []
        if conversation_name:
            conversation_messages = self.repository.list_recent_conversation_messages(
                account_id,
                conversation_name,
                limit=DEFAULT_MEMORY_MESSAGE_LIMIT,
            )
        _, prompt_preview = self.build_prompt_messages(
            account,
            knowledge,
            faq_items,
            user_message,
            conversation_messages,
        )
        return prompt_preview

    async def test_ai(self, prompt_text):
        config = self.repository.get_global_ai_config()
        return await self.ai_client.test_connection(config, prompt_text)

    async def handle_new_message(
        self,
        account_id,
        conversation_name,
        user_message,
        conversation_messages,
        fingerprint,
    ):
        account = self.repository.get_account(account_id)
        if not account:
            raise RuntimeError("账号不存在")

        policy = self.repository.get_reply_policy(account_id)
        knowledge = self.repository.get_knowledge_profile(account_id)
        faq_items = self.repository.list_faq_items(account_id)
        today_count = self.repository.get_today_reply_count(account_id)
        decision = self.rule_engine.evaluate(account, policy, user_message, today_count)
        prepared_history = self._prepare_conversation_messages(
            conversation_messages,
            user_message,
        )
        context_text = self._serialize_history_text(prepared_history)

        task_id = self.repository.create_reply_task(
            account_id=account_id,
            conversation_name=conversation_name,
            user_message=user_message,
            context_text=context_text,
            fingerprint=fingerprint,
            status="pending",
        )

        if not decision.allowed:
            self.repository.update_reply_task(task_id, "skipped")
            self._emit(
                "info",
                "reply_skipped",
                f"会话 {conversation_name} 未触发自动回复：{decision.reason}",
                account_id,
            )
            return {"success": False, "reason": decision.reason}

        messages, prompt_preview = self.build_prompt_messages(
            account,
            knowledge,
            faq_items,
            user_message,
            self.repository.list_recent_conversation_messages(
                account_id,
                conversation_name,
                limit=DEFAULT_MEMORY_MESSAGE_LIMIT,
            ),
        )

        config = self.repository.get_global_ai_config()
        try:
            ai_reply = await self.ai_client.generate(config, messages)
            ai_reply = truncate_text(ai_reply, max_chars=account.context_max_chars)
            if not ai_reply:
                raise RuntimeError("AI 回复为空")
        except Exception as exc:
            self.repository.update_reply_task(task_id, "ai_failed")
            self.repository.add_reply_record(
                task_id=task_id,
                account_id=account_id,
                conversation_name=conversation_name,
                prompt_text=prompt_preview,
                ai_reply_text="",
                send_status="ai_failed",
                error_message=str(exc),
            )
            self._emit("error", "ai_failed", f"AI 调用失败：{exc}", account_id, notify=True)
            return {"success": False, "reason": str(exc)}

        send_result = await self.browser_runtime.send_reply(
            account,
            conversation_name,
            ai_reply,
        )

        if send_result.get("success"):
            self.repository.update_reply_task(task_id, "sent")
            self.repository.add_reply_record(
                task_id=task_id,
                account_id=account_id,
                conversation_name=conversation_name,
                prompt_text=prompt_preview,
                ai_reply_text=ai_reply,
                send_status="sent",
            )
            self.repository.update_account_fields(
                account_id,
                last_replied_fingerprint=fingerprint,
                last_outbound_text=ai_reply,
                last_reply_at=now_iso(),
                status="监控中",
                last_error="",
            )
            self._emit(
                "info",
                "reply_sent",
                f"已自动回复会话：{conversation_name}",
                account_id,
            )
            return {"success": True, "reply_text": ai_reply}

        self.repository.update_reply_task(task_id, "reply_failed")
        self.repository.add_reply_record(
            task_id=task_id,
            account_id=account_id,
            conversation_name=conversation_name,
            prompt_text=prompt_preview,
            ai_reply_text=ai_reply,
            send_status="reply_failed",
            error_message=send_result.get("reason", ""),
        )
        self._emit(
            "warning",
            "reply_failed",
            f"自动回复发送失败：{conversation_name} - {send_result.get('reason', '')}",
            account_id,
            notify=True,
        )
        return {"success": False, "reason": send_result.get("reason", "")}
