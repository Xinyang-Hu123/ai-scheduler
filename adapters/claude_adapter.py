"""Claude CLI 适配器。"""
import subprocess

from adapters.base import BaseAdapter, check_binary, strip_ansi
from config import DEFAULT_TIMEOUT


class ClaudeAdapter(BaseAdapter):
    """通过 `claude` 命令行工具提问。"""

    name = "claude"

    def run(self, question: str) -> str:
        """调用 `claude -p`，返回干净 stdout。超时 300s。"""
        # 用 stdin 传问题，避免位置参数与 flag 冲突
        try:
            result = subprocess.run(
                [
                    "claude",
                    "-p",                        # 非交互模式，用完退出
                    "--output-format", "text",   # 纯文本，不带 JSON 包装
                ],
                input=question,
                capture_output=True,
                text=True,
                timeout=DEFAULT_TIMEOUT,
            )
        except FileNotFoundError as e:
            check_binary("claude", e)

        if result.returncode != 0:
            stderr = strip_ansi(result.stderr.strip())
            raise RuntimeError(f"claude 退出码 {result.returncode}: {stderr}")

        return strip_ansi(result.stdout).strip()
