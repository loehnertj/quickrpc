'''Defines a basic :class:`Promise` class.

A Promise (also known as a Deferred or a Future) is like an order slip
for something that is still being produced.

This is just a barebone implementation, with method names aligned with
:class:`concurrent.Future` from the standard lib.
'''

from enum import Enum
from threading import Event

__all__ = ['Promise', 'PromiseError', 'PromiseTimeoutError', 'PromiseDoneError']

class PromiseState(Enum):
    pending = 0
    fulfilled = 1
    failed = 2
    
class PromiseError(Exception):
    '''promise-related error'''
class PromiseTimeoutError(PromiseError, TimeoutError):
    '''waiting for the promise took too long.'''
class PromiseDoneError(PromiseError):
    '''raised to the promise issuer if a result or exception was already set.'''

class Promise(object):
    '''Encapsulates a result that will arrive later.

    A Promise (also known as a Deferred or a Future) is like an order slip
    for something that is still being produced.
    
    Promises are dispensed by asynchronous functions. Calling .result()
    waits until the operation is complete, then returns the result.
    '''
    
    def __init__(self):
        self._state = PromiseState.pending
        self._evt = Event()
        self._result = None
        
    def set_result(self, val):
        '''called by the promise issuer to set the result.'''
        self._set(PromiseState.fulfilled, val)
    
    def set_exception(self, exception):
        '''called by the promise issuer to indicate failure.'''
        self._set(PromiseState.failed, exception)
        
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
        '''
        if not self._evt.wait(timeout):
            raise PromiseTimeoutError()
            
        if self._state == PromiseState.fulfilled:
            return self._result 
        elif self._state == PromiseState.failed:
            raise self._result
        else:
            assert False, 'unexpected Promise state'
            
    __call__ = result
