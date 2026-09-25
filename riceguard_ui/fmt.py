"""Formatting helpers, same output as web/src/services/format.ts (en-US, the viewer's own time zone)."""
from datetime import datetime, timedelta, timezone


def file_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    units = ["KB", "MB", "GB"]
    v, i = n / 1024, 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{v:.1f} {units[i]}" if v < 10 else f"{int(v + 0.5)} {units[i]}"


def file_type(mime: str) -> str:
    t = mime.split("/")[1].upper() if "/" in mime else mime
    return "JPG" if t == "JPEG" else t


def pct(v: float, digits: int = 0) -> str:
    return f"{v * 100:.{digits}f}%"


def _local(ts: datetime, tz_offset_min) -> datetime:
    """UTC -> the browser's local time. tz_offset_min follows JavaScript getTimezoneOffset (UTC+8 -> -480)."""
    return ts.astimezone(timezone.utc) - timedelta(minutes=tz_offset_min or 0)


def date_time(ts: datetime, tz_offset_min) -> str:
    d = _local(ts, tz_offset_min)
    hour = d.hour % 12 or 12
    return f"{d:%b} {d.day}, {d.year}, {hour}:{d:%M} {'AM' if d.hour < 12 else 'PM'}"


def relative(ts: datetime, tz_offset_min) -> str:
    diff = (datetime.now(timezone.utc) - ts).total_seconds()
    if diff < 60:
        return "Just now"
    if diff < 3600:
        return f"{int(diff // 60)} min ago"
    if diff < 86400:
        return f"{int(diff // 3600)} hr ago"
    days = int(diff // 86400)
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    d = _local(ts, tz_offset_min)
    return f"{d:%b} {d.day}"
