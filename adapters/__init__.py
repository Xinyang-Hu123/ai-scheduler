"""Adapters 包：提供平台 -> 适配器的工厂函数。"""
from adapters.base import BaseAdapter
from adapters.claude_adapter import ClaudeAdapter
from adapters.codex_adapter import CodexAdapter

# 平台名 -> 适配器类
_REGISTRY: dict[str, type[BaseAdapter]] = {
    "claude": ClaudeAdapter,
    "codex": CodexAdapter,
}

# 可选平台列表
AVAILABLE_PLATFORMS = list(_REGISTRY.keys())


def get_adapter(platform: str) -> BaseAdapter:
    """根据平台名返回对应的适配器实例。

    Raises:
        ValueError: 不支持的平台。
    """
    cls = _REGISTRY.get(platform)
    if cls is None:
        raise ValueError(
            f"不支持的平台 '{platform}'，可选: {', '.join(AVAILABLE_PLATFORMS)}"
        )
    return cls()
