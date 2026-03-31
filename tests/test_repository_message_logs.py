import tempfile
import unittest
from pathlib import Path

from douyin_automation.storage.database import AppRepository, DatabaseManager


class RepositoryMessageLogsTest(unittest.TestCase):
    def test_list_recent_message_logs_returns_task_and_reply_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.db"
            repository = AppRepository(DatabaseManager(db_path))

            skipped_task_id = repository.create_reply_task(
                account_id=1,
                conversation_name="老客户",
                user_message="在吗",
                context_text="",
                fingerprint="fp-skipped",
            )
            repository.update_reply_task(skipped_task_id, "skipped")

            sent_task_id = repository.create_reply_task(
                account_id=2,
                conversation_name="新客户",
                user_message="请问怎么收费",
                context_text="",
                fingerprint="fp-sent",
            )
            repository.update_reply_task(sent_task_id, "sent")
            repository.add_reply_record(
                task_id=sent_task_id,
                account_id=2,
                conversation_name="新客户",
                prompt_text="prompt",
                ai_reply_text="您好，这边按套餐收费。",
                send_status="sent",
            )

            rows = repository.list_recent_message_logs(limit=10)

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["conversation_name"], "新客户")
            self.assertEqual(rows[0]["user_message"], "请问怎么收费")
            self.assertEqual(rows[0]["task_status"], "sent")
            self.assertEqual(rows[0]["send_status"], "sent")
            self.assertEqual(rows[0]["ai_reply_text"], "您好，这边按套餐收费。")

            self.assertEqual(rows[1]["conversation_name"], "老客户")
            self.assertEqual(rows[1]["user_message"], "在吗")
            self.assertEqual(rows[1]["task_status"], "skipped")
            self.assertEqual(rows[1]["send_status"], "")
            self.assertEqual(rows[1]["ai_reply_text"], "")


if __name__ == "__main__":
    unittest.main()
