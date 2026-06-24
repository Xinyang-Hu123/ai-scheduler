"""daemon.py 单元测试：_terminate_unix 的优雅退出与 SIGKILL 兜底。"""
import subprocess
import sys
import time

import pytest

from commands import daemon

# 这些用例依赖 POSIX 信号语义，Windows 跳过
pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX 信号专用"
)


def _wait_exit(proc: subprocess.Popen, timeout: float = 5.0) -> bool:
    """等待进程退出，返回是否已退出。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.05)
    return False


def test_terminate_sigterm_path():
    """普通进程收到 SIGTERM 即退出。"""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        daemon._terminate_unix(proc.pid, timeout=5)
        assert _wait_exit(proc)
    finally:
        if proc.poll() is None:
            proc.kill()


def test_terminate_sigkill_fallback():
    """忽略 SIGTERM 的进程应被 SIGKILL 兜底结束。"""
    code = (
        "import signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "time.sleep(60)"
    )
    proc = subprocess.Popen([sys.executable, "-c", code])
    try:
        daemon._terminate_unix(proc.pid, timeout=1)
        assert _wait_exit(proc)  # SIGTERM 被忽略，靠 SIGKILL 结束
    finally:
        if proc.poll() is None:
            proc.kill()


def test_terminate_already_dead_is_noop():
    """目标进程已退出时不抛异常。"""
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    daemon._terminate_unix(proc.pid, timeout=1)  # 不应抛出
