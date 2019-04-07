import logging
import base64
import binascii
import re
from .codecs import Codec, Message, Reply, ErrorReply, DecodeError, EncodeError, RemoteError, _fmt_exc
L = lambda: logging.getLogger(__name__)

 
class TerseCodec(Codec):
    '''Terse codec: encodes with minimum puncutation.

    encodes to: method[id] param1:1, param2:"foo"<NL>
    values:
    
        * int/float: 1.0
        * bytes: '(base64-string'
        * str: "python-escaped str"
        * list: [val1 val2 val3 ...]
        * dict: {key1:val1 key2:val2 ...}
        
    Reply is encoded to: [id]:value
    Error is encoded to: [id]! message:"string" details:"string"

    * Commands must be terminated by newline. 
    * Newlines, double quote and backslash in strings are escaped as usual
    * Allowed dtypes: int, float, str, bytes (content base64-encoded), list, dict
    '''

    shorthand = 'terse'
    @classmethod
    def fromstring(cls, expression):
        '''terse:'''
        return cls()

    def encode(self, method, kwargs, id=0, sec_out=None):
        '''encodes the call, including trailing newline'''
        if sec_out: raise EncodeError('Security is not supported by TerseCodec.')
        return _encode_method(method, id, kwargs)
    
    def encode_reply(self, in_reply_to, result, sec_out=None):
        if sec_out: raise EncodeError('Security is not supported by TerseCodec.')
        return b'[%d]:%s'%(in_reply_to.id, _encode_value(result))
    
    def encode_error(self, in_reply_to, exception, errorcode=0, sec_out=None):
        if sec_out: raise EncodeError('Security is not supported by TerseCodec.')
        text = _encode_value(str(exception))
        details = _encode_value(_fmt_exc(exception))
        return b'[%d]! message:%s details:%s'%(in_reply_to.id, text, details)

    def decode(self, data, sec_in=None):
        if sec_in: raise DecodeError('Security is not supported by TerseCodec')
        lines = data.split(b'\n')
        leftover = lines.pop()
        messages = []
        for line in lines:
            try:
                obj, idx = _decode(line + b'\n')
            except DecodeError as e:
                L().warning(e)
                continue
            else:
                if idx <= len(line):
                    L().warning('_decode left something over: %r'%line[idx:])
                messages.append(obj)
        if leftover:
            L().debug('leftover data: %r'%(leftover[:50]+b" ... "+leftover[-50:]))
        return messages, leftover

def _encode_method(method, id, params):
    return b'%s%s %s\n'%(
        method.encode('utf8'),
        b'/%d'%id if id>0 else b'',
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
    '''returns object, idx OR raises DecodeError.
    identifier params <NL>
    '''
    idx = 0
    params = {}
    # skip empty telegrams
    while data[idx:idx+1] in b'\r\n':
        idx += 1
    if b'\n' not in data:
        raise DecodeError('Incomplete data')
    
    if data[idx] == b'[':
        idnum, idx = _decode_idnum(data, idx)
        if data[idx] == b':':
            return _decode_reply(data, idx+1, id=idnum)
        elif data[idx] == b'!':
            return _decode_error(data, idx+1, id=idnum)
        else:
            raise DecodeError('Received invalid reply')
    
    return _decode_message(data, idx)
    
def _decode_message(data, idx):
    method, idx = _decode_identifier(data, idx)
    if data[idx] == b'[':
        id = _decode_idnum(data, idx)
    else:
        id = 0
    idx = _skipws(data, idx)
    params, idx = _decode_pairs(data, idx)
    idx = _expect(data, idx, b'\n')
    return Message(method, params, id=id), idx

def _decode_reply(data, idx, id):
    idx = _skipws(data, idx)
    val, idx = _decode_value(data, idx)
    idx = _expect(data, idx, b'\n')
    return Reply(val, id), idx

def _decode_error(data, idx, id):
    idx = _skipws(data, idx)
    data, idx = _decode_pairs(data, idx)
    idx = _expect(data, idx, b'\n')
    msg = data.get('message', '')
    details = data.get('details', '')
    return ErrorReply(message, details), idx

def _decode_pairs(data, idx, assignchar = b':'):
    pairs = dict()
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

_num_re = re.compile(br'-?\d*(\.\d*)?([eE][+-?]\d+)?')
def _decode_num(data, idx):
    m = _num_re.match(data, idx)
    if not m:
        raise DecodeError('Expected number at position %d'%idx)
    if b'.' not in m.group() and b'e' not in m.group().lower():
        return int(m.group()), m.end()
    return float(m.group()), m.end()

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

_str_re = re.compile(br'(\\"|[^"])*["]')
def _decode_str(data, idx):
    idx = _expect(data, idx, b'"')
    m = _str_re.match(data, idx)
    if not m.group():
        raise DecodeError('Expected quoted value at position %d'%idx)
    value = m.group()[:-1].decode('utf8').replace('\\n', '\n').replace('\\"', '\"').replace('\\\\', '\\')
    return value, m.end()

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

_id_re = re.compile(br'.*?(?=[ :\n])')
def _decode_identifier(data, idx):
    m = _id_re.match(data, idx)
    if not m:
        raise DecodeError('Expected identifier at position %d'%idx)
    return m.group().strip().decode('utf8'), m.end()

_idnum_re = re.compile(br'\[\d+\]')
def _decode_idnum(data, idx):
    m = _idnum_re.match(data, idx)
    if not m:
        raise DecodeError('Expected [id] at position %d'%idx)
    return int(m.group()[1:-1].decode('ascii')), m.end()
    

def _skipws(data, idx):
    while data[idx:idx+1] in b' \r':
        idx += 1
    return idx
    
def _expect(data, idx, chars):
    while data[idx:idx+1] == b' ':
        idx += 1
    if data[idx:idx+len(chars)] != chars:
        raise DecodeError('Expected characters "%s" at position %d'%(chars.decode('ascii'), idx))
    return idx + len(chars)
