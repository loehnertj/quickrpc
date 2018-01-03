QuickRPC for Python: Small, interoperable, automagic RPC library.
-----

QuickRPC is a library that is designed for quick and painless setup of communication channels and Remote-call protocols.



A remote interface is defined like so::

    from quickrpc.remote_api import RemoteAPI
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
    
The interface is used over a `Transport`, which might e.g. be a TCP connection or Stdio::

    transport = TcpServerTransport(port=8888)
    api = EchoAPI(codec=TerseCodec(), transport=transport)
    # on incoming "say", call "echo"
    api.say.connect(lambda sender="", text="": api.echo(text=text))
    
    transport.start()
    input('Serving on :8888 - press ENTER to stop')
    transport.stop()
    
That's it! You could now connect to the server e.g. via telnet::
    
    $ telnet localhost 8888
    say text="hello"
    
    
TODO
----

This is a hobby project. If you need something quick, contact me or better, send a pull request. :-)

That said, proper documentation is #1 on the priority list. For now, use the source.
