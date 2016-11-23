import logging
from collections import namedtuple
import queue

from .concepts import Transport

L = lambda: logging.getLogger(__name__)

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
        self.transport.remove(transport)
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
            