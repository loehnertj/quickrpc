'''Security Providers.'''

import logging
from .util import subclasses

__all__ = [
    'SecurityError',
    'InvalidSignatureError',
    'UnknownUserError',
    'Security',
    'NullSecurity',
    'NoSecurity',
]
    
    

L = lambda: logging.getLogger(__name__)

class SecurityError(Exception):
    '''Security-related error'''

class InvalidSignatureError(SecurityError):
    '''Received message had an invalid signature'''
    
class UnknownUserError(SecurityError):
    '''User account not found'''


class Security:
    '''Base class for Security providers.
    
    A security provider has ``sec_in`` and ``sec_out`` methods, which are used 
    to process inbound and outbound messages, respectively.
    
    Apart from that, it is up to the security provider what it does to the 
    messages and how it manages authentication.
    '''
    shorthand = ''
    
    @classmethod
    def fromstring(cls, expression):
        '''Creates a security instance from a given string expression.

        The expression must be "<shorthand>:<specific parameters>",
        with shorthand being the wanted Security's .shorthand property.
        For the specific parameters, see the respective Security's .fromstring
        method.
        '''
        shorthand, _, expr = expression.partition(':')
        for subclass in subclasses(cls):
            if subclass.shorthand == shorthand:
                return subclass.fromstring(expression)
        raise ValueError('Could not find a security class with shorthand %s'%shorthand)
    
    def sec_out(self, payload):
        '''Secure an outbound message.
        
        Parameters:
            payload (bytes): Payload data for the frame.
            
        Returns ``(secinfo, new_payload)``:
        
            * ``secinfo`` (dict): security information, dictionary str->str
            * ``new_payload`` (bytes): transformed payload; ``None`` indicates that original payload can be used.
            
        ``secinfo`` can contain arbitrary keys specified by the subclass.
        
        The provider can e.g. calculate a signature and/or encrypt the payload.
        '''
        return {}, None
        
    def sec_in(self, payload, secinfo):
        '''Secure an inbound message.
        
        Parameters:
            payload (bytes): Payload as received.
            secinfo (dict of str -> str): Security headers as received.
            
        Returns:
            new_payload (bytes); ``None`` indicates that received payload can be used.
            
        The provider can e.g. decrypt the payload and or check the signature 
        (raising an exception on failure).
        '''
        return None
        
        
class NullSecurity(Security):
    '''no security added, no user management at all (anonymous communication).
    
    Default if nothing is specified.
    '''
    shorthand = 'null'
    @classmethod
    def fromstring(cls, expression):
        return cls()
    sec_out = None
    sec_in = None
    
    
class NoSecurity(Security):
    '''Provides transmission of a username, without any checking.
    
    There is no validation or message integrity checking. 
    
    Only use this if you absolutely trust each communication 
    endpoint. ... Actually, please don't.
    
    To specify username for outbound messages, set the ``user`` attribute.
    '''
    
    shorthand = 'blindly_believe_everything'
    def __init__(self, user=''):
        self.user = user
        
    @classmethod
    def fromstring(cls, expression):
        return cls()
        
    def sec_out(self, payload):
        '''return ``self.user`` as username.'''
        return {'user': self.user}, None
    
    def sec_in(self, payload, secinfo):
        '''does nothing'''
        return None