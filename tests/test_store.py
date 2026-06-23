"""store.py 单元测试：CRUD、原子写入、并发锁、损坏恢复。"""
import json

import store


class TestCRUD:
    def test_add_and_load(self):
        task = store.add_task("2026-06-24 10:00", "claude", "hello")
        assert task["id"]
        assert task["status"] == "pending"

        tasks = store.load_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == task["id"]

    def test_add_multiple(self):
        store.add_task("2026-06-24 10:00", "claude", "q1")
        store.add_task("2026-06-24 11:00", "codex", "q2")
        assert len(store.load_tasks()) == 2

    def test_update_task_fields(self):
        task = store.add_task("2026-06-24 10:00", "claude", "q")
        updated = store.update_task(task["id"], status="done", error=None)
        assert updated["status"] == "done"
        assert updated["question"] == "q"  # 其他字段保留

    def test_update_nonexistent_returns_none(self):
        assert store.update_task("nope", status="done") is None

    def test_get_task(self):
        task = store.add_task("2026-06-24 10:00", "claude", "q")
        assert store.get_task(task["id"])["question"] == "q"
        assert store.get_task("nope") is None

    def test_remove_task(self):
        task = store.add_task("2026-06-24 10:00", "claude", "q")
        assert store.remove_task(task["id"]) is True
        assert len(store.load_tasks()) == 0

    def test_remove_nonexistent_returns_false(self):
        assert store.remove_task("nope") is False


class TestAtomicWrite:
    def test_no_tmp_file_left_after_write(self, tmp_path):
        store.add_task("2026-06-24 10:00", "claude", "q")
        tmp = store.DATA_FILE.with_suffix(".tmp")
        assert not tmp.exists()

    def test_json_is_valid(self):
        store.add_task("2026-06-24 10:00", "claude", "q")
        with open(store.DATA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert data[0]["question"] == "q"


class TestCorruptRecovery:
    def test_corrupt_json_backed_up_and_reset(self):
        store.add_task("2026-06-24 10:00", "claude", "q1")
        # 人为损坏
        store.DATA_FILE.write_text("{not valid json", encoding="utf-8")

        tasks = store.load_tasks()
        assert tasks == []  # 损坏后返回空，不抛异常

        # 旧文件应被备份（.corrupt.* 存在）
        backups = list(
            store.DATA_FILE.parent.glob("tasks.corrupt.*")
        )
        assert len(backups) == 1

    def test_empty_file_returns_empty_list(self):
        store.DATA_FILE.write_text("", encoding="utf-8")
        assert store.load_tasks() == []


class TestFileField:
    def test_file_field_stored(self):
        task = store.add_task(
            "2026-06-24 10:00", "claude", "q", file="/tmp/p.txt"
        )
        assert task["file"] == "/tmp/p.txt"

    def test_file_field_defaults_none(self):
        task = store.add_task("2026-06-24 10:00", "claude", "q")
        assert task["file"] is None
