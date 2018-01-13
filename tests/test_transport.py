import pytest
from time import time
from unittest.mock import Mock, call

from quickrpc.transports import Transport, MuxTransport, RestartingTransport, TransportError


class MyVal: pass

class MyTransportError(Exception): pass

class MyTransport(Transport):
    def __init__(self):
        Transport.__init__(self)
        self.mock = Mock()
        
    def open(self):
        self.mock.open()
        
    def run(self):
        self.mock.run()
        while self.running:
            time.sleep(0.01)
        self.mock.close()
        
    @property
    def mock_calls(self):
        return self.mock.mock_calls
        
class MyFailingTransport(MyTransport):
    def open(self):
        self.mock.open()
        raise MyTransportError()
    
@pytest.fixture
def my_tr(): return MyTransport()

@pytest.fixture
def my_ftr(): return MyFailingTransport()

@pytest.fixture
def mux_tr(): return MuxTransport()


def test_succeeding_start(my_tr):
    my_tr.start()
    my_tr.stop()
    assert my_tr.mock_calls == [call.open(), call.run(), call.close()]

def test_failing_start(my_ftr):
    with pytest.raises(MyTransportError):
        my_ftr.start()
    assert my_ftr.mock_calls == [call.open()]

def test_receive(my_tr):
    receiver = Mock()
    my_tr.set_on_received(receiver.r)
    my_tr.received('sender', MyVal)
    assert receiver.mock_calls == [call.r('sender', MyVal)]
     
def test_mux_add_before_start(mux_tr, my_tr):
    mux_tr += my_tr()
    mux_tr.start()
    mux_tr.stop()
    assert my_tr.mock_calls == [call.open(), call.run(), call.close()]
    
def test_mux_add_before_start(mux_tr, my_tr):
    mux_tr += my_tr
    mux_tr.start()
    mux_tr.stop()
    assert my_tr.mock_calls == [call.open(), call.run(), call.close()]
    
def test_mux_add_after_start(mux_tr, my_tr):
    mux_tr.start()
    mux_tr += my_tr
    mux_tr -= my_tr
    mux_tr.stop()
    assert my_tr.mock_calls == [call.open(), call.run(), call.close()]
    
def test_mux_receive(mux_tr, my_tr):
    my_recv = Mock()
    mux_tr.set_on_received(my_recv.r)
    mux_tr += my_tr
    mux_tr.start()
    my_tr.received('sender', b'data')
    mux_tr.stop()
    assert my_recv.mock_calls == [call.r('sender', b'data')]
    
def test_mux_with_failure(mux_tr, my_tr, my_ftr):
    mux_tr += my_ftr
    mux_tr += my_tr
    # notice that the mux_tr raises a TransportError wrapping the subtransport's
    # exceptions (in this case, a single MyTransportError).
    with pytest.raises(TransportError) as excinfo:
        mux_tr.start()
    # my_tr starts normally, then is stopped when the other one fails.
    assert my_tr.mock_calls == [call.open(), call.run(), call.close()]
    assert my_ftr.mock_calls == [call.open()]
    assert len(excinfo.value.exceptions) == 1
    assert isinstance(excinfo.value.exceptions[0], MyTransportError)
    
