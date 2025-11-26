# main_window.py
import sys
import os
import logging
from ctypes import wintypes

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QProgressBar, QPushButton, QApplication, QMessageBox,
                               QDialog, QDialogButtonBox, QFormLayout, QGraphicsDropShadowEffect, QFrame)
from PySide6.QtCore import Qt, QPoint, QSettings, Signal, QTimer, QSize
from PySide6.QtGui import QKeySequence, QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath, QTransform

# 引入你的本地模块
from config import (
    DEFAULT_BASE_DELAY_MS, DEFAULT_RANDOM_DELAY_MS,
    DEFAULT_START_HOTKEY, DEFAULT_STOP_HOTKEY,
)
from styles import THEMES
from ui_texts import LANGS, get_text
from core_engine import WinSystem, PasteWorker
from components import ToggleSwitch  # <--- 必须导入这个新组件

logger = logging.getLogger(__name__)


class HotkeyButton(QPushButton):
    """ 热键录制按钮，样式由 QSS 控制，这里主要处理逻辑 """
    hotkeyChanged = Signal(int, str)

    def __init__(self):
        super().__init__()
        self.current_vk = 0
        self.setObjectName("HotkeyBtn")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recording = False
        defaults = LANGS["zh"]["buttons"]
        self.none_text = defaults["none"]
        self.recording_text = defaults["recording"]
        self.invalid_key_text = defaults["invalid_key"]
        self.setText(self.none_text)
        self.setFixedHeight(34)  # 固定高度

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.recording = True
            self.setText(self.recording_text)
            self.grabKeyboard()
            # 录制时高亮，直接在这里覆盖样式以获得即时反馈
            self.setStyleSheet("""
                background-color: #EFF6FF; 
                color: #3B82F6; 
                border-radius: 8px;
                border: 1px solid #BFDBFE;
                font-weight: bold;
            """)
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if not self.recording:
            return super().keyPressEvent(e)

        key = e.key()
        native_vk = e.nativeVirtualKey()

        if key == Qt.Key.Key_Escape:
            self._finish_record(0, self.none_text)
            return

        if key in [Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta]:
            return

        # 处理 F1-F24 的特殊情况
        if native_vk == 0:
            if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
                native_vk = 0x70 + (key - Qt.Key.Key_F1)
            else:
                self.setText(self.invalid_key_text)
                return

        key_seq = QKeySequence(key)
        self._finish_record(native_vk, key_seq.toString())

    def _finish_record(self, vk, text):
        self.recording = False
        self.releaseKeyboard()
        self.current_vk = vk
        self.setText(text)
        self.setStyleSheet("")  # 清除内联样式，恢复外部 QSS
        self.hotkeyChanged.emit(vk, text)

    def apply_texts(self, buttons: dict):
        self.none_text = buttons["none"]
        self.recording_text = buttons["recording"]
        self.invalid_key_text = buttons["invalid_key"]
        if not self.current_vk:
            self.setText(self.none_text)


class SettingsDialog(QDialog):
    """
    完全重写的设置弹窗
    特点：无边框 (Frameless)、阴影卡片、Toggle开关、填充式输入框
    """

    def __init__(self, parent, lang: str, theme: str, base_delay: int, random_delay: int, start_hotkey: tuple,
                 stop_hotkey: tuple):
        super().__init__(parent)
        self.parent_ref = parent
        self.lang = lang
        self.theme = theme
        self.buttons = LANGS.get(lang, LANGS["zh"])["buttons"]
        self.msgs = LANGS.get(lang, LANGS["zh"])["messages"]

        # 1. 设置无边框和透明背景，为了显示阴影
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(340, 440)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 留出阴影空间

        # 2. 背景容器 (模拟圆角卡片)
        self.container = QWidget()
        self.container.setObjectName("SettingsContainer")

        # 添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 8)
        self.container.setGraphicsEffect(shadow)

        main_layout.addWidget(self.container)

        # 容器内部布局
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # 标题栏
        self.title_label = QLabel(self.msgs["settings_title"])
        layout.addWidget(self.title_label)

        # 表单区域
        form_layout = QFormLayout()
        form_layout.setSpacing(16)
        form_layout.setHorizontalSpacing(24)  # 标签和输入框的间距
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # 基础延迟
        self.base_label = self._make_label(self.msgs["base_label"])
        self.base_input = QLineEdit(str(base_delay))
        self.base_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addRow(self.base_label, self.base_input)

        # 随机浮动
        self.random_label = self._make_label(self.msgs["random_label"])
        self.random_input = QLineEdit(str(random_delay))
        self.random_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addRow(self.random_label, self.random_input)

        # 热键设置
        self.start_btn = HotkeyButton()
        self.start_btn.current_vk = start_hotkey[1]
        self.start_btn.setText(start_hotkey[0])
        self.start_btn.apply_texts(self.buttons)
        self.start_label = self._make_label(self.msgs["start_hotkey"])
        form_layout.addRow(self.start_label, self.start_btn)

        self.stop_btn = HotkeyButton()
        self.stop_btn.current_vk = stop_hotkey[1]
        self.stop_btn.setText(stop_hotkey[0])
        self.stop_btn.apply_texts(self.buttons)
        self.stop_label = self._make_label(self.msgs["stop_hotkey"])
        form_layout.addRow(self.stop_label, self.stop_btn)

        layout.addLayout(form_layout)

        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #F3F4F6; max-height: 1px;")
        layout.addWidget(line)

        # --- 开关区域 ---
        # 语言开关
        lang_row = QHBoxLayout()
        self.lang_label = self._make_label(self.buttons["lang_toggle"])
        lang_row.addWidget(self.lang_label)
        lang_row.addStretch()
        # 蓝色表示 EN
        self.lang_switch = ToggleSwitch(active_color="#3B82F6")
        self.lang_switch.setChecked(lang == "en")
        self.lang_switch.stateChanged.connect(self._toggle_lang_var)
        lang_row.addWidget(self.lang_switch)
        layout.addLayout(lang_row)

        layout.addStretch()

        # --- 底部按钮 ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(38)
        self.ok_btn.clicked.connect(self._on_accept)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(38)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        self._result = None
        self._dragging = False
        self._drag_pos = QPoint()
        # --- 输入框通用样式 (填充风格，无边框) ---
        self._apply_dialog_theme_styles()

    def _make_label(self, text):
        lbl = QLabel(text)
        # 标签颜色稍微深一点
        lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #4B5563; background: transparent;")
        lbl.setFixedWidth(140)  # 统一中英文标签宽度
        return lbl

    def _toggle_lang_var(self, state):
        self.lang = "en" if state else "zh"
        self._apply_language_texts()
        if self.parent_ref:
            self.parent_ref.lang = self.lang
            self.parent_ref.settings.setValue("lang", self.lang)
            self.parent_ref._apply_language_texts()

    def _on_accept(self):
        try:
            base = int(self.base_input.text())
            rand = int(self.random_input.text())
            if base < 0 or rand < 0: raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.msgs["apply_failed"], self.msgs["invalid_number_hint"])
            return

        self._result = {
            "base": base, "rand": rand,
            "start_vk": self.start_btn.current_vk, "start_txt": self.start_btn.text(),
            "stop_vk": self.stop_btn.current_vk, "stop_txt": self.stop_btn.text(),
            "lang": self.lang,
        }
        self.accept()

    def get_result(self):
        return self._result

    def _apply_language_texts(self):
        self.buttons = LANGS.get(self.lang, LANGS["zh"])["buttons"]
        self.msgs = LANGS.get(self.lang, LANGS["zh"])["messages"]
        self.title_label.setText(self.msgs["settings_title"])
        self.base_label.setText(self.msgs["base_label"])
        self.random_label.setText(self.msgs["random_label"])
        self.start_label.setText(self.msgs["start_hotkey"])
        self.stop_label.setText(self.msgs["stop_hotkey"])
        self.lang_label.setText(self.buttons["lang_toggle"])
        self.start_btn.apply_texts(self.buttons)
        self.stop_btn.apply_texts(self.buttons)

    # 允许无边框弹窗拖动
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _apply_dialog_theme_styles(self):
        container_css = """
            QWidget#SettingsContainer {
                background: #FFFFFF;
                border-radius: 20px;
                border: 1px solid #F3F4F6;
            }
        """
        title_css = "font-size: 20px; font-weight: 800; color: #111827;"
        input_style = """
            QLineEdit, QPushButton#HotkeyBtn {
                background: #F3F4F6;
                border: none;
                border-radius: 8px;
                padding: 0px 12px;
                font-size: 14px;
                color: #374151;
                font-weight: 600;
                height: 34px;
            }
            QLineEdit:focus { 
                background: #EFF6FF; 
                color: #3B82F6; 
            }
            QPushButton#HotkeyBtn:hover {
                background: #E5E7EB;
            }
        """
        ok_css = """
            QPushButton {
                background: #3B82F6; color: white; border-radius: 19px; font-weight: bold; padding: 0 28px;
            }
            QPushButton:hover { background: #2563EB; }
        """
        cancel_css = """
            QPushButton {
                background: #F3F4F6; color: #6B7280; border-radius: 19px; font-weight: bold; padding: 0 28px;
            }
            QPushButton:hover { background: #E5E7EB; color: #374151; }
        """

        self.container.setStyleSheet(container_css)
        self.title_label.setStyleSheet(title_css)
        self.setStyleSheet(input_style)
        self.ok_btn.setStyleSheet(ok_css)
        self.cancel_btn.setStyleSheet(cancel_css)


class MainWindow(QMainWindow):
    HK_START = 101
    HK_STOP = 102

    def __init__(self, base_override: int | None = None, random_override: int | None = None):
        super().__init__()
        self.lang = "zh"
        self.theme = "light"
        self.always_on_top = False
        self.base_override = base_override
        self.random_override = random_override

        self._spinner_timer = QTimer(self)
        self._spinner_frames = ["|", "/", "-", "\\"]
        self._spinner_index = 0
        self._spinner_active = False
        self.worker = None
        self._progress_target = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._tick_progress)

        self._init_window()
        self._setup_ui()
        self._load_config()

        self.is_dragging = False
        self.drag_position = QPoint()

    def _init_window(self):
        self.setWindowTitle("miHoYo Tool Pro")
        self.resize(360, 240)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

    def _setup_ui(self):
        # 外层容器用于给阴影留出空间
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(0)

        self.main_widget = QWidget()
        self.main_widget.setObjectName("MainWidget")
        container_layout.addWidget(self.main_widget)
        self.setCentralWidget(container)

        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.main_widget.setGraphicsEffect(shadow)

        self._create_title_bar(layout)

        # --- 状态卡片区 ---
        status_card = QWidget()
        status_card.setObjectName("StatusCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 20, 16, 20)
        status_layout.setSpacing(10)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_spinner = QLabel("")
        self.status_spinner.setFixedWidth(14)
        self.status_spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_spinner.setStyleSheet("color: #3B82F6; font-weight: bold;")
        self.status_spinner.setVisible(False)

        self.status_label = QLabel()
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        status_row.addWidget(self.status_spinner)
        status_row.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(16)

        status_layout.addLayout(status_row)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(status_card)

        # --- 按钮区域 ---
        btn_container = QWidget()
        btn_row = QHBoxLayout(btn_container)
        btn_row.setSpacing(16) # 间距适中
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setFixedHeight(44) # 高度增加到 44px
        self.start_btn.setFixedWidth(140)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_task)

        self.stop_btn = QPushButton()
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.setFixedHeight(44)
        self.stop_btn.setFixedWidth(140)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_task)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addWidget(btn_container, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def _create_title_bar(self, parent_layout):
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(4, 0, 4, 0)
        title_layout.setSpacing(10)

        self.title_label = QLabel("miHoYo Tool")
        self.title_label.setObjectName("TitleLabel")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        self.pin_btn = self._create_win_btn("pin", self._toggle_pin)
        self.settings_btn = self._create_win_btn("settings", self._open_settings)
        self.min_btn = self._create_win_btn("minimize", lambda: WinSystem.minimize_window_anim(int(self.winId())))
        self.close_btn = self._create_win_btn("close", self.close, "CloseBtn")

        btn_layout.addWidget(self.pin_btn)
        btn_layout.addWidget(self.settings_btn)
        btn_layout.addWidget(self.min_btn)
        btn_layout.addWidget(self.close_btn)
        title_layout.addWidget(btn_container)

        self._refresh_icons()
        parent_layout.addLayout(title_layout)
        parent_layout.addSpacing(8)

    def _create_win_btn(self, kind, callback, obj_name="WinCtrlBtn"):
        btn = QPushButton()
        btn.setObjectName(obj_name)
        # 增大按钮点击区域到 36px
        btn.setFixedSize(36, 36)
        # 增大图标显示区域
        btn.setIconSize(QSize(22, 22)) 
        btn.clicked.connect(callback)
        if kind == "pin":
            btn.setCheckable(True)
        return btn

    def _icon_color(self):
        # 统一使用深灰色，只有 active 时变色
        base = QColor("#9CA3AF") if self.theme == "dark" else QColor("#4B5563")
        if self.always_on_top:
            return QColor("#3B82F6")
        return base

    def _make_icon(self, kind: str, color: QColor) -> QIcon:
        size = 64 # 画布放大，抗锯齿更好
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 基础笔刷配置
        pen = QPen(color, 4.0) # 加粗线条
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        c = size / 2 
        
        if kind == "pin":
            # === 现代实心图钉 (45度倾斜) ===
            painter.translate(c, c)
            painter.rotate(45) # 旋转画布
            painter.translate(-c, -c)
            
            # 画实心头部
            painter.setBrush(color) 
            painter.setPen(Qt.PenStyle.NoPen)
            
            # 头部圆角矩形
            head_w, head_h = 16, 24
            painter.drawRoundedRect(c - head_w/2, c - 18, head_w, head_h, 6, 6)
            
            # 针尖 (线条)
            pen_pin = QPen(color, 4.0)
            pen_pin.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_pin)
            painter.drawLine(int(c), int(c + 8), int(c), int(c + 24))

        elif kind == "settings":
            # === 现代实心齿轮 ===
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            
            # 1. 外圈基座
            path.addEllipse(QPoint(int(c), int(c)), 16, 16)
            
            # 2. 6个齿 (使用旋转变换)
            tooth_w, tooth_h = 10, 6
            for i in range(6):
                t = QTransform()
                t.translate(c, c)
                t.rotate(i * 60)
                t.translate(-c, -c)
                # 添加齿的矩形路径
                sub_path = QPainterPath()
                sub_path.addRoundedRect(c - tooth_w/2, c - 22, tooth_w, tooth_h, 2, 2)
                path.addPath(t.map(sub_path))
            
            # 3. 中间挖空 (减去一个小圆)
            hole = QPainterPath()
            hole.addEllipse(QPoint(int(c), int(c)), 8, 8)
            final_path = path.subtracted(hole)
            
            painter.drawPath(final_path)

        elif kind == "minimize":
            painter.drawLine(int(c - 10), int(c), int(c + 10), int(c))

        elif kind == "close":
            offset = 10
            painter.drawLine(int(c - offset), int(c - offset), int(c + offset), int(c + offset))
            painter.drawLine(int(c + offset), int(c - offset), int(c - offset), int(c + offset))

        painter.end()
        return QIcon(pm)

    def _refresh_icons(self):
        color = self._icon_color()
        pin_color = QColor("#3B82F6") if self.always_on_top else color
        self.pin_btn.setIcon(self._make_icon("pin", pin_color))
        self.settings_btn.setIcon(self._make_icon("settings", color))
        self.min_btn.setIcon(self._make_icon("minimize", color))
        self.close_btn.setIcon(self._make_icon("close", color))

        # 【关键修改】图标显示尺寸从 18 增加到 22
        icon_size = QSize(22, 22)
        for btn in [self.pin_btn, self.settings_btn, self.min_btn, self.close_btn]:
            btn.setIconSize(icon_size)
            btn.setText("")
        self.pin_btn.setChecked(self.always_on_top)

    # --- 以下为业务逻辑，保持不变 ---

    def _load_config(self):
        self.settings = QSettings("MihoyoTool", "Config")
        self.lang = self.settings.value("lang", "zh")
        self.theme = "light"
        self.always_on_top = bool(self.settings.value("pin", False, type=bool))

        self.base_delay = self.base_override if self.base_override is not None else int(
            self.settings.value("base", DEFAULT_BASE_DELAY_MS))
        self.random_delay = self.random_override if self.random_override is not None else int(
            self.settings.value("float", DEFAULT_RANDOM_DELAY_MS))

        self.start_hotkey_vk = int(self.settings.value("start_vk", DEFAULT_START_HOTKEY[1]))
        self.start_hotkey_text = str(self.settings.value("start_txt", DEFAULT_START_HOTKEY[0]))
        self.stop_hotkey_vk = int(self.settings.value("stop_vk", DEFAULT_STOP_HOTKEY[1]))
        self.stop_hotkey_text = str(self.settings.value("stop_txt", DEFAULT_STOP_HOTKEY[0]))

        self._register_hotkeys()
        self._apply_theme()
        self._apply_language_texts(initial=True)
        self._apply_pin(self.always_on_top)

    def start_task(self):
        if self.worker and self.worker.isRunning(): return
        text = QApplication.clipboard().text()
        if not text:
            self.status_label.setText(self.s("empty_clipboard"))
            logger.info("Start aborted: clipboard empty")
            return
        text = text.replace('\r\n', '\n')
        base = self.base_delay
        float_val = self.random_delay
        self.start_btn.setEnabled(False)
        self.start_btn.setText(f"{self.b('start')} ({self.start_hotkey_text})")
        self.stop_btn.setEnabled(True)
        self.status_label.setText(self.s("injecting"))
        self._start_spinner()
        self._set_progress_target(0, instant=True)
        self.worker = PasteWorker(text, base, float_val)
        self.worker.progress_signal.connect(self._set_progress_target)
        self.worker.status_signal.connect(self._set_status_text)
        self.worker.finished_signal.connect(self.on_finished)
        logger.info("Task started: %d chars, base=%dms random=%dms", len(text), base, float_val)
        self.worker.start()

    def stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._set_status_value("stopping")
            self._start_spinner()
            logger.info("Stop requested by user")

    def on_finished(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setText(f"{self.b('start')} ({self.start_hotkey_text})")
        self.stop_btn.setEnabled(False)
        self._set_progress_target(0, instant=True)
        status = self.status_label.text()
        if status in (self.s("interrupted"), self.s("stopped")):
            self.status_label.setText(self.s("stopped_by_user"))
        else:
            self.status_label.setText(self.s("done"))
        self._stop_spinner()
        logger.info("Task finished; status=%s", status)

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
        self.settings.setValue("base", self.base_delay)
        self.settings.setValue("float", self.random_delay)
        self.settings.setValue("lang", self.lang)
        self.settings.setValue("theme", self.theme)
        self.settings.setValue("pin", self.always_on_top)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_START)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_STOP)
        event.accept()

    def _register_hotkeys(self):
        if self.start_hotkey_vk and not WinSystem.register_hotkey(int(self.winId()), self.HK_START,
                                                                  self.start_hotkey_vk):
            logger.warning("Hotkey restore failed: %s(%s)", self.start_hotkey_text, hex(self.start_hotkey_vk))
        if self.stop_hotkey_vk and not WinSystem.register_hotkey(int(self.winId()), self.HK_STOP, self.stop_hotkey_vk):
            logger.warning("Hotkey restore failed: %s(%s)", self.stop_hotkey_text, hex(self.stop_hotkey_vk))

    def _apply_settings(self, base_delay: int, random_delay: int, start_vk: int, start_txt: str, stop_vk: int,
                        stop_txt: str):
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_START)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_STOP)

        if start_vk and not WinSystem.register_hotkey(int(self.winId()), self.HK_START, start_vk):
            QMessageBox.warning(self, self.msg("hotkey_conflict_title"), self.msg("hotkey_conflict"))
            WinSystem.register_hotkey(int(self.winId()), self.HK_START, self.start_hotkey_vk)
            WinSystem.register_hotkey(int(self.winId()), self.HK_STOP, self.stop_hotkey_vk)
            return
        if stop_vk and not WinSystem.register_hotkey(int(self.winId()), self.HK_STOP, stop_vk):
            QMessageBox.warning(self, self.msg("hotkey_conflict_title"), self.msg("hotkey_conflict"))
            WinSystem.register_hotkey(int(self.winId()), self.HK_START, self.start_hotkey_vk)
            WinSystem.register_hotkey(int(self.winId()), self.HK_STOP, self.stop_hotkey_vk)
            return

        self.base_delay = base_delay
        self.random_delay = random_delay
        self.start_hotkey_vk = start_vk
        self.start_hotkey_text = start_txt
        self.stop_hotkey_vk = stop_vk
        self.stop_hotkey_text = stop_txt

        self.settings.setValue("base", self.base_delay)
        self.settings.setValue("float", self.random_delay)
        self.settings.setValue("start_vk", self.start_hotkey_vk)
        self.settings.setValue("start_txt", self.start_hotkey_text)
        self.settings.setValue("stop_vk", self.stop_hotkey_vk)
        self.settings.setValue("stop_txt", self.stop_hotkey_text)

        self._apply_language_texts()

    def _open_settings(self):
        dlg = SettingsDialog(
            self,
            self.lang,
            self.theme,
            self.base_delay,
            self.random_delay,
            (self.start_hotkey_text, self.start_hotkey_vk),
            (self.stop_hotkey_text, self.stop_hotkey_vk),
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            res = dlg.get_result()
            if res:
                self._apply_settings(
                    res["base"],
                    res["rand"],
                    res["start_vk"],
                    res["start_txt"],
                    res["stop_vk"],
                    res["stop_txt"],
                )
                if res.get("lang") and res["lang"] != self.lang:
                    self.lang = res["lang"]
                    self.settings.setValue("lang", self.lang)
                    self._apply_language_texts()

    def _start_spinner(self):
        if self._spinner_active:
            return
        self._spinner_active = True
        self._spinner_timer.timeout.connect(self._tick_spinner)
        self._spinner_timer.start(120)
        self.status_spinner.setVisible(True)

    def _stop_spinner(self):
        if not self._spinner_active:
            return
        self._spinner_active = False
        self._spinner_timer.stop()
        self._spinner_timer.timeout.disconnect(self._tick_spinner)
        self.status_spinner.setText("")
        self.status_spinner.setVisible(False)

    def _tick_spinner(self):
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        self.status_spinner.setText(self._spinner_frames[self._spinner_index])

    def _set_progress_target(self, value: int, instant: bool = False):
        value = max(0, min(100, int(value)))
        current = self.progress_bar.value()
        if instant or value < current:
            self._progress_target = value
            self._progress_timer.stop()
            self.progress_bar.setValue(value)
            return
        self._progress_target = value
        if not self._progress_timer.isActive():
            self._progress_timer.start(16)

    def _tick_progress(self):
        current = self.progress_bar.value()
        diff = self._progress_target - current
        if diff <= 0:
            self._progress_timer.stop()
            return
        step = max(1, min(8, int(diff * 0.2)))
        next_val = current + step
        if next_val >= self._progress_target:
            next_val = self._progress_target
            self._progress_timer.stop()
        self.progress_bar.setValue(next_val)

    def _apply_theme(self):
        theme_css = THEMES.get(self.theme, THEMES["light"])
        self.setStyleSheet(theme_css)
        self._refresh_icons()

    def _apply_language_texts(self, initial=False):
        self.setWindowTitle(self.window_text())
        self.title_label.setText(self.title_text())
        self.min_btn.setToolTip(self.wb("minimize"))
        self.close_btn.setToolTip(self.wb("close"))
        self.pin_btn.setToolTip(self.b("unpin") if self.always_on_top else self.b("pin"))
        self.settings_btn.setToolTip(self.b("settings"))

        if not self.worker or not self.worker.isRunning():
            self.status_label.setText(self.s("waiting"))
            self.start_btn.setText(f"{self.b('start')} ({self.start_hotkey_text})")
        self.stop_btn.setText(f"{self.b('stop')} ({self.stop_hotkey_text})")

    def _toggle_theme(self):
        # 暂不支持暗色主题，保持为 light
        self.theme = "light"
        self._apply_theme()
        self.settings.setValue("theme", self.theme)

    def _toggle_pin(self):
        self.always_on_top = not self.always_on_top
        self._apply_pin(self.always_on_top)
        self.settings.setValue("pin", self.always_on_top)
        self._apply_language_texts()

    def _apply_pin(self, flag: bool):
        self.always_on_top = flag
        if hasattr(self, "pin_btn"):
            self.pin_btn.setChecked(flag)
            base_color = self._icon_color()
            pin_color = QColor("#3B82F6") if self.always_on_top else base_color
            self.pin_btn.setIcon(self._make_icon("pin", pin_color))
        current = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if current != flag:
            # 使用 Win32 API 避免窗口闪烁
            WinSystem.set_topmost(int(self.winId()), flag)
            self.show()

    def l(self, key: str):
        return get_text(self.lang, "labels", key)

    def b(self, key: str):
        return get_text(self.lang, "buttons", key)

    def s(self, key: str):
        return get_text(self.lang, "status", key)

    def msg(self, key: str, **kwargs):
        return get_text(self.lang, "messages", key, **kwargs)

    def wb(self, key: str):
        return get_text(self.lang, "window_buttons", key)

    def window_text(self):
        return LANGS.get(self.lang, LANGS["zh"]).get("window_title", "miHoYo Tool Pro")

    def title_text(self):
        return LANGS.get(self.lang, LANGS["zh"]).get("title", "miHoYo Tool")

    def _update_hotkey_hint(self):
        messages = LANGS.get(self.lang, LANGS["zh"]).get("messages", {})
        if "hotkey_hint" in messages:
            self.hotkey_hint.setText(self.msg("hotkey_hint", start=self.start_hotkey_text, stop=self.stop_hotkey_text))
        else:
            self.hotkey_hint.setText(f"{self.start_hotkey_text} / {self.stop_hotkey_text}")

    def _set_status_value(self, key: str):
        self.status_label.setText(self.s(key))

    def _set_status_text(self, text: str):
        if text.startswith("status:"):
            parts = text.split(":")
            code = parts[1] if len(parts) > 1 else ""
            if code == "preparing":
                suffix = parts[2] if len(parts) > 2 else ""
                self.status_label.setText(f"{self.s('preparing')} {suffix}".strip())
                return
            mapping = {
                "typing": "typing",
                "stopped": "stopped",
                "finished": "success",
            }
            key = mapping.get(code)
            if key:
                self._set_status_value(key)
                return
        self.status_label.setText(text)
