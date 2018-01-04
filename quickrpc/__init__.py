'''Com library with layer concept.

* Transport: describes a channel that can send and receive byte data.
* Codec: decodes/encodes messages into bytes.
* RemoteAPI: a class whose methods correspond to outgoing / incoming remote calls.
'''

from . import transports
# import, so that subclasses become known
from . import network_transports
from . import codecs
from . import terse_codec
from .remote_api import RemoteAPI, incoming, outgoing

__all__ = [
        'RemoteAPI',
        'incoming',
        'outgoing',
        'transport',
        'codec'
        ]


transport = transports.Transport.fromstring
codec = codecs.Codec.fromstring
