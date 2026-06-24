"""scheduler 单元测试：run_once 到期执行、跳过未来、失败处理、结果落盘。"""
import signal
from unittest.mock import patch

import pytest

import scheduler
import store
from adapters.base import BaseAdapter, BinaryNotFoundError


class _MockAdapter(BaseAdapter):
    """记录调用、可控返回的 mock adapter。"""

    name = "mock"
    calls: list[str] = []
    fail_on: str | None = None
    response: str = "# Mock\n\nAnswer: **42**"

    def run(self, question: str) -> str:
        _MockAdapter.calls.append(question)
        if _MockAdapter.fail_on and _MockAdapter.fail_on in question:
            raise RuntimeError("simulated failure")
        return _MockAdapter.response


@pytest.fixture(autouse=True)
def reset_mock():
    _MockAdapter.calls = []
    _MockAdapter.fail_on = None
    _MockAdapter.response = "# Mock\n\nAnswer: **42**"
    yield


@pytest.fixture(autouse=True)
def mock_get_adapter():
    """让 scheduler 用 _MockAdapter 而非真实 claude/codex。"""
    with patch.object(scheduler, "get_adapter", return_value=_MockAdapter()):
        yield


class TestRunOnce:
    def test_executes_due_task(self):
        store.add_task("2020-01-01 00:00", "claude", "hello")
        n = scheduler.run_once()
        assert n == 1

        tasks = store.load_tasks()
        assert tasks[0]["status"] == "done"
        assert "hello" in _MockAdapter.calls[0]

    def test_skips_future_task(self):
        store.add_task("2099-12-31 23:59", "claude", "future")
        n = scheduler.run_once()
        assert n == 0

        tasks = store.load_tasks()
        assert tasks[0]["status"] == "pending"

    def test_skips_done_task(self):
        task = store.add_task("2020-01-01 00:00", "claude", "done already")
        store.update_task(task["id"], status="done")
        n = scheduler.run_once()
        assert n == 0
        assert len(_MockAdapter.calls) == 0

    def test_skips_failed_task(self):
        task = store.add_task("2020-01-01 00:00", "claude", "failed already")
        store.update_task(task["id"], status="failed", error="boom")
        n = scheduler.run_once()
        assert n == 0

    def test_executes_multiple_due(self):
        store.add_task("2020-01-01 00:00", "claude", "q1")
        store.add_task("2020-01-01 00:00", "codex", "q2")
        n = scheduler.run_once()
        assert n == 2
        assert len(_MockAdapter.calls) == 2


class TestResultFile:
    def test_result_written_to_file(self):
        task = store.add_task("2020-01-01 00:00", "claude", "hello")
        scheduler.run_once()

        result_file = scheduler.RESULTS_DIR / f"{task['id']}.txt"
        assert result_file.exists()
        assert "Answer: **42**" in result_file.read_text("utf-8")

    def test_no_result_file_on_failure(self):
        _MockAdapter.fail_on = "boom"
        task = store.add_task("2020-01-01 00:00", "claude", "boom question")
        scheduler.run_once()

        result_file = scheduler.RESULTS_DIR / f"{task['id']}.txt"
        assert not result_file.exists()


class TestFailureHandling:
    def test_failed_task_records_error(self):
        _MockAdapter.fail_on = "explode"
        store.add_task("2020-01-01 00:00", "claude", "explode me")
        scheduler.run_once()

        tasks = store.load_tasks()
        assert tasks[0]["status"] == "failed"
        assert "simulated failure" in tasks[0]["error"]

    def test_binary_not_found_error(self):
        def boom(question):
            raise BinaryNotFoundError("未找到 'claude'")

        with patch.object(scheduler, "get_adapter") as m:
            m.return_value.run = boom
            store.add_task("2020-01-01 00:00", "claude", "q")
            scheduler.run_once()

        tasks = store.load_tasks()
        assert tasks[0]["status"] == "failed"
        assert "未找到" in tasks[0]["error"]


class TestInvalidScheduledAt:
    def test_bad_time_format_marked_failed(self):
        store.add_task("not-a-date", "claude", "q")
        scheduler.run_once()

        tasks = store.load_tasks()
        assert tasks[0]["status"] == "failed"
        assert "格式非法" in tasks[0]["error"]


@pytest.fixture
def restore_signals():
    """run_loop 会注册 SIGTERM/SIGINT 处理器，测试后恢复，避免影响 pytest。"""
    old_term = signal.getsignal(signal.SIGTERM)
    old_int = signal.getsignal(signal.SIGINT)
    yield
    signal.signal(signal.SIGTERM, old_term)
    signal.signal(signal.SIGINT, old_int)


class TestRunLoopShutdown:
    def test_loop_exits_when_stop_requested(self, monkeypatch, capsys, restore_signals):
        """收到停止信号后，循环在当前轮次结束即退出并记录日志。"""
        calls = []

        def fake_run_once():
            calls.append(1)
            scheduler._request_stop(None, None)  # 模拟信号置位
            return 0

        monkeypatch.setattr(scheduler, "run_once", fake_run_once)
        scheduler.run_loop(interval=1)

        assert len(calls) == 1  # 只跑了一轮就退出
        assert "daemon 已停止" in capsys.readouterr().out


class TestFileContext:
    def test_file_content_appended_to_question(self, tmp_path):
        """--question + --file：问题在前，文件内容作为附加上下文。"""
        ctx = tmp_path / "ctx.txt"
        ctx.write_text("CONTEXT_BODY", encoding="utf-8")
        store.add_task(
            "2020-01-01 00:00", "claude", "explain this", file=str(ctx)
        )
        scheduler.run_once()
        prompt = _MockAdapter.calls[0]
        assert "explain this" in prompt
        assert "CONTEXT_BODY" in prompt  # 真正读取的是内容，而非路径

    def test_file_only_uses_content_as_prompt(self, tmp_path):
        """仅 --file（无 --question）：文件内容本身即提问。"""
        ctx = tmp_path / "prompt.txt"
        ctx.write_text("THE_WHOLE_PROMPT", encoding="utf-8")
        store.add_task("2020-01-01 00:00", "claude", "", file=str(ctx))
        scheduler.run_once()
        assert _MockAdapter.calls[0] == "THE_WHOLE_PROMPT"

    def test_missing_file_notes_path_and_still_runs(self):
        """文件执行时不可读：附上提示但不让整条任务失败。"""
        store.add_task(
            "2020-01-01 00:00", "claude", "explain this", file="/tmp/nope.py"
        )
        scheduler.run_once()

        tasks = store.load_tasks()
        assert tasks[0]["status"] == "done"
        assert "/tmp/nope.py" in _MockAdapter.calls[0]
