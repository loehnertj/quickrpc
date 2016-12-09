'''
UDP announcer.
'''
import logging
import sys
L = lambda: logging.getLogger(__name__)

from neatocom.network_transports import UdpTransport
from neatocom.announcer_api import make_announcer

def run(port):
    transport = UdpTransport(port=port)
    announcer = make_announcer(transport, description="Test announcer")
    L().info('starting transport, port %d'%port)
    transport.start()
    L().info('running')
    input('Press enter to quit')
    L().info('Stopping transport')
    transport.stop()
    L().info('Exit')

if __name__=='__main__':
    port = 8888
    if len(sys.argv) > 1:
        port = int(sys.argv[2])
    logging.basicConfig(level='DEBUG')
    run(port)
