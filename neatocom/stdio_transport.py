import sys
from .concepts import Transport


class StdioTransport(Transport):
    def stop(self):
        self.running=False

    def send(self, data, receivers=None):
        sys.stdout.buffer.write(data)

    def run(self):
        '''run, blocking.'''
        self.running = True
        leftover = b''
        while self.running:
            # FIXME: read binary
            data = input().encode('utf8')
            leftover = self.received(sender='stdio', data=leftover + data)


def test():
    t = StdioTransport()
    print('enter something, Ctrl+C to quit')
    t.run()

if __name__ == '__main__':
    test()
