import unittest
from types import SimpleNamespace

from douyin_automation.services.monitor_service import MonitorService


class FakeRepository:
    def __init__(self, account):
        self.account = account
        self.snapshots = {}
        self.event_logs = []
        self.updated_fields = []
        self.replaced_messages = []

    def get_account(self, account_id):
        if self.account.account_id == account_id:
            return self.account
        return None

    def get_snapshot(self, account_id, conversation_name):
        return self.snapshots.get((account_id, conversation_name))

    def save_snapshot(self, snapshot):
        self.snapshots[(snapshot.account_id, snapshot.conversation_name)] = {
            "fingerprint": snapshot.fingerprint
        }

    def replace_conversation_messages(self, account_id, conversation_name, messages):
        self.replaced_messages.append((account_id, conversation_name, list(messages)))

    def update_account_fields(self, account_id, **fields):
        self.updated_fields.append((account_id, fields))
        for key, value in fields.items():
            setattr(self.account, key, value)

    def add_event_log(self, level, event_type, message, account_id=None, detail_json=""):
        self.event_logs.append(
            {
                "level": level,
                "event_type": event_type,
                "message": message,
                "account_id": account_id,
                "detail_json": detail_json,
            }
        )


class FakeLoginService:
    async def ensure_account_login(self, account_id):
        return True


class FakeBrowserRuntime:
    def __init__(self, conversations, messages=None):
        self.conversations = conversations
        self.messages = messages or []

    async def fetch_conversation_list(self, account):
        return list(self.conversations)

    async def fetch_conversation_messages(self, account, conversation_name):
        return list(self.messages)


class FakeReplyService:
    def __init__(self):
        self.calls = []

    async def handle_new_message(self, **kwargs):
        self.calls.append(kwargs)
        return {"success": True}


class MonitorServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_session_bootstrap_skips_messages_before_current_start(self):
        account = SimpleNamespace(
            account_id=1,
            enabled=True,
            bootstrap_completed=True,
            last_outbound_text="",
            last_replied_fingerprint="",
            last_seen_fingerprint="",
            status="",
            last_error="",
        )
        repository = FakeRepository(account)
        browser_runtime = FakeBrowserRuntime(
            conversations=[
                {"name": "测试会话", "lastMsg": "这是一条启动前历史消息", "time": "10:00"}
            ]
        )
        reply_service = FakeReplyService()
        service = MonitorService(
            repository,
            browser_runtime,
            FakeLoginService(),
            reply_service,
        )
        service._session_bootstrap_pending.add(account.account_id)

        await service._poll_account(account.account_id)

        self.assertFalse(reply_service.calls)
        self.assertNotIn(account.account_id, service._session_bootstrap_pending)
        self.assertIn((account.account_id, "测试会话"), repository.snapshots)
        self.assertTrue(
            any(
                log["event_type"] == "monitor_session_bootstrap"
                for log in repository.event_logs
            )
        )

    async def test_new_message_emits_message_received_and_calls_reply_service(self):
        account = SimpleNamespace(
            account_id=2,
            enabled=True,
            bootstrap_completed=True,
            last_outbound_text="",
            last_replied_fingerprint="",
            last_seen_fingerprint="",
            status="",
            last_error="",
        )
        repository = FakeRepository(account)
        browser_runtime = FakeBrowserRuntime(
            conversations=[
                {"name": "新会话", "lastMsg": "请问怎么收费", "time": "11:00"}
            ],
            messages=[
                {"role": "user", "message_text": "请问怎么收费"},
                {"role": "assistant", "message_text": "这里是旧回复"},
            ],
        )
        reply_service = FakeReplyService()
        service = MonitorService(
            repository,
            browser_runtime,
            FakeLoginService(),
            reply_service,
        )

        await service._poll_account(account.account_id)

        self.assertEqual(len(reply_service.calls), 1)
        self.assertEqual(reply_service.calls[0]["conversation_name"], "新会话")
        self.assertEqual(reply_service.calls[0]["user_message"], "请问怎么收费")
        self.assertEqual(len(repository.replaced_messages), 1)
        self.assertTrue(
            any(log["event_type"] == "message_received" for log in repository.event_logs)
        )
        self.assertNotEqual(account.last_seen_fingerprint, "")


if __name__ == "__main__":
    unittest.main()
