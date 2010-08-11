import warnings
import re, textwrap
from datetime import datetime, date

from webob.byterange import Range, ContentRange
from webob.etag import AnyETag, NoETag, ETagMatcher, IfRange, NoIfRange
from webob.datetime_utils import serialize_date


CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)
QUOTES_RE = re.compile('"(.*)"')
SCHEME_RE = re.compile(r'^[a-z]+:', re.I)


class environ_getter(object):
    """For delegating an attribute to a key in self.environ."""

    def __init__(self, key, default='', doc=None, rfc_section=None):
        self.key = key
        self.default = default
        docstring = "Gets, sets and deletes the %r key from the environment." % key
        docstring += _rfc_reference(key, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.environ.get(self.key, self.default)

    def __set__(self, obj, value):
        if value is not None:
            obj.environ[self.key] = value
        elif self.key in obj.environ:
            del obj.environ[self.key]

    def __delete__(self, obj):
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
    return " For more information on %s see `section %s <%s>`_." % (
        header, section, link)


class header_getter(object):
    """For delegating an attribute to a header in self.headers"""

    def __init__(self, header, default=None, doc=None, rfc_section=None):
        self.header = header
        self.default = default
        docstring = "Gets and sets and deletes the %s header" % header
        docstring += _rfc_reference(header, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.headers.get(self.header, self.default)

    def __set__(self, obj, value):
        if value is None:
            obj.headers.pop(self.header, None)
        else:
            if isinstance(value, unicode):
                # This is the standard encoding for headers:
                value = value.encode('ISO-8859-1')
            obj.headers[self.header] = value

    def __delete__(self, obj):
        del obj.headers[self.header]

    def __repr__(self):
        return '<Proxy for header %s>' % self.header



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

    def __init__(self, key):
        self.key = key

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






def parse_etag(value, default=True):
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

def serialize_etag(value, default=True):
    if value is None:
        return None
    if value is AnyETag:
        if default:
            return None
        else:
            return '*'
    return str(value)

# FIXME: weak entity tags are not supported, would need special class
def parse_etag_response(value):
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

def serialize_etag_response(value):
    if value is not None:
        return '"%s"' % value.replace('"', '\\"')

def parse_if_range(value):
    if not value:
        return NoIfRange
    else:
        return IfRange.parse(value)

def serialize_if_range(value):
    if value is None:
        return value
    if isinstance(value, (datetime, date)):
        return serialize_date(value)
    if not isinstance(value, str):
        value = str(value)
    return value or None

def parse_range(value):
    if not value:
        return None
    # Might return None too:
    return Range.parse(value)

def serialize_range(value):
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

def parse_int(value):
    if value is None or value == '':
        return None
    return int(value)

def parse_int_safe(value):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None

def serialize_int(value):
    if value is None:
        return None
    return str(value)

def parse_content_range(value):
    if not value or not value.strip():
        return None
    # May still return None
    return ContentRange.parse(value)

def serialize_content_range(value):
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

def parse_list(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return [v.strip() for v in value.split(',')
            if v.strip()]

def serialize_list(value):
    if not value:
        return None
    if isinstance(value, unicode):
        value = str(value)
    if isinstance(value, str):
        return value
    return ', '.join(map(str, value))

def parse_accept(value, header_name, AcceptClass, NilClass):
    if not value:
        return NilClass(header_name)
    return AcceptClass(header_name, value)

def serialize_accept(value, header_name, AcceptClass, NilClass):
    if not value or isinstance(value, NilClass):
        return None
    if isinstance(value, (list, tuple, dict)):
        value = NilClass(header_name) + value
    value = str(value).strip()
    if not value:
        return None
    return value

_rx_auth_param = re.compile(r'([a-z]+)=(".*?"|[^,]*)(?:\Z|, *)')

def parse_auth_params(params):
    r = {}
    for k, v in _rx_auth_param.findall(params):
        r[k] = v.strip('"')
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
                params = parse_auth_params(params)
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
