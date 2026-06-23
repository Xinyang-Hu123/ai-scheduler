"""任务持久化存储：基于 JSON 文件的简单 CRUD。

安全特性：
- 原子写入：先写 .tmp 再 os.replace，避免崩溃导致文件损坏。
- 文件锁：daemon 与 CLI 并发读写时用排它锁串行化，防止丢更新。
- 损坏恢复：检测到非法 JSON 时备份旧文件并返回空列表，而非静默丢数据。
"""
import json
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Optional

from config import DATA_FILE, ensure_dirs

# 锁文件（与数据文件同目录）
_LOCK_FILE = DATA_FILE.with_suffix(".lock")


def _acquire_lock():
    """获取跨进程排它文件锁，返回可关闭的锁对象。"""
    ensure_dirs()
    lock_fh = open(_LOCK_FILE, "a+")

    if sys.platform == "win32":
        try:
            import msvcrt

            msvcrt.locking(lock_fh.fileno(), msvcrt.LK_LOCK, 1)
        except (OSError, ImportError):
            pass  # 锁不可用时降级为无锁（单写者场景仍安全）
    else:
        try:
            import fcntl

            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        except (OSError, ImportError):
            pass

    return lock_fh


class _LockGuard:
    """with 上下文：持锁期间执行临界区，退出时释放。"""

    def __init__(self):
        self._fh = None

    def __enter__(self):
        self._fh = _acquire_lock()
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            if sys.platform != "win32":
                try:
                    import fcntl

                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                except (OSError, ImportError):
                    pass
            self._fh.close()


def _lock():
    """获取锁上下文管理器。"""
    return _LockGuard()


def _read_raw() -> list[dict[str, Any]]:
    """读取并解析 JSON（不加锁）。文件缺失或损坏时返回空列表。"""
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        # 损坏：备份后重置，避免静默吞掉用户数据
        backup = DATA_FILE.with_suffix(
            f".corrupt.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        try:
            os.replace(DATA_FILE, backup)
            print(
                f"[ai-scheduler] 警告: tasks.json 损坏，已备份到 {backup}",
                file=sys.stderr,
            )
        except OSError:
            pass
        return []
    except OSError:
        return []


def _write_raw(tasks: list[dict[str, Any]]) -> None:
    """原子写入：先写 .tmp 再 os.replace。"""
    ensure_dirs()
    tmp = DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA_FILE)


def load_tasks() -> list[dict[str, Any]]:
    """加载全部任务（加锁）。文件不存在或损坏时返回空列表。"""
    with _lock():
        return _read_raw()


def save_tasks(tasks: list[dict[str, Any]]) -> None:
    """保存全部任务到磁盘（加锁 + 原子写入）。"""
    with _lock():
        _write_raw(tasks)


def add_task(
    scheduled_at: str,
    platform: str,
    question: str,
    file: Optional[str] = None,
) -> dict[str, Any]:
    """新增一条任务并保存，返回新建的任务字典。"""
    with _lock():
        tasks = _read_raw()
        now = datetime.now().isoformat()
        task = {
            "id": uuid.uuid4().hex[:8],
            "scheduled_at": scheduled_at,
            "platform": platform,
            "question": question,
            "file": file,
            "status": "pending",
            "error": None,
            "created_at": now,
            "updated_at": now,
        }
        tasks.append(task)
        _write_raw(tasks)
    return task


def update_task(task_id: str, **fields: Any) -> Optional[dict[str, Any]]:
    """按 id 更新指定字段，返回更新后的任务（未找到返回 None）。"""
    with _lock():
        tasks = _read_raw()
        updated: Optional[dict[str, Any]] = None
        for task in tasks:
            if task["id"] == task_id:
                task.update(fields)
                task["updated_at"] = datetime.now().isoformat()
                updated = task
                break
        if updated is not None:
            _write_raw(tasks)
    return updated


def remove_task(task_id: str) -> bool:
    """按 id 删除任务，返回是否删除成功。"""
    with _lock():
        tasks = _read_raw()
        new_tasks = [t for t in tasks if t["id"] != task_id]
        if len(new_tasks) == len(tasks):
            return False
        _write_raw(new_tasks)
    return True


def get_task(task_id: str) -> Optional[dict[str, Any]]:
    """按 id 查询单条任务。"""
    for task in load_tasks():
        if task["id"] == task_id:
            return task
    return None
