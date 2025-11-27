# main_window.py
import sys
import os
import logging
from ctypes import wintypes

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QLineEdit, QProgressBar, QPushButton, QApplication, QMessageBox,
                               QDialog, QDialogButtonBox, QFormLayout, QGraphicsDropShadowEffect, QFrame,
                               QSizePolicy)
from PySide6.QtCore import Qt, QPoint, QSettings, Signal, QTimer, QSize
from PySide6.QtGui import QKeySequence, QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath, QTransform

# 引入你的本地模块
from config import (
    DEFAULT_BASE_DELAY_MS,
    DEFAULT_RANDOM_DELAY_MS,
    DEFAULT_COUNTDOWN_SEC,
    DEFAULT_START_HOTKEY,
    DEFAULT_STOP_HOTKEY,
    DEFAULT_CONTINUE_HOTKEY,
)
from styles import THEMES
from ui_texts import LANGS, get_text
from core_engine import WinSystem, PasteWorker
from components import ToggleSwitch  # <--- 必须导入这个新组件

logger = logging.getLogger(__name__)


class HotkeyButton(QPushButton):
    """ 热键录制按钮，样式由 QSS 控制，这里主要处理逻辑 """
    hotkeyChanged = Signal(int, int, str)

    def __init__(self):
        super().__init__()
        self.current_vk = 0
        self.current_mods = 0
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
        modifiers = e.modifiers()

        if key == Qt.Key.Key_Escape:
            self._finish_record(0, 0, self.none_text)
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

        win_mods = 0
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            win_mods |= WinSystem.MOD_CONTROL
        if modifiers & Qt.KeyboardModifier.AltModifier:
            win_mods |= WinSystem.MOD_ALT
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            win_mods |= WinSystem.MOD_SHIFT
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            win_mods |= WinSystem.MOD_WIN

        seq_value = int(modifiers.value) | key
        key_seq = QKeySequence(seq_value)
        self._finish_record(native_vk, win_mods, key_seq.toString())

    def _finish_record(self, vk, mods, text):
        self.recording = False
        self.releaseKeyboard()
        self.current_vk = vk
        self.current_mods = mods
        self.setText(text)
        self.setStyleSheet("")  # 清除内联样式，恢复外部 QSS
        self.hotkeyChanged.emit(vk, mods, text)

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

    def __init__(self, parent, lang: str, theme: str, base_delay: int, random_delay: int, countdown_seconds: int,
                 start_hotkey: tuple, continue_hotkey: tuple):
        super().__init__(parent)
        self.parent_ref = parent
        self.lang = lang
        self.theme = theme
        self.buttons = LANGS.get(lang, LANGS["zh"])["buttons"]
        self.msgs = LANGS.get(lang, LANGS["zh"])["messages"]

        # 1. 设置无边框和透明背景，为了显示阴影
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(340, 500)

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

        # 启动等待
        self.wait_label = self._make_label(self.msgs["countdown_label"])
        self.wait_input = QLineEdit(str(countdown_seconds))
        self.wait_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addRow(self.wait_label, self.wait_input)

        # 热键设置
        self.start_btn = HotkeyButton()
        self.start_btn.current_vk = start_hotkey[1]
        self.start_btn.current_mods = start_hotkey[2]
        self.start_btn.setText(start_hotkey[0])
        self.start_btn.apply_texts(self.buttons)
        self.start_btn.hotkeyChanged.connect(lambda _vk, _mods, txt: self._on_hotkey_record(self.start_btn, txt))
        self.start_label = self._make_label(self.msgs["start_hotkey"])
        form_layout.addRow(self.start_label, self.start_btn)

        self.continue_btn = HotkeyButton()
        self.continue_btn.current_vk = continue_hotkey[1]
        self.continue_btn.current_mods = continue_hotkey[2]
        self.continue_btn.setText(continue_hotkey[0])
        self.continue_btn.apply_texts(self.buttons)
        self.continue_btn.hotkeyChanged.connect(lambda _vk, _mods, txt: self._on_hotkey_record(self.continue_btn, txt))
        self.continue_label = self._make_label(self.msgs["continue_hotkey"])
        form_layout.addRow(self.continue_label, self.continue_btn)

        # 提示区域
        self.hotkey_notice = QLabel(self.container)
        self.hotkey_notice.setObjectName("HotkeyNotice")
        self.hotkey_notice.setWordWrap(True)
        self.hotkey_notice.setVisible(False)
        self.hotkey_notice.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hotkey_notice.setStyleSheet("""
            QLabel#HotkeyNotice {
                background: #ECFDF3;
                color: #065F46;
                border: 1px solid #A7F3D0;
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        self._hotkey_notice_timer = QTimer(self)
        self._hotkey_notice_timer.setSingleShot(True)
        self._hotkey_notice_timer.timeout.connect(self._hide_hotkey_notice)

        layout.addLayout(form_layout)
        # 默认允许直接编辑，避免进入设置时短暂不可操作
        self._inputs_armed = True
        self._set_inputs_enabled(True)

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
        # 避免默认自动聚焦到第一个输入框：仅点击后才聚焦
        for field in (self.base_input, self.random_input, self.wait_input):
            field.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.container.setFocus()

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
            wait_secs = int(self.wait_input.text())
            if base < 0 or rand < 0 or wait_secs < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, self.msgs["apply_failed"], self.msgs["invalid_number_hint"])
            return

        self._result = {
            "base": base,
            "rand": rand,
            "wait": wait_secs,
            "start_vk": self.start_btn.current_vk,
            "start_mod": self.start_btn.current_mods,
            "start_txt": self.start_btn.text(),
            "continue_vk": self.continue_btn.current_vk,
            "continue_mod": self.continue_btn.current_mods,
            "continue_txt": self.continue_btn.text(),
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
        self.wait_label.setText(self.msgs["countdown_label"])
        self.start_label.setText(self.msgs["start_hotkey"])
        self.continue_label.setText(self.msgs["continue_hotkey"])
        self.lang_label.setText(self.buttons["lang_toggle"])
        self.start_btn.apply_texts(self.buttons)
        self.continue_btn.apply_texts(self.buttons)
        # 语言切换后若仍未激活输入，保持禁用状态
        if not getattr(self, "_inputs_armed", True):
            self._set_inputs_enabled(False)

    def _set_inputs_enabled(self, enabled: bool):
        self.base_input.setReadOnly(not enabled)
        self.random_input.setReadOnly(not enabled)
        self.wait_input.setReadOnly(not enabled)
        self.start_btn.setEnabled(enabled)
        self.continue_btn.setEnabled(enabled)

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
                background: #F8FAFF;
                border-radius: 20px;
                border: 1px solid #E0E7FF;
            }
        """
        title_css = "font-size: 21px; font-weight: 900; color: #0F172A; font-family: 'Manrope','Segoe UI Variable Display','Segoe UI','Microsoft YaHei UI','PingFang SC',sans-serif;"
        input_style = """
            QLineEdit, QPushButton#HotkeyBtn {
                background: #EEF2FF;
                border: 1px solid #E0E7FF;
                border-radius: 8px;
                padding: 0px 12px;
                font-size: 14px;
                color: #0F172A;
                font-weight: 700;
                font-family: 'Manrope','Segoe UI Variable Display','Segoe UI','Microsoft YaHei UI','PingFang SC',sans-serif;
                height: 34px;
            }
            QLineEdit:focus { 
                background: #E0E7FF; 
                color: #1D4ED8; 
            }
            QPushButton#HotkeyBtn:hover {
                background: #E5ECFF;
            }
        """
        ok_css = """
            QPushButton {
                background: #1D4ED8; color: white; border-radius: 19px; font-weight: 850; padding: 0 28px;
                font-family: 'Manrope','Segoe UI Variable Display','Segoe UI','Microsoft YaHei UI','PingFang SC',sans-serif;
            }
            QPushButton:hover { background: #1E40AF; }
        """
        cancel_css = """
            QPushButton {
                background: #EFF6FF; color: #1F2937; border-radius: 19px; font-weight: 750; padding: 0 28px; border: 1px solid #E0E7FF;
                font-family: 'Manrope','Segoe UI Variable Display','Segoe UI','Microsoft YaHei UI','PingFang SC',sans-serif;
            }
            QPushButton:hover { background: #E5ECFF; color: #0F172A; }
        """

        self.container.setStyleSheet(container_css)
        self.title_label.setStyleSheet(title_css)
        self.setStyleSheet(input_style)
        self.ok_btn.setStyleSheet(ok_css)
        self.cancel_btn.setStyleSheet(cancel_css)

    def _on_hotkey_record(self, btn: QPushButton, text: str):
        # 简易防空检查
        if text.strip().lower() in ("", "none", self.buttons.get("invalid_key", "")):
            self._show_hotkey_notice(False, self.msgs.get("hotkey_invalid", "Invalid hotkey"))
            return

        # 冲突检测：如果其它按钮已使用同一组合，则清空其它按钮
        current_combo = (btn.current_vk, btn.current_mods)
        peers = [self.start_btn, self.continue_btn]
        overridden = []
        for peer in peers:
            if peer is btn:
                continue
            if peer.current_vk and (peer.current_vk, peer.current_mods) == current_combo:
                peer.current_vk = 0
                peer.current_mods = 0
                peer.setText(peer.none_text)
                overridden.append(peer)

        if overridden:
            self._show_hotkey_notice(False, self.msgs.get("hotkey_override", "").format(key=text))
        else:
            self._show_hotkey_notice(True, self.msgs.get("hotkey_saved", "").format(key=text))

    def _hide_hotkey_notice(self):
        self.hotkey_notice.setVisible(False)
        self.hotkey_notice.clear()

    def _show_hotkey_notice(self, success: bool, message: str):
        prefix = "✓ " if success else "⚠ "
        self.hotkey_notice.setText(f"{prefix}{message}")
        color = "#065F46" if success else "#92400E"
        bg = "#ECFDF3" if success else "#FEF3C7"
        border = "#A7F3D0" if success else "#FCD34D"
        self.hotkey_notice.setStyleSheet(f"""
            QLabel#HotkeyNotice {{
                background: {bg};
                color: {color};
                border: 1px solid {border};
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        self._position_hotkey_notice()
        self.hotkey_notice.setVisible(True)
        self._hotkey_notice_timer.start(2200)

    def _position_hotkey_notice(self):
        max_w = max(160, self.container.width() - 32)
        self.hotkey_notice.setFixedWidth(min(max_w, 360))
        self.hotkey_notice.adjustSize()
        x = max(12, int((self.container.width() - self.hotkey_notice.width()) / 2))
        y = 12
        self.hotkey_notice.move(x, y)
        self.hotkey_notice.raise_()

    def resizeEvent(self, event):
        if getattr(self, "hotkey_notice", None) and self.hotkey_notice.isVisible():
            self._position_hotkey_notice()
        super().resizeEvent(event)


class MainWindow(QMainWindow):
    HK_START = 101
    HK_CONTINUE = 102

    def __init__(self, base_override: int | None = None, random_override: int | None = None):
        super().__init__()
        self.lang = "zh"
        self.theme = "light"
        self.always_on_top = False
        self.base_override = base_override
        self.random_override = random_override
        self.countdown_seconds = DEFAULT_COUNTDOWN_SEC
        self.pending_text = ""
        self.pending_offset = 0
        self._hold_finish = False

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
        self.resize(340, 240)
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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

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
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setSpacing(8)

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
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFixedHeight(18)

        status_layout.addLayout(status_row)
        status_layout.addWidget(self.progress_bar)

        layout.addWidget(status_card)

        # --- 控制卡片 ---
        control_card = QWidget()
        control_card.setObjectName("ControlCard")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(16, 12, 16, 12)
        control_layout.setSpacing(8)

        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("StartBtn")
        self.start_btn.setFixedHeight(44)
        self.start_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_task)

        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("ContinueBtn")
        self.toggle_btn.setFixedHeight(44)
        self.toggle_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setEnabled(True)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.toggle_btn)
        control_layout.addWidget(btn_container)

        layout.addWidget(control_card, 0)

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

    def _load_svg_icon(self, filename: str, fallback: QIcon | None = None) -> QIcon:
        path = os.path.join("svg", filename)
        if os.path.exists(path):
            return QIcon(path)
        return fallback or QIcon()

    def _refresh_icons(self):
        color = self._icon_color()
        pin_icon_name = "push-pin.svg" if self.always_on_top else "push-pin-simple.svg"
        pin_icon = self._load_svg_icon(pin_icon_name, self._make_icon("pin", color))
        settings_icon = self._load_svg_icon("gear.svg", self._make_icon("settings", color))
        min_icon = self._load_svg_icon("arrows-in-simple.svg", self._make_icon("minimize", color))
        close_icon = self._load_svg_icon("x.svg", self._make_icon("close", color))

        self.pin_btn.setIcon(pin_icon)
        self.settings_btn.setIcon(settings_icon)
        self.min_btn.setIcon(min_icon)
        self.close_btn.setIcon(close_icon)

        icon_size = QSize(20, 20)
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
            self.settings.value("base", DEFAULT_BASE_DELAY_MS, type=int))
        self.random_delay = self.random_override if self.random_override is not None else int(
            self.settings.value("float", DEFAULT_RANDOM_DELAY_MS, type=int))
        self.countdown_seconds = int(self.settings.value("countdown", DEFAULT_COUNTDOWN_SEC, type=int))

        self.start_hotkey_vk = int(self.settings.value("start_vk", DEFAULT_START_HOTKEY[1], type=int))
        self.start_hotkey_mod = int(self.settings.value("start_mod", DEFAULT_START_HOTKEY[2], type=int))
        self.start_hotkey_text = str(self.settings.value("start_txt", DEFAULT_START_HOTKEY[0]))
        self.continue_hotkey_vk = int(self.settings.value("continue_vk", DEFAULT_CONTINUE_HOTKEY[1], type=int))
        self.continue_hotkey_mod = int(self.settings.value("continue_mod", DEFAULT_CONTINUE_HOTKEY[2], type=int))
        self.continue_hotkey_text = str(self.settings.value("continue_txt", DEFAULT_CONTINUE_HOTKEY[0]))
        # 暂停/继续统一同一组合键，保持 stop 文案为同一键
        self.stop_hotkey_vk = self.continue_hotkey_vk
        self.stop_hotkey_mod = self.continue_hotkey_mod
        self.stop_hotkey_text = self.continue_hotkey_text

        self._register_hotkeys()
        self._apply_theme()
        self._apply_language_texts(initial=True)
        self._apply_pin(self.always_on_top)
        self._update_toggle_button_text()

    def _launch_worker(self, text: str, start_offset: int = 0, resume: bool = False):
        if self.worker and self.worker.isRunning():
            return
        if not text:
            self.status_label.setText(self.s("empty_clipboard"))
            return
        total_len = len(text)
        initial_progress = int((start_offset / total_len) * 100) if total_len else 0
        self.pending_offset = start_offset

        self.start_btn.setEnabled(True)
        self.toggle_btn.setEnabled(True)
        state_key = "continuing" if resume else "injecting"
        self.status_label.setText(self.s(state_key))
        self._start_spinner()
        self._set_progress_target(initial_progress, instant=True)

        self.worker = PasteWorker(text, self.base_delay, self.random_delay, start_offset, self.countdown_seconds)
        self.worker.progress_signal.connect(self._set_progress_target)
        self.worker.status_signal.connect(self._set_status_text)
        self.worker.finished_signal.connect(self.on_finished)
        logger.info(
            "Task started%s: %d chars, base=%dms random=%dms offset=%d wait=%ds",
            " (resume)" if resume else "",
            len(text),
            self.base_delay,
            self.random_delay,
            start_offset,
            self.countdown_seconds,
        )
        self.worker.start()

    def start_task(self):
        if self.worker and self.worker.isRunning(): return
        text = QApplication.clipboard().text()
        if not text:
            self.status_label.setText(self.s("empty_clipboard"))
            logger.info("Start aborted: clipboard empty")
            return
        self._hold_finish = False
        text = text.replace('\r\n', '\n')
        self.pending_text = text
        self.pending_offset = 0
        self._launch_worker(text, start_offset=0, resume=False)
        self._update_toggle_button_text()

    def continue_task(self):
        if self.worker and self.worker.isRunning():
            return
        if not self.pending_text or self.pending_offset >= len(self.pending_text):
            self.status_label.setText(self.s("no_pending"))
            return
        self._hold_finish = False
        self._launch_worker(self.pending_text, start_offset=self.pending_offset, resume=True)
        self._update_toggle_button_text()

    def stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self._set_status_value("stopping")
            self._start_spinner()
            self.toggle_btn.setEnabled(False)
            logger.info("Stop requested by user")

    def on_finished(self):
        finished_worker = self.worker
        self.worker = None

        self.start_btn.setEnabled(True)
        self.toggle_btn.setEnabled(True)
        self._stop_spinner()

        if finished_worker:
            if finished_worker.completed:
                self.pending_text = ""
                self.pending_offset = 0
                # 任务完成时保持 100%，避免立刻归零
                self._set_progress_target(100, instant=True)
                self.status_label.setText(self.s("done"))
                self._hold_finish = True
            else:
                if finished_worker.next_offset < len(finished_worker.content):
                    self.pending_text = finished_worker.content
                    self.pending_offset = finished_worker.next_offset
                    progress = int((self.pending_offset / len(self.pending_text)) * 100)
                    self._set_progress_target(progress, instant=True)
                    self.status_label.setText(self.s("stopped_by_user"))
                else:
                    self.pending_text = ""
                    self.pending_offset = 0
                    self._set_progress_target(0, instant=True)
                    self.status_label.setText(self.s("stopped_by_user"))
                self._hold_finish = False
        else:
            self.status_label.setText(self.s("done"))
            self._hold_finish = True

        can_resume = bool(self.pending_text and self.pending_offset < len(self.pending_text))
        self.start_btn.setEnabled(True)
        self._update_toggle_button_text()
        logger.info("Task finished; resume_available=%s", can_resume)

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG" or event_type == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312:  # WM_HOTKEY
                if msg.wParam == self.HK_START:
                    self.start_task()
                elif msg.wParam == self.HK_CONTINUE:
                    self._on_toggle_clicked()
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
        self.settings.setValue("countdown", self.countdown_seconds)
        self.settings.setValue("lang", self.lang)
        self.settings.setValue("pin", self.always_on_top)
        self.settings.setValue("start_vk", self.start_hotkey_vk)
        self.settings.setValue("start_mod", self.start_hotkey_mod)
        self.settings.setValue("start_txt", self.start_hotkey_text)
        self.settings.setValue("continue_vk", self.continue_hotkey_vk)
        self.settings.setValue("continue_mod", self.continue_hotkey_mod)
        self.settings.setValue("continue_txt", self.continue_hotkey_text)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_START)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_CONTINUE)
        event.accept()

    def _register_hotkeys(self):
        if self.start_hotkey_vk and not WinSystem.register_hotkey(
                int(self.winId()), self.HK_START, self.start_hotkey_vk, self.start_hotkey_mod):
            logger.warning("Hotkey restore failed: %s(%s)", self.start_hotkey_text, hex(self.start_hotkey_vk))
        if self.continue_hotkey_vk and not WinSystem.register_hotkey(
                int(self.winId()), self.HK_CONTINUE, self.continue_hotkey_vk, self.continue_hotkey_mod):
            logger.warning("Hotkey restore failed: %s(%s)", self.continue_hotkey_text, hex(self.continue_hotkey_vk))

    def _apply_settings(self, base_delay: int, random_delay: int, countdown: int,
                        start_vk: int, start_mod: int, start_txt: str,
                        continue_vk: int, continue_mod: int, continue_txt: str):
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_START)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_CONTINUE)

        old_values = (
            self.start_hotkey_vk, self.start_hotkey_mod,
            self.continue_hotkey_vk, self.continue_hotkey_mod
        )

        def restore():
            if old_values[0]:
                WinSystem.register_hotkey(int(self.winId()), self.HK_START, old_values[0], old_values[1])
            if old_values[2]:
                WinSystem.register_hotkey(int(self.winId()), self.HK_CONTINUE, old_values[2], old_values[3])

        actions = [
            {"name": "start", "vk": start_vk, "mod": start_mod, "txt": start_txt, "id": self.HK_START},
            {"name": "continue", "vk": continue_vk, "mod": continue_mod, "txt": continue_txt, "id": self.HK_CONTINUE},
        ]

        # 冲突静默覆盖：后出现的功能占用该组合，之前的被清空（置为 None）
        used = {}
        for idx, act in enumerate(actions):
            combo = (act["vk"], act["mod"])
            if not act["vk"]:
                continue
            if combo in used:
                prev_idx = used[combo]
                actions[prev_idx]["vk"] = 0
                actions[prev_idx]["mod"] = 0
                actions[prev_idx]["txt"] = self.b("none")
            used[combo] = idx

        for act in actions:
            if act["vk"] and not WinSystem.register_hotkey(int(self.winId()), act["id"], act["vk"], act["mod"]):
                self._show_hotkey_notice(False, self.msg("hotkey_conflict_runtime", **{"key": act["txt"]}))
                restore()
                return

        start_vk, start_mod, start_txt = actions[0]["vk"], actions[0]["mod"], actions[0]["txt"]
        continue_vk, continue_mod, continue_txt = actions[1]["vk"], actions[1]["mod"], actions[1]["txt"]

        self.base_delay = base_delay
        self.random_delay = random_delay
        self.countdown_seconds = countdown
        self.start_hotkey_vk = start_vk
        self.start_hotkey_mod = start_mod
        self.start_hotkey_text = start_txt
        self.continue_hotkey_vk = continue_vk
        self.continue_hotkey_mod = continue_mod
        self.continue_hotkey_text = continue_txt
        # 暂停/继续统一同一按键
        self.stop_hotkey_vk = continue_vk
        self.stop_hotkey_mod = continue_mod
        self.stop_hotkey_text = continue_txt

        self.settings.setValue("base", self.base_delay)
        self.settings.setValue("float", self.random_delay)
        self.settings.setValue("countdown", self.countdown_seconds)
        self.settings.setValue("start_vk", self.start_hotkey_vk)
        self.settings.setValue("start_mod", self.start_hotkey_mod)
        self.settings.setValue("start_txt", self.start_hotkey_text)
        self.settings.setValue("continue_vk", self.continue_hotkey_vk)
        self.settings.setValue("continue_mod", self.continue_hotkey_mod)
        self.settings.setValue("continue_txt", self.continue_hotkey_text)

        self._apply_language_texts()

    def _open_settings(self):
        # 防止误触：先停用快捷键和主要控制
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_START)
        WinSystem.unregister_hotkey(int(self.winId()), self.HK_CONTINUE)
        start_enabled = self.start_btn.isEnabled()
        toggle_enabled = self.toggle_btn.isEnabled()
        self.start_btn.setEnabled(False)
        self.toggle_btn.setEnabled(False)

        dlg = SettingsDialog(
            self,
            self.lang,
            self.theme,
            self.base_delay,
            self.random_delay,
            self.countdown_seconds,
            (self.start_hotkey_text, self.start_hotkey_vk, self.start_hotkey_mod),
            (self.continue_hotkey_text, self.continue_hotkey_vk, self.continue_hotkey_mod),
        )
        try:
            if dlg.exec() == QDialog.DialogCode.Accepted:
                res = dlg.get_result()
                if res:
                    self._apply_settings(
                        res["base"],
                        res["rand"],
                        res["wait"],
                        res["start_vk"],
                        res["start_mod"],
                        res["start_txt"],
                        res["continue_vk"],
                        res["continue_mod"],
                        res["continue_txt"],
                    )
                    if res.get("lang") and res["lang"] != self.lang:
                        self.lang = res["lang"]
                        self.settings.setValue("lang", self.lang)
                        self._apply_language_texts()
            else:
                # 取消时恢复旧快捷键注册
                self._register_hotkeys()
        finally:
            # 恢复按钮可用状态，结合当前运行状态
            worker_running = self.worker and self.worker.isRunning()
            can_resume = bool(self.pending_text and self.pending_offset < len(self.pending_text))
            self.start_btn.setEnabled(start_enabled and not worker_running)
            self.toggle_btn.setEnabled(toggle_enabled or worker_running or can_resume)
            self._update_toggle_button_text()

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
            if self.pending_text and self.pending_offset < len(self.pending_text):
                self.status_label.setText(self.s("resume_ready"))
            elif self._hold_finish:
                self.status_label.setText(self.s("done"))
            elif not self._hold_finish:
                self.status_label.setText(self.s("waiting"))
                self._set_progress_target(0, instant=True)
                self._hold_finish = False
        self._update_toggle_button_text()

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
            self._refresh_icons()

        # 同步 Qt flag 与 Win32，确保取消置顶可靠
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) != flag:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, flag)
            self.show()

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

    def _show_hotkey_notice(self, success: bool, message: str):
        if success:
            self.status_label.setText(message)
            return
        QMessageBox.warning(self, self.msg("hotkey_conflict_title"), message)

    def window_text(self):
        return LANGS.get(self.lang, LANGS["zh"]).get("window_title", "miHoYo Tool Pro")

    def title_text(self):
        return LANGS.get(self.lang, LANGS["zh"]).get("title", "miHoYo Tool")

    def _update_toggle_button_text(self):
        running = self.worker and self.worker.isRunning()
        can_resume = bool(self.pending_text and self.pending_offset < len(self.pending_text))
        # 暂停/继续共用同一热键，图标随状态变化
        text = self.continue_hotkey_text
        if can_resume and not running:
            icon = self._load_svg_icon("play.svg", self._make_icon("minimize", QColor("#FFFFFF")))
        else:
            icon = self._load_svg_icon("pause.svg", self._make_icon("minimize", QColor("#FFFFFF")))

        self.toggle_btn.setText(text)
        self.toggle_btn.setIcon(icon)
        self.toggle_btn.setIconSize(QSize(20, 20))
        self.start_btn.setText(self.start_hotkey_text)
        self.start_btn.setIcon(self._load_svg_icon("rocket-launch.svg", self._make_icon("minimize", QColor("#FFFFFF"))))
        self.start_btn.setIconSize(QSize(20, 20))

    def _on_toggle_clicked(self):
        if self.worker and self.worker.isRunning():
            self.stop_task()  # 充当“暂停”
            return
        if self.pending_text and self.pending_offset < len(self.pending_text):
            self.continue_task()
        else:
            self.start_task()

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
