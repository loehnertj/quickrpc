import pytest
import threading
from unittest.mock import Mock, call
from quickrpc.promise import Promise, PromiseDoneError, PromiseTimeoutError, PromiseDeadlockError

class MyVal: pass

class MyError(Exception): pass

@pytest.fixture
def p():
    return Promise()

@pytest.fixture
def mock():
    return Mock()


def test_promise_with_result(p):
    p.set_result(MyVal)
    assert p.result() is MyVal
    
def test_promise_with_exception(p):
    p = Promise()
    p.set_exception(MyError())
    with pytest.raises(MyError):
        p.result()

def test_promise_timeout():
    p = Promise(setter_thread=threading.Thread())
    with pytest.raises(PromiseTimeoutError):
        p.result(timeout=0.1)

def test_promise_fulfilled_twice(p):
    with pytest.raises(PromiseDoneError):
        p.set_result(1)
        p.set_result(2)

def test_promise_deadlock_protection(p):
    with pytest.raises(PromiseDeadlockError):
        p.result(timeout=0.1)

def test_promise_callback_added_early(p, mock):
    p.then(mock.foo)
    p.set_result(1)
    assert mock.mock_calls == [call.foo(1)]

def test_promise_callback_added_late(p, mock):
    p.set_result(1)
    p.then(mock.foo)
    assert mock.mock_calls == [call.foo(1)]

def test_promise_callback_with_error(p):
    mock = Mock(side_effect=Exception())
    p.then(mock.foo)
    # exception should be swallowed
    p.set_result(1)

def test_promise_errback_shortcircuit(p, mock):
    e = Exception()
    p.then(mock.foo) # also used as errback
    p.set_exception(e)
    assert mock.mock_calls == [call.foo(e)]

