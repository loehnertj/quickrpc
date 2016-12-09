'''
Generic transport testing rig.

Stuff entered on stdin is sent to the transport;
stuff received on the transport is written to stdout.

enter empty line to quit.

Don't use with StdioTransport or it is your own fault.
'''
import logging
L = lambda: logging.getLogger(__name__)

from neatocom.network_transports import TcpServerTransport
transport = TcpServerTransport(port=8888)

def run(transport):
    def handler(sender, received):
        print('Message from <%s>: %s'%(sender, received))
    # Do not do this at home
    handler.handle_received = handler
    transport.set_api(handler)
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
