import sys
from .concepts import Transport

class StdioTransport(Transport):
    def send(self, data, receivers=None):
        sys.stdout.buffer.write(data)
        
    def run(self):
        '''run, blocking.'''
        while True:
            # FIXME: read binary
            data = input().encode('utf8')
            if data==b'':
                return
            leftover = self.received(sender='stdio', data=data)
            

def test():
    t = StdioTransport()
    print('enter something, empty line to quit')
    t.run()
    
if __name__=='__main__':
    test()