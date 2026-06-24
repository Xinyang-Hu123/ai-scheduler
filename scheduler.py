"""调度器：轮询 tasks.json，到点执行任务并把结果落盘。"""
import signal
import time
import traceback
from datetime import datetime
from pathlib import Path

from adapters import get_adapter
from config import POLL_INTERVAL, RESULTS_DIR, ensure_dirs
from store import load_tasks, update_task

# 收到停止信号后置位，让轮询循环优雅退出
_stop_requested = False


def _log(msg: str) -> None:
    """带时间戳的 daemon 日志输出（写入 scheduler.log）。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[ai-scheduler {ts}] {msg}", flush=True)


def _request_stop(signum, frame) -> None:  # noqa: ARG001
    """信号处理：请求循环在当前轮次后退出。"""
    global _stop_requested
    _stop_requested = True


def _interruptible_sleep(seconds: int) -> None:
    """按秒分片睡眠，收到停止信号时尽快返回（响应延迟 <= 1s）。"""
    for _ in range(seconds):
        if _stop_requested:
            return
        time.sleep(1)


def _build_prompt(task: dict) -> str:
    """组装最终发给 AI 的提问：问题文本 + 可选的附加文件内容。

    --file 的内容在执行时（而非添加时）读取，确保拿到最新内容：
        - 只有 --file：文件内容本身即提问
        - --question + --file：问题在前，文件内容作为附加上下文
        - 文件已不可读：附上提示而非让整条任务失败
    """
    question = (task.get("question") or "").strip()
    file_path = task.get("file")
    if not file_path:
        return question

    try:
        content = Path(file_path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        note = f"[无法读取附加文件 {file_path}: {exc}]"
        return f"{question}\n\n{note}" if question else note

    if not question:
        return content
    return f"{question}\n\n--- 附加文件内容（{file_path}）---\n{content}"


def _run_single(task: dict) -> None:
    """执行单条任务：调用 adapter -> 写结果文件 -> 更新状态。"""
    task_id = task["id"]
    question = _build_prompt(task)

    adapter = get_adapter(task["platform"])
    output = adapter.run(question)

    ensure_dirs()
    result_file = RESULTS_DIR / f"{task_id}.txt"
    result_file.write_text(output, encoding="utf-8")

    update_task(task_id, status="done", error=None)


def run_once() -> int:
    """检查一轮任务，执行所有到期的 pending 任务。返回执行的任务数。"""
    tasks = load_tasks()
    now = datetime.now()
    executed = 0

    for task in tasks:
        if task["status"] != "pending":
            continue
        try:
            scheduled_at = datetime.fromisoformat(task["scheduled_at"])
        except (ValueError, KeyError):
            # 时间格式非法，标记失败
            update_task(task["id"], status="failed", error="scheduled_at 格式非法")
            executed += 1
            continue

        if scheduled_at > now:
            continue  # 还没到时间

        try:
            _run_single(task)
            executed += 1
        except Exception as exc:  # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            update_task(task["id"], status="failed", error=err)
            executed += 1
            traceback.print_exc()

    return executed


def run_loop(interval: int = POLL_INTERVAL) -> None:
    """常驻轮询循环，每 interval 秒检查一次。

    收到 SIGTERM / SIGINT 时在当前轮次结束后优雅退出并记录日志。
    """
    global _stop_requested
    _stop_requested = False
    # 仅在主线程注册信号处理器（run_once 直接调用时不受影响）
    try:
        signal.signal(signal.SIGTERM, _request_stop)
        signal.signal(signal.SIGINT, _request_stop)
    except ValueError:
        pass  # 非主线程：跳过信号注册，退化为不可中断循环

    _log(f"daemon 已启动，轮询间隔 {interval}s")
    while not _stop_requested:
        try:
            n = run_once()
            if n:
                _log(f"本轮执行 {n} 个任务")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        _interruptible_sleep(interval)
    _log("daemon 已停止")


if __name__ == "__main__":
    run_loop()
