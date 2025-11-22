import time
import random
import ctypes
from ctypes import wintypes, Structure, Union, c_ulong, c_uint64, sizeof, POINTER, c_int, c_uint
from PySide6.QtCore import QThread, Signal

# 指针长度适配
ULONG_PTR = c_uint64 if sizeof(ctypes.c_void_p) == 8 else c_ulong


class KEYBDINPUT(Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class INPUT_UNION(Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(Structure):
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", INPUT_UNION)]


class WinSystem:
    # WinAPI 常量
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_RETURN = 0x0D
    WM_SYSCOMMAND = 0x0112
    SC_MINIMIZE = 0xF020

    _user32 = ctypes.windll.user32
    _shell32 = ctypes.windll.shell32

    @staticmethod
    def is_user_an_admin() -> bool:
        try:
            return WinSystem._shell32.IsUserAnAdmin()
        except:
            return False

    @staticmethod
    def set_app_id(app_id: str):
        try:
            WinSystem._shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except AttributeError:
            pass

    @staticmethod
    def send_input_batch(inputs: list):
        n_inputs = len(inputs)
        input_array = (INPUT * n_inputs)(*inputs)
        WinSystem._user32.SendInput.argtypes = [c_uint, POINTER(INPUT), c_int]
        WinSystem._user32.SendInput(n_inputs, input_array, sizeof(INPUT))

    @staticmethod
    def minimize_window_anim(hwnd: int):
        # 发送系统命令以保留最小化动画
        WinSystem._user32.PostMessageW(wintypes.HWND(hwnd), WinSystem.WM_SYSCOMMAND, WinSystem.SC_MINIMIZE, 0)

    @staticmethod
    def register_hotkey(hwnd: int, hotkey_id: int, vk: int) -> bool:
        return WinSystem._user32.RegisterHotKey(wintypes.HWND(hwnd), hotkey_id, 0, vk)

    @staticmethod
    def unregister_hotkey(hwnd: int, hotkey_id: int) -> bool:
        return WinSystem._user32.UnregisterHotKey(wintypes.HWND(hwnd), hotkey_id)


class InputSimulator:
    @staticmethod
    def _make_input(vk=0, scan=0, flags=0) -> INPUT:
        inp = INPUT()
        inp.type = WinSystem.INPUT_KEYBOARD
        inp.ki.wVk = vk
        inp.ki.wScan = scan
        inp.ki.dwFlags = flags
        return inp

    @staticmethod
    def send_char(char: str):
        if char == '\n':
            InputSimulator.send_vk(WinSystem.VK_RETURN)
            return

        # Unicode 模式模拟按键
        scan_code = ord(char)
        down = InputSimulator._make_input(scan=scan_code, flags=WinSystem.KEYEVENTF_UNICODE)
        up = InputSimulator._make_input(scan=scan_code, flags=WinSystem.KEYEVENTF_UNICODE | WinSystem.KEYEVENTF_KEYUP)
        WinSystem.send_input_batch([down, up])
        time.sleep(0.0005)  # 极短延迟防止丢键

    @staticmethod
    def send_vk(vk_code: int):
        down = InputSimulator._make_input(vk=vk_code)
        up = InputSimulator._make_input(vk=vk_code, flags=WinSystem.KEYEVENTF_KEYUP)
        WinSystem.send_input_batch([down, up])
        time.sleep(0.0005)


class PasteWorker(QThread):
    progress_signal = Signal(int)
    status_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, content: str, base_delay: int, random_delay: int):
        super().__init__()
        self.content = content
        self.base_delay = base_delay
        self.random_delay = random_delay
        self.is_running = True

    def stop(self):
        self.is_running = False

    def _smart_sleep(self, delay_ms: float):
        # 混合延迟策略：
        # >15ms 使用系统 sleep 释放 CPU
        # <15ms 使用空转循环以保证高精度
        seconds = delay_ms / 1000.0
        if seconds > 0.015:
            time.sleep(seconds - 0.01)

        target = time.perf_counter() + seconds
        while time.perf_counter() < target:
            pass

    def run(self):
        for i in range(3, 0, -1):
            if not self.is_running: return
            self.status_signal.emit(f"准备中... {i}")
            time.sleep(1)

        self.status_signal.emit("正在输入...")
        total = len(self.content)

        if total == 0:
            self.finished_signal.emit()
            return

        for i, char in enumerate(self.content):
            if not self.is_running:
                self.status_signal.emit("已中断")
                break

            InputSimulator.send_char(char)

            current_delay = self.base_delay
            if self.random_delay > 0:
                current_delay += random.randrange(0, self.random_delay)

            self._smart_sleep(current_delay)

            # 降低 UI 刷新频率，避免卡顿
            if i % 5 == 0 or i == total - 1:
                progress = int(((i + 1) / total) * 100)
                self.progress_signal.emit(progress)

        if self.is_running:
            self.status_signal.emit("任务完成")
            self.progress_signal.emit(100)

        self.finished_signal.emit()