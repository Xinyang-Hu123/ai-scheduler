"""Claude CLI 适配器。"""
from adapters.base import BaseAdapter, run_cli


class ClaudeAdapter(BaseAdapter):
    """通过 `claude` 命令行工具提问。"""

    name = "claude"

    def run(self, question: str) -> str:
        """调用 `claude -p`（非交互打印模式），问题经 stdin 传入。"""
        return run_cli(
            "claude",
            [
                "claude",
                "-p",                        # 非交互模式，打印后退出
                "--output-format", "text",   # 纯文本，不带 JSON 包装
            ],
            input=question,  # 用 stdin 传问题，避免与位置参数/flag 冲突
        )
