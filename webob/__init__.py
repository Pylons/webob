import cgi
from webob.datetime_utils import *
from webob.request import *
from webob.response import *

__all__ = [
    'Request', 'Response',
    'UTC', 'day', 'week', 'hour', 'minute', 'second', 'month', 'year',
    'html_escape'
]

def html_escape(s):
    """HTML-escape a string or object

    This converts any non-string objects passed into it to strings
    (actually, using ``unicode()``).  All values returned are
    non-unicode strings (using ``&#num;`` entities for all non-ASCII
    characters).

    None is treated specially, and returns the empty string.
    """
    if s is None:
        return ''
    if hasattr(s, '__html__'):
        return s.__html__()
    if not isinstance(s, basestring):
        if hasattr(s, '__unicode__'):
            s = unicode(s)
        else:
            s = str(s)
    s = cgi.escape(s, True)
    if isinstance(s, unicode):
        s = s.encode('ascii', 'xmlcharrefreplace')
    return s


BaseRequest.ResponseClass = Response
Response.RequestClass = Request



