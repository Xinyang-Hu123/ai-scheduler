"""ai-scheduler CLI 入口。"""
import sys

import typer
from rich.console import Console

from commands.add import add_command
from commands.daemon import app as daemon_app
from commands.list import list_command
from commands.remove import remove_command
from commands.results import results_command
from config import ensure_dirs

console = Console()

app = typer.Typer(
    name="ai-scheduler",
    help="定时自动调用 claude / codex 命令行工具提问",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# 子命令注册
app.command(name="add")(add_command)
app.command(name="list")(list_command)
app.command(name="ls")(list_command)
app.command(name="remove")(remove_command)
app.command(name="rm")(remove_command)
app.command(name="results")(results_command)
app.add_typer(daemon_app, name="daemon")


@app.command()
def run(
    interval: int = typer.Option(
        30, "--interval", "-i", help="轮询间隔（秒）"
    ),
) -> None:
    """前台运行调度器（调试用）。"""
    from scheduler import run_loop

    run_loop(interval=interval)


@app.callback()
def main() -> None:
    """启动前确保目录就绪。"""
    ensure_dirs()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--internal-scheduler":
        # PyInstaller 打包后 daemon 启动的内部入口
        from scheduler import run_loop

        ensure_dirs()
        run_loop()
    else:
        app()
