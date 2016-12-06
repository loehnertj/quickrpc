from neatocom.codecs import JsonCodec, TerseCodec

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
    jc = JsonCodec()
    data=jc.encode(**_testdata)
    print(repr(data))
    print()
    msgs, rest = jc.decode(data)
    for m in msgs:
        print(m.method, m.kwargs)
    print("rest: %s"%rest)

def test_terse_codec():
    jc = TerseCodec()
    data=jc.encode(**_testdata)
    print(repr(data))
    print()
    msgs, rest = jc.decode(data)
    for m in msgs:
        print(m.method, m.kwargs)
    print("rest: %s"%rest)

if __name__=='__main__':
    test_json_codec()
    test_terse_codec()