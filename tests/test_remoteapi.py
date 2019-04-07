'''Far from complete. Created to test the new pass_secinfo feature.'''
import pytest
from unittest.mock import Mock, call

from quickrpc import RemoteAPI, incoming, outgoing
from quickrpc.security import Security

class MyApi(RemoteAPI):
    @incoming
    def icall(self, sender, arg1=None):
        pass
    
class MyTransport:
    def __init__(self):
        self.receive = None
        
    def set_on_received(self, callback):
        self.receive = callback
        
@pytest.fixture
def tt():
    return MyTransport()

@pytest.fixture
def testmsg():
    return b'{"jsonrpc":"2.0", "method": "icall", "params": {"arg1": "val1"} }\0'

@pytest.fixture
def stestmsg():
    return (
        b'{"jsonrpc":"2.0", "method": "rpc.secinfo", "params": {"user": "b"} }\0'
        b'{"jsonrpc":"2.0", "method": "icall", "params": {"arg1": "val1"} }\0'
    )

def test_incoming(tt, testmsg, stestmsg):
    m = Mock()
    a = MyApi(codec='jrpc', transport=tt)
    a.icall.connect(m.icall)
    tt.receive('sender1', testmsg)
    
    a.security = Security.fromstring('blindly_believe_everything')
    a.security.user = 'a'
    tt.receive('sender1', stestmsg)
    
    a.icall.pass_secinfo(True)
    tt.receive('sender1', stestmsg)
    
    assert m.mock_calls == [
        call.icall('sender1', arg1='val1'),
        call.icall('sender1', arg1='val1'),
        call.icall('sender1', arg1='val1', secinfo={'user':'b'}),
        ]
    
    