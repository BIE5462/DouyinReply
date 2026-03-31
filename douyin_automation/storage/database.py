"""SQLite 数据库与仓储实现。"""

import csv
import sqlite3
from pathlib import Path

from ..config import (
    DEFAULT_AI_BASE_URL,
    DEFAULT_AI_MAX_TOKENS,
    DEFAULT_AI_MODEL,
    DEFAULT_AI_TEMPERATURE,
    DEFAULT_AI_TIMEOUT_SECONDS,
    DEFAULT_MEMORY_MESSAGE_LIMIT,
)
from ..models.entities import (
    AccountConfig,
    ConversationMessage,
    FAQItem,
    GlobalAIConfig,
    KnowledgeProfile,
    ReplyPolicy,
)
from ..utils.time_utils import now_iso


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_account_inheritance_columns(self, conn):
        existing_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()
        }
        inheritance_migrations = (
            (
                "inherit_reply_policy",
                """
                ALTER TABLE accounts
                ADD COLUMN inherit_reply_policy INTEGER NOT NULL DEFAULT 1
                """,
                "reply_policies",
            ),
            (
                "inherit_knowledge_profile",
                """
                ALTER TABLE accounts
                ADD COLUMN inherit_knowledge_profile INTEGER NOT NULL DEFAULT 1
                """,
                "knowledge_profiles",
            ),
            (
                "inherit_faq_items",
                """
                ALTER TABLE accounts
                ADD COLUMN inherit_faq_items INTEGER NOT NULL DEFAULT 1
                """,
                "faq_items",
            ),
        )
        for column_name, alter_sql, source_table in inheritance_migrations:
            if column_name in existing_columns:
                continue
            conn.execute(alter_sql)
            conn.execute(
                f"""
                UPDATE accounts
                SET {column_name} = 0
                WHERE id IN (
                    SELECT DISTINCT account_id
                    FROM {source_table}
                    WHERE account_id IS NOT NULL
                )
                """
            )

    def _seed_global_templates(self, conn):
        conn.execute(
            """
            INSERT INTO global_reply_policy_templates(
                template_id,
                work_start,
                work_end,
                cooldown_seconds,
                daily_limit,
                blacklist_keywords,
                whitelist_keywords,
                manual_takeover,
                monitor_interval_seconds,
                reply_max_retries
            )
            SELECT 1, '09:00', '22:00', 300, 50, '', '', 0, 15, 2
            WHERE NOT EXISTS (
                SELECT 1
                FROM global_reply_policy_templates
                WHERE template_id = 1
            )
            """
        )
        conn.execute(
            """
            INSERT INTO global_knowledge_profile_templates(
                template_id,
                system_prompt,
                business_summary,
                tone_style
            )
            SELECT 1, '', '', ''
            WHERE NOT EXISTS (
                SELECT 1
                FROM global_knowledge_profile_templates
                WHERE template_id = 1
            )
            """
        )

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL,
                    browser_name TEXT NOT NULL UNIQUE,
                    creator_url TEXT NOT NULL,
                    chat_url TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    auto_reply_enabled INTEGER NOT NULL DEFAULT 1,
                    manual_takeover INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT '未配置',
                    last_error TEXT NOT NULL DEFAULT '',
                    last_browser_id TEXT NOT NULL DEFAULT '',
                    last_seen_fingerprint TEXT NOT NULL DEFAULT '',
                    last_replied_fingerprint TEXT NOT NULL DEFAULT '',
                    last_outbound_text TEXT NOT NULL DEFAULT '',
                    last_monitor_at TEXT NOT NULL DEFAULT '',
                    last_login_check_at TEXT NOT NULL DEFAULT '',
                    last_reply_at TEXT NOT NULL DEFAULT '',
                    bootstrap_completed INTEGER NOT NULL DEFAULT 0,
                    context_max_chars INTEGER NOT NULL DEFAULT 2000
                );

                CREATE TABLE IF NOT EXISTS reply_policies (
                    account_id INTEGER PRIMARY KEY,
                    work_start TEXT NOT NULL DEFAULT '09:00',
                    work_end TEXT NOT NULL DEFAULT '22:00',
                    cooldown_seconds INTEGER NOT NULL DEFAULT 300,
                    daily_limit INTEGER NOT NULL DEFAULT 50,
                    blacklist_keywords TEXT NOT NULL DEFAULT '',
                    whitelist_keywords TEXT NOT NULL DEFAULT '',
                    manual_takeover INTEGER NOT NULL DEFAULT 0,
                    monitor_interval_seconds INTEGER NOT NULL DEFAULT 15,
                    reply_max_retries INTEGER NOT NULL DEFAULT 2
                );

                CREATE TABLE IF NOT EXISTS global_reply_policy_templates (
                    template_id INTEGER PRIMARY KEY CHECK (template_id = 1),
                    work_start TEXT NOT NULL DEFAULT '09:00',
                    work_end TEXT NOT NULL DEFAULT '22:00',
                    cooldown_seconds INTEGER NOT NULL DEFAULT 300,
                    daily_limit INTEGER NOT NULL DEFAULT 50,
                    blacklist_keywords TEXT NOT NULL DEFAULT '',
                    whitelist_keywords TEXT NOT NULL DEFAULT '',
                    manual_takeover INTEGER NOT NULL DEFAULT 0,
                    monitor_interval_seconds INTEGER NOT NULL DEFAULT 15,
                    reply_max_retries INTEGER NOT NULL DEFAULT 2
                );

                CREATE TABLE IF NOT EXISTS knowledge_profiles (
                    account_id INTEGER PRIMARY KEY,
                    system_prompt TEXT NOT NULL DEFAULT '',
                    business_summary TEXT NOT NULL DEFAULT '',
                    tone_style TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS global_knowledge_profile_templates (
                    template_id INTEGER PRIMARY KEY CHECK (template_id = 1),
                    system_prompt TEXT NOT NULL DEFAULT '',
                    business_summary TEXT NOT NULL DEFAULT '',
                    tone_style TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS faq_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    question TEXT NOT NULL DEFAULT '',
                    answer TEXT NOT NULL DEFAULT '',
                    keywords TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS global_faq_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL DEFAULT '',
                    answer TEXT NOT NULL DEFAULT '',
                    keywords TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS message_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    conversation_name TEXT NOT NULL,
                    last_message_text TEXT NOT NULL,
                    time_label TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    UNIQUE(account_id, conversation_name)
                );

                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    conversation_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conversation_messages_lookup
                ON conversation_messages(account_id, conversation_name, id DESC);

                CREATE TABLE IF NOT EXISTS reply_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    conversation_name TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    context_text TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reply_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    account_id INTEGER NOT NULL,
                    conversation_name TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    ai_reply_text TEXT NOT NULL,
                    send_status TEXT NOT NULL,
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    account_id INTEGER,
                    message TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                """
            )
            self._ensure_account_inheritance_columns(conn)
            self._seed_global_templates(conn)


class AppRepository:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.db.initialize()
        self._ensure_default_config()

    def _ensure_default_config(self):
        self.save_global_ai_config(self.get_global_ai_config())

    def set_config(self, key, value):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO app_config(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (key, str(value)),
            )

    def get_config(self, key, default=""):
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key = ?",
                (key,),
            ).fetchone()
        return row["value"] if row else default

    def save_global_ai_config(self, config: GlobalAIConfig):
        self.set_config("ai.base_url", config.base_url)
        self.set_config("ai.api_key", config.api_key)
        self.set_config("ai.model", config.model)
        self.set_config("ai.temperature", config.temperature)
        self.set_config("ai.max_tokens", config.max_tokens)
        self.set_config("ai.timeout_seconds", config.timeout_seconds)

    def get_global_ai_config(self):
        return GlobalAIConfig(
            base_url=self.get_config("ai.base_url", DEFAULT_AI_BASE_URL),
            api_key=self.get_config("ai.api_key", ""),
            model=self.get_config("ai.model", DEFAULT_AI_MODEL),
            temperature=float(
                self.get_config("ai.temperature", str(DEFAULT_AI_TEMPERATURE))
            ),
            max_tokens=int(
                self.get_config("ai.max_tokens", str(DEFAULT_AI_MAX_TOKENS))
            ),
            timeout_seconds=int(
                self.get_config(
                    "ai.timeout_seconds",
                    str(DEFAULT_AI_TIMEOUT_SECONDS),
                )
            ),
        )

    def list_accounts(self):
        with self.db.connect() as conn:
            rows = conn.execute("SELECT * FROM accounts ORDER BY id ASC").fetchall()
        return [AccountConfig.from_row(row) for row in rows]

    def get_account(self, account_id):
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        return AccountConfig.from_row(row) if row else None

    def save_account(self, account: AccountConfig):
        payload = (
            account.display_name,
            account.browser_name,
            account.creator_url,
            account.chat_url,
            int(account.enabled),
            int(account.auto_reply_enabled),
            int(account.manual_takeover),
            account.status,
            account.last_error,
            account.last_browser_id,
            account.last_seen_fingerprint,
            account.last_replied_fingerprint,
            account.last_outbound_text,
            account.last_monitor_at,
            account.last_login_check_at,
            account.last_reply_at,
            int(account.bootstrap_completed),
            int(account.inherit_reply_policy),
            int(account.inherit_knowledge_profile),
            int(account.inherit_faq_items),
            account.context_max_chars,
        )
        with self.db.connect() as conn:
            if account.account_id:
                conn.execute(
                    """
                    UPDATE accounts
                    SET display_name = ?, browser_name = ?, creator_url = ?, chat_url = ?,
                        enabled = ?, auto_reply_enabled = ?, manual_takeover = ?, status = ?,
                        last_error = ?, last_browser_id = ?, last_seen_fingerprint = ?,
                        last_replied_fingerprint = ?, last_outbound_text = ?, last_monitor_at = ?,
                        last_login_check_at = ?, last_reply_at = ?, bootstrap_completed = ?,
                        inherit_reply_policy = ?, inherit_knowledge_profile = ?, inherit_faq_items = ?,
                        context_max_chars = ?
                    WHERE id = ?
                    """,
                    payload + (account.account_id,),
                )
                account_id = account.account_id
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO accounts(
                        display_name, browser_name, creator_url, chat_url,
                        enabled, auto_reply_enabled, manual_takeover, status,
                        last_error, last_browser_id, last_seen_fingerprint,
                        last_replied_fingerprint, last_outbound_text, last_monitor_at,
                        last_login_check_at, last_reply_at, bootstrap_completed,
                        inherit_reply_policy, inherit_knowledge_profile, inherit_faq_items,
                        context_max_chars
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    payload,
                )
                account_id = cursor.lastrowid
        self.ensure_account_defaults(account_id)
        return account_id

    def ensure_account_defaults(self, account_id):
        return

    def update_account_fields(self, account_id, **fields):
        if not fields:
            return
        columns = []
        values = []
        for key, value in fields.items():
            columns.append(f"{key} = ?")
            values.append(value)
        values.append(account_id)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE accounts SET {', '.join(columns)} WHERE id = ?",
                tuple(values),
            )

    def get_global_reply_policy(self):
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM global_reply_policy_templates WHERE template_id = 1"
            ).fetchone()
        return ReplyPolicy.from_row(row) if row else ReplyPolicy()

    def save_global_reply_policy(self, policy: ReplyPolicy):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO global_reply_policy_templates(
                    template_id, work_start, work_end, cooldown_seconds, daily_limit,
                    blacklist_keywords, whitelist_keywords, manual_takeover,
                    monitor_interval_seconds, reply_max_retries
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    work_start = excluded.work_start,
                    work_end = excluded.work_end,
                    cooldown_seconds = excluded.cooldown_seconds,
                    daily_limit = excluded.daily_limit,
                    blacklist_keywords = excluded.blacklist_keywords,
                    whitelist_keywords = excluded.whitelist_keywords,
                    manual_takeover = excluded.manual_takeover,
                    monitor_interval_seconds = excluded.monitor_interval_seconds,
                    reply_max_retries = excluded.reply_max_retries
                """,
                (
                    policy.work_start,
                    policy.work_end,
                    policy.cooldown_seconds,
                    policy.daily_limit,
                    policy.blacklist_keywords,
                    policy.whitelist_keywords,
                    int(policy.manual_takeover),
                    policy.monitor_interval_seconds,
                    policy.reply_max_retries,
                ),
            )

    def get_reply_policy_override(self, account_id):
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM reply_policies WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        return ReplyPolicy.from_row(row) if row else None

    def get_reply_policy(self, account_id):
        account = self.get_account(account_id)
        if not account or account.inherit_reply_policy:
            return self.get_global_reply_policy()
        return self.get_reply_policy_override(account_id) or self.get_global_reply_policy()

    def save_reply_policy(self, policy: ReplyPolicy):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO reply_policies(
                    account_id, work_start, work_end, cooldown_seconds, daily_limit,
                    blacklist_keywords, whitelist_keywords, manual_takeover,
                    monitor_interval_seconds, reply_max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    work_start = excluded.work_start,
                    work_end = excluded.work_end,
                    cooldown_seconds = excluded.cooldown_seconds,
                    daily_limit = excluded.daily_limit,
                    blacklist_keywords = excluded.blacklist_keywords,
                    whitelist_keywords = excluded.whitelist_keywords,
                    manual_takeover = excluded.manual_takeover,
                    monitor_interval_seconds = excluded.monitor_interval_seconds,
                    reply_max_retries = excluded.reply_max_retries
                """,
                (
                    policy.account_id,
                    policy.work_start,
                    policy.work_end,
                    policy.cooldown_seconds,
                    policy.daily_limit,
                    policy.blacklist_keywords,
                    policy.whitelist_keywords,
                    int(policy.manual_takeover),
                    policy.monitor_interval_seconds,
                    policy.reply_max_retries,
                ),
            )

    def delete_reply_policy_override(self, account_id):
        with self.db.connect() as conn:
            conn.execute(
                "DELETE FROM reply_policies WHERE account_id = ?",
                (account_id,),
            )

    def get_global_knowledge_profile(self):
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM global_knowledge_profile_templates WHERE template_id = 1"
            ).fetchone()
        return KnowledgeProfile.from_row(row) if row else KnowledgeProfile()

    def save_global_knowledge_profile(self, profile: KnowledgeProfile):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO global_knowledge_profile_templates(
                    template_id, system_prompt, business_summary, tone_style
                )
                VALUES (1, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    system_prompt = excluded.system_prompt,
                    business_summary = excluded.business_summary,
                    tone_style = excluded.tone_style
                """,
                (
                    profile.system_prompt,
                    profile.business_summary,
                    profile.tone_style,
                ),
            )

    def get_knowledge_profile_override(self, account_id):
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_profiles WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        return KnowledgeProfile.from_row(row) if row else None

    def get_knowledge_profile(self, account_id):
        account = self.get_account(account_id)
        if not account or account.inherit_knowledge_profile:
            return self.get_global_knowledge_profile()
        return self.get_knowledge_profile_override(account_id) or self.get_global_knowledge_profile()

    def save_knowledge_profile(self, profile: KnowledgeProfile):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO knowledge_profiles(account_id, system_prompt, business_summary, tone_style)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    system_prompt = excluded.system_prompt,
                    business_summary = excluded.business_summary,
                    tone_style = excluded.tone_style
                """,
                (
                    profile.account_id,
                    profile.system_prompt,
                    profile.business_summary,
                    profile.tone_style,
                ),
            )

    def delete_knowledge_profile_override(self, account_id):
        with self.db.connect() as conn:
            conn.execute(
                "DELETE FROM knowledge_profiles WHERE account_id = ?",
                (account_id,),
            )

    def list_global_faq_items(self):
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM global_faq_items
                ORDER BY id ASC
                """
            ).fetchall()
        return [FAQItem.from_row(row) for row in rows]

    def replace_global_faq_items(self, items):
        with self.db.connect() as conn:
            conn.execute("DELETE FROM global_faq_items")
            for item in items:
                conn.execute(
                    """
                    INSERT INTO global_faq_items(question, answer, keywords, enabled)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        item.question,
                        item.answer,
                        item.keywords,
                        int(item.enabled),
                    ),
                )

    def list_faq_items_override(self, account_id):
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM faq_items
                WHERE account_id = ?
                ORDER BY id ASC
                """,
                (account_id,),
            ).fetchall()
        return [FAQItem.from_row(row) for row in rows]

    def list_faq_items(self, account_id):
        account = self.get_account(account_id)
        if not account or account.inherit_faq_items:
            return self.list_global_faq_items()
        return self.list_faq_items_override(account_id)

    def replace_faq_items(self, account_id, items):
        with self.db.connect() as conn:
            conn.execute("DELETE FROM faq_items WHERE account_id = ?", (account_id,))
            for item in items:
                conn.execute(
                    """
                    INSERT INTO faq_items(account_id, question, answer, keywords, enabled)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        item.question,
                        item.answer,
                        item.keywords,
                        int(item.enabled),
                    ),
                )

    def delete_faq_items_override(self, account_id):
        with self.db.connect() as conn:
            conn.execute("DELETE FROM faq_items WHERE account_id = ?", (account_id,))

    def get_snapshot(self, account_id, conversation_name):
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM message_snapshots
                WHERE account_id = ? AND conversation_name = ?
                """,
                (account_id, conversation_name),
            ).fetchone()
        return row

    def save_snapshot(self, snapshot):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO message_snapshots(
                    account_id, conversation_name, last_message_text,
                    time_label, fingerprint, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, conversation_name) DO UPDATE SET
                    last_message_text = excluded.last_message_text,
                    time_label = excluded.time_label,
                    fingerprint = excluded.fingerprint,
                    observed_at = excluded.observed_at
                """,
                (
                    snapshot.account_id,
                    snapshot.conversation_name,
                    snapshot.last_message_text,
                    snapshot.time_label,
                    snapshot.fingerprint,
                    snapshot.observed_at,
                ),
            )

    def replace_conversation_messages(self, account_id, conversation_name, messages):
        latest_messages = list(messages or [])[-DEFAULT_MEMORY_MESSAGE_LIMIT:]
        with self.db.connect() as conn:
            conn.execute(
                """
                DELETE FROM conversation_messages
                WHERE account_id = ? AND conversation_name = ?
                """,
                (account_id, conversation_name),
            )
            for message in latest_messages:
                role = (
                    message.get("role")
                    if isinstance(message, dict)
                    else getattr(message, "role", "user")
                )
                message_text = (
                    message.get("message_text")
                    if isinstance(message, dict)
                    else getattr(message, "message_text", "")
                )
                observed_at = (
                    message.get("observed_at")
                    if isinstance(message, dict)
                    else getattr(message, "observed_at", "")
                ) or now_iso()
                conn.execute(
                    """
                    INSERT INTO conversation_messages(
                        account_id, conversation_name, role, message_text, observed_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        account_id,
                        conversation_name,
                        role,
                        message_text,
                        observed_at,
                    ),
                )

    def list_recent_conversation_messages(
        self,
        account_id,
        conversation_name,
        limit=DEFAULT_MEMORY_MESSAGE_LIMIT,
    ):
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversation_messages
                WHERE account_id = ? AND conversation_name = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (account_id, conversation_name, limit),
            ).fetchall()
        return [ConversationMessage.from_row(row) for row in reversed(rows)]

    def create_reply_task(self, account_id, conversation_name, user_message, context_text, fingerprint, status="pending"):
        timestamp = now_iso()
        with self.db.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reply_tasks(
                    account_id, conversation_name, user_message, context_text,
                    fingerprint, status, retry_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    account_id,
                    conversation_name,
                    user_message,
                    context_text,
                    fingerprint,
                    status,
                    timestamp,
                    timestamp,
                ),
            )
        return cursor.lastrowid

    def update_reply_task(self, task_id, status, retry_count=None):
        fields = ["status = ?", "updated_at = ?"]
        values = [status, now_iso()]
        if retry_count is not None:
            fields.append("retry_count = ?")
            values.append(retry_count)
        values.append(task_id)
        with self.db.connect() as conn:
            conn.execute(
                f"UPDATE reply_tasks SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )

    def add_reply_record(self, task_id, account_id, conversation_name, prompt_text, ai_reply_text, send_status, error_message=""):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO reply_records(
                    task_id, account_id, conversation_name, prompt_text,
                    ai_reply_text, send_status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    account_id,
                    conversation_name,
                    prompt_text,
                    ai_reply_text,
                    send_status,
                    error_message,
                    now_iso(),
                ),
            )

    def add_event_log(self, level, event_type, message, account_id=None, detail_json=""):
        with self.db.connect() as conn:
            conn.execute(
                """
                INSERT INTO event_logs(level, event_type, account_id, message, detail_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (level, event_type, account_id, message, detail_json, now_iso()),
            )

    def get_today_reply_count(self, account_id):
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM reply_records
                WHERE account_id = ? AND date(created_at) = date('now', 'localtime')
                      AND send_status = 'sent'
                """,
                (account_id,),
            ).fetchone()
        return int(row["total"]) if row else 0

    def list_recent_reply_records(self, limit=200):
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reply_records
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return rows

    def list_recent_message_logs(self, limit=200):
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(reply_records.created_at, reply_tasks.created_at) AS created_at,
                    reply_tasks.account_id AS account_id,
                    reply_tasks.conversation_name AS conversation_name,
                    reply_tasks.user_message AS user_message,
                    reply_tasks.status AS task_status,
                    COALESCE(reply_records.send_status, '') AS send_status,
                    COALESCE(reply_records.ai_reply_text, '') AS ai_reply_text,
                    COALESCE(reply_records.error_message, '') AS error_message
                FROM reply_tasks
                LEFT JOIN reply_records
                    ON reply_records.task_id = reply_tasks.id
                ORDER BY reply_tasks.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return rows

    def list_recent_event_logs(self, limit=200):
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM event_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return rows

    def dashboard_stats(self):
        with self.db.connect() as conn:
            account_total = conn.execute(
                "SELECT COUNT(*) AS total FROM accounts"
            ).fetchone()["total"]
            monitor_total = conn.execute(
                "SELECT COUNT(*) AS total FROM accounts WHERE status = '监控中'"
            ).fetchone()["total"]
            pending_login_total = conn.execute(
                "SELECT COUNT(*) AS total FROM accounts WHERE status = '待登录'"
            ).fetchone()["total"]
            error_total = conn.execute(
                "SELECT COUNT(*) AS total FROM accounts WHERE status = '异常'"
            ).fetchone()["total"]
            today_reply_total = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM reply_records
                WHERE date(created_at) = date('now', 'localtime')
                      AND send_status = 'sent'
                """
            ).fetchone()["total"]
        return {
            "account_total": int(account_total),
            "monitor_total": int(monitor_total),
            "pending_login_total": int(pending_login_total),
            "error_total": int(error_total),
            "today_reply_total": int(today_reply_total),
        }

    def export_reply_records_csv(self, csv_path):
        rows = self.list_recent_reply_records(limit=5000)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as file_obj:
            writer = csv.writer(file_obj)
            writer.writerow(
                [
                    "id",
                    "task_id",
                    "account_id",
                    "conversation_name",
                    "prompt_text",
                    "ai_reply_text",
                    "send_status",
                    "error_message",
                    "created_at",
                ]
            )
            for row in rows:
                writer.writerow(
                    [
                        row["id"],
                        row["task_id"],
                        row["account_id"],
                        row["conversation_name"],
                        row["prompt_text"],
                        row["ai_reply_text"],
                        row["send_status"],
                        row["error_message"],
                        row["created_at"],
                    ]
                )

    def is_first_run(self):
        ai_config = self.get_global_ai_config()
        accounts = self.list_accounts()
        return not ai_config.api_key or not accounts
