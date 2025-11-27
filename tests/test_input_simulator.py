from core_engine import InputSimulator, WinSystem


def test_send_char_failure(monkeypatch):
    def fake_send(inputs):
        return 0

    monkeypatch.setattr(WinSystem, "send_input_batch", staticmethod(fake_send))
    assert InputSimulator.send_char("a") is False


def test_send_vk_success(monkeypatch):
    def fake_send(inputs):
        return len(inputs)

    monkeypatch.setattr(WinSystem, "send_input_batch", staticmethod(fake_send))
    assert InputSimulator.send_vk(0x41) is True


def test_send_char_emoji(monkeypatch):
    captured = {}

    def fake_send(inputs):
        captured["len"] = len(inputs)
        return len(inputs)

    monkeypatch.setattr(WinSystem, "send_input_batch", staticmethod(fake_send))
    assert InputSimulator.send_char("😊") is True
    # surrogate pair -> 4 INPUTs (down/down + up/up)
    assert captured.get("len") == 4


def test_send_char_zwj_sequence(monkeypatch):
    captured = {}

    def fake_send(inputs):
        captured["len"] = len(inputs)
        return len(inputs)

    monkeypatch.setattr(WinSystem, "send_input_batch", staticmethod(fake_send))
    family = "👨‍👩‍👧‍👦"
    assert InputSimulator.send_char(family) is True
    # 4 emojis (2 units each) + 3 ZWJ = 11 code units -> 22 INPUTs
    assert captured.get("len") == 22
