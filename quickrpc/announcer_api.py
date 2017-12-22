
__all__ = ['AnnouncerAPI', 'make_announcer', 'make_udp_announcer']

import logging
from .remote_api import RemoteAPI, incoming, outgoing
from .codecs import TerseCodec
L = lambda: logging.getLogger(__name__)


class AnnouncerAPI(RemoteAPI):
    '''AnnouncerAPI provides a means of discovering services in some kind of distributed system.
    
    "Clients" broadcast a seek call.
    All "servers" who feel spoken to respond with an advertise call to the seeker.
    '''
    
    @incoming
    def seek(self, sender, filter=''):
        '''Request advertising of present services.
        
        filter is a to-be-defined expression or data structure 
        specifying the services that are wanted.
        '''
        pass
    
    @outgoing
    def advertise(self, receivers=None, description=''):
        '''Advertise that I am present.
        
        Usually the advertisement should be sent only to the seeker, in return of seek().
        
        description is a to-be-defined expression or structure
        giving details about service type, version, etc.
        '''
        pass


def make_announcer(transport, description='', filter_func=None, codec=TerseCodec()):
    '''Returns a ready-to-use announcer server running over the given transport.
    
    Sets the transport's API.
    
    description is the service description to hand out.
    
    filter_func is a predicate accepting the `filter` parameter of
    AnnouncerAPI.seek and returning True if the filter matches this service. If
    left out, it is assumed to be always True.
    
    All you need to do afterwards is to call transport.start(). Keep a reference to
    the transport.
    '''
    
    if not filter_func:
        filter_func = lambda filter: True
    api = AnnouncerAPI(codec, transport)
    api.description = description
    
    def on_seek(sender, filter=''):
        if filter_func(filter):
            L().info('Sending advertisement to %s'%sender)
            api.advertise(receivers=None, description=api.description)
    api.seek.connect(on_seek)
    return api


def make_udp_announcer(port, description='', filter_func=None, codec=TerseCodec()):
    '''makes an annoncer using UdpTransport(port) and returns it.
    
    Start/stop with announcer.transport.start() / .stop().
    '''
    from .network_transports import UdpTransport
    transport = UdpTransport(port)
    return make_announcer(transport, description, filter_func, codec)
