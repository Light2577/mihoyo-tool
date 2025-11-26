import time
import random
import logging
import ctypes
from ctypes import wintypes, Structure, Union, c_ulong, c_uint64, sizeof, POINTER, c_int, c_uint, c_long
from PySide6.QtCore import QThread, Signal, QElapsedTimer

# 指针长度适配
ULONG_PTR = c_uint64 if sizeof(ctypes.c_void_p) == 8 else c_ulong
logger = logging.getLogger(__name__)


class KEYBDINPUT(Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(Structure):
    _fields_ = [("dx", c_long), ("dy", c_long),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUT_UNION(Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(Structure):
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", INPUT_UNION)]


class WinSystem:
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    VK_RETURN = 0x0D
    WM_SYSCOMMAND = 0x0112
    SC_MINIMIZE = 0xF020

    _user32 = ctypes.windll.user32
    _shell32 = ctypes.windll.shell32

    _user32.SendInput.argtypes = [c_uint, POINTER(INPUT), c_int]
    _user32.SendInput.restype = c_uint
    _user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, c_int, c_int, c_int, c_int, c_uint]
    _user32.SetWindowPos.restype = wintypes.BOOL

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
    def set_topmost(hwnd: int, enable: bool):
        """Use Win32 API to toggle topmost without causing Qt window recreate."""
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOACTIVATE = 0x0010
        flags = SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE
        insert_after = wintypes.HWND(-1 if enable else -2)  # HWND_TOPMOST / HWND_NOTOPMOST
        WinSystem._user32.SetWindowPos(wintypes.HWND(hwnd), insert_after, 0, 0, 0, 0, flags)

    @staticmethod
    def send_input_batch(inputs: list):
        n_inputs = len(inputs)
        input_array = (INPUT * n_inputs)(*inputs)
        return WinSystem._user32.SendInput(n_inputs, input_array, sizeof(INPUT))

    @staticmethod
    def minimize_window_anim(hwnd: int):
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
        inp.ki.time = 0
        inp.ki.dwExtraInfo = 0
        return inp

    @staticmethod
    def send_char(char: str):
        if char == '\n':
            return InputSimulator.send_vk(WinSystem.VK_RETURN)

        scan_code = ord(char)
        down = InputSimulator._make_input(scan=scan_code, flags=WinSystem.KEYEVENTF_UNICODE)
        up = InputSimulator._make_input(scan=scan_code, flags=WinSystem.KEYEVENTF_UNICODE | WinSystem.KEYEVENTF_KEYUP)

        sent = WinSystem.send_input_batch([down, up])
        if sent == 0:
            logger.warning("SendInput failed for char=%s", repr(char))
            return False
        time.sleep(0.001)
        return True

    @staticmethod
    def send_vk(vk_code: int):
        down = InputSimulator._make_input(vk=vk_code)
        up = InputSimulator._make_input(vk=vk_code, flags=WinSystem.KEYEVENTF_KEYUP)
        sent = WinSystem.send_input_batch([down, up])
        if sent == 0:
            logger.warning("SendInput failed for vk=%s", hex(vk_code))
            return False
        time.sleep(0.001)
        return True


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
        logger.info("PasteWorker stop requested")
        self.is_running = False

    def run(self):
        logger.info("PasteWorker started: %d chars, base=%dms random=%dms", len(self.content), self.base_delay, self.random_delay)
        stopped = False
        try:
            for i in range(3, 0, -1):
                if not self.is_running:
                    stopped = True
                    break
                self.status_signal.emit(f"status:preparing:{i}")
                self._sleep_cancelable(1000)

            if stopped:
                self.status_signal.emit("status:stopped")
                return

            self.status_signal.emit("status:typing")
            total = len(self.content)

            if total == 0:
                self.status_signal.emit("status:stopped")
                return

            for i, char in enumerate(self.content):
                if not self.is_running:
                    self.status_signal.emit("status:stopped")
                    stopped = True
                    break

                if not InputSimulator.send_char(char):
                    self.status_signal.emit("status:stopped")
                    stopped = True
                    logger.error("SendInput returned 0; stop typing")
                    break

                current_delay_ms = self.base_delay
                if self.random_delay > 0:
                    current_delay_ms += random.randrange(0, self.random_delay)

                if current_delay_ms > 0:
                    self._sleep_cancelable(current_delay_ms)

                # [关键修改] 移除 % 5 限制，每输入一个字符都更新进度，实现极致丝滑
                progress = int(((i + 1) / total) * 100)
                self.progress_signal.emit(progress)

            if not stopped and self.is_running:
                self.status_signal.emit("status:finished")
                self.progress_signal.emit(100)
                logger.info("PasteWorker finished normally")
            else:
                logger.info("PasteWorker interrupted by user")
        finally:
            self.finished_signal.emit()
            logger.info("PasteWorker exit (stopped=%s)", stopped)

    def _sleep_cancelable(self, total_ms: int):
        """可中断睡眠，避免忙等，占用低且响应 stop。"""
        if total_ms <= 0:
            return
        timer = QElapsedTimer()
        timer.start()
        # 最小粒度 5ms，保证停止时 UI 反馈更快
        while self.is_running:
            elapsed = timer.elapsed()
            if elapsed >= total_ms:
                break
            remaining = total_ms - elapsed
            chunk = min(10, max(5, remaining))
            QThread.msleep(int(chunk))
