"""Codex CLI 适配器。"""
from adapters.base import BaseAdapter, run_cli


class CodexAdapter(BaseAdapter):
    """通过 `codex` 命令行工具提问。

    无人值守场景的关键 flag：
        --ask-for-approval never  不暂停等待人工批准（否则 daemon 会一直挂到超时）
        --skip-git-repo-check     不强制要求运行在 git 仓库内

    沙箱保持默认的只读模式：本工具只是「提问取答案」，不需要改文件，
    只读最安全。如需让 codex 真正动手改代码，再加 --sandbox workspace-write。
    """

    name = "codex"

    def run(self, question: str) -> str:
        """调用 `codex exec`（非交互批处理模式），返回最终回答。"""
        return run_cli(
            "codex",
            [
                "codex",
                "exec",
                "--ask-for-approval", "never",
                "--skip-git-repo-check",
                question,
            ],
        )
