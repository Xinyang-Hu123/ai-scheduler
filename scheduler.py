"""调度器：轮询 tasks.json，到点执行任务并把结果落盘。"""
import time
import traceback
from datetime import datetime

from adapters import get_adapter
from config import POLL_INTERVAL, RESULTS_DIR, ensure_dirs
from store import load_tasks, update_task


def _run_single(task: dict) -> None:
    """执行单条任务：调用 adapter -> 写结果文件 -> 更新状态。"""
    task_id = task["id"]
    question = task["question"]

    # 若指定了 --file，把文件内容拼接到问题中
    file_path = task.get("file")
    if file_path:
        # TODO: 更优雅地处理文件上下文（如分片/引用）
        question = f"{question}\n\n[附加上下文文件: {file_path}]"

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
    """常驻轮询循环，每 interval 秒检查一次。"""
    print(f"[ai-scheduler] daemon 已启动，轮询间隔 {interval}s")
    while True:
        try:
            n = run_once()
            if n:
                print(f"[ai-scheduler] 本轮执行 {n} 个任务")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        time.sleep(interval)


if __name__ == "__main__":
    run_loop()
