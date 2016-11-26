import logging

from socket import timeout
from socketserver import ThreadingTCPServer, BaseRequestHandler
from threading import Thread, Event
from .concepts import Transport
from .mux_transport import MuxTransport

L = lambda: logging.getLogger(__name__)

class TcpServerTransport(MuxTransport):
    '''transport that accepts TCP connections as transports.
    
    Basically a mux transport coupled with a TcpServer. Each time somebody
    connects, the connection is wrapped into a transport and added to the
    muxer.
    
    There is (for now) no explicit notification about connects/disconnects; 
    use the API for that.
    '''
    def __init__(self, port, interface=''):
        MuxTransport.__init__(self)
        self.addr = (interface, port)
        
    def run(self):
        server = ThreadingTCPServer(self.addr, _TcpConnection, bind_and_activate=True)
        server.mux = self
        Thread(target=server.serve_forever, name="TcpServerTransport_Listen").start()
        
        MuxTransport.run(self)
        
        server.shutdown()
        
    def close(self, name):
        '''close the connection with the given sender/receiver name.
        '''
        for transport in self.transports:
            if transport.name == name:
                transport.transport_running.clear()
                                    
                                    
class _TcpConnection(BaseRequestHandler, Transport):
    '''Bridge between TcpServer (BaseRequestHandler) and Transport.
    
    Implicitly created by the TcpServer. .handle() waits until
    Transport.start() is called, and closes the connection and
    exits upon call of .stop().
    
    The Transport also stops upon client-side close of connection.
    
    The _TcpConnection registers and unregisters itself with the TcpServerTransport.
    '''
    
    # BaseRequestHandler overrides
    def __init__(self, request, client_address, server):
        BaseRequestHandler.__init__(self, request, client_address, server)
        Transport.__init__(self)
        
    def setup(self):
        self.name = '%s:%s'%self.client_address
        L().debug('TCP connect from %s'%self.name)
        
        self.request.settimeout(0.5)
        self.transport_running = Event()
        # add myself to the muxer, which will .start() me.
        self.server.mux.add_transport(self)
        
    def handle(self):
        self.transport_running.wait()
        leftover = b''
        while self.transport_running.is_set():
            try:
                data = self.request.recv(1024).strip()
            except timeout:
                continue
            if data == b'':
                # Connection was closed.
                self.stop()
                break
            L().debug('data from %s: %r'%(self.name, data))
            leftover = self.received(sender=self.name, data=leftover+data)
        
    def finish(self):
        L().debug('Closed TCP connection to %s'%self.name)
        # Getting here implies that this transport already stopped.
        self.server.mux.remove_transport(self, stop=False)
    
    # Transport overrides
    def start(self):
        self.transport_running.set()
        
    def run(self):
        # _TcpConnection starts "running" by itself (since the connection is already opened by definition).
        raise Exception('You shall not use .run()')
        
    def stop(self):
        self.transport_running.clear()
        
    def send(self, data, receivers=None):
        if not self.transport_running.is_set():
            raise Exception('Tried to send over non-running transport!')
        if receivers is not None and not self.name in receivers:
            return
        # FIXME: do something on failure
        self.request.sendall(data)