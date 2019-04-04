__all__ = ['UdpTransport', 'TcpServerTransport', 'TcpClientTransport']

import logging

import socket as sk
from select import select
from socketserver import ThreadingTCPServer, BaseRequestHandler
from threading import Thread, Event
from .transports import Transport, MuxTransport

L = lambda: logging.getLogger(__name__)

class UdpTransport(Transport):
    '''transport that communicates over UDP datagrams.

    Connectionless - sender/receiver are IP addresses. Sending and receiving is
    done on the same port. Sending with receiver=None makes a broadcast.

    Use messages > 500 Bytes at your own peril.
    '''
    shorthand = 'udp'
    @classmethod
    def fromstring(cls, expression):
        '''udp:1234 - the number being the port for send/receive.'''
        _, _, rest = expression.partition(':')
        return cls(port=int(rest))

    def __init__(self, port):
        Transport.__init__(self)
        self.port = port

    def open(self):
        self.socket = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
        self.socket.settimeout(0.5)
        self.socket.setsockopt(sk.SOL_SOCKET, sk.SO_BROADCAST, 1)
        self.socket.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEADDR, 1)
        self.socket.setsockopt(sk.SOL_SOCKET, sk.IP_MULTICAST_LOOP, 1)
        try:
            self.socket.setsockopt(sk.SOL_SOCKET, sk.SO_REUSEPORT, 1)
        except AttributeError:
            # SO_REUSEPORT not available.
            pass
        self.socket.bind(('', self.port))

    def run(self):
        self.running = True
        while self.running:
            try:
                data, addr = self.socket.recvfrom(2048)
            except sk.timeout:
                continue
            host, port = addr
            # not using leftover data  here, since udp packets are
            # not guaranteed to arrive in order.
            L().debug('message from udp %s: %s'%(host, data))
            self.received(data=data, sender=host)
        self.socket.close()

    def send(self, data, receivers=None):
        L().debug('message to udp %r: %s'%(receivers, data))
        if receivers:
            for receiver in receivers:
                self.socket.sendto(data, (receiver, self.port))
        else:
            self.socket.sendto(data, ('<broadcast>', self.port))

class TcpClientTransport(Transport):
    '''Transport that connects to a TCP server.

    Optionally, a keepalive message can be configured. ``keepalive_msg`` is sent verbatim
    every ``keepalive_interval`` seconds while the connection is idle. Any sending or
    receiving resets the timer. You can change the attributes anytime.
    '''
    shorthand = 'tcp'

    _CHECK_INTERVAL = 0.5
    @classmethod
    def fromstring(cls, expression):
        '''tcp:<host>:<port>'''
        _, host, port = expression.split(':')
        # uses default connect timeout
        return cls(host=host, port=int(port))

    def __init__(self, host, port, connect_timeout=10, keepalive_msg=b'', keepalive_interval=10, buffersize=1024):
        Transport.__init__(self)
        self.address = (host, port)
        self.name = '%s:%s'%self.address
        self.connect_timeout = connect_timeout
        self.keepalive_msg = keepalive_msg
        self.keepalive_interval = keepalive_interval
        self._keepalive_countdown = keepalive_interval
        self.buffersize = buffersize

    def send(self, data, receivers=None):
        if receivers is not None and not self.name in receivers:
            return
        if not self.running:
            raise IOError('Tried to send over non-running transport!')
        self._keepalive_countdown = self.keepalive_interval
        L().debug('TcpClientTransport .send to %s: %r'%(self.name, data))
        # FIXME: do something on failure
        self.socket.sendall(data)

    def open(self):
        L().debug('TcpClientTransport.open() called')
        try:
            self.socket = sk.create_connection(self.address, self.connect_timeout)
        except ConnectionRefusedError:
            L().error('Connection to %s failed'%(self.name))
            raise
        L().info('Connected to %s'%(self.name,))
        # Sets the timeout for .read and .write
        self._keepalive_countdown = self.keepalive_interval

    def run(self):
        '''run, blocking.'''
        self.running = True
        leftover = b''
        while self.running:
            readable, _, _ = select([self.socket], [], [], self._CHECK_INTERVAL)
            if not readable:
                self._keepalive_tick()
                continue
            try:
                data = self.socket.recv(self.buffersize)
            except ConnectionError:
                data = b''
            self._keepalive_countdown = self.keepalive_interval
            if data == b'':
                # Connection was closed.
                self.running=False
                self.socket=None
                L().info('Connection to %s closed by remote side.'%(self.name,))
                break
            L().debug('data from %s: %r'%(self.name, data))
            leftover = self.received(sender=self.name, data=leftover+data)

        if self.socket:
            L().info('Closing connection to %s.'%(self.name,))
            self.socket.close()
        L().debug('TcpClientTransport %s has finished'%(self.name))

    def _keepalive_tick(self):
        if self.keepalive_msg:
            self._keepalive_countdown -= self._CHECK_INTERVAL
            if self._keepalive_countdown <= 0:
                L().debug('send keepalive')
                self.socket.sendall(self.keepalive_msg)
                self._keepalive_countdown = self.keepalive_interval


class TcpServerTransport(MuxTransport):
    '''transport that accepts TCP connections as transports.

    Basically a mux transport coupled with a TcpServer. Each time somebody
    connects, the connection is wrapped into a transport and added to the
    muxer.

    There is (for now) no explicit notification about connects/disconnects;
    use the API for that.

    Use .close() for server-side disconnect.

    You can optionally pass an announcer (as returned by announcer_api.make_udp_announcer).
    It will be started/stopped together with the TcpServerTransport.

    Optionally, a keepalive message can be configured. On each connection,
    ``keepalive_msg`` is sent verbatim every ``keepalive_interval`` seconds
    while the connection is idle. Any sending or receiving resets the timer.
    You can change the attributes directly while transport is stopped.

    Threads:
     - TcpServerTransport.run() blocks (use .start() for automatic extra Thread)
     - .run() starts a new thread for listening to connections
     - each incoming connection will start another Thread.
    '''
    shorthand = 'tcpserv'
    @classmethod
    def fromstring(cls, expression):
        '''tcpserv:<interface>:<port>

        Leave <interface> empty to listen on all interfaces.
        '''
        _, iface, port = expression.split(':')
        return cls(port=int(port), interface=iface)

    def __init__(self, port, interface='', announcer=None, keepalive_msg=b'', keepalive_interval=10, buffersize=1024):
        self.addr = (interface, port)
        self.name = '%s:%s'%self.addr
        self.announcer = announcer
        self.keepalive_msg = keepalive_msg
        self.keepalive_interval = keepalive_interval
        self.buffersize = buffersize
        MuxTransport.__init__(self)

    def open(self):
        self.server = ThreadingTCPServer(self.addr, _TcpConnection, bind_and_activate=True)
        self.server.mux = self
        Thread(target=self.server.serve_forever, name="TcpServerTransport_Listen").start()
        if self.announcer:
            try:
                self.announcer.transport.start()
            finally:
                self.server.shutdown()

    def run(self):
        MuxTransport.run(self)

        if self.announcer:
            self.announcer.transport.stop()

        self.server.shutdown()
        self.server.server_close()

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

    _CHECK_INTERVAL = 0.5

    # BaseRequestHandler overrides
    def __init__(self, request, client_address, server):
        # circumvent Transport.__init__, since none of the threading logic is used here
        #Transport.__init__(self)
        self._on_received = None
        self.keepalive_msg = server.mux.keepalive_msg
        self.keepalive_interval = server.mux.keepalive_interval
        self.buffersize = server.mux.buffersize
        self._keepalive_countdown = self.keepalive_interval
        BaseRequestHandler.__init__(self, request, client_address, server)

    @property
    def running(self):
        return self.transport_running.is_set()

    def setup(self):
        '''called by the ThreadingTCPServer.

        Adds the connection to the parent muxer, then waits
        for .start() to be called.
        '''
        self.name = '%s:%s'%self.client_address
        L().info('TCP connect from %s'%self.name)

        self.transport_running = Event()
        # add myself to the muxer, which will .start() me.
        self.server.mux.add_transport(self)

    def handle(self):
        # should be set almost-instantly; otherwise something is wrong.
        self.transport_running.wait(timeout=1.0)
        leftover = b''
        while self.transport_running.is_set():
            readable, _, _ = select([self.request], [],[], self._CHECK_INTERVAL)
            if not readable:
                self._keepalive_tick()
                continue
            try:
                data = self.request.recv(self.buffersize)
            except ConnectionError:
                data = b''
            self._keepalive_countdown = self.keepalive_interval
            #data = data.replace(b'\r\n', b'\n')
            if data == b'':
                # Connection was closed.
                L().info('Connection to %s closed by remote side.'%(self.name,))
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
        if receivers is not None and not self.name in receivers:
            return
        if not self.transport_running.is_set():
            raise IOError('Tried to send over non-running transport!')
        self._keepalive_countdown = self.keepalive_interval
        # FIXME: do something on failure
        L().debug('_TcpConnection .send to %s: %r'%(self.name, data))
        try:
            self.request.sendall(data)
        except Exception:
            L().error('TcpServerTransport._TcpConnection: sending failed, see exc. info', exc_info=True)
            raise

    def _keepalive_tick(self):
        if self.keepalive_msg:
            self._keepalive_countdown -= self._CHECK_INTERVAL
            if self._keepalive_countdown <= 0:
                L().debug('send keepalive')
                self.request.sendall(self.keepalive_msg)
                self._keepalive_countdown = self.keepalive_interval
