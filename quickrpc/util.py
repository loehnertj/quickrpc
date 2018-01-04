
__all__ = [
        'subclasses',
        'paren_partition'
        ]

def subclasses(cls):
    for subclass in cls.__subclasses__():
        yield from subclasses(subclass)
        yield subclass

def paren_partition(text):
    '''pop first parenthesized expression from a string.

    The text must start with one of ({[<. The function finds the matching
    closing paren, then returns a tuple of (paren_content, paren, rest):

     * paren_content is the text in parens, without the actual parens
     * paren is the opening paren
     * rest is what comes after the closing paren.

    >>> paren_partition('(a (contrived) example)(foo)bar')
    ('a (contrived) example', '(', '(foo)bar')
    '''
    op = text[0]
    if op not in '{[(<': raise ValueError('Text must start with a paren')
    cl = '}])>'['{[(<'.index(op)]
    balance = 0
    for pos, char in enumerate(text):
        if char == op: balance +=1
        if char == cl: balance -=1
        if balance == 0:
            # at the closing paren
            return text[1:pos], op, text[pos+1:]
    # fell off the end
    raise ValueError('Opening paren was not closed')


