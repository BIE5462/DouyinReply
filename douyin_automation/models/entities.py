"""系统核心数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import (
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MAX_TOKENS,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_TEMPERATURE,
    DEFAULT_AI_TIMEOUT_SECONDS,
    DEFAULT_BROWSER_NAME,
    DEFAULT_CHAT_URL,
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_COOLDOWN_SECONDS,
    DEFAULT_CREATOR_URL,
    DEFAULT_DAILY_LIMIT,
    DEFAULT_MONITOR_INTERVAL_SECONDS,
    DEFAULT_REPLY_MAX_RETRIES,
    DEFAULT_WORK_END,
    DEFAULT_WORK_START,
)


def _get_value(row: Any, key: str, default=None):
    if row is None:
        return default
    try:
        value = row[key]
    except (TypeError, KeyError, IndexError):
        value = getattr(row, key, default)
    return default if value is None else value


@dataclass
class GlobalAIConfig:
    base_url: str = DEFAULT_AI_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_AI_MODEL
    temperature: float = DEFAULT_AI_TEMPERATURE
    max_tokens: int = DEFAULT_AI_MAX_TOKENS
    timeout_seconds: int = DEFAULT_AI_TIMEOUT_SECONDS

    @property
    def is_complete(self):
        return bool(self.base_url and self.api_key and self.model)


@dataclass
class ReplyPolicy:
    account_id: int | None = None
    work_start: str = DEFAULT_WORK_START
    work_end: str = DEFAULT_WORK_END
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS
    daily_limit: int = DEFAULT_DAILY_LIMIT
    blacklist_keywords: str = ""
    whitelist_keywords: str = ""
    manual_takeover: bool = False
    monitor_interval_seconds: int = DEFAULT_MONITOR_INTERVAL_SECONDS
    reply_max_retries: int = DEFAULT_REPLY_MAX_RETRIES

    @classmethod
    def from_row(cls, row):
        return cls(
            account_id=_get_value(row, "account_id"),
            work_start=_get_value(row, "work_start", DEFAULT_WORK_START),
            work_end=_get_value(row, "work_end", DEFAULT_WORK_END),
            cooldown_seconds=int(
                _get_value(row, "cooldown_seconds", DEFAULT_COOLDOWN_SECONDS)
            ),
            daily_limit=int(_get_value(row, "daily_limit", DEFAULT_DAILY_LIMIT)),
            blacklist_keywords=_get_value(row, "blacklist_keywords", ""),
            whitelist_keywords=_get_value(row, "whitelist_keywords", ""),
            manual_takeover=bool(_get_value(row, "manual_takeover", 0)),
            monitor_interval_seconds=int(
                _get_value(
                    row,
                    "monitor_interval_seconds",
                    DEFAULT_MONITOR_INTERVAL_SECONDS,
                )
            ),
            reply_max_retries=int(
                _get_value(row, "reply_max_retries", DEFAULT_REPLY_MAX_RETRIES)
            ),
        )


@dataclass
class KnowledgeProfile:
    account_id: int | None = None
    system_prompt: str = ""
    business_summary: str = ""
    tone_style: str = ""

    @classmethod
    def from_row(cls, row):
        return cls(
            account_id=_get_value(row, "account_id"),
            system_prompt=_get_value(row, "system_prompt", ""),
            business_summary=_get_value(row, "business_summary", ""),
            tone_style=_get_value(row, "tone_style", ""),
        )


@dataclass
class FAQItem:
    faq_id: int | None = None
    account_id: int | None = None
    question: str = ""
    answer: str = ""
    keywords: str = ""
    enabled: bool = True

    @classmethod
    def from_row(cls, row):
        return cls(
            faq_id=_get_value(row, "id"),
            account_id=_get_value(row, "account_id"),
            question=_get_value(row, "question", ""),
            answer=_get_value(row, "answer", ""),
            keywords=_get_value(row, "keywords", ""),
            enabled=bool(_get_value(row, "enabled", 1)),
        )


@dataclass
class AccountConfig:
    account_id: int | None = None
    display_name: str = ""
    browser_name: str = DEFAULT_BROWSER_NAME
    creator_url: str = DEFAULT_CREATOR_URL
    chat_url: str = DEFAULT_CHAT_URL
    enabled: bool = True
    auto_reply_enabled: bool = True
    manual_takeover: bool = False
    status: str = "未配置"
    last_error: str = ""
    last_browser_id: str = ""
    last_seen_fingerprint: str = ""
    last_replied_fingerprint: str = ""
    last_outbound_text: str = ""
    last_monitor_at: str = ""
    last_login_check_at: str = ""
    last_reply_at: str = ""
    bootstrap_completed: bool = False
    inherit_reply_policy: bool = True
    inherit_knowledge_profile: bool = True
    inherit_faq_items: bool = True
    context_max_chars: int = DEFAULT_CONTEXT_MAX_CHARS

    @classmethod
    def from_row(cls, row):
        return cls(
            account_id=_get_value(row, "id"),
            display_name=_get_value(row, "display_name", ""),
            browser_name=_get_value(row, "browser_name", DEFAULT_BROWSER_NAME),
            creator_url=_get_value(row, "creator_url", DEFAULT_CREATOR_URL),
            chat_url=_get_value(row, "chat_url", DEFAULT_CHAT_URL),
            enabled=bool(_get_value(row, "enabled", 1)),
            auto_reply_enabled=bool(_get_value(row, "auto_reply_enabled", 1)),
            manual_takeover=bool(_get_value(row, "manual_takeover", 0)),
            status=_get_value(row, "status", "未配置"),
            last_error=_get_value(row, "last_error", ""),
            last_browser_id=_get_value(row, "last_browser_id", ""),
            last_seen_fingerprint=_get_value(row, "last_seen_fingerprint", ""),
            last_replied_fingerprint=_get_value(row, "last_replied_fingerprint", ""),
            last_outbound_text=_get_value(row, "last_outbound_text", ""),
            last_monitor_at=_get_value(row, "last_monitor_at", ""),
            last_login_check_at=_get_value(row, "last_login_check_at", ""),
            last_reply_at=_get_value(row, "last_reply_at", ""),
            bootstrap_completed=bool(_get_value(row, "bootstrap_completed", 0)),
            inherit_reply_policy=bool(_get_value(row, "inherit_reply_policy", 1)),
            inherit_knowledge_profile=bool(
                _get_value(row, "inherit_knowledge_profile", 1)
            ),
            inherit_faq_items=bool(_get_value(row, "inherit_faq_items", 1)),
            context_max_chars=int(
                _get_value(row, "context_max_chars", DEFAULT_CONTEXT_MAX_CHARS)
            ),
        )


@dataclass
class ConversationSnapshot:
    account_id: int
    conversation_name: str
    last_message_text: str
    time_label: str
    fingerprint: str
    observed_at: str


@dataclass
class ConversationMessage:
    message_id: int | None = None
    account_id: int | None = None
    conversation_name: str = ""
    role: str = "user"
    message_text: str = ""
    observed_at: str = ""

    @classmethod
    def from_row(cls, row):
        return cls(
            message_id=_get_value(row, "id"),
            account_id=_get_value(row, "account_id"),
            conversation_name=_get_value(row, "conversation_name", ""),
            role=_get_value(row, "role", "user"),
            message_text=_get_value(row, "message_text", ""),
            observed_at=_get_value(row, "observed_at", ""),
        )


@dataclass
class ReplyTask:
    task_id: int | None = None
    account_id: int | None = None
    conversation_name: str = ""
    user_message: str = ""
    context_text: str = ""
    fingerprint: str = ""
    status: str = "pending"
    retry_count: int = 0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ReplyRecord:
    record_id: int | None = None
    task_id: int | None = None
    account_id: int | None = None
    conversation_name: str = ""
    prompt_text: str = ""
    ai_reply_text: str = ""
    send_status: str = ""
    error_message: str = ""
    created_at: str = ""
