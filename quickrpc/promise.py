'''Defines a basic :class:`Promise` class.

A Promise (also known as a Deferred or a Future) is like an order slip
for something that is still being produced.

This is just a barebone implementation, with method names aligned with
:class:`concurrent.Future` from the standard lib.
'''

import logging
from enum import Enum
from threading import Event, current_thread

L = lambda: logging.getLogger(__name__)

__all__ = ['Promise', 'PromiseError', 'PromiseTimeoutError', 'PromiseDoneError', 'PromiseDeadlockError']

class PromiseState(Enum):
    pending = 0
    fulfilled = 1
    failed = 2
    
class PromiseError(Exception):
    '''promise-related error'''
class PromiseTimeoutError(PromiseError, TimeoutError):
    '''waiting for the promise took too long.'''
class PromiseDoneError(PromiseError, RuntimeError):
    '''raised to the promise issuer if a result or exception was already set.'''
class PromiseDeadlockError(PromiseError, RuntimeError):
    '''raised if the result-setter thread tries to wait for the result (i.e. itself).'''

class Promise(object):
    '''Encapsulates a result that will arrive later.

    A Promise (also known as a Deferred or a Future) is like an order slip
    for something that is still being produced.
    
    Promises are dispensed by asynchronous functions. Calling .result()
    waits until the operation is complete, then returns the result.

    You can also use .then(callback) to have the promise call you with the result.

    The constructor takes an argument ``setter_thread``, which should be the
    thread that will set the result later. If not given, the current thread
    is assumed (which will usually be the case). The ``setter_thread`` is
    used to provide basic deadlock protection.
    '''
    
    def __init__(self, setter_thread=None):
        self._state = PromiseState.pending
        self._evt = Event()
        self._result = None
        self._setter_thread = setter_thread or current_thread()
        self._callback = lambda result: None
        self._errback = lambda error: None
        
    def set_result(self, val):
        '''called by the promise issuer to set the result.'''
        self._set(PromiseState.fulfilled, val)
        try:
            self._callback(val)
        except Exception as e:
            L().error('Promise callback raised an exception', exc_info=True)
    
    def set_exception(self, exception):
        '''called by the promise issuer to indicate failure.'''
        if not isinstance(exception, BaseException):
            # shrinkwrap whatever it is
            exception = Exception(repr(exception))
        self._set(PromiseState.failed, exception)
        try:
            self._errback(exception)
        except Exception as e:
            L().error('Promise errback raised an exception', exc_info=True)
        
    def _set(self, state, result):
        if self._evt.is_set():
            raise PromiseDoneError()
        self._state = state
        self._result = result
        self._evt.set()
    
    def result(self, timeout=1.0):
        '''Return the result, waiting for it if necessary.
        
        If the promise failed, this will raise the exception that the issuer gave.
        
        If the promise is still unfulfilled after the `timeout` (in seconds) elapsed,
        PromiseTimeoutError is raised.

        If the promise is unfulfilled and the calling thread is the designated
        promise-setter thread, PromiseDeadlockError is raised immediately.
        '''
        L().debug('Promise.result: current_Thread is %r and setter_thread is %r'%(current_thread(), self._setter_thread))
        if not self._evt.is_set() and current_thread() is self._setter_thread:
            raise PromiseDeadlockError('The thread would wait for itself')
        if not self._evt.wait(timeout):
            raise PromiseTimeoutError()
            
        if self._state == PromiseState.fulfilled:
            return self._result 
        elif self._state == PromiseState.failed:
            raise self._result
        else:
            assert False, 'unexpected Promise state'

    def then(self, callback, errback=None):
        '''set handler to run as soon as the result is set.

        callback takes the result as single argument.
        
        You can also set an errback that is called in case of an exception.
        If not set, the exception will be passed to callback as result.

        If the result already arrived, callback or errback is called immediately.
        '''
        self._callback = callback
        self._errback = errback or callback

        if self._state == PromiseState.fulfilled:
            self._callback(self._result)
        elif self._state == PromiseState.failed:
            self._errback(self._result)


    __call__ = result

