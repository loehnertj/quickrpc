'''transports based on Qt communication classes, running in the Qt event loop.
'''

__all__ = [
    'QProcessTransport',
    'QTcpTransport',
]

import sys
import logging
from PyQt4.QtCore import QProcess
from PyQt4.QtNetwork import QUdpSocket, QTcpSocket, QAbstractSocket, QHostAddress
from .transports import Transport
from .util import paren_partition

L = lambda: logging.getLogger(__name__)


class QProcessTransport(Transport):
    '''A Transport communicating with a child process.
    
    Start the process using .start().
    
    Sent data is written to the process' stdin.
    
    Data is received from the process's stdout and processed on the Qt mainloop 
    thread.
    '''
    shorthand='qprocess'
    @classmethod
    def fromstring(cls, expression):
        '''qprocess:(<commandline>)'''
        _, _, expr = expression.partition(':')
        cmdline, _, _ = paren_partition(expr)
        return cls(cmdline, sendername=expression)

    def __init__(self, cmdline, sendername='qprocess'):
        self.cmdline = cmdline
        self.sendername = sendername
        self.leftover = b''
        self.process = QProcess()
        self.process.readyRead.connect(self.on_ready_read)
        self.process.finished.connect(self.on_finished)

    def start(self):
        L().debug('starting: %r'%self.cmdline)
        self.process.start(self.cmdline)
        
    def stop(self, kill=False):
        if kill:
            self.process.kill()
        else:
            self.process.terminate()
            self.process.waitForFinished()

    def send(self, data, receivers=None):
        if receivers is not None and self.sendername not in receivers:
            return
        L().debug('message to child processs: %s'%data)
        self.process.write(data.decode('utf8'))

    def on_ready_read(self):
        data = self.process.readAllStandardOutput().data()
        errors = self.process.readAllStandardError().data().decode('utf8')
        if errors:
            L().error('Error from child process:\n%s' % errors)
        pdata = data.decode('utf8')
        if len(pdata) > 100:
            pdata = pdata[:100] + '...'
        #if pdata.startswith('{'):
        L().debug('message from child process: %s'%pdata)
        self.leftover = self.received(
            sender=self.sendername,
            data=self.leftover + data
        )

    def on_finished(self):
        L().info('Child process exited.')


class QTcpTransport(Transport):
    '''A Transport connecting to a TCP server.
    
    Connect using .start().
    
    Received data is processed on the Qt mainloop thread.
    '''
    shorthand='qtcp'
    @classmethod
    def fromstring(cls, expression):
        '''qtcp:<host>:<port>'''
        _, host, port = expression.split(':')
        return cls(host=host, port=int(port), sendername=expression)

    def __init__(self, host, port, sendername='qtcp'):
        self.address = (host, port)
        self.sendername = sendername
        self.leftover = b''
        self.socket = QTcpSocket()
        self.socket.readyRead.connect(self.on_ready_read)
        self.socket.error.connect(self.on_error)
        self.socket.connected.connect(self.on_connect)

    def start(self):
        if self.socket.state() != QAbstractSocket.UnconnectedState:
            L().debug('start(): Socket is not in UnconnectedState, doing nothing')
            return
        L().debug('connecting to: %s'%(self.address,))
        self.socket.connectToHost(self.address[0], self.address[1])
        
    def stop(self):
        self.socket.flush()
        self.socket.disconnectFromHost()

    def send(self, data, receivers=None):
        if receivers is not None and self.sendername not in receivers:
            return
        L().debug('message to tcp server: %s'%data)
        self.socket.write(data.decode('utf8'))

    def on_ready_read(self):
        data = self.socket.readAll().data()
        pdata = data
        if len(pdata) > 100:
            pdata = pdata[:100] + b'...'
        #if pdata.startswith('{'):
        L().debug('message from tcp server: %s'%pdata)
        self.leftover = self.received(
            sender=self.sendername,
            data=self.leftover + data
        )
        
    def on_connect(self):
         L().info('QTcpSocket: Established connection to %s'%(self.address,))

    def on_error(self, error):
        L().info('QTcpSocket raised error: %s'%error)
        
        
class QUdpTransport(Transport):
    '''A Transport sending and receiving UDP datagrams.
    
    Connectionless - sender/receiver are IP addresses. Sending and receiving is 
    done on the same port. Sending with receiver=None makes a broadcast.
    
    Use messages > 500 Byte at your own peril.
    
    Received data is processed on the Qt mainloop thread.
    '''
    shorthand='qudp'
    @classmethod
    def fromstring(cls, expression):
        '''qudp:<port>'''
        _, port = expression.split(':')
        return cls(port=int(port))

    def __init__(self, port):
        self.port = port
        self.leftover = b''
        self.socket = QUdpSocket()
        self.socket.readyRead.connect(self.on_ready_read)
        self.socket.error.connect(self.on_error)

    def start(self):
        if self.socket.state() != QAbstractSocket.UnconnectedState:
            L().debug('QUdpSocket.start(): Socket is not in UnconnectedState, doing nothing')
            return
        L().debug('QUdpTransport: binding to port %d'%(self.port,))
        self.socket.bind(self.port, QUdpSocket.ShareAddress)
        
    def stop(self):
        self.socket.flush()
        self.socket.close()

    def send(self, data, receivers=None):
        L().debug('message to udp %s: %s'%(receivers,data))
        data = data.decode('utf8')
        if receivers:
            for receiver in receivers:
                self.socket.writeDatagram(data, QHostAddress(receiver), self.port)
        else:
            self.socket.writeDatagram(data, QHostAddress.Broadcast, self.port)

    def on_ready_read(self):
        while self.socket.hasPendingDatagrams():
            data, host, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
            assert isinstance(data, bytes)
            sender = host.toString()
            pdata = data
            if len(pdata) > 100:
                pdata = pdata[:100] + b'...'
            L().debug('UDP message from %s: %s'%(sender, pdata))
            self.leftover = self.received(
                sender=sender,
                data=self.leftover + data
            )

    def on_error(self, error):
        L().info('QTcpSocket raised error: %s'%error)
