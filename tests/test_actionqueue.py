import pytest
import threading
import time
from unittest.mock import Mock, call
from quickrpc.action_queue import ActionQueue

from quickrpc.promise import Promise

@pytest.fixture
def aq():
    return ActionQueue()

def action():
    time.sleep(0.1)

def test_aq_basic(aq):
    assert not aq._running.is_set()
    aq.put(action)
    assert aq._running.is_set()
    assert threading.active_count() == 2
    time.sleep(0.2)
    assert not aq._running.is_set()
    assert threading.active_count() == 1

def test_aq_two_items(aq):
    aq.put(action)
    aq.put(action)
    time.sleep(0.15)
    assert aq._running.is_set()
    time.sleep(0.1)
    assert not aq._running.is_set()
