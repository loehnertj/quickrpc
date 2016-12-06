'''Tests connecting via QProcessTransport.

Connects to inverted echo echo_api and says something.
'''
import logging
import os, sys

from PyQt4.QtGui import QApplication, QPushButton

from neatocom.echo_api import EchoAPI
from neatocom.codecs import JsonCodec
from neatocom.qprocess_transport import QProcessTransport

L = lambda: logging.getLogger(__name__)


def send_stuff_factory(api):
    msg = ['Ni!']
    def send_stuff():
        print('saying: %s' % msg[0])
        # should be echoed immediately
        api.say(text=msg[0])
        msg[0] = msg[0] + " Ni!"
    def send_quit():
        print('sending quit message')
        api.quit()
    return send_stuff, send_quit



def on_echo(sender, text=""):
    print("echoed: '%s'" % text)


def test():
    a = QApplication(sys.argv)

    python = sys.executable
    transport = QProcessTransport('%s -m neatocom.echo_api' % python)
    api = EchoAPI(codec=JsonCodec(), transport=transport)
    api.invert()
    api.echo.connect(on_echo)

    transport.start()
    send_stuff, send_quit = send_stuff_factory(api)

    myButton = QPushButton()
    myButton.clicked.connect(send_stuff)
    myButton.show()
    
    a.lastWindowClosed.connect(send_quit)
    a.exec_()

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    test()
