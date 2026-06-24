"""results 命令：查看已完成任务的结果。"""
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from config import RESULTS_DIR
from store import get_task, load_tasks

console = Console()

# markdown 结构特征：命中任一即认为内容是 markdown
_MD_PATTERNS = [
    r"^#{1,6}\s",        # 标题 # ##
    r"^\s*[-*+]\s",      # 无序列表
    r"^\s*\d+\.\s",      # 有序列表
    r"^>\s",             # 引用
    r"^\|.+\|",          # 表格
    r"```",              # 代码块
    r"\*\*.+?\*\*",      # 加粗
    r"\[.+?\]\(.+?\)",   # 链接
]


def _human_size(num: int) -> str:
    """把字节数格式化为人类可读大小（B/KB/MB/GB）。"""
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"  # 理论不可达，兜底


def _looks_like_markdown(text: str) -> bool:
    """启发式判断文本是否为 markdown，否则按纯文本输出避免误渲染。"""
    return any(re.search(pat, text, re.MULTILINE) for pat in _MD_PATTERNS)


def _list_done_tasks() -> list[dict]:
    """返回所有已完成的任务（按完成时间倒序，最近完成的在前）。"""
    done = [t for t in load_tasks() if t["status"] == "done"]
    done.sort(key=lambda t: t.get("updated_at", ""), reverse=True)
    return done


def results_command(
    task_id: str = typer.Argument(
        None, help="任务 ID；不传则列出所有已完成任务摘要"
    ),
    raw: bool = typer.Option(
        False, "--raw", help="以纯文本输出（不做 markdown 渲染）"
    ),
) -> None:
    """查看任务结果。无参数列出摘要，带 task_id 输出结果内容。"""
    if task_id is None:
        # 列出所有已完成任务摘要
        done = _list_done_tasks()
        if not done:
            console.print("[dim]暂无已完成的任务[/dim]")
            return

        table = Table(title="已完成任务", show_lines=True)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("平台", style="magenta")
        table.add_column("完成时间", style="blue")
        table.add_column("结果大小", style="green")

        for t in done:
            result_file = RESULTS_DIR / f"{t['id']}.txt"
            size = (
                _human_size(result_file.stat().st_size)
                if result_file.exists()
                else "-"
            )
            table.add_row(
                t["id"],
                t["platform"],
                t.get("updated_at", "-"),
                size,
            )

        console.print(table)
        console.print(
            "\n[dim]提示: 运行 `ai-scheduler results <ID>` 查看完整结果[/dim]"
        )
        return

    # 查看指定任务结果
    task = get_task(task_id)
    if task is None:
        console.print(f"[bold red]✗[/bold red] 未找到任务 {task_id}")
        raise typer.Exit(code=1)

    if task["status"] != "done":
        console.print(
            f"[yellow]任务 {task_id} 状态为 {task['status']}，尚无结果[/yellow]"
        )
        if task.get("error"):
            console.print(f"[red]错误信息: {task['error']}[/red]")
        raise typer.Exit(code=1)

    result_file: Path = RESULTS_DIR / f"{task_id}.txt"
    if not result_file.exists():
        console.print(f"[bold red]✗[/bold red] 结果文件不存在: {result_file}")
        raise typer.Exit(code=1)

    content = result_file.read_text(encoding="utf-8")

    # 顶部信息面板
    info = (
        f"[cyan]ID[/cyan]    : {task['id']}\n"
        f"[cyan]平台[/cyan]  : {task['platform']}\n"
        f"[cyan]时间[/cyan]  : {task['updated_at']}\n"
        f"[cyan]问题[/cyan]  : {task['question'][:80]}"
    )
    console.print(Panel(info, title=f"任务 {task_id}", border_style="blue"))

    # 渲染结果内容：--raw 强制纯文本；否则按内容是否像 markdown 决定渲染方式
    if raw or not _looks_like_markdown(content):
        console.print(content)
    else:
        console.print(Markdown(content))
