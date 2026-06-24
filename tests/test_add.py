"""add.py 单元测试：时间解析、过期顺延、参数校验。"""
from datetime import datetime, timedelta

import pytest
import typer

from commands.add import parse_scheduled_at


class TestParseScheduledAt:
    def test_full_datetime(self):
        result = parse_scheduled_at("2026-06-24 23:30")
        assert result == "2026-06-24T23:30:00"

    def test_full_datetime_with_seconds(self):
        result = parse_scheduled_at("2026-06-24 23:30:45")
        assert result == "2026-06-24T23:30:45"

    def test_time_only_future_today(self):
        """只给时间且未过 -> 今天。"""
        now = datetime.now()
        # 用 1 小时后的时间，避免跨午夜
        future_dt = now + timedelta(hours=1)
        if future_dt.date() != now.date():
            # 跨午夜了，改用 1 分钟后
            future_dt = now + timedelta(minutes=1)
        future = future_dt.strftime("%H:%M")
        result = parse_scheduled_at(future)
        parsed = datetime.fromisoformat(result)
        assert parsed.date() == now.date()

    def test_time_only_past_rolls_to_tomorrow(self):
        """只给时间且已过 -> 顺延明天。"""
        now = datetime.now()
        past_dt = now - timedelta(hours=3)
        # 跨午夜时改用今天凌晨，确保时间确实已过
        if past_dt.date() != now.date():
            past_dt = now.replace(hour=0, minute=5, second=0, microsecond=0)
        past = past_dt.strftime("%H:%M")
        result = parse_scheduled_at(past)
        parsed = datetime.fromisoformat(result)
        assert parsed.date() == (now + timedelta(days=1)).date()

    def test_invalid_format_raises(self):
        with pytest.raises(typer.BadParameter):
            parse_scheduled_at("not-a-time")

    def test_garbage_raises(self):
        with pytest.raises(typer.BadParameter):
            parse_scheduled_at("9999-99-99 99:99")

    def test_empty_string_raises(self):
        with pytest.raises(typer.BadParameter):
            parse_scheduled_at("")


class TestRolloverEdgeCases:
    def test_exactly_now_rolls_to_tomorrow(self):
        """时间恰好等于现在（<=）应顺延。"""
        now = datetime.now().replace(second=0, microsecond=0)
        at_str = now.strftime("%H:%M")
        result = parse_scheduled_at(at_str)
        parsed = datetime.fromisoformat(result)
        # <= 触发顺延，所以应是明天同一时刻
        assert parsed.date() == (now + timedelta(days=1)).date()
