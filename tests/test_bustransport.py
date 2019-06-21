import pytest
from unittest.mock import Mock, call
import time

from quickrpc import transport, bus_transport

def test_bustransport_names():
    t1 = transport('internal')
    t2 = transport('internal:internal')
    t3 = transport('internal:bus2:foo')
    assert t1.bus == t2.bus
    assert t1.bus.name == 'internal'
    assert t3.bus.name == 'bus2'
    assert t1.name == 'internal.0'
    assert t2.name == 'internal.1'
    assert t3.name == 'foo'
    # reset global state
    bus_transport.Bus.get_instance('internal').kill()
    bus_transport.Bus.get_instance('bus2').kill()

def test_bustransport_distribute():
    receiver = Mock()
    receiver.r1 = Mock(return_value=b'')
    receiver.r2 = Mock(return_value=b'')

    t1 = transport('internal')
    t2 = transport('internal')
    t1.set_on_received(receiver.r1)
    t2.set_on_received(receiver.r2)
    with pytest.raises(IOError):
        t1.send(b'something')
    t1.start()
    t1.send(b'msg1')

    t2.start()
    t1.send(b'msg2')

    # next message goes to t1 and t2. t1 might process it before t2 processed msg2,
    # so wait a small moment.
    time.sleep(0.1)
    # rapid messages processed in order
    t1.send(b'msg3', receivers=['internal.0', 'internal.1'])
    t1.send(b'msg4')
    t1.send(b'msg5')
    # allow processing of queued messages before stopping
    time.sleep(0.1)
    t2.stop()

    t1.send(b'msg6')

    # send to unregistered peer
    with pytest.raises(IOError):
        t1.send(b'msg7', receivers=['internal.1'])

    t1.stop()
    assert receiver.mock_calls == [
        # first message went nowhere
        call.r2('internal.0', b'msg2'),
        call.r1('internal.0', b'msg3'),
        call.r2('internal.0', b'msg3'),
        call.r2('internal.0', b'msg4'),
        call.r2('internal.0', b'msg5'),
        # msg6 messsage went nowhere
    ]

def test_bustransport_kill():
    t1 = transport('internal:bus')
    t1.start()
    assert t1.running == True
    bus_transport.Bus.get_instance('bus').kill()
    assert t1.running == False
    assert t1.bus is None