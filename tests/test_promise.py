import pytest
from quickrpc.promise import Promise, PromiseDoneError, PromiseTimeoutError

class MyVal: pass

class MyError(Exception): pass

def test_promise_with_result():
    p = Promise()
    p.set_result(MyVal)
    assert p.result() is MyVal
    
def test_promise_with_exception():
    p = Promise()
    p.set_exception(MyError())
    with pytest.raises(MyError):
        p.result()

def test_promise_timeout():
    p = Promise()
    with pytest.raises(PromiseTimeoutError):
        p.result(timeout=0.1)

def test_promise_fulfilled_twice():
    p = Promise()
    with pytest.raises(PromiseDoneError):
        p.set_result(1)
        p.set_result(2)
