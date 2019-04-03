# coding: utf8
'''A Transport abstracts a two-way bytestream interface.

It can be started and stopped, and send and receive byte sequences
to one or more receivers.

Classes defined here:
 * :any:`Transport`: abstract base
 * :any:`MuxTransport`: a transport that multiplexes several sub-transports.
 * :any:`RestartingTransport`: a transport that automatically restarts its child.
 * :any:`StdioTransport`: reads from stdin, writes to stdout.
 * :any:`TcpServerTransport`: a transport that accepts tcp connections and muxes 
   them into one transport. Actually a forward to quickrpc.network_transports.
 * :any:`TcpClientTransport`: connects to a TCP server. This is a forward to 
   quickrpc.network_transports.
 * :any:`RestartingTcpClientTransport`: a TCP Client that reconnects automatically.

'''

__all__ = [
    'Transport',
    'MuxTransport',
    'RestartingTransport',
    'StdioTransport',
    'TcpServerTransport',
    'TcpClientTransport',
    'RestartingTcpClientTransport',
]

from collections import namedtuple
import logging
import queue
import sys
import select
import threading
import time
from .util import subclasses, paren_partition
from .promise import Promise, PromiseDoneError

L = lambda: logging.getLogger(__name__)

class TransportError(Exception):
    '''Generic Transport-related error.'''


class Transport(object):
    '''A transport abstracts a two-way bytestream interface.
    
    This is the base class, which provides multithreading logic
    but no actual communication channel.
    
    In a subclass, the following methods must be implemented:
    
     * :meth:`send` to send outgoing messages
     * :meth:`open` to initialize the channel (if necessary)
     * :meth:`run` to receive messages until it is time to stop.
    
    Incoming messages are passed to a callback. It must be set before the first 
    message arrives via :meth:`set_on_received`.
    
    Provided threading functionality:
    
    - :meth:`start` opens and runs the channel in a new thread
    - :meth:`stop` signals :meth:`run` to stop, by setting :attr:`running` to False.
        
    The classmethod :meth:`fromstring` can be used to create a 
    :class:`Transport` instance from a string (for enhanced configurability).
    '''
    # The shorthand to use for string creation.
    shorthand = ''

    def __init__(self):
        self._on_received = None
        self.running = False
        # This lock guards calls to .start() and .stop().
        # E.g. someone might try to stop while we are still starting.
        self._transition_lock = threading.Lock()
        self._thread = None
        
    @classmethod
    def fromstring(cls, expression):
        '''Creates a transport from a given string expression.

        The expression must be "<shorthand>:<specific parameters>",
        with shorthand being the wanted transport's .shorthand property.
        For the specific parameters, see the respective transport's .fromstring
        method.
        
        The base class implementation searches among all known subclasses
        for the Transport matching the given shorthand, and returns
        ``Subclass.fromstring(expression)``.
        '''
        shorthand, _, expr = expression.partition(':')
        for subclass in subclasses(cls):
            if subclass.shorthand == shorthand:
                return subclass.fromstring(expression)
        raise ValueError('Could not find a transport class with shorthand %s'%shorthand)

    @property
    def receiver_thread(self):
        '''The thread on which on_received will be called.'''
        return self._thread

    def open(self):
        '''Open the communication channel. e.g. bind and activate a socket.
        
        Override me.
        
        ``open`` is called on the new thread opened by `start`. I.e. the same thread in
        which the Transport will ``run``.
        
        When ``open()`` returns, the communication channel should be ready for send and receive.
        '''
        
    def run(self):
        '''Runs the transport, blocking.
        
        Override me.
        
        This contains the transport's mainloop, which must:
        
         - receive bytes from the channel (usually blocking)
         - pass the bytes to ``self.received``
         - check periodically (e.g. each second) if ``self.running`` has been cleared
         - if so, close the channel and return.
        '''
        self.running = True
        
    
    def start(self, block=True, timeout=10):
        '''Run in a new thread.
        
        If ``block`` is True, waits until startup is complete i.e. :meth:`open` 
        returns. Then returns True.
        
        if nonblocking, returns a promise.
        
        If something goes wrong during start, the Exception, like e.g. a 
        ``socket.error``, is passed through to the caller.
        '''
        
        def starter():
            with self._transition_lock:
                try:
                    self.open()
                except Exception as e:
                    p.set_exception(e)
                    return
                else:
                    p.set_result(True)
            try:
                self.run()
            finally:
                self.running = False

        self._thread = threading.Thread(target=starter, name=self.__class__.__name__)
        p = Promise(setter_thread=self._thread)

        self._thread.start()
        return p.result(timeout=timeout) if block else p
    
    
    def stop(self, block=True):
        '''Stop running transport (possibly from another thread).
        
        Resets :attr:`running` to signal to :meth:`run` that it should stop.
        
        Actual stopping can take a moment. If ``block`` is True, :meth:`.stop` 
        waits until :meth:`run` returns.
        '''
        with self._transition_lock:
            self.running = False
            thread = self._thread
            # If cross-thread stop, wait until actually stopped.
            # conditions:
            # - block is set
            # - thread is not None
            # - thread is not the current_thread() (catches "stop-from-within" deadlock)
            if block and thread and thread is not threading.current_thread():
                    self._thread.join()
            self._thread = None
    
    def set_on_received(self, on_received):
        '''Sets the function to call upon receiving data.
    
        The callback's signature is ``on_received(sender, data)``, where ``sender`` is a
        string describing the origin; ``data`` is the received bytes.
        If decoding leaves trailing bytes, they should be returned. The Transport 
        stores them and prepends them to the next received bytes.
        '''
        self._on_received = on_received
        
    def send(self, data, receivers=None):
        '''Sends the given data to the specified receiver(s).
        
        ``receivers`` is an iterable yielding strings. ``receivers=None`` sends 
        the data to all connected peers.
        
        TODO: specify behaviour when sending on a stopped or failed Transport.
        '''
        raise NotImplementedError("Override me")
    
    def received(self, sender, data):
        '''To be called by :meth:`run` when the subclass received data.
        
        ``sender`` is a unique string identifying the source. e.g. IP address and port.
        
        If the given data has an undecodable "tail", it is returned.
        In this case :meth:`run` must prepend the tail to the next received bytes from this channel,
        because it is probably an incomplete message.
        '''
        if not self._on_received:
            raise AttributeError("Transport received a message but has no handler set.")
        return self._on_received(sender, data)


class StdioTransport(Transport):
    shorthand = 'stdio'
    @classmethod
    def fromstring(cls, expression):
        '''No configuration options, just use "stdio:".'''
        return cls()

    def stop(self):
        L().debug('StdioTransport.stop() called')
        Transport.stop(self)

    def send(self, data, receivers=None):
        if receivers is not None and 'stdio' not in receivers:
            return
        L().debug('StdioTransport.send %r'%data)
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    def run(self):
        '''run, blocking.'''
        L().debug('StdioTransport.run() called')
        self.running = True
        leftover = b''
        while self.running:
            # FIXME: This loses bytes on startup.
            data = self._input()
            #data = input().encode('utf8') + b'\n'
            if data is None: 
                continue
            L().debug("received: %r"%data)
            leftover = self.received(sender='stdio', data=leftover + data)
        L().debug('StdioTransport has finished')
            
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
    
    Adding a transport changes its on_received binding to the mux transport.
    If MuxTransport is already running, the added transport is start()ed by default.
    
    Removing a transport stop()s it by default.
    
    Running/Stopping the MuxTransport also runs/stops all muxed transports.
    '''
    shorthand='mux'
    @classmethod
    def fromstring(cls, expression):
        '''mux:(<transport1>)(<transport2>)...
        
        where <transport1>, .. are again valid transport expressions.
        '''
        _, _, params = expression.partition(':')
        t = cls()
        while params != '':
            expr, _, params = paren_partition(params)
            t.add_transport(Transport.fromstring(expr))
        return t
        
    
    def __init__(self):
        Transport.__init__(self)
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
        transport.set_on_received(self.handle_received)
        if start and self.running:
            transport.start()
        return self
        
    def remove_transport(self, transport, stop=True):
        '''remove and stop the transport.'''
        self.transports.remove(transport)
        transport.set_on_received(None)
        if stop:
            transport.stop()
        return self
        
    __iadd__ = add_transport
    __isub__ = remove_transport
    
    def stop(self):
        L().debug('MuxTransport.stop() called')
        Transport.stop(self)
    
    def open(self):
        '''Start all transports that were added so far.
        
        The subtransports are started in parallel, then we wait until all of 
        them are up.
        
        If any transport fails to start, all transports are stopped again,
        and TransportError is raised. It will have a .exceptions attribute being
        a list of all failures.
        '''
        
        L().debug('MuxTransport.run() called')
        promises = []
        exceptions = []
        running = []
        for transport in self.transports:
            promises.append(transport.start(block=False))
        # wait on all the promises
        for transport, promise in zip(self.transports, promises):
            try:
                if promise.result():
                    running.append(transport)
            except Exception as e:
                exceptions.append(e)
        if exceptions:
            # Oh my. Stop everything again.
            L().error('Some transports failed to start. Aborting.')
            for transport in running:
                transport.stop()
            e = TransportError()
            e.exceptions = exceptions
            raise e
        
        L().debug('Thread overview: %s'%([t.name for t in threading.enumerate()],))
        
    def run(self):
        self.running = True
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
        L().debug('MuxTransport has finished')
            

class RestartingTransport(Transport):
    '''A transport that wraps another transport and keeps restarting it.

    E.g. you can wrap a TcpClientTransport to try reconnecting it.
    
    >>> tr = RestartingTransport(TcpClientTransport(*address), check_interval=10)

    check_interval gives the Restart interval in seconds. It may not be kept exactly.
    It cannot be lower than 1 second. Restarting is attempted as long as the transport is running.
    
    Adding a transport changes its on_received handler to the RestartingTransport.
    '''
    shorthand='restart'
    @classmethod
    def fromstring(cls, expression):
        '''restart:10:<subtransport>

        10 (seconds) is the restart interval.

        <subtransport> is any valid transport string.
        '''
        _, _, expr = expression.partition(':')
        interval, _, expr = expr.partition(':')
        if interval:
            interval = int(interval)
        else:
            interval=10
        return cls(
                transport=Transport.fromstring(expr),
                check_interval=interval,
                name=expression
                )

    def __init__(self, transport, check_interval=10, name=''):
        Transport.__init__(self)
        self.check_interval = check_interval
        self.transport = transport
        self.transport.set_on_received(self.received)
        self._poll_interval = 1
        self.name = name
        self._start_promise = None

    @property
    def receiver_thread(self):
        '''Thread on which receive() is called - in this case, receiver_thread of the child.'''
        return self.transport.receiver_thread
    
    @property
    def subtransport_running(self):
        '''True if the child transport is currently running.'''
        return self.transport.running

    def stop(self):
        # First stop self!
        Transport.stop(self)
        
    def open(self):
        self._start_promise = self.transport.start(block=False)

    def run(self):
        self.running = True
        restart_timer = self.check_interval
        while self.running:
            time.sleep(self._poll_interval)
            if self._start_promise:
                # still starting, wait for result
                try:
                    self._start_promise.result(timeout=1.0)
                except TimeoutError:
                    pass
                except Exception as e:
                    L().info('Start of (%s) failed. Traceback follows. Retry in %g seconds'%(self.transport.name, self.check_interval), exc_info=True)
                    self._start_promise = None
                else:
                    # started
                    self._start_promise = None
            elif not self.transport.running:
                restart_timer -= self._poll_interval
                if restart_timer <= 0:
                    L().info("trying to restart (%s)"%self.name)
                    self._start_promise = self.transport.start(block=False)
                    restart_timer = self.check_interval
        self.transport.stop()

    def send(self, data, receivers=None):
        self.transport.send(data, receivers)

def RestartingTcpClientTransport(host, port, check_interval=10):
    '''Convenience wrapper for the most common use case. Returns TcpClientTransport wrapped in a RestartingTransport.'''
    t = TcpClientTransport(host, port)
    return RestartingTransport(t, check_interval=check_interval, name=t.name)

def TcpServerTransport(port, interface='', announcer=None):
    from .network_transports import TcpServerTransport
    return TcpServerTransport(port, interface, announcer)

def TcpClientTransport(host, port):
    from .network_transports import TcpClientTransport
    return TcpClientTransport(host, port)
