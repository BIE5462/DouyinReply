"""时间工具。"""

from datetime import datetime, time


def now_local():
    return datetime.now()


def now_iso():
    return now_local().isoformat(timespec="seconds")


def parse_hhmm(value, fallback="09:00"):
    target = value or fallback
    hour_str, minute_str = target.split(":", 1)
    return time(int(hour_str), int(minute_str))


def is_within_work_hours(current_dt, start_hhmm, end_hhmm):
    current_time = current_dt.time()
    start_time = parse_hhmm(start_hhmm)
    end_time = parse_hhmm(end_hhmm)
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    return current_time >= start_time or current_time <= end_time
