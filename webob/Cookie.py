import string, re

__all__ = ['Cookie']

_legal_chars = string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~"
_trans_noop = ''.join(chr(x) for x in xrange(256))


_escape_map = dict((chr(i), '\\%03o' % i) for i in xrange(256))
_escape_map.update(zip(_legal_chars, _legal_chars))
_escape_map['"'] = '\\"'
_escape_map['\\'] = '\\\\'
_escape_char = _escape_map.__getitem__

def needs_quoting(v):
    return string.translate(v, _trans_noop, _legal_chars)

def _quote(v):
    if needs_quoting(v):
        return '"' + ''.join(map(_escape_char, v)) + '"'
    return v

_rx_unquote = re.compile(r'\\([0-3][0-7][0-7]|.)')

def _unquote(v):
    if v and v[0] == v[-1] == '"':
        v = v[1:-1]
        def _ch_unquote(m):
            v = m.group(1)
            if v.isdigit():
                return chr(int(v, 8))
            return v
        v = _rx_unquote.sub(_ch_unquote, v)
    return v


#assert _quote('a"\xff') == r'"a\"\377"'
#assert _unquote(r'"a\"\377"') == 'a"\xff'




# The _getdate() routine is used to set the expiration time in
# the cookie's HTTP header.      By default, _getdate() returns the
# current time in the appropriate "expires" format for a
# Set-Cookie header.     The one optional argument is an offset from
# now, in seconds.      For example, an offset of -3600 means "one hour ago".
# The offset may be a floating point number.

from time import gmtime, time
from datetime_utils import months, weekdays

def _getdate(future=0):
    now = time()
    year, month, day, hh, mm, ss, wd, y, z = gmtime(now + future)
    return "%s, %02d-%3s-%4d %02d:%02d:%02d GMT" % \
           (weekdays[wd], day, months[month], year, hh, mm, ss)


# A class to hold ONE key,value pair.
# In a cookie, each such pair may have several attributes.
#       so this class is used to keep the attributes associated
#       with the appropriate key,value pair.


_cookie_props = {
    "expires" : "expires",
    "path" : "Path",
    "comment" : "Comment",
    "domain" : "Domain",
    "max-age" : "Max-Age",
    "secure" : "secure",
    "httponly" : "HttpOnly",
    "version" : "Version",
}

class Morsel(dict):
    def __init__(self, name=None, value=None):
        # Set defaults
        self.key = self.value = None
        # Set default attributes
        for K in _cookie_props:
            dict.__setitem__(self, K, "")
        if name is not None:
            self.set(name, value)



    def __setitem__(self, K, V):
        K = K.lower()
        if K in _cookie_props:
            dict.__setitem__(self, K, V)

    def set(self, key, val):
        assert key.lower() not in _cookie_props
        if needs_quoting(key):
            return
        self.key = key
        self.value = val

    def output(self, header="Set-Cookie:"):
        return "%s %s" % (header, self.OutputString())

    __str__ = output

    def __repr__(self):
        return '<%s: %s=%s>' % (self.__class__.__name__, self.key, repr(self.value))

    def OutputString(self):
        httponly = False

        result = []
        RA = result.append
        # First, the key=value pair
        RA("%s=%s" % (self.key, _quote(self.value)))

        items = self.items()
        items.sort()
        for K,V in items:
            if V == "": continue
            if K not in _cookie_props: continue
            if K == "expires" and type(V) == type(1):
                RA("%s=%s" % (_cookie_props[K], _getdate(V)))
            elif K == "max-age" and type(V) == type(1):
                RA("%s=%d" % (_cookie_props[K], V))
            elif K == "secure":
                RA(str(_cookie_props[K]))
            elif K == "httponly":
                httponly = True
            else:
                RA("%s=%s" % (_cookie_props[K], V))
        if httponly:
            RA('HttpOnly')
        result = '; '.join(result)
        return result



_re_quoted = r'"(?:[^\"]|\.)*"'  # any doublequoted string
_re_legal_char  = r"[\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\=]"
_re_expires_val = r"\w{3},\s[\w\d-]{9,11}\s[\d:]{8}\sGMT"
_rx_cookie = re.compile(
    # key
    (r"(%s+?)" % _re_legal_char)
    # =
    + r"\s*=\s*"
    # val
    + r"(%s|%s|%s*)" % (_re_quoted, _re_expires_val, _re_legal_char)
)


class Cookie(dict):
    def __init__(self, input=None):
        if not input:
            return
        M = None
        for key, val in _rx_cookie.findall(input):
            if key.lower() in _cookie_props:
                if M:
                    M[key] = _unquote(val)
            elif key[0] == '$':
                continue
            else:
                M = self._set(key, _unquote(val))

    def _set(self, key, val):
        morsel = self.get(key, Morsel())
        morsel.set(key, val)
        dict.__setitem__(self, key, morsel)
        return morsel

    __setitem__ = _set

    def output(self, attrs=None, header="Set-Cookie:", sep="\r\n"):
        """Return a string suitable for HTTP."""
        return sep.join(m.output(attrs, header) for _,v in sorted(self.items()))

    __str__ = output

    def __repr__(self):
        items = ['%s=%s' % (k, v.value) for k,v in sorted(self.items())]
        return '<%s: %s>' % (self.__class__.__name__, ' '.join(items))


#print repr(Cookie('foo=bar'))
