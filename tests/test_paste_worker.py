import sys
import time

import pytest
from PySide6.QtCore import QCoreApplication

from core_engine import PasteWorker


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    return app


def test_cancelable_sleep_stops_immediately():
    worker = PasteWorker("", 0, 0)
    worker.is_running = False
    start = time.perf_counter()
    worker._sleep_cancelable(50)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.02


def test_cancelable_sleep_respects_delay():
    worker = PasteWorker("", 0, 0)
    worker.is_running = True
    start = time.perf_counter()
    worker._sleep_cancelable(30)
    elapsed = time.perf_counter() - start
    assert 0.02 <= elapsed <= 0.2
