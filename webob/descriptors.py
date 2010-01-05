import warnings
import re, textwrap
from datetime import datetime, date

from webob.byterange import Range, ContentRange
from webob.etag import AnyETag, NoETag, ETagMatcher, IfRange, NoIfRange
from webob import datetime_utils


CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)
QUOTES_RE = re.compile('"(.*)"')
SCHEME_RE = re.compile(r'^[a-z]+:', re.I)


class environ_getter(object):
    """For delegating an attribute to a key in self.environ."""

    def __init__(self, key, default='', default_factory=None,
                 settable=True, deletable=True, doc=None,
                 rfc_section=None):
        self.key = key
        self.default = default
        self.default_factory = default_factory
        self.settable = settable
        self.deletable = deletable
        docstring = "Gets"
        if self.settable:
            docstring += " and sets"
        if self.deletable:
            docstring += " and deletes"
        docstring += " the %r key from the environment." % self.key
        docstring += _rfc_reference(self.key, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        if self.key not in obj.environ:
            if self.default_factory:
                val = obj.environ[self.key] = self.default_factory()
                return val
            else:
                return self.default
        return obj.environ[self.key]

    def __set__(self, obj, value):
        if not self.settable:
            raise AttributeError("Read-only attribute (key %r)" % self.key)
        if value is None:
            if self.key in obj.environ:
                del obj.environ[self.key]
        else:
            obj.environ[self.key] = value

    def __delete__(self, obj):
        if not self.deletable:
            raise AttributeError("You cannot delete the key %r" % self.key)
        del obj.environ[self.key]

    def __repr__(self):
        return '<Proxy for WSGI environ %r key>' % self.key

def _rfc_reference(header, section):
    if not section:
        return ''
    major_section = section.split('.')[0]
    link = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec%s.html#sec%s' % (
        major_section, section)
    if header.startswith('HTTP_'):
        header = header[5:].title().replace('_', '-')
    return "  For more information on %s see `section %s <%s>`_." % (
        header, section, link)


class header_getter(object):
    """For delegating an attribute to a header in self.headers"""

    def __init__(self, header, default=None,
                 settable=True, deletable=True, doc=None, rfc_section=None):
        self.header = header
        self.default = default
        self.settable = settable
        self.deletable = deletable
        docstring = "Gets"
        if self.settable:
            docstring += " and sets"
        if self.deletable:
            docstring += " and deletes"
        docstring += " the %s header" % self.header
        docstring += _rfc_reference(self.header, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.headers.get(self.header, self.default)

    def __set__(self, obj, value):
        if not self.settable:
            raise AttributeError("Read-only attribute (header %s)" % self.header)
        if value is None:
            if self.header in obj.headers:
                del obj.headers[self.header]
        else:
            if isinstance(value, unicode):
                # This is the standard encoding for headers:
                value = value.encode('ISO-8859-1')
            obj.headers[self.header] = value

    def __delete__(self, obj):
        if not self.deletable:
            raise AttributeError("You cannot delete the header %s" % self.header)
        del obj.headers[self.header]

    def __repr__(self):
        return '<Proxy for header %s>' % self.header

class set_via_call(object):
    def __init__(self, func, adapt_args=None):
        self.func = func
        self.adapt_args = adapt_args
    def __get__(self, obj, type=None):
        return self.__class__(self.func.__get__(obj, type))
    def __set__(self, obj, value):
        if self.adapt_args is None:
            args, kw = (value,), {}
        else:
            result = self.adapt_args(value)
            if result is None:
                return
            args, kw = result
        self.func(obj, *args, **kw)
    def __repr__(self):
        return 'set_via_call(%r)' % self.func
    def __call__(self, *args, **kw):
        return self.func(*args, **kw)


class converter(object):
    """
    Wraps a descriptor, and applies additional conversions when reading and writing
    """
    def __init__(self, descriptor, getter_converter, setter_converter, convert_name=None, doc=None, converter_args=()):
        self.descriptor = descriptor
        self.getter_converter = getter_converter
        self.setter_converter = setter_converter
        self.convert_name = convert_name
        self.converter_args = converter_args
        docstring = descriptor.__doc__ or ''
        docstring += "  Converts it as a "
        if convert_name:
            docstring += convert_name + '.'
        else:
            docstring += "%r and %r." % (getter_converter, setter_converter)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = self.descriptor.__get__(obj, type)
        return self.getter_converter(value, *self.converter_args)

    def __set__(self, obj, value):
        value = self.setter_converter(value, *self.converter_args)
        self.descriptor.__set__(obj, value)

    def __delete__(self, obj):
        self.descriptor.__delete__(obj)

    def __repr__(self):
        if self.convert_name:
            name = ' %s' % self.convert_name
        else:
            name = ''
        return '<Converted %r%s>' % (self.descriptor, name)


class deprecated_property(object):
    """
    Wraps a descriptor, with a deprecation warning or error
    """
    def __init__(self, descriptor, attr, message, warning=True):
        self.descriptor = descriptor
        self.attr = attr
        self.message = message
        self.warning = warning

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        self.warn()
        return self.descriptor.__get__(obj, type)

    def __set__(self, obj, value):
        self.warn()
        self.descriptor.__set__(obj, value)

    def __delete__(self, obj):
        self.warn()
        self.descriptor.__delete__(obj)

    def __repr__(self):
        return '<Deprecated attribute %s: %r>' % (
            self.attr,
            self.descriptor)

    def warn(self):
        if not self.warning:
            raise DeprecationWarning(
                'The attribute %s is deprecated: %s' % (self.attr, self.message))
        else:
            warnings.warn(
                'The attribute %s is deprecated: %s' % (self.attr, self.message),
                DeprecationWarning,
                stacklevel=3)


class UnicodePathProperty(object):
    """
        upath_info and uscript_name descriptor implementation
    """

    def __init__(self, key, doc=None):
        self.key = key
        #if doc:
        #    docstring += textwrap.dedent(doc)
        #self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        str_path = obj.environ[self.key]
        return str_path.decode('UTF8', obj.unicode_errors)

    def __set__(self, obj, path):
        if not isinstance(path, unicode):
            path = path.decode('ASCII') # or just throw an error?
        str_path = path.encode('UTF8', obj.unicode_errors)
        obj.environ[self.key] = str_path

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.key)



########################
## Converter functions
########################


def _adapt_cache_expires(value):
    if value is False:
        return None
    if value is True:
        return (0,), {}
    else:
        return (value,), {}




def _parse_etag(value, default=True):
    if value is None:
        value = ''
    value = value.strip()
    if not value:
        if default:
            return AnyETag
        else:
            return NoETag
    if value == '*':
        return AnyETag
    else:
        return ETagMatcher.parse(value)

def _serialize_etag(value, default=True):
    if value is None:
        return None
    if value is AnyETag:
        if default:
            return None
        else:
            return '*'
    return str(value)

# FIXME: weak entity tags are not supported, would need special class
def _parse_etag_response(value):
    """
    See:
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.19
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.11
    """
    if value is not None:
        unquote_match = QUOTES_RE.match(value)
        if unquote_match is not None:
            value = unquote_match.group(1)
            value = value.replace('\\"', '"')
        return value

def _serialize_etag_response(value):
    if value is not None:
        return '"%s"' % value.replace('"', '\\"')

def _parse_if_range(value):
    if not value:
        return NoIfRange
    else:
        return IfRange.parse(value)

def _serialize_if_range(value):
    if value is None:
        return value
    if isinstance(value, (datetime, date)):
        return datetime_utils._serialize_date(value)
    if not isinstance(value, str):
        value = str(value)
    return value or None

def _parse_range(value):
    if not value:
        return None
    # Might return None too:
    return Range.parse(value)

def _serialize_range(value):
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError(
                "If setting .range to a list or tuple, it must be of length 2 (not %r)"
                % value)
        value = Range([value])
    if value is None:
        return None
    value = str(value)
    return value or None

def _parse_int(value):
    if value is None or value == '':
        return None
    return int(value)

def _parse_int_safe(value):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None

def _serialize_int(value):
    if value is None:
        return None
    return str(value)

def _parse_content_range(value):
    if not value or not value.strip():
        return None
    # May still return None
    return ContentRange.parse(value)

def _serialize_content_range(value):
    if value is None:
        return None
    if isinstance(value, (tuple, list)):
        if len(value) not in (2, 3):
            raise ValueError(
                "When setting content_range to a list/tuple, it must "
                "be length 2 or 3 (not %r)" % value)
        if len(value) == 2:
            begin, end = value
            length = None
        else:
            begin, end, length = value
        value = ContentRange(begin, end, length)
    value = str(value).strip()
    if not value:
        return None
    return value

def _parse_list(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return [v.strip() for v in value.split(',')
            if v.strip()]

def _serialize_list(value):
    if not value:
        return None
    if isinstance(value, unicode):
        value = str(value)
    if isinstance(value, str):
        return value
    return ', '.join(map(str, value))

def _parse_accept(value, header_name, AcceptClass, NilClass):
    if not value:
        return NilClass(header_name)
    return AcceptClass(header_name, value)

def _serialize_accept(value, header_name, AcceptClass, NilClass):
    if not value or isinstance(value, NilClass):
        return None
    if isinstance(value, (list, tuple, dict)):
        value = NilClass(header_name) + value
    value = str(value).strip()
    if not value:
        return None
    return value


def parse_params(params):
    r = {}
    for pair in params.split(', '):
        key, value = pair.split('=')
        r[key] = value.strip('"')
    return r

# see http://lists.w3.org/Archives/Public/ietf-http-wg/2009OctDec/0297.html
known_auth_schemes = ['Basic', 'Digest', 'WSSE', 'HMACDigest', 'GoogleLogin', 'Cookie', 'OpenID']
known_auth_schemes = dict.fromkeys(known_auth_schemes, None)

def parse_auth(val):
    if val is not None:
        authtype, params = val.split(' ', 1)
        if authtype in known_auth_schemes:
            if authtype == 'Basic' and '"' not in params:
                # this is the "Authentication: Basic XXXXX==" case
                pass
            else:
                params = parse_params(params)
        return authtype, params
    return val

def serialize_auth(val):
    if isinstance(val, (tuple, list)):
        authtype, params = val
        if isinstance(params, dict):
            params = ', '.join(map('%s="%s"'.__mod__, params.items()))
        assert isinstance(params, str)
        return '%s %s' % (authtype, params)
    return val
