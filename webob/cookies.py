import string, re
import time
from datetime import datetime, date, timedelta

__all__ = ['Cookie']

class Cookie(dict):
    def __init__(self, input=None):
        if input:
            self.load(input)

    def load(self, data):
        ckey = None
        for key, val in _rx_cookie.findall(data):
            if key.lower() in _cookie_propertys:
                if ckey:
                    self[ckey][key] = _unquote(val)
            elif key[0] == '$':
                continue
            else:
                self[key] = _unquote(val)
                ckey = key

    def __setitem__(self, key, val):
        if needs_quoting(key):
            return
        dict.__setitem__(self, key, Morsel(key, val))

    def __str__(self):
        return '; '.join(str(m) for _,m in sorted(self.items()))

    def __repr__(self):
        return '<%s: [%s]>' % (self.__class__.__name__, ', '.join(map(repr, self.values())))




def cookie_property(key, serialize=lambda v: v):
    def fset(self, v):
        self[key] = serialize(v)
    return property(lambda self: self[key], fset)

def serialize_max_age(v):
    if isinstance(v, timedelta):
        return str(v.seconds + v.days*24*60*60)
    elif isinstance(v, int):
        return str(v)
    else:
        return v

def serialize_cookie_date(v):
    if v is None:
        return None
    elif isinstance(v, str):
        return v
    elif isinstance(v, int):
        v = timedelta(seconds=v)
    if isinstance(v, timedelta):
        v = datetime.utcnow() + v
    if isinstance(v, (datetime, date)):
        v = v.timetuple()
    r = time.strftime('%%s, %d-%%s-%Y %H:%M:%S GMT', v)
    return r % (weekdays[v[6]], months[v[1]])

class Morsel(dict):
    __slots__ = ('name', 'value')
    def __init__(self, name, value):
        assert name.lower() not in _cookie_propertys
        assert not needs_quoting(name)
        self.name = name
        self.value = value
        self.update(dict.fromkeys(_cookie_propertys, None))

    path = cookie_property('path')
    domain = cookie_property('domain')
    comment = cookie_property('comment')
    expires = cookie_property('expires', serialize_cookie_date)
    max_age = cookie_property('max-age', serialize_max_age)
    httponly = cookie_property('httponly', bool)
    secure = cookie_property('secure', bool)

    def __setitem__(self, k, v):
        k = k.lower()
        if k in _cookie_propertys:
            dict.__setitem__(self, k, v)

    def __str__(self):
        result = []
        RA = result.append
        RA("%s=%s" % (self.name, _quote(self.value)))
        for k in _cookie_valprops:
            v = self[k]
            if v:
                assert isinstance(v, str), v
                RA("%s=%s" % (_cookie_propertys[k], _quote(v)))
        if self.secure:
            RA('secure')
        if self.httponly:
            RA('HttpOnly')
        return '; '.join(result)

    def __repr__(self):
        return '<%s: %s=%s>' % (self.__class__.__name__, self.name, repr(self.value))

_cookie_propertys = {
    "expires" : "expires",
    "path" : "Path",
    "comment" : "Comment",
    "domain" : "Domain",
    "max-age" : "Max-Age",
    "secure" : "secure",
    "httponly" : "HttpOnly",
}
_cookie_valprops = list(set(_cookie_propertys) - set(['secure', 'httponly']))
_cookie_valprops.sort()




#
# parsing
#

_re_quoted = r'"(?:[^\"]|\.)*"'  # any doublequoted string
_legal_special_chars = "~!@#$%^&*()_+=-`.?|:/(){}<>',"
_re_legal_char  = r"[\w\d%s]" % ''.join(map(r'\%s'.__mod__, _legal_special_chars))
_re_expires_val = r"\w{3},\s[\w\d-]{9,11}\s[\d:]{8}\sGMT"
_rx_cookie = re.compile(
    # key
    (r"(%s+?)" % _re_legal_char)
    # =
    + r"\s*=\s*"
    # val
    + r"(%s|%s|%s*)" % (_re_quoted, _re_expires_val, _re_legal_char)
)

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



#
# serializing
#

_trans_noop = ''.join(chr(x) for x in xrange(256))

_no_escape_special_chars = "!#$%&'*+-.^_`|~/"
_no_escape_chars = string.ascii_letters + string.digits + _no_escape_special_chars
#_no_escape_chars = string.ascii_letters + string.digits + _legal_special_chars
_escape_noop_chars = _no_escape_chars+':, '
_escape_map = dict((chr(i), '\\%03o' % i) for i in xrange(256))
_escape_map.update(zip(_escape_noop_chars, _escape_noop_chars))
_escape_map['"'] = '\\"'
_escape_map['\\'] = '\\\\'
_escape_char = _escape_map.__getitem__


weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
months = (None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def needs_quoting(v):
    return string.translate(v, _trans_noop, _no_escape_chars)

def _quote(v):
    if needs_quoting(v):
        return '"' + ''.join(map(_escape_char, v)) + '"'
    return v



#print _quote(serialize_cookie_date(0))

#assert _quote('a"\xff') == r'"a\"\377"'
#assert _unquote(r'"a\"\377"') == 'a"\xff'

#print repr(Cookie('foo=bar'))
# c = Cookie('bad_cookie=; expires="... GMT"; Max-Age=0; Path=/')
# print c
#print c['bad_cookie'].items()
