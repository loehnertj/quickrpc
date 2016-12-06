# coding: utf8
'''
Codecs convert message structures into bytes and vice versa.

Classes defined here:
 * Codec: base class
 * Message, DecodeError
'''

__all__ = [
    'Codec',
    'DecodeError',
    'Message',
]

import logging
import json 
import base64
import binascii
import re
L = lambda: logging.getLogger(__name__)


class DecodeError(Exception): pass


class Message(object):
    def __init__(self, method, kwargs):
        self.method = method
        self.kwargs = kwargs


class AttrDict(dict):
    __getattr__ = dict.__getitem__


class Codec(object):
    '''Responsible for serializing and deserializing method calls.
    
    Subclass and override `encode` and `decode`.
    '''
    def decode(self, data):
        '''decode data to method call with kwargs.
        
        Return:
        [messages], remainder
        where [messages] is the list of decoded messages and remainder
        is leftover data (which may contain the beginning of another message).
        
        If a message cannot be decoded properly, an exception is added in the message list.
        Decode should never *raise* an error, because in this case the remaining data
        cannot be retrieved.
        
        Each message has a .method attribute (string) and a .kwargs attribute (dict),
        meaning exactly what they look like.
        '''
        pass
    
    def encode(self, method, kwargs=None):
        '''encode a method call with given kwargs.'''
        pass
    

class MyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return {'__bytes': base64.b64encode(obj).decode('utf8')}
        return json.JSONEncoder.default(self, obj)
    
class MyJsonDecoder(json.JSONDecoder):
    pass


class JsonCodec(Codec):
    '''Json codec: convert to json
    
    bytes values are converted into a base64-encoded string and prepended by "b".
    str values are prepended by "s".
    method name is added as dict param __method.
    '''
    def encode(self, method, kwargs):
        data = kwargs.copy()
        data['__method'] = method
        data = json.dumps(data, cls=MyJsonEncoder).encode('utf8')
        return data + b'\n'

    def decode(self, data):
        try:
            data = data.decode('utf8')
        except UnicodeDecodeError as e:
            return [e], b''
        messages = []
        data_before_msg = []
        while data!='':
            data_before_msg.append(data)
            message, data = self._decode_first(data)
            messages.append(message)
            while data.startswith('\n'):
                data = data[1:]
        # rollback trailing exceptions (might be start of incomplete data)
        while messages and isinstance(messages[-1], Exception):
            data = data_before_msg.pop()
            messages.pop()
        return messages, data.encode('utf8')
    
    def _decode_first(self, data):
        def obj_hook(val):
            if '__bytes' in val:
                return base64.b64decode(val['__bytes'].encode('utf8'))
            return AttrDict(val)
        decoder = MyJsonDecoder(object_hook=obj_hook)
        try:
            jdict, idx = decoder.raw_decode(data)
        except json.JSONDecodeError as e:
            # skip forward to the next opening brace.
            # add a "sentinel" brace to jump to the end in case of no brace.
            idx = (data+'{').find('{', 1)
            baddata, data = data[:idx], data[idx:]
            return DecodeError('Not a valid json string: "%s"'%baddata), data
        if not isinstance(jdict, dict):
            return DecodeError('json toplevel object is not a dict'), data[idx:]
        try:
            method = jdict['__method']
        except KeyError:
            return DecodeError('json dict is missing the __method key'), data[idx:]
        del jdict['__method']
        if not isinstance(method, str):
            return DecodeError('given __method is not a string'), data[idx:]
        return Message(method, jdict), data[idx:]
        
        
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
            str(key).encode('utf8') + b':' + _encode_value(value)
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
    pairs = AttrDict()
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
        return _decode_num(data, idx)
    func = {
        b'[': _decode_list,
        b'{': _decode_dict,
        b'"': _decode_str,
        b"'": _decode_bytes,
    }.get(ch, None)
    if func is None:
        raise DecodeError('Unsupported Value at position %s'%idx)
    return func(data, idx)

def _decode_num(data, idx):
    m = re.match(br'-?\d*(\.\d*)?([eE][+-?]\d+)?', data[idx:])
    if not m:
        raise DecodeError('Expected number at position %d'%idx)
    if b'.' not in m.group() and b'e' not in m.group().lower():
        return int(m.group()), idx+m.end()
    return float(m.group()), idx+m.end()

def _decode_bytes(data, idx):
    try:
        end = data.index(b"'", idx+1)
    except ValueError:
        raise DecodeError('unterminated bytes value at %d'%idx)
    try:
        value = base64.b64decode(data[idx+1:end])
    except binascii.Error:
        raise DecodeError('invalid base64 string')
    return value, end+1

def _decode_str(data, idx):
    qc = b'"'
    idx = _expect(data, idx, qc)
    m = re.match(br'(\\$|[^$])*[$]'.replace(b'$', qc), data[idx:])
    if not m.group():
        raise DecodeError('Expected quoted value at position %d'%idx)
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
    m = re.match(br'\s*[0-9a-zA-Z_][a-zA-Z_0-9]*', data[idx:])
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