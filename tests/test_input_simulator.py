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
