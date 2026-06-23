"""daemon 命令：后台启动 / 停止调度器。"""
import os
import signal
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

from config import LOG_FILE, PID_FILE, ensure_dirs

console = Console()

app = typer.Typer(help="调度器 daemon 管理", no_args_is_help=True)

# scheduler.py 的绝对路径
_SCHEDULER_SCRIPT = str(Path(__file__).resolve().parent.parent / "scheduler.py")


def _read_pid() -> int | None:
    """读取 pid 文件，返回 pid（无效则 None）。"""
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def _write_pid(pid: int) -> None:
    ensure_dirs()
    PID_FILE.write_text(str(pid))


def _clear_pid() -> None:
    PID_FILE.unlink(missing_ok=True)


def _is_running(pid: int) -> bool:
    """判断 pid 对应进程存活，且是我们的 scheduler（防 PID 复用误判）。"""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    # 进一步核对命令行，避免 PID 被复用给无关进程
    return _is_our_scheduler(pid)


def _is_our_scheduler(pid: int) -> bool:
    """检查 pid 进程的命令行是否包含 scheduler.py。"""
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                [
                    "wmic", "process", "where", f"processid={pid}",
                    "get", "commandline",
                ],
                capture_output=True, text=True, timeout=5,
            )
            return "scheduler.py" in out.stdout
        else:
            out = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True, text=True, timeout=5,
            )
            return "scheduler.py" in out.stdout
    except (subprocess.SubprocessError, OSError):
        # ps 不可用时仅凭 pid 存活判断（降级）
        return True


@app.command()
def start() -> None:
    """后台启动 scheduler daemon。"""
    pid = _read_pid()
    if pid is not None and _is_running(pid):
        console.print(
            f"[yellow]daemon 已在运行 (pid={pid})[/yellow]"
        )
        return

    ensure_dirs()

    if sys.platform == "win32":
        # Windows: 用 DETACHED_PROCESS 后台启动
        # TODO: 验证 Windows 下的日志重定向
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        proc = subprocess.Popen(
            [sys.executable, _SCHEDULER_SCRIPT],
            stdout=open(LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
        )
    else:
        # Mac/Linux: 用 nohup 后台启动
        proc = subprocess.Popen(
            [sys.executable, _SCHEDULER_SCRIPT],
            stdout=open(LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    _write_pid(proc.pid)
    console.print(
        f"[bold green]✓[/bold green] daemon 已启动 (pid={proc.pid})\n"
        f"  日志: {LOG_FILE}"
    )


@app.command()
def stop() -> None:
    """停止 scheduler daemon。"""
    pid = _read_pid()
    if pid is None:
        console.print("[yellow]daemon 未在运行（无 pid 文件）[/yellow]")
        return

    if not _is_running(pid):
        console.print("[yellow]daemon 进程已不存在，清理 pid 文件[/yellow]")
        _clear_pid()
        return

    try:
        if sys.platform == "win32":
            # Windows: taskkill 强制终止进程树
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                capture_output=True,
            )
        else:
            # 先 SIGTERM，优雅退出
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    _clear_pid()
    console.print(f"[bold green]✓[/bold green] daemon 已停止 (pid={pid})")


@app.command()
def status() -> None:
    """查看 daemon 运行状态。"""
    pid = _read_pid()
    if pid is not None and _is_running(pid):
        console.print(f"[green]● daemon 运行中 (pid={pid})[/green]")
    else:
        console.print("[red]○ daemon 未运行[/red]")
