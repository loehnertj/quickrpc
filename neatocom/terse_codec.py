import logging
L = lambda: logging.getLogger(__name__)
import base64
import binascii
import re

from .concepts import Codec, Message, DecodeError

class AttrDict(dict):
    __getattr__ = dict.__getitem__

class TerseCodec(Codec):
    '''Terse codec: encodes with minimum puncutation.

    encodes to: method param1:1, param2:"foo"<NL>
    values:
        * int/float: 1.0
        * bytes: '(base64-string'
        * str: "python-escaped str"
        * list: [val1 val2 val3 ...]
        * dict: {key1:val1 key2:val2 ...}

    * Commands must be terminated by newline. 
    * Newlines, double quote and backslash in strings are escaped as usual
    * Allowed dtypes: int, float, str, bytes (content base64-encoded), list, dict
    '''
    def encode(self, method, kwargs):
        '''encodes the call, including trailing newline'''
        return _encode_method(method, kwargs)

    def decode(self, data):
        lines = data.split(b'\n')
        leftover = lines.pop()
        messages = []
        for line in lines:
            try:
                method, params, idx = _decode(line + b'\n')
            except DecodeError as e:
                L().warning(e)
                continue
            else:
                if idx <= len(line):
                    L().warning('_decode left something over: %r'%line[idx:])
                messages.append(Message(method, params))
        if leftover:
            L().debug('leftover data: %r'%(leftover[:50]+b" ... "+leftover[-50:]))
        return messages, leftover

def _encode_method(method, params):
    return b'%s %s\n'%(
        method.encode('utf8'),
        b' '.join(
            name.encode('utf8') + b':' + _encode_value(value)
            for name, value in params.items()
        )
    )

def _encode_value(value):
    if isinstance(value, (int, float)):
        return b'%g'%value
    elif isinstance(value, str):
        value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
        return ('"'+value+'"').encode('utf8')
    elif isinstance(value, bytes):
        return b"'" + base64.b64encode(value) + b"'"
    elif isinstance(value, (list, tuple, set)):
        return _encode_iterable(value)
    elif isinstance(value, dict):
        return _encode_dict(value)
    
def _encode_iterable(l):
    return b'[' + b' '.join(_encode_value(value) for value in l) + b']'

def _encode_dict(d):
    return b'{' + (
        b' '.join(
            key.encode('utf8') + b':' + _encode_value(value)
            for key, value in d.items()
        )
    ) + b'}'
        
def _decode(data):
    '''returns method, params, idx OR raises DecodeError.
    identifier params <NL>
    '''
    idx = 0
    params = {}
    while data[idx:idx+1] == b'\n':
        idx += 1
    if b'\n' not in data:
        raise DecodeError('Incomplete data')
    
    method, idx = _decode_identifier(data, idx)
    idx = _skipws(data, idx)
    params, idx = _decode_pairs(data, idx)
    idx = _expect(data, idx, b'\n')
    return method, params, idx

def _decode_pairs(data, idx, assignchar = b':'):
    pairs = {}
    while True:
        idx = _skipws(data, idx)
        # XXX: sentinel chars from other grammar terms!
        if data[idx:idx+1] in b'}\n':
            return pairs, idx
        key, value, idx = _decode_pair(data, idx, assignchar)
        pairs[key] = value

def _decode_pair(data, idx, assignchar):
    key, idx = _decode_identifier(data, idx)
    # this may throw DecodeError
    idx = _expect(data, idx, assignchar)
    value, idx = _decode_value(data, idx)
    return key, value, idx

def _decode_value(data, idx):
    idx = _skipws(data, idx)
    ch = data[idx:idx+1]
    if ch in b'-.0123456789':
        return _decode_float(data, idx)
    func = {
        b'[': _decode_list,
        b'{': _decode_dict,
        b'"': _decode_str,
        b"'": _decode_bytes,
    }.get(ch, None)
    if func is None:
        raise DecodeError('Unsupported Value at position %s'%idx)
    return func(data, idx)

def _decode_float(data, idx):
    m = re.match(br'-?\d*(\.\d*)?([eE][+-?]\d+)?', data[idx:])
    if not m:
        raise DecodeError('Expected number at position %d'%idx)
    return float(m.group()), idx+m.end()

def _decode_bytes(data, idx):
    return _decode_bytes_or_string(data, idx, 'b')

def _decode_str(data, idx):
    return _decode_bytes_or_string(data, idx, 's')

def _decode_bytes_or_string(data, idx, type='b'):
    qc = b"'" if type=='b' else b'"'
    idx = _expect(data, idx, qc)
    m = re.match(br'(\\$|[^$])*[$]'.replace(b'$', qc), data[idx:])
    if not m.group():
        raise DecodeError('Expected quoted value at position %d'%idx)
    if type == 'b':
        try:
            value = base64.b64decode(m.group()[:-1])
        except binascii.Error:
            raise DecodeError('invalid base64 string')
    elif type == 's':
        value = m.group()[:-1].decode('utf8').replace('\\n', '\n').replace('\\"', '\"').replace('\\\\', '\\')
    return value, idx+m.end()

def _decode_dict(data, idx):
    idx = _expect(data, idx, b'{')
    contents, idx = _decode_pairs(data, idx, assignchar=b':')
    idx = _expect(data, idx, b'}')
    return contents, idx

def _decode_list(data, idx):
    idx = _expect(data, idx, b'[')
    l = []
    while True:
        idx = _skipws(data, idx)
        if data[idx:idx+1] == b']':
            break
        value, idx = _decode_value(data, idx)
        l.append(value)
    idx = _expect(data, idx, b']')
    return l, idx

def _decode_identifier(data, idx):
    m = re.match(br'\s*[a-zA-Z_][a-zA-Z_0-9]*', data[idx:])
    if not m:
        raise DecodeError('Expected identifier at position %d'%idx)
    return m.group().strip().decode('utf8'), idx + m.end()

def _skipws(data, idx):
    while data[idx:idx+1] == b' ':
        idx += 1
    return idx
    
def _expect(data, idx, chars):
    while data[idx:idx+1] == b' ':
        idx += 1
    if data[idx:idx+len(chars)] != chars:
        raise DecodeError('Expected characters "%s" at position %d'%(chars.decode('ascii'), idx))
    return idx + len(chars)
    

def test():
    tc = TerseCodec()
    data=tc.encode(method="my_method", kwargs={
        'int': 1,
        'float': 1.1,
        'str': "abc",
        'str_with_nl': 'foo\nbar',
        'list': [1, 2, 3],
        'dict': {'a': 1, 'b': 2},
        'nested_dict': {'a': {'b': 1}},
        'bytes': b'0123456789',
    })
    print(repr(data))
    print()
    msgs, rest = tc.decode(data)
    for m in msgs:
        print(m.method, m.kwargs)
    print("rest: %r"%rest)
    
if __name__=='__main__':
    test()
