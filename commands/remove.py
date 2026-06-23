"""remove 命令：删除任务。"""
import typer
from rich.console import Console

from config import RESULTS_DIR
from store import remove_task

console = Console()


def remove_command(
    task_id: str = typer.Argument(..., help="要删除的任务 ID"),
) -> None:
    """按 ID 删除一条任务。"""
    # 删除结果文件（若存在）
    result_file = RESULTS_DIR / f"{task_id}.txt"
    result_file.unlink(missing_ok=True)

    if remove_task(task_id):
        console.print(f"[bold green]✓[/bold green] 任务 {task_id} 已删除")
    else:
        console.print(f"[bold red]✗[/bold red] 未找到任务 {task_id}")
        raise typer.Exit(code=1)
