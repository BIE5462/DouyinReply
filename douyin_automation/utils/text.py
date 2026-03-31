"""文本处理工具。"""


def normalize_text(text):
    return " ".join((text or "").split())


def split_keywords(text):
    normalized = (text or "").replace("，", ",").replace("\r", "\n")
    parts = []
    for chunk in normalized.replace(",", "\n").splitlines():
        item = chunk.strip()
        if item:
            parts.append(item)
    return parts


def contains_any_keyword(text, keywords):
    source = normalize_text(text).lower()
    return any(keyword.lower() in source for keyword in keywords if keyword)


def truncate_text(text, max_chars=300):
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
