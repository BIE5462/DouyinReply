"""指纹与去重工具。"""

import hashlib

from .text import normalize_text


def build_conversation_fingerprint(account_id, conversation_name, last_message_text, time_label):
    payload = "||".join(
        [
            str(account_id or ""),
            normalize_text(conversation_name),
            normalize_text(last_message_text),
            normalize_text(time_label),
        ]
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()
