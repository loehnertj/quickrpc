import json 
import base64

from .concepts import Codec, Message

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
        data = data.decode('utf8')
        messages = []
        message = True
        while message:
            message, data = self._decode_first(data)
            if message:
                messages.append(message)
            while data.startswith('\n'):
                data = data[1:]
        return messages, data
    
    def _decode_first(self, data):
        # FIXME: detect and skip bad data at begin of stream.
        def obj_hook(val):
            if '__bytes' in val:
                return base64.b64decode(val['__bytes'].encode('utf8'))
            return val
        decoder = MyJsonDecoder(object_hook=obj_hook)
        try:
            jdict, idx = decoder.raw_decode(data)
        except json.JSONDecodeError:
            return None, data
        method = jdict['__method']
        del jdict['__method']
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
