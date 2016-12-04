import sys
import logging
from PyQt4.QtNetwork import QTcpSocket, QAbstractSocket
from .concepts import Transport

L = lambda: logging.getLogger(__name__)


class QTcpTransport(Transport):
    '''A Transport connecting to a TCP server.
    
    Connect using .start().
    
    Received data is processed on the Qt mainloop thread.
    '''
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