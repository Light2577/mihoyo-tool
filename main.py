import sys
import ctypes
import logging
import argparse
from pathlib import Path

try:
    import PySide6
except ImportError:
    ctypes.windll.user32.MessageBoxW(0, "缺失依赖：PySide6", "启动错误", 0x10)
    sys.exit(1)

from PySide6.QtWidgets import QApplication
from core_engine import WinSystem
from config import APP_ID, setup_logging
from main_window import MainWindow


logger = logging.getLogger(__name__)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="miHoYo Tool")
    parser.add_argument("--base-ms", type=int, help="默认基础延迟 (毫秒)")
    parser.add_argument("--random-ms", type=int, help="默认随机浮动延迟 (毫秒)")
    parser.add_argument("--log-file", type=str, help="自定义日志文件路径")
    return parser.parse_args(argv)


def main():
    args = parse_args(sys.argv[1:])
    log_file = setup_logging(Path(args.log_file) if args.log_file else None)
    logger.info("Launching miHoYo Tool (log at %s)", log_file)

    # 确保任务栏图标独立显示
    WinSystem.set_app_id(APP_ID)

    if not WinSystem.is_user_an_admin():
        logger.warning("Elevating to administrator for hotkey and input APIs")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    app = QApplication(sys.argv)
    window = MainWindow(base_override=args.base_ms, random_override=args.random_ms)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
