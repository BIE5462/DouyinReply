"""自动回复规则引擎。"""

from dataclasses import dataclass
from datetime import datetime

from ..utils.text import contains_any_keyword, split_keywords
from ..utils.time_utils import is_within_work_hours


@dataclass
class RuleDecision:
    allowed: bool
    reason: str


class RuleEngine:
    def evaluate(self, account, policy, user_message, today_reply_count):
        if not account.enabled:
            return RuleDecision(False, "账号未启用")
        if not account.auto_reply_enabled:
            return RuleDecision(False, "账号已关闭自动回复")
        if account.manual_takeover or policy.manual_takeover:
            return RuleDecision(False, "当前处于人工接管状态")

        now = datetime.now()
        if not is_within_work_hours(now, policy.work_start, policy.work_end):
            return RuleDecision(False, "当前不在工作时段")

        if today_reply_count >= policy.daily_limit:
            return RuleDecision(False, "已达到每日上限")

        blacklist = split_keywords(policy.blacklist_keywords)
        if blacklist and contains_any_keyword(user_message, blacklist):
            return RuleDecision(False, "命中黑名单关键词")

        whitelist = split_keywords(policy.whitelist_keywords)
        if whitelist and not contains_any_keyword(user_message, whitelist):
            return RuleDecision(False, "未命中白名单关键词")

        return RuleDecision(True, "允许自动回复")
