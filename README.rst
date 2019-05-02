QuickRPC for Python: Small, interoperable, automagic RPC library.
=================================================================

QuickRPC is a library that is designed for quick and painless setup of communication channels and Remote-call protocols.

**Python 3 only**

A remote interface is defined like so::

    from quickrpc import RemoteAPI, incoming, outgoing

    class EchoAPI(RemoteAPI):
        '''Demo of how to use RemoteAPI.
        EchoAPI answers incoming `say` calls with an `echo` call.
        '''
        @incoming
        def say(self, sender="", text=""): pass

        @outgoing
        def echo(self, receivers=None, text=""): pass
    
The interface is used over a `Transport`, which might e.g. be a TCP connection or Stdio::

    api = EchoAPI(codec='jsonrpc', transport='tcpserv::8888')
    # on incoming "say", call "echo"
    api.say.connect(lambda sender="", text="": api.echo(text=text))
    
    # transport starts in a new thread.
    api.transport.start()
    input('Serving on :8888 - press ENTER to stop')
    api.transport.stop()
    
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

LICENSE
-------

MIT License: https://github.com/loehnertj/quickrpc/blob/master/LICENSE
    
    
DOCUMENTATION
-------------

Please proceed to http://quickrpc.readthedocs.io/en/latest/index.html
    
TODO
----

This is a hobby project. If you need something quick, contact me or better, send a pull request. :-)

Things I might add in the future: In-process "loopback" transport; Serial interface transport; ``msgpack`` Codec.

SSH support would be really cool but don't hold your breath for that.
