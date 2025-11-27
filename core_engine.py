import time
import random
import logging
import ctypes
import unicodedata
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
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
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
    def register_hotkey(hwnd: int, hotkey_id: int, vk: int, modifiers: int = 0) -> bool:
        """Register global hotkey with optional modifier flags."""
        return WinSystem._user32.RegisterHotKey(wintypes.HWND(hwnd), hotkey_id, modifiers, vk)

    @staticmethod
    def unregister_hotkey(hwnd: int, hotkey_id: int) -> bool:
        return WinSystem._user32.UnregisterHotKey(wintypes.HWND(hwnd), hotkey_id)


class InputSimulator:
    @staticmethod
    def _utf16_units(text: str) -> list[int]:
        """Return UTF-16 code units for given text (handles surrogate pairs)."""
        units: list[int] = []
        for ch in text:
            codepoint = ord(ch)
            if codepoint <= 0xFFFF:
                units.append(codepoint)
            else:
                cp = codepoint - 0x10000
                units.extend([0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF)])
        return units

    @staticmethod
    def _is_regional_indicator(cp: int) -> bool:
        return 0x1F1E6 <= cp <= 0x1F1FF

    @staticmethod
    def iter_graphemes(text: str):
        """Very small grapheme splitter to keep ZWJ/VS/RI sequences together."""
        chars = list(text or "")
        i = 0
        while i < len(chars):
            cluster = [chars[i]]
            i += 1
            while i < len(chars):
                c = chars[i]
                cp = ord(c)
                prev_cp = ord(cluster[-1])
                if c == "\u200d":  # ZWJ stays in cluster
                    cluster.append(c)
                    i += 1
                    continue
                if prev_cp == 0x200D:  # char after ZWJ joins cluster
                    cluster.append(c)
                    i += 1
                    continue
                if cp in (0xFE0E, 0xFE0F) or unicodedata.combining(c):
                    cluster.append(c)
                    i += 1
                    continue
                if InputSimulator._is_regional_indicator(prev_cp) and InputSimulator._is_regional_indicator(cp):
                    cluster.append(c)
                    i += 1
                    continue
                break
            yield "".join(cluster)

    @staticmethod
    def count_graphemes(text: str) -> int:
        return sum(1 for _ in InputSimulator.iter_graphemes(text))

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
        """Send a character or multi-codepoint grapheme (emoji/ZWJ supported)."""
        if char == '\n':
            return InputSimulator.send_vk(WinSystem.VK_RETURN)

        units = InputSimulator._utf16_units(char)
        inputs = []
        for unit in units:
            inputs.append(InputSimulator._make_input(scan=unit, flags=WinSystem.KEYEVENTF_UNICODE))
        for unit in units:
            inputs.append(InputSimulator._make_input(scan=unit, flags=WinSystem.KEYEVENTF_UNICODE | WinSystem.KEYEVENTF_KEYUP))

        sent = WinSystem.send_input_batch(inputs)
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

    def __init__(self, content: str, base_delay: int, random_delay: int, start_offset: int = 0,
                 countdown_seconds: int = 3):
        super().__init__()
        self.content = content or ""
        self.graphemes = list(InputSimulator.iter_graphemes(self.content))
        self.base_delay = base_delay
        self.random_delay = random_delay
        self.total_graphemes = len(self.graphemes)
        self.start_offset = max(0, min(start_offset, self.total_graphemes))
        self.countdown_seconds = max(0, countdown_seconds)
        self.is_running = True
        self.completed = False
        self.next_offset = self.start_offset

    def stop(self):
        logger.info("PasteWorker stop requested")
        self.is_running = False

    def run(self):
        total = self.total_graphemes
        self.next_offset = self.start_offset
        logger.info(
            "PasteWorker started: %d chars, base=%dms random=%dms offset=%d wait=%ds",
            len(self.content),
            self.base_delay,
            self.random_delay,
            self.start_offset,
            self.countdown_seconds,
        )

        stopped = False
        try:
            # 倒计时
            for i in range(self.countdown_seconds, 0, -1):
                if not self.is_running:
                    stopped = True
                    break
                self.status_signal.emit(f"status:preparing:{i}")
                self._sleep_cancelable(1000)

            if stopped:
                self.status_signal.emit("status:stopped")
                return

            if total == 0 or self.start_offset >= total:
                self.status_signal.emit("status:stopped")
                self.progress_signal.emit(0)
                return

            self.status_signal.emit("status:typing")
            for idx in range(self.start_offset, total):
                if not self.is_running:
                    stopped = True
                    break

                char = self.graphemes[idx]
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

                self.next_offset = idx + 1
                progress = int(((idx + 1) / total) * 100)
                self.progress_signal.emit(progress)

            if not stopped and self.is_running:
                self.completed = True
                self.next_offset = total
                self.status_signal.emit("status:finished")
                self.progress_signal.emit(100)
                logger.info("PasteWorker finished normally")
            else:
                self.completed = False
                logger.info("PasteWorker interrupted by user at offset=%d", self.next_offset)
                self.status_signal.emit("status:stopped")
        finally:
            self.finished_signal.emit()
            logger.info("PasteWorker exit (stopped=%s, completed=%s, next_offset=%d)", stopped, self.completed, self.next_offset)

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
