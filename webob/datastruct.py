"""
Contains some data structures.
"""

from webob.util.dictmixin import DictMixin

key2header = {
    'CONTENT_TYPE': 'Content-Type',
    'CONTENT_LENGTH': 'Content-Length',
    'HTTP_CONTENT_TYPE': 'Content_Type',
    'HTTP_CONTENT_LENGTH': 'Content_Length',
}

header2key = dict([(v.upper(),k) for (k,v) in key2header.items()])

def _trans_key(key):
    if not isinstance(key, basestring):
        return None
    elif key in key2header:
        return key2header[key]
    elif key.startswith('HTTP_'):
        return key[5:].replace('_', '-').title()
    else:
        return None

def _trans_name(name):
    name = name.upper()
    if name in header2key:
        return header2key[name]
    return 'HTTP_'+name.replace('-', '_')

class EnvironHeaders(DictMixin):
    """An object that represents the headers as present in a
    WSGI environment.

    This object is a wrapper (with no internal state) for a WSGI
    request object, representing the CGI-style HTTP_* keys as a
    dictionary.  Because a CGI environment can only hold one value for
    each key, this dictionary is single-valued (unlike outgoing
    headers).
    """

    def __init__(self, environ):
        self.environ = environ


    def __getitem__(self, hname):
        return self.environ[_trans_name(hname)]

    def __setitem__(self, hname, value):
        self.environ[_trans_name(hname)] = value

    def __delitem__(self, hname):
        del self.environ[_trans_name(hname)]

    def keys(self):
        return filter(None, map(_trans_key, self.environ))

    def __contains__(self, hname):
        key = _trans_name(hname)
        return key and (key in self.environ)
