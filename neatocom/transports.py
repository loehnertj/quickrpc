# coding: utf8
'''A transport abstracts a transport layer, which may be multichannel.

For details, see doc of class Transport.

Classes defined here:
 * Transport: abstract base
 * StdioTransport: reads from stdin, writes to stdout.
 * MuxTransport: a transport that multiplexes several sub-transports.
 * TcpServerTransport: a transport that accepts tcp connections and muxes 
    them into one transport. Actually a forward to neatocom.tcp_server_transport.

'''

__all__ = [
    'Transport',
    'StdioTransport',
    'MuxTransport',
    'TcpServerTransport',
]

from collections import namedtuple
import logging
import queue
import sys
import select
import threading
L = lambda: logging.getLogger(__name__)



class Transport(object):
    ''' abstracts a transport layer, which may be multichannel.
    
    Outgoing messages are sent via .send(). (Override!)
    Incoming messages are passed to api.handle_received().
    The api must be set beforehand via set_api().
    
    There are some facilities in place for threaded transports:
    - .run() shall run the transport (possibly blocking)
    - .start() shall start the transport nonblocking
    - .stop() shall stop the transport gracefully
    - Bool property .running for state and signaling 
        (default .stop() sets running to False).
        
    - .set_api is used to set the handler. The api must have
        a method handle_received(sender, data).
        
    '''
    def __init__(self):
        self._api = None
        self.running = False
        
    def run(self):
        '''Runs the transport, possibly blocking. Override me.'''
        self.running = True
        
    def start(self):
        '''Run in a new thread.'''
        self._thread = threading.Thread(target=self.run, name=self.__class__.__name__)
        self._thread.start()
    
    def stop(self):
        '''Stop running transport (possibly from another thread).
        
        By default, sets self.running=False, then .join()s the thread.'''
        self.running = False
        self._thread.join()
    
    def set_api(self, api):
        '''sets the dispatcher using this transport. Received data is given to the dispatcher.'''
        self._api = api
        
    def send(self, data, receivers=None):
        '''sends the given data to the specified receiver(s).
        
        receivers=None means send to all.
        '''
        raise NotImplementedError("Override me")
    
    def received(self, sender, data):
        '''to be called when the subclass received data.
        For multichannel transports, sender is a unique id identifying the source.
        
        If the given data has an undecodable "tail", it is returned.
        In this case you should prepend the tail to the next received bytes from this channel,
        because it is probably an incomplete message.
        '''
        if not self._api:
            raise AttributeError("Transport received a message but has no API set.")
        return self._api.handle_received(sender, data)


class StdioTransport(Transport):
    def stop(self):
        L().info('StdioTransport.stop() called')
        self.running=False

    def send(self, data, receivers=None):
        if receivers is not None and 'stdio' not in receivers:
            return
        L().debug('StdioTransport.send %r'%data)
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    def run(self):
        '''run, blocking.'''
        L().info('StdioTransport.run() called')
        self.running = True
        leftover = b''
        while self.running:
            # FIXME: This loses bytes on startup.
            data = self._input()
            #data = input().encode('utf8') + b'\n'
            if data is None: 
                continue
            L().info("received: %r"%data)
            leftover = self.received(sender='stdio', data=leftover + data)
        L().info('StdioTransport has finished')
            
    def _input(self, timeout=0.1):
        '''Input with 0.1s timeout. Return None on timeout.'''
        i, o, e = select.select([sys.stdin.buffer], [], [], timeout)
        if i:
            return sys.stdin.buffer.read1(65536)
        else:
            return None


InData = namedtuple('InData', 'sender data')

class MuxTransport(Transport):
    '''A transport that muxes several transports.
    
    Incoming data is serialized into the thread of MuxTransport.run().
    
    Add Transports via mux_transport += transport.
    Remove via mux_transport -= transport.
    
    Adding a transport changes its API binding to the mux transport.
    If MuxTransport is already running, the added transport is start()ed by default.
    
    Removing a transport stop()s it by default.
    
    Running/Stopping the MuxTransport also runs/stops all muxed transports.
    '''
    
    def __init__(self):
        self.in_queue = queue.Queue()
        self.transports = []
        self.running = False
        # sender --> leftover bytes
        self.leftovers = {}
        
    def send(self, data, receivers=None):
        # Let everyone decide for himself.
        for transport in self.transports:
            transport.send(data, receivers=receivers)
        
    def handle_received(self, sender, data):
        '''handles INCOMING data from any of the muxed transports.
        b'' is returned as leftover ALWAYS; MuxTransport keeps
        internal remainder buffers for all senders, since the
        leftover is only available after the message was processed.
        '''
        self.in_queue.put(InData(sender, data))
        return b''
    
    def add_transport(self, transport, start=True):
        '''add and start the transport (if running).'''
        self.transports.append(transport)
        transport.set_api(self)
        if start and self.running:
            transport.start()
        return self
        
    def remove_transport(self, transport, stop=True):
        '''remove and stop the transport.'''
        self.transports.remove(transport)
        transport.set_api(None)
        if stop:
            transport.stop()
        return self
        
    __iadd__ = add_transport
    __isub__ = remove_transport
    
    def stop(self):
        L().info('MuxTransport.stop() called')
        self.running = False
    
    def run(self):
        L().info('MuxTransport.run() called')
        self.running = True
        for transport in self.transports:
            transport.start()
        L().debug('Thread overview: %s'%([t.name for t in threading.enumerate()],))
        while self.running:
            try:
                indata = self.in_queue.get(timeout=0.5)
            except queue.Empty:
                # timeout passed, check self.running and try again.
                continue
            L().debug('MuxTransport: received %r'%(indata,))
            leftover = self.leftovers.get(indata.sender, b'')
            leftover = self.received(indata.sender, leftover + indata.data)
            self.leftovers[indata.sender] = leftover
            
        # stop all transports
        for transport in self.transports:
            transport.stop()
        L().info('MuxTransport has finished')
            

def TcpServerTransport(port, interface=''):
    from .tcp_server_transport import TcpServerTransport
    return TcpServerTransport(port, interface)