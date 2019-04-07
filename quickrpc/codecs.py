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
    'EncodeError',
    'Message',
    'Reply', 
    'ErrorReply',
    'RemoteError',
    'JsonRpcCodec',
]

import logging
import json 
import base64
from traceback import format_exception
from .util import subclasses

L = lambda: logging.getLogger(__name__)

# Wouldn't it be great if traceback could contain that by itself :-/
_fmt_exc = lambda e: '\n'.join(format_exception(type(e), e, e.__traceback__))


class DecodeError(Exception): pass
class EncodeError(Exception): pass

class RemoteError(Exception):
    def __init__(self, message, details):
        Exception.__init__(self, message)
        self.message = message
        self.details = details


class Message(object):
    def __init__(self, method, kwargs, id=0, secinfo=None):
        self.method = method
        self.kwargs = kwargs
        self.id = id
        self.secinfo = secinfo or {}

class Reply(object):
    def __init__(self, result, id, secinfo=None):
        self.result = result
        self.id = int(id)
        self.secinfo = secinfo or {}

class ErrorReply(object):
    def __init__(self, exception, id, errorcode=0, secinfo=None):
        self.exception = exception
        self.id = int(id)
        self.errorcode = errorcode
        self.secinfo = secinfo or {}


class Codec(object):
    '''Responsible for serializing and deserializing method calls.
    
    Subclass and override :any:`encode`, :any:`decode`, optionally 
    :any:`encode_reply`, :any:`encode_error`.
    
    *Protocol overview*
    
    Byte-data payload is generated from python data by using:
    
        * :any:`encode` for "regular" messages / requests
        * :any:`encode_reply` for return data
        * :any:`encode_error` for error return data.
        
    Python data is retrieved from bytes by :any:`decode`. This returns a list of 
    objects, which can be instances of :any:`Message`, :any:`Reply` and 
    :any:`ErrorReply`.
    
    *Security*
    
    Let *payload* denote the "inner" message data and *frame* the message going on the wire, both being byte sequences.
    ``encode*()`` can be given a sec_out() callback, taking the payload data and returning ``(secinfo, new_payload)``.
    
    secinfo is a dict containing e.g. user info, signature, etc. (specific of Security provider).
    
    new_payload is an optional transformed payload (bytes), e.g. encrypted data. If omitted, use original payload.
    ``encode*()`` then builds a frame using new payload and secinfo data, e.g. add crypt headers.
    
    Depending on protocol, encode could be downwards-compatible if "guest" security applies i.e. secinfo is empty and payload stays untransformed.
    
    Decoding: ``decode`` again takes a sec_in() callback, accepting security info and payload data, returning the "unpacked" payload.
    E.g. secinfo could check the signature and raise an error if the message was 
    forged. The secinfo dictionary is returned within the :any:`Message`, 
    :any:`Reply` or :any:`ErrorReply` object.
    
    '''
    # The shorthand to use for string creation.
    shorthand = ''

    @classmethod
    def fromstring(cls, expression):
        '''Creates a codec from a given string expression.

        The expression must be "<shorthand>:<specific parameters>",
        with shorthand being the wanted Codec's .shorthand property.
        For the specific parameters, see the respective Codec's .fromstring
        method.
        '''
        shorthand, _, expr = expression.partition(':')
        for subclass in subclasses(cls):
            if subclass.shorthand == shorthand:
                return subclass.fromstring(expression)
        raise ValueError('Could not find a codec class with shorthand %s'%shorthand)


    def decode(self, data, sec_in=None):
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
            .method attribute (string), .kwargs attribute (dict), .id, .secinfo (dict)
        Reply attributes
            .result, .id, .secinfo (dict)
        ErrorReply attributes
            .exception, .id, .errorcode, .secinfo (dict)
        '''
    
    def encode(self, method, kwargs=None, id=0, sec_out=None):
        '''encode a method call with given kwargs.
        
        sec_out callback parameters:
        
            * payload (bytes): Payload data for the frame.
            
        sec_out returns ``(secinfo, new_payload)``:
        
            * ``sec_info`` (dict): security information, dictionary str->str, keys defined by Security provider.
            * ``new_payload`` (bytes): transformed payload; ``None`` indicates that original payload can be used.
            
        Returns: frame data (bytes)
        '''

    def encode_reply(self, in_reply_to, result, sec_out=None):
        '''encode reply to the Message'''

    def encode_error(self, in_reply_to, exception, errorcode=0, sec_out=None):
        '''encode error caused by the given Message.'''

def TerseCodec():
    from .terse_codec import TerseCodec
    return TerseCodec()


class MyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return {'__bytes': base64.b64encode(obj).decode('utf8')}
        return json.JSONEncoder.default(self, obj)
    
class MyJsonDecoder(json.JSONDecoder):
    pass


class JsonRpcCodec(Codec):
    '''Json codec: convert to json
    
    bytes values are converted into a an object containing the single key 
    ``__bytes`` with value being base64-encoded data.
    
    If security is used, the following "Authenticated-JSON-RPC" protocol applies:
    
    *Encoding*
    
    Prepend a special, valid json-rpc message before the payload:
    
    ``{"jsonrpc": "2.0", "method": "rpc.secinfo", "params": <secinfo>}<DELIM><payload><DELIM>``
    
    If secinfo is empty, NOTHING is prepended (i.e. behaves like unextended JSON-RPC)
    
    .. note:: 
        Payload must not contain the delimiter even if it is encrypted. Raw data could be b64-encoded.
        If payload is encrypted, basic-JSON-RPC compatibility is of course lost.
    
    *Decoding with security*
    
    Decode delimited messages one-by-one as usual ("one" being the bytes between delimiters).
    
    If a ``rpc.secinfo`` call is detected, take the unaltered payload from the 
    next message, giving secinfo and payload. If next message is incomplete (no 
    trailing delim), throw the ``rpc.secinfo`` message back into the remainder.
    
    For regular call (method != ``rpc.secinfo``), return the message itself as 
    payload wtih empty secinfo. 
    
    *Discussion:*
    
     - allows framing without touching payload :-)
     - allows decoding the header without decoding payload :-)
     - allows using byte-payload as is, particularly allows encrypted+literal payload to coexist (however encrypted payload breaks JSON-RPC compat!) :-)
     - Msg to "unaware" peer: will throw the rpc.secinfo calls away silently or loudly, but 
       is able to operate. Missing ID indicates a notification, i.e. peer will not send 
       response back per JSON-RPC spec. :-)
     - Msg from "unaware" peer: will implicitly be treated as no-security message.
    
    '''
    shorthand = 'jrpc'
    @classmethod
    def fromstring(cls, expression):
        '''jrpc:delimiter
        
        delimiter is the character splitting the telegrams and must not occur
        within any telegram. Default = <null>.
        '''
        _, _, delim = expression.partition(':')
        delim = delim.encode('ascii')
        return cls(delimiter = delim or b'\0')

    def __init__(self, delimiter=b'\0'):
        self.delimiter = delimiter

    def encode(self, method, kwargs, id=0, sec_out=None):
        return self._encode_generic(id=id, method=method, params=kwargs, sec_out=sec_out)

    def encode_reply(self, in_reply_to, result, sec_out=None):
        return self._encode_generic(id=in_reply_to.id, result=result, sec_out=sec_out)

    def encode_error(self, in_reply_to, exception, errorcode=0, sec_out=None):
        return self._encode_generic(
                id=in_reply_to.id,
                error= {
                    'code': errorcode,
                    'message': str(exception),
                    'data': _fmt_exc(exception),
                    },
                sec_out=sec_out
            )

    def _encode_generic(self, id=0, sec_out=None, **fields):
        data = { 'jsonrpc': '2.0', }
        data.update(fields)
        if id: data['id'] = id
        data = json.dumps(data, cls=MyJsonEncoder).encode('utf8')
        if sec_out:
            secinfo, new_data = sec_out(data)
        else:
            secinfo, new_data = {}, None
        if not new_data is None:
            data = new_data
        if self.delimiter in data:
            raise EncodeError('Data must not contain the message delimiter %r'%(self.delimiter,))
        if secinfo:
            header = {
                'jsonrpc': '2.0',
                'method': 'rpc.secinfo',
                'params': secinfo
            }
            header = json.dumps(header, cls=MyJsonEncoder).encode('utf8')
            return b''.join([header, self.delimiter, data, self.delimiter])
        else:
            return data + self.delimiter

    def decode(self, data, sec_in=None):
        telegrams = data.split(self.delimiter)
        messages = []
        secinfo = None
        for telegram in telegrams[:-1]:
            if not telegram:
                continue
            if secinfo is not None:
                if sec_in is None:
                    messages.append(DecodeError('Got secured message without knowing how to process it.'))
                    secinfo = None
                    continue
                new_telegram = sec_in(telegram, secinfo)
                if new_telegram is not None:
                    telegram = new_telegram
            message = self._decode_one(telegram, secinfo)
            secinfo = None
            if isinstance(message, Message) and message.method == 'rpc.secinfo':
                secinfo = message.kwargs or {}
                # keep around for next iteration (message follows)
            else:
                messages.append(message)
        if secinfo is None:
            return messages, telegrams[-1]
        else:
            # dangling secinfo - received header without message
            # put header message back into remainder
            return messages, self.delimiter.join(telegrams[-2:])
    
    def _decode_one(self, data, secinfo):
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
                    id=jdict.get('id', 0),
                    secinfo=secinfo
                    )
        elif 'result' in jdict:
            return Reply(
                    result=jdict['result'],
                    id=jdict.get('id',0),
                    secinfo=secinfo
                    )

        elif 'error' in jdict:
            err = jdict['error']
            e = RemoteError(err.get('message', 'Unknown error'), err.get('data', ''))
            return ErrorReply(
                    exception = e,
                    id=jdict.get('id',0),
                    errorcode = err.get('code', 0),
                    secinfo=secinfo
                    )
        else:
            return DecodeError('Message does not contain method, result or error key.')

