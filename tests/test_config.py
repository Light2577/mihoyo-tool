from config import (
    DEFAULT_BASE_DELAY_MS,
    DEFAULT_RANDOM_DELAY_MS,
    DEFAULT_START_HOTKEY,
    DEFAULT_STOP_HOTKEY,
    APP_ID,
)


def test_defaults_exist():
    assert DEFAULT_BASE_DELAY_MS >= 0
    assert DEFAULT_RANDOM_DELAY_MS >= 0
    assert isinstance(APP_ID, str)


def test_hotkey_defaults_format():
    key_name, key_vk = DEFAULT_START_HOTKEY
    assert key_name
    assert isinstance(key_vk, int)

    stop_name, stop_vk = DEFAULT_STOP_HOTKEY
    assert stop_name
    assert isinstance(stop_vk, int)
