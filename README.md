# ai-scheduler

定时自动调用 `claude` / `codex` 命令行工具提问的 CLI 工具。

到点自动拉起 AI CLI、把回答落盘、终端用 rich 美化输出。一个用来**定时召唤 AI 的闹钟**——调度逻辑是纯代码，AI 只是被调度的对象。

## 功能

- `add` — 新增定时提问任务（支持 `--at` 时间 / `--platform` 平台 / `--question` 或 `--file` 问题来源）
- `list` — 列出全部任务（rich 表格，支持 `--status` 过滤）
- `remove` — 按 ID 删除任务
- `daemon` — 后台启动 / 停止 / 查看调度器状态
- `results` — 查看已完成任务结果（无参列摘要，带 ID 用 rich Markdown 渲染）

## 安装

```bash
pip install .
```

安装后即可使用 `ai-scheduler` 命令。也可直接 `python main.py` 运行。

依赖：`typer`、`rich`（见 `requirements.txt`）。

## 快速上手

```bash
# 新增任务：今天 23:30 用 claude 提问
ai-scheduler add --at "23:30" -p claude -q "总结今天的科技新闻"

# 指定日期 + 从文件读取问题
ai-scheduler add --at "2026-06-24 09:00" -p codex -f prompt.txt

# 启动后台调度器（到点自动执行）
ai-scheduler daemon start

# 查看任务列表
ai-scheduler list

# 查看某个任务的结果（rich markdown 渲染）
ai-scheduler results <task_id>

# 停止调度器
ai-scheduler daemon stop
```

## 数据存放

| 路径 | 说明 |
|------|------|
| `~/.ai-scheduler/tasks.json` | 任务数据（原子写入 + 文件锁，防并发损坏） |
| `~/.ai-scheduler/results/<id>.txt` | 每个已完成任务的 AI 回答 |
| `~/.ai-scheduler/scheduler.pid` | daemon 进程 PID |
| `~/.ai-scheduler/scheduler.log` | daemon 运行日志 |

## 时间格式

`--at` 支持两种格式：

- `"23:30"` — 今天的 23:30；若已过则自动顺延到明天
- `"2026-06-24 23:30"` — 指定日期时间

## 工作原理

```
add → tasks.json (pending)
              ↓
        daemon 每 30s 轮询
              ↓
     scheduled_at <= now ?
              ↓
   adapter.run(question)  ← claude / codex CLI
              ↓
   results/<id>.txt 落盘
              ↓
   status → done / failed
```

调度器每 30 秒检查一次 `tasks.json`，找 `status=="pending"` 且到期的任务，调对应 adapter 执行，结果写到 `results/<id>.txt`，状态更新为 `done`（成功）或 `failed`（失败，记录 error）。

## 前置要求

需提前安装并登录对应的 AI 命令行工具：

- [claude](https://claude.ai) CLI
- [codex](https://github.com/openai/codex) CLI

未安装时会提示：`未找到 'claude' 命令行工具，请先安装并确保它在 PATH 中。`

## 开发

```bash
pip install -e ".[dev]"
pytest              # 运行测试
ruff check .        # 代码检查
```

## License

MIT
