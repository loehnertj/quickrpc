'''Layer concepts for communication.

The concepts are base classes you can build upon.

* Transport: describes a channel that can send and receive byte data.
* Codec: decodes/encodes messages into bytes.
* RemoteAPI: a class whose methods correspond to outgoing / incoming remote calls.
* @outgoing, @incoming: decorators for RemoteAPI subclass methods.

'''
import logging
L = lambda: logging.getLogger(__name__)


class RemoteAPI(object):
    '''Describes an API i.e. a set of allowed outgoing and incoming calls.
    
    .codec holds the Codec for (de)serializing data.
    .transport holds the underlying transport.
    
    .message_error(exception) is called each time a message cannot be decoded
    or handled properly
    By default, it logs the error as warning.
    
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
    def __init__(self, codec=None, transport=None):
        self.codec = codec
        self.transport = transport
        
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
                # whichwill yield the inverse-decorated field.
                setattr(self, attr, field.inverted().__get__(self))
        
            
    def handle_received(self, sender, data):
        messages, remainder = self.codec.decode(data)
        for message in messages:
            if isinstance(message, Exception):
                self.message_error(message)
                continue
            try:
                method = getattr(self, message.method)
            except AttributeError:
                self.message_error(AttributeError("Incoming call of %s not defined on the api"%message.method))
                continue
            if not hasattr(method, "_remote_api_incoming"):
                self.message_error(AttributeError("Incoming call of %s not marked as @incoming on the api"%message.method))
                continue
            method(sender, **message.kwargs)
        return remainder
    
    def message_error(self, exception):
        L().warning(exception)
        
    def unhandled_calls(self):
        '''Generator, returns the names of all *incoming*, unconnected methods.
        
        If no results are returned, all incoming messages are connected.
        '''
        result = []
        for attr in dir(self):
            field = getattr(self, attr)
            if hasattr(field, '_remote_api_incoming') and not field._listeners:
                yield attr
                


def incoming(unbound_method):
    def fn(self, sender, **kwargs):
        try:
            unbound_method(self, sender, **kwargs)
        except TypeError:
            # signature is wrong
            L().warning('incoming call with wrong signature, ignored')
            return
        for listener in fn._listeners:
            listener(sender, **kwargs)
    # Presence of this attribute indicates that this method is a valid incoming target
    fn._remote_api_incoming = None
    fn._listeners = []
    fn.connect = lambda listener: fn._listeners.append(listener)
    fn.disconnect = lambda listener: fn._listeners.remove(listener)
    fn.__name__ = unbound_method.__name__
    fn.__doc__ = unbound_method.__doc__
    fn.inverted = lambda: outgoing(unbound_method)
    return fn


def outgoing(unbound_method):
    '''generates a dispatcher call under name of the method.
    method's body will be called before sending.
    '''
    def fn(self, receivers=None, **kwargs):
        # this ensures that all kwargs are valid
        unbound_method(self, receivers, **kwargs)
        data = self.codec.encode(unbound_method.__name__, kwargs=kwargs)
        self.transport.send(data, receivers=receivers)
    fn._remote_api_outgoing = None
    fn.__name__ = unbound_method.__name__
    fn.__doc__ = unbound_method.__doc__
    fn.inverted = lambda: incoming(unbound_method)
    return fn