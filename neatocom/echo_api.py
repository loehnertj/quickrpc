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

    t = StdioTransport()
    api = EchoAPI(codec=JsonCodec(), transport=t)
    api.say.connect(lambda sender="", text="": api.echo(text=text))
    api.quit.connect(lambda sender="": t.stop())

    # print('supported: {"__method":"say", "text": "hello world"} and {"__method":"quit"}')
    t.run()

if __name__ == '__main__':
    import logging
    logging.basicConfig(level='DEBUG', filename='echo_api.log')
    test()
