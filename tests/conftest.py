"""pytest 配置：将 config 路径重定向到临时目录，隔离测试数据。"""
import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """每个测试用独立的临时数据目录，避免污染真实 ~/.ai-scheduler。"""
    base = tmp_path / "ai-scheduler"
    base.mkdir(parents=True, exist_ok=True)

    results = base / "results"
    results.mkdir(parents=True, exist_ok=True)

    data_file = base / "tasks.json"
    lock_file = base / "tasks.lock"

    import config
    import store
    import scheduler

    # 补丁 config 模块常量
    monkeypatch.setattr(config, "BASE_DIR", base)
    monkeypatch.setattr(config, "DATA_FILE", data_file)
    monkeypatch.setattr(config, "RESULTS_DIR", results)
    monkeypatch.setattr(config, "PID_FILE", base / "scheduler.pid")
    monkeypatch.setattr(config, "LOG_FILE", base / "scheduler.log")

    # store 从 config 导入了符号，持有自己的引用，需同步补丁
    monkeypatch.setattr(store, "DATA_FILE", data_file)
    monkeypatch.setattr(store, "_LOCK_FILE", lock_file)
    monkeypatch.setattr(store, "ensure_dirs", config.ensure_dirs)

    # scheduler 从 config/store 导入的引用也需同步
    monkeypatch.setattr(scheduler, "RESULTS_DIR", results)
    monkeypatch.setattr(scheduler, "ensure_dirs", config.ensure_dirs)

    yield base
