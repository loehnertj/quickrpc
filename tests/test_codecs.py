import pytest
from quickrpc.codecs import JsonRpcCodec, TerseCodec, DecodeError

_testdata=dict(method="my_method", kwargs={
    'int': 1,
    'float': 1.1,
    'str': "abc",
    'str_with_nl': 'foo\nbar',
    'list': [1, 2, 3],
    'dict': {'a': 1, 'b': 2},
    'bytes': b'0123456789',
})

def sec_out(payload):
    return {'user': 'john'}, b'123' + payload

def sec_in(payload, secinfo):
    assert secinfo['user'] == 'john'
    assert payload.startswith(b'123')
    return payload[3:]


def test_json_codec():
    jc = JsonRpcCodec()
    data=jc.encode(**_testdata)
    # TODO: make _testdata an OrderedDict and assert the exact data here
    msgs, rest = jc.decode(data)
    assert len(msgs) == 1
    assert msgs[0].method == _testdata['method']
    assert msgs[0].kwargs == _testdata['kwargs']
    assert rest == b''
    
def test_json_secure_codec():
    jc = JsonRpcCodec()
    data = jc.encode(method="test", kwargs={}, sec_out=sec_out)
    parts = data.split(b'\0')
    assert len(parts) == 3
    # incomplete
    msgs, rest = jc.decode(parts[0], sec_in=sec_in)
    assert msgs == []
    assert rest == parts[0]
    # complete header, no data
    msgs, rest = jc.decode(parts[0]+b'\0', sec_in=sec_in)
    assert msgs == []
    assert rest == parts[0] + b'\0'
    
    # no terminator = still incomplete
    msgs, rest = jc.decode(parts[0]+b'\0'+parts[1], sec_in=sec_in)
    assert msgs == []
    assert rest == parts[0] + b'\0' + parts[1]
    
    # no sec_in given
    msgs, rest = jc.decode(parts[0]+b'\0'+parts[1]+b'\0')
    assert rest == b''
    assert isinstance(msgs[0], DecodeError)
    # complete msg
    msgs, rest = jc.decode(parts[0]+b'\0'+parts[1]+b'\0', sec_in=sec_in)
    assert len(msgs) == 1
    assert rest == b''
    msg = msgs[0]
    assert msg.method == 'test'
    assert msg.kwargs == {}
    assert msg.secinfo == {'user':'john'}
    
    # test mix of unsecure and secure msg
    # test code adds 3 chars before payload.
    msgs, rest = jc.decode(b'\0'.join([
        parts[1][3:],
        parts[0],
        parts[1],
        parts[1][3:],
        b''
    ]), sec_in=sec_in)
    assert rest == b''
    assert len(msgs) == 3
    assert [msg.method for msg in msgs] == ['test']*3
    assert msgs[0].secinfo == {}
    assert msgs[1].secinfo == {'user':'john'}
    assert msgs[2].secinfo == {}
    

def test_terse_codec():
    jc = TerseCodec()
    data=jc.encode(**_testdata)
    # TODO: make _testdata an OrderedDict and assert the exact data here
    msgs, rest = jc.decode(data)
    assert len(msgs) == 1
    assert msgs[0].method == _testdata['method']
    assert msgs[0].kwargs == _testdata['kwargs']
    assert rest == b''
