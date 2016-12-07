'''Tests QUdpTransport.

Runs the EchoApi as udp server on port 8889.

connect e.g. via nc -4u <host> 8889
'''
import logging
import os, sys

from PyQt4.QtGui import QApplication, QPushButton

from neatocom.echo_api import EchoAPI
from neatocom.codecs import TerseCodec
from neatocom.QtTransports import QUdpTransport

L = lambda: logging.getLogger(__name__)


def handler_factory(api):
    msg = ['Ni!']
    def on_say(sender, text=''):
        print('echoing: %s to %s'%(text, sender))
        api.echo(receivers=[sender], text=text)
    return on_say




def test():
    a = QApplication(sys.argv)

    python = sys.executable
    transport = QUdpTransport(8889)
    api = EchoAPI(codec=TerseCodec(), transport=transport)

    on_say = handler_factory(api)
    api.say.connect(on_say)
    # no reaction on quit message
    
    transport.start()
    
    def greeting():
        api.echo(text='Hello World!')

    myButton = QPushButton()
    myButton.clicked.connect(greeting)
    myButton.show()
    
    a.exec_()

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    test()
