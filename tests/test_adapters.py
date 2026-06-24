"""adapters 单元测试：strip_ansi、check_binary、run_cli、get_adapter 工厂。"""
import sys

import pytest

from adapters import AVAILABLE_PLATFORMS, get_adapter
from adapters.base import (
    BaseAdapter,
    BinaryNotFoundError,
    check_binary,
    run_cli,
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


class TestRunCli:
    """用无害的 python 子进程验证 run_cli 的子进程处理逻辑（无需 claude/codex）。"""

    def test_happy_path_returns_stdout(self):
        out = run_cli("py", [sys.executable, "-c", "print('hello')"])
        assert out == "hello"

    def test_input_passed_via_stdin(self):
        out = run_cli(
            "py",
            [sys.executable, "-c",
             "import sys; sys.stdout.write(sys.stdin.read().upper())"],
            input="abc",
        )
        assert out == "ABC"

    def test_nonzero_exit_raises_with_stderr(self):
        with pytest.raises(RuntimeError, match="退出码 3"):
            run_cli(
                "py",
                [sys.executable, "-c",
                 "import sys; sys.stderr.write('boom'); sys.exit(3)"],
            )

    def test_timeout_raises_clean_error(self):
        with pytest.raises(RuntimeError, match="超时"):
            run_cli(
                "py",
                [sys.executable, "-c", "import time; time.sleep(5)"],
                timeout=1,
            )

    def test_missing_binary_raises(self):
        with pytest.raises(BinaryNotFoundError):
            run_cli("nope", ["this-binary-does-not-exist-xyz123"])

    def test_strips_ansi_from_output(self):
        out = run_cli(
            "py",
            [sys.executable, "-c", "print('\\x1b[31mred\\x1b[0m')"],
        )
        assert out == "red"

    def test_no_input_does_not_block_on_stdin(self):
        # 不传 input 时 stdin 接 DEVNULL，子进程读到 EOF 而非挂起
        out = run_cli(
            "py",
            [sys.executable, "-c",
             "import sys; print('empty' if sys.stdin.read() == '' else 'got')"],
        )
        assert out == "empty"


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
