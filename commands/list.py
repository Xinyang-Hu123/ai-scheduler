"""list 命令：列出所有任务。"""
import typer
from rich.console import Console
from rich.table import Table

from store import load_tasks

console = Console()

# 状态 -> 颜色
_STATUS_STYLE = {
    "pending": "yellow",
    "done": "green",
    "failed": "red",
}


def list_command(
    status: str = typer.Option(
        None, "--status", "-s", help="按状态过滤: pending/done/failed"
    ),
) -> None:
    """列出全部任务（可用 --status 过滤）。"""
    tasks = load_tasks()

    if status:
        tasks = [t for t in tasks if t["status"] == status]

    if not tasks:
        console.print("[dim]暂无任务[/dim]")
        return

    table = Table(title="ai-scheduler 任务列表", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("平台", style="magenta")
    table.add_column("计划时间", style="blue")
    table.add_column("状态")
    table.add_column("问题预览", overflow="fold")

    for t in tasks:
        style = _STATUS_STYLE.get(t["status"], "white")
        question = t.get("question", "")
        preview = question if len(question) <= 40 else question[:37] + "..."
        table.add_row(
            t["id"],
            t["platform"],
            t["scheduled_at"],
            f"[{style}]{t['status']}[/{style}]",
            preview,
        )

    console.print(table)
    console.print(f"\n[dim]共 {len(tasks)} 条任务[/dim]")
