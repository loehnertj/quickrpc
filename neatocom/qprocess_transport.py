import sys
import logging
from PyQt4.QtCore import QProcess
from .concepts import Transport

L = lambda: logging.getLogger(__name__)


class QProcessTransport(Transport):
    '''A Transport communicating with a child process.
    
    Start the process using .start().
    
    Sent data is written to the process' stdin.
    Data is received from the process's stdout and processed
        on the Qt mainloop thread.
    '''
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

    def send(self, data, receivers=None):
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
        if pdata.startswith('{'):
            L().debug('message from child process: %s'%pdata)
        self.leftover = self.received(
            sender=self.sendername,
            data=self.leftover + data
        )

    def on_finished(self):
        L().info('Child process exited.')