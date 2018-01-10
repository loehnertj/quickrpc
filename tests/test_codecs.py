
from quickrpc.codecs import JsonRpcCodec, TerseCodec

_testdata=dict(method="my_method", kwargs={
    'int': 1,
    'float': 1.1,
    'str': "abc",
    'str_with_nl': 'foo\nbar',
    'list': [1, 2, 3],
    'dict': {'a': 1, 'b': 2},
    'bytes': b'0123456789',
})

def test_json_codec():
    jc = JsonRpcCodec()
    data=jc.encode(**_testdata)
    # TODO: make _testdata an OrderedDict and assert the exact data here
    msgs, rest = jc.decode(data)
    assert len(msgs) == 1
    assert msgs[0].method == _testdata['method']
    assert msgs[0].kwargs == _testdata['kwargs']
    assert rest == b''

def test_terse_codec():
    jc = TerseCodec()
    data=jc.encode(**_testdata)
    # TODO: make _testdata an OrderedDict and assert the exact data here
    msgs, rest = jc.decode(data)
    assert len(msgs) == 1
    assert msgs[0].method == _testdata['method']
    assert msgs[0].kwargs == _testdata['kwargs']
    assert rest == b''
