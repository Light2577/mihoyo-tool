# main.py
import sys
import ctypes

# 1. 依赖检查
try:
    import PySide6
except ImportError:
    ctypes.windll.user32.MessageBoxW(0, "未找到 PySide6 库。\n请运行: pip install pyside6", "启动错误", 0x10)
    sys.exit(1)

from PySide6.QtWidgets import QApplication
from core_engine import WinSystem
from 主窗口 import MainWindow


def main():
    # 2. AppID 设置 (确保任务栏图标分离)
    WinSystem.set_app_id('mihoyo.tool.app.v2.0.refactored')

    # 3. 提权检查 (模拟输入需要管理员权限)
    if not WinSystem.is_user_an_admin():
        # 重新以管理员身份运行自身
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    # 4. 启动 GUI
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()