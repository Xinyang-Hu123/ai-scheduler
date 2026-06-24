"""Adapter 抽象基类与共享的子进程调用逻辑。"""
import re
import subprocess
from abc import ABC, abstractmethod
from typing import NoReturn

from config import DEFAULT_TIMEOUT

# ANSI 转义码正则
_ANSI_ESCAPE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def strip_ansi(text: str) -> str:
    """去除 ANSI 转义码，返回干净文本。"""
    return _ANSI_ESCAPE.sub('', text)


class BinaryNotFoundError(RuntimeError):
    """AI 命令行工具未安装或不在 PATH 中。"""


def check_binary(name: str, err: "FileNotFoundError") -> NoReturn:
    """把 subprocess 的 FileNotFoundError 转换为清晰错误（必定抛出）。"""
    raise BinaryNotFoundError(
        f"未找到 '{name}' 命令行工具，请先安装并确保它在 PATH 中。"
    ) from err


def run_cli(
    name: str,
    cmd: list[str],
    *,
    input: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """运行一个 CLI 子进程，返回去除 ANSI 后的 stdout。

    统一处理所有 adapter 共同的失败场景：

    Args:
        name: 工具名（用于报错信息，如 "claude"）。
        cmd: 完整命令行（列表形式，不经过 shell，无注入风险）。
        input: 经 stdin 传入的内容；为 None 时把 stdin 接到 DEVNULL，
            避免子进程在无人值守时阻塞等待输入。
        timeout: 超时秒数。

    Returns:
        工具的标准输出（已去 ANSI、去首尾空白）。

    Raises:
        BinaryNotFoundError: 工具未安装。
        RuntimeError: 执行超时，或退出码非零。
    """
    kwargs: dict = {"capture_output": True, "text": True, "timeout": timeout}
    if input is not None:
        kwargs["input"] = input
    else:
        kwargs["stdin"] = subprocess.DEVNULL

    try:
        result = subprocess.run(cmd, **kwargs)
    except FileNotFoundError as e:
        check_binary(name, e)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"{name} 执行超时（{timeout}s）") from e

    if result.returncode != 0:
        stderr = strip_ansi((result.stderr or "").strip())
        raise RuntimeError(f"{name} 退出码 {result.returncode}: {stderr}")

    return strip_ansi(result.stdout or "").strip()


class BaseAdapter(ABC):
    """所有 AI 命令行工具适配器的基类。"""

    name: str = "base"

    @abstractmethod
    def run(self, question: str) -> str:
        """执行提问，返回工具的 stdout 文本。

        Args:
            question: 向 AI 工具提出的完整问题。

        Returns:
            工具的标准输出内容。

        Raises:
            RuntimeError: 工具执行失败或超时。
        """
        ...
