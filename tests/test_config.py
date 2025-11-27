from config import (
    DEFAULT_BASE_DELAY_MS,
    DEFAULT_RANDOM_DELAY_MS,
    DEFAULT_COUNTDOWN_SEC,
    DEFAULT_START_HOTKEY,
    DEFAULT_CONTINUE_HOTKEY,
    APP_ID,
)


def test_defaults_exist():
    assert DEFAULT_BASE_DELAY_MS >= 0
    assert DEFAULT_RANDOM_DELAY_MS >= 0
    assert DEFAULT_COUNTDOWN_SEC >= 0
    assert isinstance(APP_ID, str)


def test_hotkey_defaults_format():
    for hotkey in (DEFAULT_START_HOTKEY, DEFAULT_CONTINUE_HOTKEY):
        key_name, key_vk, key_mod = hotkey
        assert key_name
        assert isinstance(key_vk, int)
        assert isinstance(key_mod, int)
