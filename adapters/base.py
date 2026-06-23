"""Adapter 抽象基类。"""
import re
from abc import ABC, abstractmethod

# ANSI 转义码正则
_ANSI_ESCAPE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def strip_ansi(text: str) -> str:
    """去除 ANSI 转义码，返回干净文本。"""
    return _ANSI_ESCAPE.sub('', text)


class BinaryNotFoundError(RuntimeError):
    """AI 命令行工具未安装或不在 PATH 中。"""


def check_binary(name: str, err: "FileNotFoundError") -> None:
    """若 subprocess 抛出 FileNotFoundError，转换为清晰错误。"""
    raise BinaryNotFoundError(
        f"未找到 '{name}' 命令行工具，请先安装并确保它在 PATH 中。"
    ) from err


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
