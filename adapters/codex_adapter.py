"""Codex CLI 适配器。"""
import subprocess

from adapters.base import BaseAdapter, check_binary, strip_ansi
from config import DEFAULT_TIMEOUT


class CodexAdapter(BaseAdapter):
    """通过 `codex` 命令行工具提问。"""

    name = "codex"

    def run(self, question: str) -> str:
        """调用 `codex exec`，返回干净 stdout。超时 300s。"""
        try:
            result = subprocess.run(
                [
                    "codex",
                    "exec",          # 非交互批处理模式
                    question,
                ],
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT,
            )
        except FileNotFoundError as e:
            check_binary("codex", e)

        if result.returncode != 0:
            stderr = strip_ansi(result.stderr.strip())
            raise RuntimeError(f"codex 退出码 {result.returncode}: {stderr}")

        return strip_ansi(result.stdout).strip()
