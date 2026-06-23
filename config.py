"""全局配置：路径定义与目录初始化。"""
from pathlib import Path

# 数据根目录 ~/.ai-scheduler
BASE_DIR = Path.home() / ".ai-scheduler"

# 任务数据文件
DATA_FILE = BASE_DIR / "tasks.json"

# 结果输出目录
RESULTS_DIR = BASE_DIR / "results"

# daemon 进程 pid 文件
PID_FILE = BASE_DIR / "scheduler.pid"

# daemon 日志文件
LOG_FILE = BASE_DIR / "scheduler.log"

# adapter 执行超时（秒）
DEFAULT_TIMEOUT = 300

# scheduler 轮询间隔（秒）
POLL_INTERVAL = 30


def ensure_dirs() -> None:
    """确保所有需要的目录存在。"""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
