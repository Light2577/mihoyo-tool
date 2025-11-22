import sys
import ctypes

try:
    import PySide6
except ImportError:
    ctypes.windll.user32.MessageBoxW(0, "缺失依赖：PySide6", "启动错误", 0x10)
    sys.exit(1)

from PySide6.QtWidgets import QApplication
from core_engine import WinSystem
from 主窗口 import MainWindow


def main():
    # 确保任务栏图标独立显示
    WinSystem.set_app_id('mihoyo.tool.app.v2.0')

    if not WinSystem.is_user_an_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()