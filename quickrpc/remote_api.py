'''RemoteAPI: a class whose methods correspond to outgoing / incoming remote calls.

@outgoing, @incoming: decorators for RemoteAPI subclass methods.

'''
import logging
from queue import Queue
import itertools as it
import inspect
from .codecs import Message, Reply, ErrorReply

L = lambda: logging.getLogger(__name__)

__all__ = [
    'RemoteAPI',
    'incoming',
    'outgoing',
]


class RemoteAPI(object):
    '''Describes an API i.e. a set of allowed outgoing and incoming calls.
    
    .codec holds the Codec for (de)serializing data.
    .transport holds the underlying transport.
    
    .message_error(exception, in_reply_to) is called each time a message cannot be decoded
    or handled properly.
    By default, it logs the error as warning.
    in_reply_to is the message that triggered the error, None if decoding failed.
    
    Methods marked as @outgoing are automatically turned into
    messages on call. The method body is executed before sending. (use e.g.
    for validation of outgoing data).
    They must accept a special `receivers` argument, which is passed to the
    Transport.
    
    Methods marked as @incoming are called by the transport when
    messages arrive. They work like signals - you can connect your
    own handler(s) to them. Connected handlers must have the same
    signature as the incoming call. All @incoming methods MUST support
    a `senders` argument.
    
    Connect like this:
    
    >>> def handler(self, foo=None): pass
    >>> remote_api.some_method.connect(handler)
    >>> # later
    >>> remote_api.some_method.disconnect(handler)
    
    Execution order: the method of remote_api is executed first,
    then the connected handlers in the order of registering.
    
    Threading:
        * outgoing messages are sent on the calling thread.
        * incoming messages are handled on the thread which
            handles Transport receive events. I.e. the
            Transport implementation defines the behaviour.
            
    For added neatness, you can .invert() the whole api,
    swapping incoming and outgoing methods.
    
    '''
    def __init__(self, codec=None, transport=None, invert=False):
        self.codec = codec
        self.transport = transport
        # FIXME: limit size of _pending_replies somehow
        self._pending_replies = {}
        self._id_dispenser = it.count()
        # pull the 0
        next(self._id_dispenser)
        if invert:
            self.invert()
        
    @property
    def transport(self):
        return self._transport
    @transport.setter
    def transport(self, value):
        self._transport = value
        if self._transport:
            self._transport.set_api(self)
            
    def invert(self):
        '''Swaps @incoming and @outgoing property
        on all methods if this INSTANCE.
        
        I.e. generates the opposite-side API.
        
        Do this before connecting any handlers to incoming calls.
        '''
        for attr in dir(self):
            field = getattr(self, attr)
            if hasattr(field, '_remote_api_incoming') or hasattr(field, '_remote_api_outgoing'):
                # The decorators add a "method" .inverted() to the field,
                # which will yield the inverse-decorated field.
                setattr(self, attr, field.inverted().__get__(self))
        

    # ---- handling of incoming messages ----

    def handle_received(self, sender, data):
        messages, remainder = self.codec.decode(data)
        for message in messages:
            if isinstance(message, Exception):
                self.message_error(message)
                continue
            elif isinstance(message, Reply) or isinstance(message, ErrorReply):
                self._deliver_reply(message)
            else:
                self._handle_method(sender, message)
        return remainder

    def _handle_method(self, sender, message):
        try:
            method = getattr(self, message.method)
        except AttributeError:
            self.message_error(AttributeError("Incoming call of %s not defined on the api"%message.method), message)
            return
        if not hasattr(method, "_remote_api_incoming"):
            self.message_error(AttributeError("Incoming call of %s not marked as @incoming on the api"%message.method), message)
            return
        has_reply = method._remote_api_incoming['has_reply']
        try:
            result = method(sender, message)
        except Exception as e:
            L().error(str(e), exc_info = True)
            if has_reply: 
                self.message_error(e, message)
        else:
            if has_reply:
                data = self.codec.encode_reply(message, result)
                self.transport.send(data)

    def message_error(self, exception, in_reply_to=None):
        '''you can use this to send an error response'''
        L().warning(exception)
        if in_reply_to.id:
            data = self.codec.encode_error(in_reply_to, exception, errorcode=0)
            self.transport.send(data)

    def _deliver_reply(self, reply):
        id = reply.id
        try:
            q = self._pending_replies.pop(id)
        except KeyError:
            # do not raise, since it cannot be caught by user.
            L().warning('Received reply that was never requested: %r'%(reply,))

        if isinstance(reply, Reply):
            q.put(reply.result)
        else:
            # do not raise, since it cannot be caught by user.
            # Instead, put the ErrorReply in the result queue.
            q.put(reply)

    # ---- handling of outgoing messages ----

    def _new_request(self):
        call_id = next(self._id_dispenser)
        q = Queue(1)
        self._pending_replies[call_id] = q
        return call_id, q

    # ---- stuff ----

    def unhandled_calls(self):
        '''Generator, returns the names of all *incoming*, unconnected methods.

        If no results are returned, all incoming messages are connected.
        '''
        result = []
        for attr in dir(self):
            field = getattr(self, attr)
            if hasattr(field, '_remote_api_incoming') and not field._listeners:
                yield attr


def incoming(unbound_method=None, has_reply=False, allow_positional_args=False):
    if not unbound_method:
        # when called as @decorator(...)
        return lambda unbound_method: incoming(unbound_method=unbound_method, has_reply=has_reply, allow_positional_args=allow_positional_args)
    # when called as @decorator or explicitly
    def fn(self, sender, message):
        if isinstance(message.kwargs, dict):
            args, kwargs = [], message.kwargs
        else:
            if not allow_positional_args:
                raise ValueError('Please call with named parameters only!')
            if isinstance(message.kwargs, list):
                args, kwargs = message.kwargs, {}
            else:
                args, kwargs = [message.kwargs], {}
        L().debug('incoming call of %s, args=%r, kwargs=%r'%(message.method, args, kwargs))
        try:
            replies = [unbound_method(self, sender, *args, **kwargs)]
        except TypeError:
            # signature is wrong
            raise TypeError('incoming call with wrong signature')
        for listener in fn._listeners:
            replies.append(listener(sender, *args, **kwargs))
        if has_reply:
            replies = [r for r in replies if r is not None]
            if len(replies) > 1:
                raise ValueError('Incoming call produced more than one reply!')
            replies.append(None) # If there is no result, reply with None
            return replies[0]

    # Presence of this attribute indicates that this method is a valid incoming target
    fn._remote_api_incoming = {'has_reply': has_reply}
    fn._listeners = []
    fn._unbound_method = unbound_method
    fn.connect = lambda listener: fn._listeners.append(listener)
    fn.disconnect = lambda listener: fn._listeners.remove(listener)
    fn.__name__ = unbound_method.__name__
    fn.__doc__ = unbound_method.__doc__
    fn.inverted = lambda: outgoing(unbound_method, has_reply=has_reply, allow_positional_args=allow_positional_args)
    return fn


def outgoing(unbound_method=None, has_reply=False, allow_positional_args=False):
    '''generates a dispatcher call under name of the method.
    method's body will be called before sending.
    '''
    if not unbound_method:
        # when called as @decorator(...)
        return lambda unbound_method: outgoing(unbound_method=unbound_method, has_reply=has_reply, allow_positional_args=allow_positional_args)
    # when called as @decorator or explicitly
    if allow_positional_args:
        sig = inspect.signature(unbound_method)
        # cut off self and sender/receiver arg
        argnames = [p.name for p in sig.parameters.values()][2:]
    else:
        argnames = []
    def fn(self, receivers=None, *args, **kwargs):
        if args and not allow_positional_args:
            raise ValueError('Please call with named parameters only!')
        else:
            # map positional to named args
            for name, arg in zip(argnames, args):
                if name in kwargs:
                    raise ValueError('argument %s given twice!'%name)
                kwargs[name] = arg
        # this ensures that all args and kwargs are valid
        unbound_method(self, receivers, **kwargs)
        if has_reply:
            call_id, return_queue = self._new_request()
        else:
            call_id = 0
        data = self.codec.encode(unbound_method.__name__, kwargs=kwargs, id=call_id)
        self.transport.send(data, receivers=receivers)
        if has_reply:
            return return_queue

    fn._remote_api_outgoing = {'has_reply': has_reply}
    fn.__name__ = unbound_method.__name__
    fn.__doc__ = unbound_method.__doc__
    fn.inverted = lambda: incoming(unbound_method, has_reply=has_reply, allow_positional_args=allow_positional_args)
    return fn