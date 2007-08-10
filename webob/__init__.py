from cStringIO import StringIO
import cgi
import urllib
import urlparse
import re
import textwrap
from UserDict import DictMixin
from Cookie import SimpleCookie
from rfc822 import parsedate_tz, mktime_tz, formatdate
from datetime import datetime, date, timedelta, tzinfo
import time
import calendar
from webob.datastruct import EnvironHeaders
from webob.multidict import MultiDict, UnicodeMultiDict, NestedMultiDict, NoVars
from webob.useragent import UserAgent, parse_search_query
from webob.etag import AnyETag, NoETag, ETagMatcher
from webob.headerdict import HeaderDict
from webob.statusreasons import status_reasons
from webob.cachecontrol import CacheControl
from webob.acceptparse import Accept, MIMEAccept, NilAccept, MIMENilAccept

_CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)
_SCHEME_RE = re.compile(r'^[a-z]+:', re.I)

__all__ = ['Request', 'Response', 'UTC', 'day', 'week', 'hour', 'minute', 'second', 'month', 'year', 'html_escape']

class _UTC(tzinfo):
    def dst(self, dt):
        return timedelta(0)
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return 'UTC'
    def __repr__(self):
        return 'UTC'

UTC = _UTC()

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
    if not isinstance(s, basestring):
        if hasattr(s, '__unicode__'):
            s = unicode(s)
        else:
            s = str(s)
    s = cgi.escape(s, True)
    if isinstance(s, unicode):
        s = s.encode('ascii', 'xmlcharrefreplace')
    return s

def timedelta_to_seconds(td):
    """
    Converts a timedelta instance to seconds.
    """
    return td.seconds + (td.days*24*60*60)

day = timedelta(days=1)
week = timedelta(weeks=7)
hour = timedelta(hours=1)
minute = timedelta(minutes=1)
second = timedelta(seconds=1)
# Estimate, I know; good enough for expirations
month = timedelta(days=30)
year = timedelta(days=365)

class NoDefault:
    pass

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
        docstring += " the %r key from the environment" % self.key
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
        docstring += " they header %s from the headers" % self.header
        docstring += _rfc_reference(self.header, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        if self.header not in obj.headers:
            return self.default
        else:
            return obj.headers[self.header]

    def __set__(self, obj, value):
        if not self.settable:
            raise AttributeError("Read-only attribute (header %s)" % self.header)
        if value is None:
            if self.header in obj.headers:
                del obj.headers[self.header]
        else:
            obj.headers[self.header] = value

    def __delete__(self, obj):
        if not self.deletable:
            raise AttributeError("You cannot delete the header %s" % self.header)
        del obj.headers[self.header]

    def __repr__(self):
        return '<Proxy for header %s>' % self.header

class converter(object):
    """
    Wraps a decorator, and applies conversion for that decorator
    """
    def __init__(self, decorator, getter_converter, setter_converter, convert_name=None, doc=None, converter_args=()):
        self.decorator = decorator
        self.getter_converter = getter_converter
        self.setter_converter = setter_converter
        self.convert_name = convert_name
        self.converter_args = converter_args
        docstring = decorator.__doc__ or ''
        docstring += " and converts it using "
        if convert_name:
            docstring += convert_name
        else:
            docstring += "%r and %r" % (getter_converter, setter_converter)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = self.decorator.__get__(obj, type)
        return self.getter_converter(value, *self.converter_args)

    def __set__(self, obj, value):
        value = self.setter_converter(value, *self.converter_args)
        self.decorator.__set__(obj, value)

    def __delete__(self, obj):
        self.decorator.__delete__(obj)

    def __repr__(self):
        if self.convert_name:
            name = ' %s' % self.convert_name
        else:
            name = ''
        return '<Converted %r%s>' % (self.decorator, name)

def _rfc_reference(header, section):
    if not section:
        return ''
    major_section = section.split('.')[0]
    link = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec%s.html#sec%s' % (
        major_section, section)
    return " for more information on %s see `section %s <%s>`_" % (
        header, section, link)

def _parse_date(value):
    if not value:
        return None
    t = parsedate_tz(value)
    if t is None:
        # Could not parse
        return None
    t = mktime_tz(t)
    return datetime.fromtimestamp(t, UTC)

def _serialize_date(dt):
    if isinstance(dt, unicode):
        dt = dt.encode('ascii')
    if isinstance(dt, str):
        return dt
    if isinstance(dt, timedelta):
        dt = datetime.now() + dt
    if isinstance(dt, (datetime, date)):
        dt = dt.timetuple()
    if isinstance(dt, (tuple, time.struct_time)):
        dt = calendar.timegm(dt)
    if not isinstance(dt, (float, int)):
        raise ValueError(
            "You must pass in a datetime, date, time tuple, or integer object, not %r" % dt)
    return formatdate(dt)

def _parse_date_delta(value):
    """
    like _parse_date, but also handle delta seconds
    """
    if not value:
        return None
    try:
        value = int(value)
    except ValueError:
        pass
    else:
        delta = timedelta(seconds=value)
        return datetime.now() + delta
    return _parse_date(value)

def _serialize_date_delta(value):
    if not value and value != 0:
        return None
    if isinstance(value, (float, int)):
        return str(int(value))
    return _serialize_date(value)

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

def _parse_int(value):
    if value is None:
        return None
    return int(value)

def _serialize_int(value):
    if value is None:
        return None
    return str(value)

def _parse_content_range(value):
    if value is None:
        return None
    value = value.strip()
    if not value.startswith('bytes '):
        # Unparseable
        return None
    value = value[len('bytes '):].strip()
    if '/' not in value:
        # Invalid, no length given
        return None
    range, length = value.split('/', 1)
    if '-' not in range:
        # Invalid, no range
        return None
    start, end = range.split('-', 1)
    try:
        start = int(start)
        if end == '*':
            end = None
        else:
            end = int(end)
        if length == '*':
            length = None
        else:
            length = int(length)
    except ValueError:
        # Parse problem
        return None
    return (start, end, length)

def _serialize_content_range(value):
    if value is None:
        return None
    if isinstance(value, unicode):
        value = str(value)
    if isinstance(value, str):
        return value
    if len(value) != 3:
        raise ValueError(
            "You must pass in a 3-tuple (not %r)" % value)
    start, end, length = value
    if end is None:
        end = '*'
    if length is None:
        length = '*'
    return 'bytes %s-%s/%s' % (start, end, length)

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

def _parse_user_agent(value):
    return UserAgent(value or '')

def _serialize_user_agent(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return value

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

class Request(object):

    ## Options:
    charset = None
    errors = 'strict'
    decode_param_names = False

    def __init__(self, environ=None, environ_getter=None, charset=NoDefault, errors=NoDefault,
                 decode_param_names=NoDefault):
        if environ is None and environ_getter is None:
            raise TypeError(
                "You must provide one of environ or environ_getter")
        if environ is not None and environ_getter is not None:
            raise TypeError(
                "You can only provide one of the environ and environ_getter arguments")
        if environ is None:
            self._environ_getter = environ_getter
        else:
            self._environ = environ
        self.headers = EnvironHeaders(environ)
        if charset is not NoDefault:
            self.charset = charset
        if errors is not NoDefault:
            self.errors = errors
        if decode_param_names is NoDefault:
            self.decode_param_names = decode_param_names

    def environ(self):
        return self._environ_getter()
    environ = property(environ)

    def _environ_getter(self):
        return self._environ

    def body__get(self):
        """
        Access the body of the request (wsgi.input) as a file-like
        object.

        If you set this value, CONTENT_LENGTH will also be updated
        (either set to -1, 0 if you delete the attribute, or if you
        set the attribute to a string then the length of the string).
        """
        return self.environ['wsgi.input']
    def body__set(self, value):
        if isinstance(value, str):
            length = len(value)
            value = StringIO(value)
        else:
            length = -1
        self.environ['wsgi.input'] = value
        self.environ['CONTENT_LENGTH'] = str(length)
    def body__del(self):
        self.environ['wsgi.input'] = StringIO('')
        self.environ['CONTENT_LENGTH'] = '0'
    body = property(body__get, body__set, body__del, doc=body__get.__doc__)

    scheme = environ_getter('wsgi.url_scheme')
    method = environ_getter('REQUEST_METHOD')
    script_name = environ_getter('SCRIPT_NAME')
    path_info = environ_getter('PATH_INFO')
    ## FIXME: should I strip out parameters?:
    content_type = environ_getter('CONTENT_TYPE')
    remote_user = environ_getter('REMOTE_USER', default=None)
    remote_addr = environ_getter('REMOTE_ADDR', default=None)

    def host_url(self):
        """
        The URL through the host (no path)
        """
        e = self.environ
        url = e['wsgi.url_scheme'] + '://'
        if e.get('HTTP_HOST'):
            host = e['HTTP_HOST']
            if ':' in host:
                host, port = host.split(':', 1)
            else:

                port = None
        else:
            host = e['SERVER_NAME']
            port = e['SERVER_PORT']
        if self.environ['wsgi.url_scheme'] == 'https':
            if port == '443':
                port = None
        elif self.environ['wsgi.url_scheme'] == 'http':
            if port == '80':
                port = None
        url += host
        if port:
            url += ':%s' % port
        return url
    host_url = property(host_url, doc=host_url.__doc__)

    def application_url(self):
        """
        The URL including SCRIPT_NAME (no PATH_INFO or query string)
        """
        return self.host_url + urllib.quote(self.environ.get('SCRIPT_NAME', ''))
    application_url = property(application_url, doc=application_url.__doc__)

    def path_url(self):
        """
        The URL including SCRIPT_NAME and PATH_INFO, but not QUERY_STRING
        """
        return self.application_url + urllib.quote(self.environ.get('PATH_INFO', ''))
    path_url = property(path_url, doc=path_url.__doc__)

    def path(self):
        """
        The path of the request, without host or query string
        """
        return urllib.quote(self.script_name) + urllib.quote(self.path_info)
    path = property(path, doc=path.__doc__)

    def path_qs(self):
        """
        The path of the request, without host but with query string
        """
        path = self.path
        qs = self.environ.get('QUERY_STRING')
        if qs:
            path += '?' + qs
        return path
    path_qs = property(path_qs, doc=path_qs.__doc__)

    def url(self):
        """
        The full request URL, including QUERY_STRING
        """
        url = self.path_url
        if self.environ.get('QUERY_STRING'):
            url += '?' + self.environ['QUERY_STRING']
        return url
    url = property(url, doc=url.__doc__)

    def relative_url(self, other_url, to_application=False):
        """
        Resolve other_url relative to the request URL.

        If ``to_application`` is True, then resolve it relative to the
        URL with only SCRIPT_NAME
        """
        if to_application:
            url = self.application_url
            if not url.endswith('/'):
                url += '/'
        else:
            url = self.path_url
        return urlparse.urljoin(url, other_url)

    def path_info_pop(self):
        """
        'Pops' off the next segment of PATH_INFO, pushing it onto
        SCRIPT_NAME, and returning the popped segment.  Returns None if
        there is nothing left on PATH_INFO.

        Does not return empty segments.
        """
        path = self.path_info
        if not path:
            return None
        while path.startswith('/'):
            self.script_name += '/'
            path = path[1:]
        if '/' not in path:
            self.script_name += path
            self.path_info = ''
            return path
        else:
            segment, path = path.split('/', 1)
            self.path_info = '/' + path
            self.script_name += segment
            return segment

    def path_info_peek(self):
        """
        Returns the next segment on PATH_INFO, or None if there is no
        next segment.  Doesn't modify the environment.
        """
        path = self.path_info
        if not path:
            return None
        path = path.lstrip('/')
        return path.split('/', 1)[0]

    def urlvars(self):
        """
        Return any variables matched in the URL (e.g.,
        ``wsgiorg.routing_args``).
        """
        if 'paste.urlvars' in self.environ:
            return self.environ['paste.urlvars']
        elif 'wsgiorg.routing_args' in self.environ:
            return self.environ['wsgiorg.routing_args'][1]
        else:
            return {}
    urlvars = property(urlvars, doc=urlvars.__doc__)

    def is_xhr(self):
        """Returns a boolean if X-Requested-With is present and a XMLHttpRequest"""
        return self.environ.get('HTTP_X_REQUESTED_WITH', '') == 'XMLHttpRequest'
    is_xhr = property(is_xhr, doc=is_xhr.__doc__)

    def host__get(self):
        """Host name provided in HTTP_HOST, with fall-back to SERVER_NAME"""
        ## FIXME: should I add in SERVER_PORT?
        return self.environ.get('HTTP_HOST', self.environ.get('SERVER_NAME'))
    def host__set(self, value):
        self.environ['HTTP_HOST'] = value
    def host__del(self):
        if 'HTTP_HOST' in self.environ:
            del self.environ['HTTP_HOST']
    host = property(host__get, host__set, host__del, doc=host__get.__doc__)

    def read_body(self):
        """
        Return the content of the request body.
        """
        try:
            length = int(self.environ.get('CONTENT_LENGTH', '0'))
        except ValueError:
            return ''
        c = self.body.read(length)
        self.body = StringIO(c)
        return c

    def str_postvars(self):
        """
        Return a MultiDict containing all the variables from a POST
        form request.  Does *not* return anything for non-POST
        requests or for non-form requests (returns empty dict-like
        object in that case).
        """
        env = self.environ
        if self.method != 'POST':
            return NoVars('Not a POST request')
        if 'webob._parsed_post_vars' in env:
            vars, body = env['webob._parsed_post_vars']
            if body is self.body:
                return vars
        # Paste compatibility:
        if 'paste.parsed_formvars' in env:
            # from paste.request.parse_formvars
            vars, body = env['paste.parsed_formvars']
            if body is self.body:
                # FIXME: is it okay that this isn't *our* MultiDict?
                return parsed
        content_type = self.content_type
        if ';' in content_type:
            content_type = content_type.split(';', 1)[0]
        if content_type not in ('', 'application/x-www-form-urlencoded',
                                'multipart/form-data'):
            # Not an HTML form submission
            return NoVars('Not an HTML form submission (Content-Type: %s)'
                          % content_type)
        if 'CONTENT_LENGTH' not in env:
            # FieldStorage assumes a default CONTENT_LENGTH of -1, but a
            # default of 0 is better:
            env['CONTENT_TYPE'] = '0'
        fs_environ = env.copy()
        fs_environ['QUERY_STRING'] = ''
        fs = cgi.FieldStorage(fp=self.body,
                              environ=fs_environ,
                              keep_blank_values=True)
        vars = MultiDict.from_fieldstorage(fs)
        FakeCGIBody.update_environ(env, vars)
        env['webob._parsed_post_vars'] = (vars, self.body)
        return vars

    str_postvars = property(str_postvars, doc=str_postvars.__doc__)

    str_POST = str_postvars

    def postvars(self):
        """
        Like str_postvars, but may decode values and keys
        """
        vars = self.str_postvars
        if self.charset:
            vars = UnicodeMultiDict(vars, encoding=self.charset,
                                    errors=self.errors,
                                    decode_keys=self.decode_param_names)
        return vars

    postvars = property(postvars, doc=postvars.__doc__)

    POST = postvars

    def str_queryvars(self):
        """
        Return a MultiDict containing all the variables from the
        QUERY_STRING.
        """
        env = self.environ
        source = env.get('QUERY_STRING', '')
        if 'webob._parsed_query_vars' in env:
            vars, qs = env['webob._parsed_query_vars']
            if qs == source:
                return vars
        if not source:
            vars = MultiDict()
        else:
            vars = MultiDict(cgi.parse_qsl(
                source, keep_blank_values=True,
                strict_parsing=False))
        env['webob._parsed_query_vars'] = (vars, source)
        return vars

    str_queryvars = property(str_queryvars, doc=str_queryvars.__doc__)

    str_GET = str_queryvars

    def queryvars(self):
        """
        Like str_queryvars, but may decode values and keys
        """
        vars = self.str_queryvars
        if self.charset:
            vars = UnicodeMultiDict(vars, encoding=self.charset,
                                    errors=self.errors,
                                    decode_keys=self.decode_param_names)
        return vars

    queryvars = property(queryvars, doc=queryvars.__doc__)

    GET = queryvars

    def str_params(self):
        """
        A dictionary-like object containing both the parameters from
        the query string and request body.
        """
        return NestedMultiDict(self.queryvars, self.postvars)

    str_params = property(str_params, doc=str_params.__doc__)

    def params(self):
        """
        Like str_params, but may decode values and keys
        """
        params = self.str_params
        if self.charset:
            params = UnicodeMultiDict(params, encoding=self.charset,
                                      errors=self.errors,
                                      decode_keys=self.decode_param_names)
        return params

    params = property(params, doc=params.__doc__)

    def str_cookies(self):
        """
        Return a *plain* dictionary of cookies as found in the request.
        """
        env = self.environ
        source = env.get('HTTP_COOKIE', '')
        if 'webob._parsed_cookies' in env:
            vars, var_source = env['webob._parsed_cookies']
            if var_source == source:
                return vars
        vars = {}
        if source:
            cookies = SimpleCookie()
            cookies.load(source)
            for name in cookies:
                vars[name] = cookies[name].value
        env['webob._parsed_cookies'] = (vars, source)
        return vars

    str_cookies = property(str_cookies, doc=str_cookies.__doc__)

    def cookies(self):
        """
        Like str_cookies, but may decode values and keys
        """
        vars = self.str_cookies
        if self.charset:
            vars = UnicodeMultiDict(vars, encoding=self.charset,
                                    errors=self.errors,
                                    decode_keys=self.decode_param_names)
        return vars

    cookies = property(cookies, doc=cookies.__doc__)

    def copy(self):
        """
        Copy the request and environment object.

        This only does a shallow copy, except of wsgi.input
        """
        env = self.environ.copy()
        data = self.read_body()
        new_body = StringIO(data)
        env['wsgi.input'] = new_body
        return self.__class__(env)

    def remove_conditional_headers(self, remove_encoding=True):
        """
        Remove headers that make the request conditional.

        These headers can cause the response to be 304 Not Modified,
        which in some cases you may not want to be possible.

        This does not remove headers like If-Match, which are used for
        conflict detection.
        """
        for key in ['HTTP_IF_MATCH', 'HTTP_IF_MODIFIED_SINCE',
                    'HTTP_IF_RANGE']:
            if key in self.environ:
                del self.environ[key]
        if remove_encoding:
            if 'HTTP_ACCEPT_ENCODING' in self.environ:
                del self.environ['HTTP_ACCEPT_ENCODING']

    accept = converter(
        environ_getter('HTTP_ACCEPT', rfc_section='14.1'),
        _parse_accept, _serialize_accept, 'mime-accept',
        converter_args=('Accept', MIMEAccept, MIMENilAccept))

    accept_charset = converter(
        environ_getter('HTTP_ACCEPT_CHARSET', rfc_section='14.2'),
        _parse_accept, _serialize_accept, 'accept',
        converter_args=('Accept-Charset', Accept, NilAccept))

    accept_encoding = converter(
        environ_getter('HTTP_ACCEPT_ENCODING', rfc_section='14.3'),
        _parse_accept, _serialize_accept, 'accept',
        converter_args=('Accept-Encoding', Accept, NilAccept))

    accept_language = converter(
        environ_getter('HTTP_ACCEPT_LANGUAGE', rfc_section='14.4'),
        _parse_accept, _serialize_accept, 'accept',
        converter_args=('Accept-Language', Accept, NilAccept))

    ## FIXME: 14.8 Authorization
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8

    ## FIXME: 14.18 Date ?
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.18

    if_match = converter(
        environ_getter('HTTP_IF_MATCH', rfc_section='14.24'),
        _parse_etag, _serialize_etag, 'etag', converter_args=(True,))

    if_modified_since = converter(
        environ_getter('HTTP_IF_MODIFIED_SINCE', rfc_section='14.25'),
        _parse_date, _serialize_date, 'date-parsed')

    if_none_match = converter(
        environ_getter('HTTP_IF_NONE_MATCH', rfc_section='14.26'),
        _parse_etag, _serialize_etag, 'etag', converter_args=(False,))

    ## FIXME: 14.27 If-Range
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.27

    if_unmodified_since = converter(
        environ_getter('HTTP_IF_UNMODIFIED_SINCE', rfc_section='14.28'),
        _parse_date, _serialize_date, 'date-parsed')

    max_forwards = converter(
        environ_getter('HTTP_MAX_FORWARDS', rfc_section='14.31'),
        _parse_int, _serialize_int, 'int')

    ## FIXME: 14.32 Pragma
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.32

    ## FIXME: 14.35 Range
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.35

    referer = environ_getter('HTTP_REFERER', rfc_section='14.36')
    referrer = referer

    def referer_search_query(self):
        """
        Return the search query used to reach this page, if there was
        one.  Returns a string.  If not found, returns None.
        """
        return parse_search_query(self.referer)
    referrer_search_query = referer_search_query

    user_agent = converter(
        environ_getter('HTTP_USER_AGENT', rfc_section='14.43'),
        _parse_user_agent, _serialize_user_agent, 'user-agent')

    def __repr__(self):
        msg = '<%s at %x %s %s>' % (
            self.__class__.__name__,
            abs(id(self)), self.method, self.url)
        return msg

    def __str__(self):
        url = self.url
        host = self.host_url
        assert url.startswith(host)
        url = url[len(host):]
        if 'Host' not in self.headers:
            self.headers['Host'] = self.host
        parts = ['%s %s' % (self.method, url)]
        for name, value in sorted(self.headers.items()):
            parts.append('%s: %s' % (name, value))
        parts.append('')
        parts.append(self.read_body())
        return '\r\n'.join(parts)

    def call_application(self, application):
        """
        Call the given WSGI application, returning ``(status_string,
        headerlist, app_iter)``

        Be sure to call ``app_iter.close()`` if it's there.
        """
        captured = []
        output = []
        def start_response(status, headers, exc_info=None):
            if exc_info is not None:
                raise exc_info[0], exc_info[1], exc_info[2]
            captured[:] = [status, headers]
            return output.append
        app_iter = application(self.environ, start_response)
        if (not captured
            or output):
            try:
                output.extend(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
            app_iter = output
        return (captured[0], captured[1], app_iter)

    # Will be filled in later:
    ResponseClass = None

    def get_response(self, application):
        """
        Like ``.call_application(application)``, except returns a
        response object with ``.status``, ``.headers``, and ``.body``
        attributes.
        """
        status, headers, app_iter = self.call_application(application)
        return self.ResponseClass(status, headers, app_iter=app_iter, request=self)

    #@classmethod
    def blank(cls, path_info, environ=None, base_url=None):
        """
        Create a blank request environ (and Request wrapper) with the
        given path_info (path_info should be urlencoded), and any keys
        from environ.

        All necessary keys will be added to the environ, but the
        values you pass in will take precedence.  If you pass in
        base_url then wsgi.url_scheme, HTTP_HOST, and SCRIPT_NAME will
        be filled in from that value.
        """
        if path_info and '?' in path_info:
            path_info, query_string = path_info.split('?', 1)
            path_info = urllib.unquote(path_info)
        else:
            path_info = urllib.unquote(path_info)
            query_string = ''
        env = {
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'PATH_INFO': path_info or '',
            'QUERY_STRING': query_string,
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': StringIO(''),
            'wsgi.errors': StringIO(),
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
            }
        if base_url:
            scheme, netloc, path, query, fragment = urlparse.urlsplit(base_url)
            if query or fragment:
                raise ValueError(
                    "base_url (%r) cannot have a query or fragment"
                    % base_url)
            if scheme:
                env['wsgi.url_scheme'] = scheme
            if netloc:
                if ':' not in netloc:
                    if scheme == 'http':
                        netloc += ':80'
                    elif scheme == 'https':
                        netloc += ':443'
                    else:
                        raise ValueError(
                            "Unknown scheme: %r" % scheme)
                host, port = netloc.split(':', 1)
                env['SERVER_PORT'] = port
                env['SERVER_NAME'] = host
                env['HTTP_HOST'] = netloc
            if path:
                env['SCRIPT_NAME'] = urllib.unquote(path)
        if environ:
            env.update(environ)
        return cls(env)

    blank = classmethod(blank)

class Response(object):

    """
    Represents a WSGI response
    """

    default_content_type = None
    render = None

    def __init__(self, status='200 OK', headerlist=None, body=None, app_iter=None,
                 request=None, content_type=None):
        if app_iter is None:
            if body is None:
                body = ''
        elif body is not None:
            raise TypeError(
                "You may only give one of the body and app_iter arguments")
        self._app_iter = app_iter
        self._body = body
        self._status = status
        if headerlist is None:
            headerlist = []
        self._headerlist = headerlist
        self._headers = None
        if request is not None:
            if hasattr(request, 'environ'):
                self._environ = request.environ
                self._request = request
            else:
                self._environ = request
                self._request = None
        else:
            self._environ = self._request = None
        if self._body is not None:
            self.content_length = len(self._body)
        if content_type is not None:
            self.content_type = content_type
        elif self.default_content_type is not None:
            self.content_type = self.default_content_type

    def __repr__(self):
        return '<%s %x %s>' % (
            self.__class__.__name__,
            abs(id(self)),
            self.status)

    def __str__(self):
        return (self.status + '\n'
                + '\n'.join(['%s: %s' % (name, value)
                             for name, value in self.headerlist])
                + '\n\n'
                + self.body)

    def status__get(self):
        """
        The status string
        """
        return self._status

    def status__set(self, value):
        if isinstance(value, int):
            value = str(value)
        if not isinstance(value, str):
            raise TypeError(
                "You must set status to a string or integer (not %s)"
                % type(value))
        if ' ' not in value:
            # Need to add a reason:
            code = int(value)
            reason = status_reasons[code]
            value += ' ' + reason
        self._status = value

    status = property(status__get, status__set, doc=status__get.__doc__)

    def status_int__get(self):
        """
        The status as an integer
        """
        return int(self.status.split()[0])
    def status_int__set(self, value):
        self.status = value
    status_int = property(status_int__get, status_int__set, doc=status_int__get.__doc__)

    def headerlist__get(self):
        """
        The list of response headers
        """
        return self._headerlist
    def headerlist__set(self, value):
        self._headers = None
        if not isinstance(value, list):
            if hasattr(value, 'items'):
                value = value.items()
            value = list(value)
        self._headerlist = value
    def headerlist__del(self):
        self.headerlist = []
    headerlist = property(headerlist__get, headerlist__set, headerlist__del, doc=headerlist__get.__doc__)

    def charset__get(self):
        """
        Get/set the charset (in the Content-Type)
        """
        header = self.headers.get('content-type')
        if not header:
            return None
        match = _CHARSET_RE.search(header)
        if match:
            return match.group(1)
        return None

    def charset__set(self, charset):
        if charset is None:
            del self.charset
            return
        try:
            header = self.headers.pop('content-type')
        except KeyError:
            raise AttributeError(
                "You cannot set the charset when on content-type is defined")
        match = _CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        header += '; charset=%s' % charset
        self.headers['content-type'] = header

    def charset__del(self):
        try:
            header = self.headers.pop('content-type')
        except KeyError:
            # Don't need to remove anything
            return
        match = _CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        self.headers['content-type'] = header

    charset = property(charset__get, charset__set, charset__del, doc=charset__get.__doc__)

    def content_type__get(self):
        """
        Get/set the Content-Type header (or None), *without* the
        charset or any parameters.

        If you include parameters (or ``;`` at all) when setting the
        content_type, any existing parameters will be deleted;
        otherwise they will be preserved.
        """
        header = self.headers.get('content-type')
        if not header:
            return None
        return header.split(';', 1)[0]

    def content_type__set(self, value):
        if ';' not in value:
            header = self.headers.get('content-type', '')
            if ';' in header:
                params = header.split(';', 1)[1]
                value += ';' + params
        self.headers['content-type'] = value

    def content_type__del(self):
        try:
            del self.headers['content-type']
        except KeyError:
            pass

    content_type = property(content_type__get, content_type__set,
                            content_type__del, doc=content_type__get.__doc__)

    def headers__get(self):
        """
        The headers in a dictionary-like object
        """
        if self._headers is None:
            self._headers = HeaderDict.view_list(self.headerlist)
        return self._headers

    def headers__set(self, value):
        if hasattr(value, 'items'):
            value = value.items()
        self.headerlist = value
        self._headers = None

    headers = property(headers__get, headers__set, doc=headers__get.__doc__)

    def body__get(self):
        """
        The body of the response, as a str
        """
        if self._body is None:
            if self._app_iter is None:
                raise AttributeError(
                    "No body has been set")
            try:
                self._body = ''.join(self._app_iter)
            finally:
                if hasattr(self._app_iter, 'close'):
                    self._app_iter.close()
            self._app_iter = None
            self.content_length = len(self._body)
        return self._body

    def body__set(self, value):
        if isinstance(value, unicode):
            charset = self.charset
            ## FIXME: should this just be separate unicode_body getter/setter?
            if not charset:
                raise TypeError(
                    "You cannot set the body to a unicode value if charset is not set")
            value = value.encode(charset)
        if not isinstance(value, str):
            raise TypeError(
                "You can only set the body to a str (not %s)"
                % type(value))
        self._body = value
        self.content_length = len(value)
        self._app_iter = None

    def body__del(self):
        self._body = None
        self.content_length = None
        self._app_iter = None

    body = property(body__get, body__set, body__del, doc=body__get.__doc__)

    def app_iter__get(self):
        """
        Returns the app_iter of the response
        """
        if self._app_iter is None:
            if self._body is None:
                raise AttributeError(
                    "No body or app_iter has been set")
            return [self._body]
        else:
            return self._app_iter

    def app_iter__set(self, value):
        if self._body is not None:
            # Undo the automatically-set content-length
            self.content_length = None
        self._app_iter = value
        self._body = None

    def app_iter__del(self):
        self.content_length = None
        self._app_iter = self._body = None

    app_iter = property(app_iter__get, app_iter__set, app_iter__del, doc=app_iter__get.__doc__)

    def set_cookie(self, key, value='', max_age=None,
                   path='/', domain=None, secure=None):
        """
        Set (add) a cookie for the response
        """
        cookies = SimpleCookie()
        cookies[key] = value
        for var_name, var_value in [
            ('max_age', max_age),
            ('path', path),
            ('domain', domain),
            ('secure', secure),
            ]:
            if var_value is not None and var_value is not False:
                cookies[key][var_name.replace('_', '-')] = str(var_value)
        header_value = cookies[key].output(header='').lstrip()
        self.headerlist.append(('Set-Cookie', header_value))

    def delete_cookie(self, key, path='/', domain=None):
        """
        Delete a cookie from the client.  Note that path and domain must match
        how the cookie was originally set.

        This sets the cookie to the empty string, and max_age=0 so
        that it should expire immediately.
        """
        self.set_cookie(key, '', path=path, domain=domain,
                        max_age=0)

    def unset_cookie(self, key):
        """
        Unset a cookie with the given name (remove it from the
        response).  If there are multiple cookies (e.g., two cookies
        with the same name and different paths or domains), all such
        cookies will be deleted.
        """
        existing = self.headers.getall('Set-Cookie')
        if not existing:
            raise KeyError(
                "No cookies at all have been set")
        del self.headers['Set-Cookie']
        found = False
        for header in existing:
            cookies = SimpleCookie()
            cookies.load(header)
            if key in cookies:
                found = True
                del cookies[key]
            header = cookies.output(header='').lstrip()
            if header:
                self.headers.add('Set-Cookie', header)
        if not found:
            raise KeyError(
                "No cookie has been set with the name %r" % key)

    def location__get(self):
        """
        Retrieve the Location header of the response, or None if there
        is no header.  If the header is not absolute and this response
        is associated with a request, make the header absolute.

        For more information see `section 14.30
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.30>`_.
        """
        if 'location' not in self.headers:
            return None
        location = self.headers['location']
        if _SCHEME_RE.search(location):
            # Absolute
            return location
        if self.request is not None:
            base_uri = self.request.url
            location = urlparse.urljoin(base_uri, location)
        return location

    def location__set(self, value):
        if not _SCHEME_RE.search(value):
            # Not absolute, see if we can make it absolute
            if self.request is not None:
                value = urlparse.urljoin(self.request.url, value)
        self.headers['location'] = value

    def location__del(self):
        if 'location' in self.headers:
            del self.headers['location']

    location = property(location__get, location__set, location__del, doc=location__get.__doc__)

    accept_ranges = header_getter('Accept-Ranges', rfc_section='14.5')

    age = converter(
        header_getter('Age', rfc_section='14.6'),
        _parse_int, _serialize_int, 'int')

    allow = converter(
        header_getter('Allow', rfc_section='14.7'),
        _parse_list, _serialize_list, 'list')

    _cache_control_obj = None

    def cache_control__get(self):
        """
        Get/set/modify the Cache-Control header (section `14.9
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9>`_)
        """
        value = self.headers.get('cache-control', '')
        if self._cache_control_obj is None:
            self._cache_control_obj = CacheControl.parse(value, updates_to=self._update_cache_control, type='response')
            self._cache_control_obj.header_value = value
        if self._cache_control_obj.header_value != value:
            new_obj = CacheControl.parse(value)
            self._cache_control_obj.properties.clear()
            self._cache_control_obj.properties.update(new_obj.properties)
            self._cache_control_obj.header_value = value
        return self._cache_control_obj

    def cache_control__set(self, value):
        # This actually becomes a copy
        if not value:
            value = ""
        if isinstance(value, dict):
            value = CacheControl(value)
        if isinstance(value, unicode):
            value = str(value)
        if isinstance(value, str):
            if self._cache_control_obj is None:
                self.headers['Cache-Control'] = value
                return
            value = CacheControl.parse(value)
        cache = self.cache_control
        cache.properties.clear()
        cache.properties.update(value.properties)

    def cache_control__del(self):
        self.cache_control = {}

    def _update_cache_control(self, cache_control_obj):
        value = str(cache_control_obj)
        if not value:
            if 'Cache-Control' in self.headers:
                del self.headers['Cache-Control']
        else:
            self.headers['Cache-Control'] = value
        cache_control_obj.header_value = value

    cache_control = property(cache_control__get, cache_control__set, cache_control__del, doc=cache_control__get.__doc__)

    def cache_expires(self, seconds=0, **kw):
        """
        Set expiration on this request.  This sets the response to
        expire in the given seconds, and any other attributes are used
        for cache_control (e.g., private=True, etc).
        """
        cache_control = self.cache_control
        if isinstance(seconds, timedelta):
            seconds = timedelta_to_seconds(seconds)
        if not seconds:
            # To really expire something, you have to force a
            # bunch of these cache control attributes, and IE may
            # not pay attention to those still so we also set
            # Expires.
            cache_control.no_store = True
            cache_control.no_cache = True
            cache_control.must_revalidate = True
            cache_control.max_age = 0
            cache_control.post_check = 0
            cache_control.pre_check = 0
            self.expires = datetime.utcnow()
        else:
            cache_control.max_age = seconds
        for name, value in kw.items():
            setattr(cache_control, name, value)

    content_encoding = header_getter('Content-Encoding', rfc_section='14.11')

    content_language = converter(
        header_getter('Content-Language', rfc_section='14.12'),
        _parse_list, _serialize_list, 'list')

    content_location = header_getter(
        'Content-Location', rfc_section='14.14')

    content_md5 = header_getter(
        'Content-MD5', rfc_section='14.14')

    ## FIXME: is (start, end, length) a sufficient parsing of this?
    ## FIXME: need to make sure request headers are symmetric with this
    content_range = converter(
        header_getter('Content-Range', rfc_section='14.16'),
        _parse_content_range, _serialize_content_range, 'range')

    content_length = converter(
        header_getter('Content-Length', rfc_section='14.17'),
        _parse_int, _serialize_int, 'int')

    date = converter(
        header_getter('Date', rfc_section='14.18'),
        _parse_date, _serialize_date, 'date-parse')

    ## FIXME: should this use _parse_etag?  Shouldn't it just be an
    ## opaque string?
    etag = converter(
        header_getter('ETag', rfc_section='14.19'),
        _parse_etag, _serialize_etag, 'etag')

    expires = converter(
        header_getter('Expires', rfc_section='14.21'),
        _parse_date, _serialize_date, 'date-parse')

    last_modified = converter(
        header_getter('Last-Modified', rfc_section='14.29'),
        _parse_date, _serialize_date, 'date-parse')

    ## FIXME: 14.32 Pragma
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.32

    ## FIXME: 14.35 Range
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.35

    retry_after = converter(
        header_getter('Retry-After', rfc_section='14.37'),
        _parse_date_delta, _serialize_date_delta, 'date-delta-parse')

    server = header_getter('Server', rfc_section='14.38')

    vary = converter(
        header_getter('Vary', rfc_section='14.44'),
        _parse_list, _serialize_list, 'list')

    ## FIXME: 14.47 WWW-Authenticate
    ## http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.47


    def request__get(self):
        """
        Return the request associated with this response if any.
        """
        if self._request is None and self._environ is not None:
            self._request = self.RequestClass(self._environ)
        return self._request

    def request__set(self, value):
        if value is None:
            del self.request
            return
        if isinstance(value, dict):
            self._environ = value
            self._request = None
        else:
            self._request = value
            self._environ = value.environ

    def request__del(self):
        self._request = self._environ = None

    request = property(request__get, request__set, request__del, doc=request__get.__doc__)

    def environ__get(self):
        """
        Get/set the request environ associated with this response, if
        any.
        """
        return self._environ

    def environ__set(self, value):
        if value is None:
            del self.environ
        self._environ = value
        self._request = None

    def environ__del(self):
        self._request = self._environ = None

    environ = property(environ__get, environ__set, environ__del, doc=environ__get.__doc__)

    def __call__(self, environ, start_response):
        """
        WSGI application interface
        """
        ## FIXME: I should watch out here for bad responses, e.g.,
        ## incomplete headers or body, etc
        start_response(self.status, self.headerlist)
        return self.app_iter

Request.ResponseClass = Response
Response.RequestClass = Request

def _cgi_FieldStorage__repr__patch(self):
    """ monkey patch for FieldStorage.__repr__

    Unbelievely, the default __repr__ on FieldStorage reads
    the entire file content instead of being sane about it.
    This is a simple replacement that doesn't do that
    """
    if self.file:
        return "FieldStorage(%r, %r)" % (
                self.name, self.filename)
    return "FieldStorage(%r, %r, %r)" % (
             self.name, self.filename, self.value)

cgi.FieldStorage.__repr__ = _cgi_FieldStorage__repr__patch

class FakeCGIBody(object):

    def __init__(self, vars):
        self.vars = vars
        self._body = None
        self.position = 0

    ## FIXME: implement more methods?
    def read(self, size=-1):
        body = self._get_body()
        if size == -1:
            v = body[self.position:]
            self.position = len(body)
            return v
        else:
            v = body[self.position:self.position+size]
            self.position = min(len(body), self.position+size)
            return v

    def _get_body(self):
        if self._body is None:
            self._body = urllib.urlencode(self.vars.items())
        return self._body

    def readline(self, size=None):
        # We ignore size, but allow it to be hinted
        rest = self._get_body()[self.position:]
        next = res.find('\r\n')
        if next == -1:
            return self.read()
        self.position += next+2
        return rest[:next+2]

    def readlines(self, hint=None):
        # Again, allow hint but ignore
        body = self._get_body()
        rest = body[self.position:]
        self.position = len(body)
        result = []
        while 1:
            next = rest.find('\r\n')
            if next == -1:
                result.append(rest)
                break
            result.append(rest[:next+2])
            rest = rest[next+2:]
        return result

    def __iter__(self):
        return iter(self.readlines())

    def __repr__(self):
        inner = repr(self.vars)
        if len(inner) > 20:
            inner = inner[:15] + '...' + inner[-5:]
        return '<%s at %x viewing %s>' % (
            self.__class__.__name__,
            abs(id(self)), inner)

    #@classmethod
    def update_environ(cls, environ, vars):
        obj = cls(vars)
        environ['CONTENT_LENGTH'] = '-1'
        environ['wsgi.input'] = obj

    update_environ = classmethod(update_environ)
