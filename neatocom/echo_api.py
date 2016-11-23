from .concepts import RemoteAPI, incoming, outgoing


class EchoAPI(RemoteAPI):
    '''Demo of how to use RemoteAPI.

    Echo API answers incoming `say` calls with an `echo` call.
    '''
    @incoming
    def say(self, sender="", text=""): pass

    @outgoing
    def echo(self, receivers=None, text=""): pass

    @incoming
    def quit(self, sender=""): pass


def test():
    from .json_codec import JsonCodec
    from .stdio_transport import StdioTransport
    from .mux_transport import MuxTransport

    t = StdioTransport()
    mt = MuxTransport()
    mt += t
    api = EchoAPI(codec=JsonCodec(), transport=mt)
    api.say.connect(lambda sender="", text="": api.echo(text=text))
    api.quit.connect(lambda sender="": mt.stop())
    mt.run()

if __name__ == '__main__':
    import logging
    print('supported: {"__method":"say", "text": "hello world"} and {"__method":"quit"}')
    logging.basicConfig(level='DEBUG', filename='echo_api.log')
    test()
