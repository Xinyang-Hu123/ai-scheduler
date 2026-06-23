"""adapters 单元测试：strip_ansi、check_binary、get_adapter 工厂。"""
import pytest

from adapters import AVAILABLE_PLATFORMS, get_adapter
from adapters.base import (
    BaseAdapter,
    BinaryNotFoundError,
    check_binary,
    strip_ansi,
)
from adapters.claude_adapter import ClaudeAdapter
from adapters.codex_adapter import CodexAdapter


class TestStripAnsi:
    def test_plain_text_unchanged(self):
        assert strip_ansi("hello world") == "hello world"

    def test_removes_color_codes(self):
        text = "\x1b[31mred text\x1b[0m"
        assert strip_ansi(text) == "red text"

    def test_removes_multiple_codes(self):
        text = "\x1b[1;32m\x1b[4mbold green underline\x1b[0m\x1b[0m"
        assert strip_ansi(text) == "bold green underline"

    def test_removes_cursor_codes(self):
        text = "\x1b[2J\x1b[HCleared"
        assert "Cleared" in strip_ansi(text)
        assert "\x1b" not in strip_ansi(text)

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_strips_then_trims_whitespace(self):
        text = "\x1b[0m  hello  \x1b[0m"
        # strip_ansi 本身不去首尾空格，ClaudeAdapter.run 会 strip
        assert strip_ansi(text).strip() == "hello"


class TestCheckBinary:
    def test_raises_binary_not_found(self):
        err = FileNotFoundError("[Errno 2] No such file: 'claude'")
        with pytest.raises(BinaryNotFoundError) as exc_info:
            check_binary("claude", err)
        assert "未找到 'claude'" in str(exc_info.value)

    def test_preserves_cause(self):
        err = FileNotFoundError("missing")
        with pytest.raises(BinaryNotFoundError) as exc_info:
            check_binary("codex", err)
        assert exc_info.value.__cause__ is err


class TestGetAdapter:
    def test_claude_returns_claude_adapter(self):
        adapter = get_adapter("claude")
        assert isinstance(adapter, ClaudeAdapter)
        assert adapter.name == "claude"

    def test_codex_returns_codex_adapter(self):
        adapter = get_adapter("codex")
        assert isinstance(adapter, CodexAdapter)
        assert adapter.name == "codex"

    def test_unknown_platform_raises(self):
        with pytest.raises(ValueError, match="不支持的平台"):
            get_adapter("chatgpt")

    def test_available_platforms_contains_both(self):
        assert "claude" in AVAILABLE_PLATFORMS
        assert "codex" in AVAILABLE_PLATFORMS


class TestAdapterBase:
    def test_base_is_abstract(self):
        with pytest.raises(TypeError):
            BaseAdapter()  # type: ignore[abstract]

    def test_subclass_must_implement_run(self):
        class Incomplete(BaseAdapter):
            name = "incomplete"

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]
