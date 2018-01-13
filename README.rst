QuickRPC for Python: Small, interoperable, automagic RPC library.
=================================================================

QuickRPC is a library that is designed for quick and painless setup of communication channels and Remote-call protocols.

**Python 3 only**

A remote interface is defined like so::

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
    say text:"hello"
    
(Exit via Ctrl+5 -> "quit")
    
INSTALLATION
------------

Requirements: Basically none, except for Python >= 3. For the ``QtTransports``, PyQt4 is required.

Then::

    pip install https://github.com/loehnertj/quickrpc/archive/master.zip
    
Or, download / clone and use ``python setup.py install``.
    
    
DOCUMENTATION
-------------

Please proceed to http://quickrpc.readthedocs.io/en/latest/index.html
    
TODO
----

This is a hobby project. If you need something quick, contact me or better, send a pull request. :-)

That said, proper documentation is #1 on the priority list. 
