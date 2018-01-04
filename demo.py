from quickrpc.remote_api import RemoteAPI, incoming, outgoing
from quickrpc.transports import TcpServerTransport
from quickrpc.codecs import TerseCodec

class EchoAPI(RemoteAPI):
    '''Demo of how to use RemoteAPI.
    EchoAPI answers incoming `say` calls with an `echo` call.
    '''
    @incoming
    def say(self, sender="", text=""): pass

    @outgoing
    def echo(self, receivers=None, text=""): pass

transport = TcpServerTransport(port=8888)
api = EchoAPI(codec=TerseCodec(), transport=transport)
# on incoming "say", call "echo"
api.say.connect(lambda sender="", text="": api.echo(text=text))

transport.start()
input('Serving on :8888 - press ENTER to stop')
transport.stop()
