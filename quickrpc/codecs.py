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
    'Reply', 
    'ErrorReply',
    'JsonrpcError',
    'JsonRpcCodec',
]

import logging
import json 
import base64
from traceback import format_exception

L = lambda: logging.getLogger(__name__)

# Wouldn't it be great if traceback could contain that by itself :-/
_fmt_exc = lambda e: '\n'.join(format_exception(type(e), e, e.__traceback__))


class DecodeError(Exception): pass

class JsonrpcError(Exception):
    def __init__(self, message, data):
        Exception.__init__(self, message)
        self.message = message
        self.data = data


class Message(object):
    def __init__(self, method, kwargs, id=0):
        self.method = method
        self.kwargs = kwargs
        self.id = id

class Reply(object):
    def __init__(self, result, id):
        self.result = result
        self.id = id

class ErrorReply(object):
    def __init__(self, exception, id, errorcode=0):
        self.exception = exception
        self.id = id
        self.errorcode = errorcode


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

        messages can be instances of:
             - Message
             - Reply (to the previous message with the same id)
             - ErrorReply (to the previous message with the same id)

        Message attributes
            .method attribute (string), .kwargs attribute (dict), .id
        Reply attributes
            .result, .id
        ErrorReply attributes
            .exception, .id, .errorcode
        '''
    
    def encode(self, method, kwargs=None, id=0):
        '''encode a method call with given kwargs.'''

    def encode_reply(self, in_reply_to, result):
        '''encode reply to the Message'''

    def encode_error(self, in_reply_to, exception, errorcode=0):
        '''encode error caused by the given Message.'''
    


class MyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return {'__bytes': base64.b64encode(obj).decode('utf8')}
        return json.JSONEncoder.default(self, obj)
    
class MyJsonDecoder(json.JSONDecoder):
    pass


class JsonRpcCodec(Codec):
    '''Json codec: convert to json
    
    bytes values are converted into a base64-encoded string and prepended by "b".
    str values are prepended by "s".
    method name is added as dict param __method.
    '''

    def __init__(self, delimiter=b'\0'):
        self.delimiter = delimiter

    def encode(self, method, kwargs, id=0):
        return self._encode_generic(id=id, method=method, params=kwargs)

    def encode_reply(self, in_reply_to, result):
        return self._encode_generic(id=in_reply_to.id, result=result)

    def encode_error(self, in_reply_to, exception, errorcode=0):
        return self._encode_generic(
                id=in_reply_to.id,
                error= {
                    'code': errorcode,
                    'message': str(exception),
                    'data': _fmt_exc(exception),
                    }
                )

    def _encode_generic(self, id=0, **fields):
        data = { 'jsonrpc': '2.0', }
        data.update(fields)
        if id: data['id'] = id
        data = json.dumps(data, cls=MyJsonEncoder).encode('utf8')
        return data + self.delimiter


    def decode(self, data):
        telegrams = data.split(self.delimiter)
        messages = []
        for telegram in telegrams[:-1]:
            if not telegram:
                continue
            message = self._decode_one(telegram)
            messages.append(message)
        return messages, telegrams[-1]
    
    def _decode_one(self, data):
        try:
            data = data.decode('utf8')
        except UnicodeDecodeError as e:
            return DecodeError("UTF8 decoding failed")
        def obj_hook(val):
            if '__bytes' in val:
                return base64.b64decode(val['__bytes'].encode('utf8'))
            return val
        decoder = MyJsonDecoder(object_hook=obj_hook)
        try:
            jdict, idx = decoder.raw_decode(data)
        except json.JSONDecodeError as e:
            return DecodeError('Not a valid json string: "%s"'%data)
        if not isinstance(jdict, dict):
            return DecodeError('json toplevel object is not a dict')
        if jdict.get('jsonrpc', '') != '2.0':
            return DecodeError('jsonrpc key missing or not "2.0"')
        if 'method' in jdict:
            return Message(
                    method=jdict['method'],
                    kwargs=jdict.get('params', {}),
                    id=jdict.get('id', 0)
                    )
        elif 'result' in jdict:
            return Reply(
                    result=jdict['result'],
                    id=jdict.get('id',0)
                    )

        elif 'error' in jdict:
            err = jdict['error']
            e = JsonrpcError(err.get('message', 'Unknown error'), err.get('data', ''))
            return ErrorReply(
                    exception = e,
                    id=jdict.get('id',0),
                    errorcode = err.get('code', 0),
                    )
        else:
            return DecodeError('Message does not contain method, result or error key.')

def TerseCodec():
    from .terse_codec import TerseCodec
    return TerseCodec()
