'''QuickRPC is a library for quick and painless setup of communication channels and Remote-call protocols.

**Python 3 only**

To use QuickRPC, you define a :class:`RemoteAPI` subclass. This is a special 
interface-like class whose methods define the possible incoming and outgoing 
calls.

Second, a :class:`~codecs.Codec` is needed to translate method calls into byte strings 
and vice-versa. This could for example be JSON-RPC or MsgPack codec.

Third, the `RemoteAPI` is bound to a :class:`~transports.Transport`. This is 
basically a send-and-receive channel out of your program. Predefined transports 
include Stdio, TCP client and server as well as UDP. Additionally there are 
wrappers that can merge multiple transports together and restart a failing 
transport.

Codecs and Transports can be instantiated from a textual definition, so that
they can easily put in a config file or on the commandline. See
:meth:`~quickrpc.transport` (alias of :func:`transports.Transport.fromstring`) and 
:meth:`~quickrpc.codec` (alias of :func:`codecs.Codec.fromstring`).
'''

from . import transports
# import, so that subclasses become known
from . import network_transports
from . import bus_transport
from . import codecs
from . import terse_codec
from .remote_api import RemoteAPI, incoming, outgoing

__all__ = [
        'RemoteAPI',
        'incoming',
        'outgoing',
        'transport',
        'codec',
        'RemoteError'
        ]


def transport(expression):
    return transports.Transport.fromstring(expression)

def codec(expression):
    return codecs.Codec.fromstring(expression)

transport.__doc__ = transports.Transport.fromstring.__doc__
codec.__doc__ = codecs.Codec.fromstring.__doc__

RemoteError = codecs.RemoteError
