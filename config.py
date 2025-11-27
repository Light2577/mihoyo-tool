import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

APP_ID = "mihoyo.tool.app.v2.0"

# 默认配置
DEFAULT_BASE_DELAY_MS = 10
DEFAULT_RANDOM_DELAY_MS = 5
DEFAULT_COUNTDOWN_SEC = 3
# (显示文本, VK 键码, 修饰键组合)
DEFAULT_START_HOTKEY = ("F9", 0x78, 0)
DEFAULT_CONTINUE_HOTKEY = ("F11", 0x7A, 0)

LOG_DIR = Path(os.getenv("LOCALAPPDATA", ".")) / "miHoYoTool"
LOG_FILE = LOG_DIR / "app.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
# 日志轮转配置：1 MB * 3 份
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3


def setup_logging(log_file: Path | None = None):
    """初始化日志，输出到文件和控制台。"""
    target_file = log_file or LOG_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        target_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    stream_handler = logging.StreamHandler()

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[file_handler, stream_handler],
    )
    logging.getLogger("PySide6").setLevel(logging.WARNING)
    return target_file
