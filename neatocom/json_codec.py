import logging
L = lambda: logging.getLogger(__name__)
import json 
import base64

from .concepts import Codec, Message, DecodeError

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
                return base64.decode(val['__bytes'].encode('utf8'))
            return val
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
        
        
def test():
    jc = JsonCodec()
    data=jc.encode(method="my_method", kwargs={
        'int': 1,
        'float': 1.1,
        'str': "abc",
        'str_with_nl': 'foo\nbar',
        'list': [1, 2, 3],
        'dict': {'a': 1, 'b': 2},
        'bytes': b'0123456789',
    })
    print(repr(data))
    print()
    msgs, rest = jc.decode(data)
    for m in msgs:
        print(m.method, m.kwargs)
    print("rest:"+rest)
    
    
if __name__=='__main__':
    test()
