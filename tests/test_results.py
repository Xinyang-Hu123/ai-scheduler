"""results.py 单元测试：大小格式化与 markdown 检测。"""
from commands.results import _human_size, _looks_like_markdown


class TestHumanSize:
    def test_zero(self):
        assert _human_size(0) == "0B"

    def test_bytes(self):
        assert _human_size(512) == "512B"

    def test_kilobytes(self):
        assert _human_size(1024) == "1.0KB"
        assert _human_size(1536) == "1.5KB"

    def test_megabytes(self):
        assert _human_size(1024 * 1024 * 3) == "3.0MB"

    def test_gigabytes(self):
        assert _human_size(1024**3 * 2) == "2.0GB"


class TestLooksLikeMarkdown:
    def test_heading(self):
        assert _looks_like_markdown("# 标题\n正文")

    def test_bullet_list(self):
        assert _looks_like_markdown("- 第一项\n- 第二项")

    def test_numbered_list(self):
        assert _looks_like_markdown("1. 第一\n2. 第二")

    def test_bold(self):
        assert _looks_like_markdown("答案是 **42**")

    def test_code_fence(self):
        assert _looks_like_markdown("```python\nprint(1)\n```")

    def test_link(self):
        assert _looks_like_markdown("见 [文档](https://example.com)")

    def test_table(self):
        assert _looks_like_markdown("| a | b |\n|---|---|\n| 1 | 2 |")

    def test_plain_text_is_not_markdown(self):
        assert not _looks_like_markdown("这就是一段普通的纯文本，没有任何标记。")

    def test_empty_is_not_markdown(self):
        assert not _looks_like_markdown("")
