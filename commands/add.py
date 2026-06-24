"""add 命令：新增定时任务。"""
from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.console import Console

from adapters import AVAILABLE_PLATFORMS
from store import add_task

console = Console()

# 支持的时间格式
_TIME_FORMATS = [
    "%Y-%m-%d %H:%M",   # 2026-06-24 23:30
    "%Y-%m-%d %H:%M:%S",
    "%H:%M",            # 23:30 -> 今天
    "%H:%M:%S",
]


def parse_scheduled_at(at: str) -> str:
    """解析时间字符串，返回 ISO 格式时间。

    支持:
        "23:30"          -> 今天的 23:30
        "2026-06-24 23:30" -> 指定日期
    """
    for fmt in _TIME_FORMATS:
        try:
            dt = datetime.strptime(at, fmt)
            if fmt in ("%H:%M", "%H:%M:%S"):
                # 只给了时间 -> 默认今天；若已过则顺延到明天
                now = datetime.now()
                dt = dt.replace(
                    year=now.year, month=now.month, day=now.day
                )
                if dt <= now:
                    dt += timedelta(days=1)
            return dt.isoformat()
        except ValueError:
            continue
    raise typer.BadParameter(
        f"无法解析时间 '{at}'。支持格式: '23:30' 或 '2026-06-24 23:30'"
    )


def add_command(
    at: str = typer.Option(
        ..., "--at", help="执行时间，如 '23:30' 或 '2026-06-24 23:30'"
    ),
    platform: str = typer.Option(
        "claude", "--platform", "-p", help=f"AI 平台: {AVAILABLE_PLATFORMS}"
    ),
    question: str | None = typer.Option(
        None, "--question", "-q", help="提问内容"
    ),
    file: Path | None = typer.Option(
        None, "--file", "-f", help="从文件读取问题内容"
    ),
) -> None:
    """新增一条定时提问任务。"""
    if platform not in AVAILABLE_PLATFORMS:
        raise typer.BadParameter(
            f"不支持的平台 '{platform}'，可选: {AVAILABLE_PLATFORMS}"
        )

    # --file 仅记录路径，内容在执行时由调度器读取（拿到最新内容）；
    # 可与 --question 组合，也可单独作为提问来源。
    if file is not None and not file.exists():
        raise typer.BadParameter(f"文件不存在: {file}")
    question = (question or "").strip()
    if not question and file is None:
        raise typer.BadParameter("必须提供 --question 或 --file")

    scheduled_at = parse_scheduled_at(at)
    task = add_task(
        scheduled_at=scheduled_at,
        platform=platform,
        question=question,
        file=str(file) if file else None,
    )

    console.print()
    console.print("[bold green]✓ 任务已添加[/bold green]")
    console.print(f"  [cyan]ID[/cyan]       : {task['id']}")
    console.print(f"  [cyan]平台[/cyan]     : {task['platform']}")
    console.print(f"  [cyan]计划时间[/cyan] : {task['scheduled_at']}")
    preview_src = question or (f"[文件: {file.name}]" if file else "")
    preview = preview_src if len(preview_src) <= 60 else preview_src[:57] + "..."
    console.print(f"  [cyan]问题[/cyan]     : {preview}")
    if datetime.fromisoformat(scheduled_at) <= datetime.now():
        console.print(
            "  [yellow]注意[/yellow]     : 计划时间已过，将在下次轮询时立即执行"
        )
    console.print()
    console.print(
        "[dim]提示: 运行 `ai-scheduler daemon start` 启动后台调度。[/dim]"
    )
