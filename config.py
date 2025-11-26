import logging
import os
from pathlib import Path

APP_ID = "mihoyo.tool.app.v2.0"

# 默认配置
DEFAULT_BASE_DELAY_MS = 10
DEFAULT_RANDOM_DELAY_MS = 5
DEFAULT_START_HOTKEY = ("F9", 0x78)
DEFAULT_STOP_HOTKEY = ("F10", 0x79)

LOG_DIR = Path(os.getenv("LOCALAPPDATA", ".")) / "miHoYoTool"
LOG_FILE = LOG_DIR / "app.log"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(log_file: Path | None = None):
    """初始化日志，输出到文件和控制台。"""
    target_file = log_file or LOG_FILE
    target_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(target_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("PySide6").setLevel(logging.WARNING)
    return target_file
