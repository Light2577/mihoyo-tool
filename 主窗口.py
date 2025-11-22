from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QProgressBar, QPushButton, QGridLayout, QApplication, QMessageBox)
from PySide6.QtCore import Qt, QPoint, QSettings, Signal
from PySide6.QtGui import QKeySequence, QIcon
import sys
import os
from ctypes import wintypes

from core_engine import WinSystem, PasteWorker

# CSS 样式
STYLESHEET = """
    QWidget#MainWidget { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 15px; }
    QLabel { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; color: #555; font-size: 13px; }
    QLabel#TitleLabel { font-size: 16px; font-weight: bold; color: #333; }
    QPushButton#WinCtrlBtn { background: transparent; color: #999; border: none; font-size: 14px; border-radius: 15px; font-weight: bold; }
    QPushButton#WinCtrlBtn:hover { background-color: #F0F0F0; color: #333; }
    QPushButton#CloseBtn { background: transparent; color: #999; border: none; font-size: 18px; border-radius: 15px; }
    QPushButton#CloseBtn:hover { background-color: #FF6B6B; color: white; }
    QLabel#StatusLabel { font-size: 24px; font-weight: bold; color: #333; }
    QLabel#ResultLabel { color: #AAA; font-size: 12px; }
    QLineEdit { border: 1px solid #EEE; border-radius: 8px; padding: 6px 10px; background: #F9F9F9; color: #555; selection-background-color: #87CEEB; }
    QLineEdit:focus { border: 1px solid #87CEEB; background: #FFF; }
    QPushButton#HotkeyBtn { border: 1px solid #EEE; border-radius: 8px; background: #F9F9F9; color: #333; padding: 6px; }
    QPushButton#HotkeyBtn:hover { border-color: #87CEEB; background: #F0F8FF; }
    QProgressBar { background: #F0F0F0; border: none; border-radius: 3px; height: 6px; }
    QProgressBar::chunk { background: #87CEEB; border-radius: 3px; }
    QPushButton#StartBtn { background: #87CEEB; color: white; border: none; border-radius: 22px; font-weight: bold; font-size: 14px; }
    QPushButton#StartBtn:hover { background: #76BEDB; }
    QPushButton#StartBtn:pressed { background: #5CA8C9; }
    QPushButton#StartBtn:disabled { background: #E0E0E0; color: #AAA; }
    QPushButton#StopBtn { background: white; color: #FF6B6B; border: 1px solid #FF6B6B; border-radius: 22px; font-weight: bold; font-size: 14px; }
    QPushButton#StopBtn:hover { background: #FFF0F0; }
    QPushButton#StopBtn:pressed { background: #FFE0E0; }
    QPushButton#StopBtn:disabled { border-color: #E0E0E0; color: #E0E0E0; background: transparent; }
"""


class HotkeyButton(QPushButton):
    hotkeyChanged = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.current_vk = 0
        self.setObjectName("HotkeyBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recording = False
        self.setText("无")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.recording = True
            self.setText("请按键...")
            self.grabKeyboard()
            self.setStyleSheet("border: 2px solid #87CEEB; color: #87CEEB; background-color: #F0F8FF;")
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if not self.recording:
            return super().keyPressEvent(e)

        key = e.key()
        native_vk = e.nativeVirtualKey()

        if key == Qt.Key.Key_Escape:
            self._finish_record(0, "无")
            return

        # 过滤纯修饰键
        if key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
            return

        # Qt 在某些环境下获取 F1-F12 的 nativeVirtualKey 会返回 0
        # 这里手动映射到 Windows VK 码 (F1=0x70)
        if native_vk == 0:
            if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
                native_vk = 0x70 + (key - Qt.Key.Key_F1)
            else:
                self.setText("无效键")
                return

        key_seq = QKeySequence(key)
        self._finish_record(native_vk, key_seq.toString())

    def _finish_record(self, vk, text):
        self.recording = False
        self.releaseKeyboard()
        self.current_vk = vk
        self.setText(text)
        self.setStyleSheet("")
        self.hotkeyChanged.emit(vk, text)


class MainWindow(QMainWindow):
    HK_START = 101
    HK_STOP = 102

    def __init__(self):
        super().__init__()
        self._init_window()
        self._setup_ui()
        self._load_config()

        self.worker = None
        self.is_dragging = False
        self.drag_position = QPoint()

    def _init_window(self):
        self.setWindowTitle("miHoYo Tool Pro")
        self.resize(400, 550)
        # 无边框 + 系统动画支持
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

    def _setup_ui(self):
        self.main_widget = QWidget()
        self.main_widget.setObjectName("MainWidget")
        self.setCentralWidget(self.main_widget)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(25, 20, 25, 30)
        layout.setSpacing(15)

        self._create_title_bar(layout)

        self.status_label = QLabel("Waiting...")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.result_label = QLabel("Ready to start")
        self.result_label.setObjectName("ResultLabel")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.result_label)
        layout.addSpacing(20)

        self._create_settings_area(layout)
        layout.addStretch()

        self.start_btn = QPushButton("开始运行")
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setFixedHeight(45)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_task)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.setFixedHeight(45)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_task)
        layout.addWidget(self.stop_btn)

    def _create_title_bar(self, parent_layout):
        title_layout = QHBoxLayout()
        title_layout.addSpacing(70)
        title_layout.addStretch()

        title = QLabel("miHoYo Tool")
        title.setObjectName("TitleLabel")
        title_layout.addWidget(title)

        title_layout.addStretch()

        btn_container = QWidget()
        btn_container.setFixedWidth(70)
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)

        min_btn = QPushButton("一")
        min_btn.setObjectName("WinCtrlBtn")
        min_btn.setFixedSize(30, 30)
        min_btn.clicked.connect(lambda: WinSystem.minimize_window_anim(int(self.winId())))

        close_btn = QPushButton("×")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(min_btn)
        btn_layout.addWidget(close_btn)
        title_layout.addWidget(btn_container)

        parent_layout.addLayout(title_layout)

    def _create_settings_area(self, parent_layout):
        container = QWidget()
        grid = QGridLayout(container)
        grid.setVerticalSpacing(15)
        grid.setHorizontalSpacing(15)

        grid.addWidget(QLabel("基础延迟 (ms)"), 0, 0)
        self.base_input = QLineEdit()
        self.base_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.base_input, 0, 1)

        grid.addWidget(QLabel("随机浮动 (ms)"), 1, 0)
        self.float_input = QLineEdit()
        self.float_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(self.float_input, 1, 1)

        grid.addWidget(QLabel("开始热键"), 2, 0)
        self.hk_start_btn = HotkeyButton()
        self.hk_start_btn.hotkeyChanged.connect(lambda vk, txt: self._update_hotkey(vk, txt, self.HK_START))
        grid.addWidget(self.hk_start_btn, 2, 1)

        grid.addWidget(QLabel("停止热键"), 3, 0)
        self.hk_stop_btn = HotkeyButton()
        self.hk_stop_btn.hotkeyChanged.connect(lambda vk, txt: self._update_hotkey(vk, txt, self.HK_STOP))
        grid.addWidget(self.hk_stop_btn, 3, 1)

        parent_layout.addWidget(container)

    def _load_config(self):
        self.settings = QSettings("MihoyoTool", "Config")

        self.base_input.setText(str(self.settings.value("base", "10")))
        self.float_input.setText(str(self.settings.value("float", "5")))

        self._restore_hotkey(self.HK_START, "start_vk", "start_txt", self.hk_start_btn, 0x78, "F9")
        self._restore_hotkey(self.HK_STOP, "stop_vk", "stop_txt", self.hk_stop_btn, 0x79, "F10")

    def _restore_hotkey(self, hk_id, key_vk, key_txt, btn, default_vk, default_txt):
        vk = int(self.settings.value(key_vk, default_vk))
        txt = str(self.settings.value(key_txt, default_txt))
        btn.setText(txt)
        btn.current_vk = vk
        WinSystem.register_hotkey(int(self.winId()), hk_id, vk)

    def _update_hotkey(self, vk, text, hk_id):
        WinSystem.unregister_hotkey(int(self.winId()), hk_id)

        if vk > 0:
            if not WinSystem.register_hotkey(int(self.winId()), hk_id, vk):
                QMessageBox.warning(self, "热键冲突", f"按键 '{text}' 已被占用")

                # 回滚
                sender_btn = self.hk_start_btn if hk_id == self.HK_START else self.hk_stop_btn
                sender_btn.setText("无")
                sender_btn.current_vk = 0
                return

        prefix = "start" if hk_id == self.HK_START else "stop"
        self.settings.setValue(f"{prefix}_vk", vk)
        self.settings.setValue(f"{prefix}_txt", text)

        if hk_id == self.HK_START and not self.start_btn.isEnabled():
            self.start_btn.setText(f"运行中 ({text})")

    def start_task(self):
        if self.worker and self.worker.isRunning(): return

        text = QApplication.clipboard().text()
        if not text:
            self.result_label.setText("剪贴板为空")
            return

        text = text.replace('\r\n', '\n')

        try:
            base = int(self.base_input.text())
            float_val = int(self.float_input.text())
        except ValueError:
            self.result_label.setText("参数错误")
            return

        self.start_btn.setEnabled(False)
        self.start_btn.setText(f"运行中 ({self.hk_start_btn.text()})")
        self.stop_btn.setEnabled(True)
        self.result_label.setText("任务进行中...")

        self.worker = PasteWorker(text, base, float_val)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.status_signal.connect(self.status_label.setText)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.status_label.setText("Stopping...")

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setText("开始运行")
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        if self.status_label.text() != "已中断":
            self.status_label.setText("Success")
            self.result_label.setText("完成")
        else:
            self.result_label.setText("用户已停止")

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG" or event_type == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == self.HK_START:
                    self.start_task()
                elif msg.wParam == self.HK_STOP:
                    self.stop_task()
        return super().nativeEvent(event_type, message)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def closeEvent(self, event):
        self.settings.setValue("base", self.base_input.text())
        self.settings.setValue("float", self.float_input.text())
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_START)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_STOP)
        event.accept()