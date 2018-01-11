'''
Generic transport testing rig.

Stuff entered on stdin is sent to the transport;
stuff received on the transport is written to stdout.

enter empty line to quit.

Don't use with StdioTransport or it is your own fault.
'''
import logging
L = lambda: logging.getLogger(__name__)

from quickrpc.network_transports import UdpTransport, TcpClientTransport, TcpServerTransport
#transport = UdpTransport(port=8889)
transport = TcpServerTransport(port=8889)

def run(transport):
    def handler(sender, received):
        print('Message from <%s>: %s'%(sender, received))
    # Do not do this at home
    transport.set_on_received(handler)
    L().info('starting transport')
    transport.start()
    L().info('good to go')
    while True:
        l = input()
        if not l:
            break
        transport.send(data=l.encode('utf8')+b'\n', receivers=None)
    L().info('Stopping transport')
    transport.stop()
    L().info('Exit')
        
            
    
    

if __name__=='__main__':
    logging.basicConfig(level='DEBUG')
    run(transport)
