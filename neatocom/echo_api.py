from .concepts import RemoteAPI, incoming, outgoing

class EchoAPI(RemoteAPI):
    '''Demo of how to use RemoteAPI.
    
    Echo API answers incoming `say` calls with an `echo` call.
    '''
    @incoming
    def say(self, sender="", text=""): pass
        
    @outgoing
    def echo(self, receivers=None, text=""): pass



def test():
    from .json_codec import JsonCodec
    from .stdio_transport import StdioTransport
    
    t = StdioTransport()
    api = EchoAPI(codec=JsonCodec(), transport=t)
    api.say.connect(lambda sender="", text="": api.echo(text=text))
    
    print('supported: {"__method":"say", "text": "hello world"}')
    t.run()
    
if __name__=='__main__':
    test()