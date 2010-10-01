import string, re

__all__ = ['Cookie']

_nulljoin = ''.join
_semispacejoin = '; '.join
_spacejoin = ' '.join

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
        return '"' + _nulljoin(map(_escape_char, v)) + '"'
    return v

_rx_unquote = re.compile(r'\\([0-3][0-7][0-7]|.)')

def _unquote(v):
    if not v or v[0] != v[-1] != '"':
        return v
    v = v[1:-1]
    def _ch_unquote(m):
        v = m.group(1)
        if v.isdigit():
            return chr(int(v, 8))
        return v
    return _rx_unquote.sub(_ch_unquote, v)

#assert _quote('a"\xff') == r'"a\"\377"'
#assert _unquote(r'"a\"\377"') == 'a"\xff'




# The _getdate() routine is used to set the expiration time in
# the cookie's HTTP header.      By default, _getdate() returns the
# current time in the appropriate "expires" format for a
# Set-Cookie header.     The one optional argument is an offset from
# now, in seconds.      For example, an offset of -3600 means "one hour ago".
# The offset may be a floating point number.
#

_weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

_monthname = [None,
              'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def _getdate(future=0, weekdayname=_weekdayname, monthname=_monthname):
    from time import gmtime, time
    now = time()
    year, month, day, hh, mm, ss, wd, y, z = gmtime(now + future)
    return "%s, %02d-%3s-%4d %02d:%02d:%02d GMT" % \
           (weekdayname[wd], day, monthname[month], year, hh, mm, ss)


# A class to hold ONE key,value pair.
# In a cookie, each such pair may have several attributes.
#       so this class is used to keep the attributes associated
#       with the appropriate key,value pair.
# This class also includes a coded_value attribute, which
#       is used to hold the network representation of the
#       value.  This is most useful when Python objects are
#       pickled for network transit.


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
        self.key = self.value = self.coded_value = None
        # Set default attributes
        for K in _cookie_props:
            dict.__setitem__(self, K, "")
        if name is not None:
            self.set(name, value, value)



    def __setitem__(self, K, V):
        K = K.lower()
        if K in _cookie_props:
            dict.__setitem__(self, K, V)

    def set(self, key, val, coded_val):
        assert key.lower() not in _cookie_props
        if needs_quoting(key):
            return
        self.key = key
        self.value = val
        self.coded_value = coded_val

    def output(self, attrs=None, header = "Set-Cookie:"):
        return "%s %s" % (header, self.OutputString(attrs))

    __str__ = output

    def __repr__(self):
        return '<%s: %s=%s>' % (self.__class__.__name__, self.key, repr(self.value))

    def OutputString(self, attrs=None):
        httponly = self.pop('httponly', False)

        result = []
        RA = result.append

        # First, the key=value pair
        RA("%s=%s" % (self.key, self.coded_value))

        # Now add any defined attributes
        if attrs is None:
            attrs = _cookie_props
        items = self.items()
        items.sort()
        for K,V in items:
            if V == "": continue
            if K not in attrs: continue
            if K == "expires" and type(V) == type(1):
                RA("%s=%s" % (_cookie_props[K], _getdate(V)))
            elif K == "max-age" and type(V) == type(1):
                RA("%s=%d" % (_cookie_props[K], V))
            elif K == "secure":
                RA(str(_cookie_props[K]))
            elif K == "httponly":
                RA(str(_cookie_props[K]))
            else:
                RA("%s=%s" % (_cookie_props[K], V))

        result = _semispacejoin(result)
        result = result.rstrip('\t ;')
        if httponly:
            result += '; HttpOnly'
        return result



#
# Pattern for finding cookie
#
# This used to be strict parsing based on the RFC2109 and RFC2068
# specifications.  I have since discovered that MSIE 3.0x doesn't
# follow the character rules outlined in those specs.  As a
# result, the parsing rules here are less strict.
#

_re_legal_chars  = r"[\w\d!#%&'~_`><@,:/\$\*\+\-\.\^\|\)\(\?\}\{\=]"
_rx_cookie = re.compile(
    r"(?x)"                       # This is a Verbose pattern
    r"(?P<key>"                   # Start of group 'key'
    ""+ _re_legal_chars +"+?"     # Any word of at least one letter, nongreedy
    r")"                          # End of group 'key'
    r"\s*=\s*"                    # Equal Sign
    r"(?P<val>"                   # Start of group 'val'
    r'"(?:[^\\"]|\\.)*"'            # Any doublequoted string
    r"|"                            # or
    r"\w{3},\s[\w\d-]{9,11}\s[\d:]{8}\sGMT" # Special case for "expires" attr
    r"|"                            # or
    ""+ _re_legal_chars +"*"        # Any word or empty string
    r")"                          # End of group 'val'
    r"\s*;?"                      # Probably ending in a semi-colon
)


class Cookie(dict):
    def __init__(self, input=None):
        if not input:
            return
        M = None
        for K,V in _rx_cookie.findall(input):
            if K.lower() in _cookie_props:
                if M:
                    M[K] = _unquote(V)
            elif K[0] == '$':
                continue
            else:
                rval, cval = self.value_decode(V)
                M = self._set(K, rval, cval)


    @staticmethod
    def value_decode(val):
        """real_value, coded_value = value_decode(STRING)
        Called prior to setting a cookie's value from the network
        representation.  The VALUE is the value read from HTTP
        header.
        Override this function to modify the behavior of cookies.
        """
        return val, val
        #return _unquote(val), val

    @staticmethod
    def value_encode(val):
        """real_value, coded_value = value_encode(VALUE)
        Called prior to setting a cookie's value from the dictionary
        representation.  The VALUE is the value being assigned.
        Override this function to modify the behavior of cookies.
        """
        strval = str(val)
        return strval, strval
        #return strval, _quote(strval)



    def _set(self, key, real_value, coded_value):
        """Private method for setting a cookie's value"""
        morsel = self.get(key, Morsel())
        morsel.set(key, real_value, coded_value)
        dict.__setitem__(self, key, morsel)
        return morsel

    def __setitem__(self, key, value):
        """Dictionary style assignment."""
        rval, cval = self.value_encode(value)
        self._set(key, rval, cval)


    def output(self, attrs=None, header="Set-Cookie:", sep="\015\012"):
        """Return a string suitable for HTTP."""
        result = []
        items = self.items()
        items.sort()
        for K,V in items:
            result.append(V.output(attrs, header))
        return sep.join(result)

    __str__ = output

    def __repr__(self):
        L = []
        items = self.items()
        items.sort()
        for K,V in items:
            L.append('%s=%s' % (K,repr(V.value)))
        return '<%s: %s>' % (self.__class__.__name__, _spacejoin(L))

