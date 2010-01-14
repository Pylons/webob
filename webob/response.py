import re
import urlparse
from cStringIO import StringIO

from Cookie import BaseCookie
from datetime import datetime, date, timedelta

from webob.headerdict import HeaderDict
from webob.statusreasons import status_reasons
from webob.cachecontrol import CacheControl, serialize_cache_control
try:
    sorted
except NameError:
    from webob.compat import sorted

from webob.descriptors import *
from webob.datetime_utils import *
from webob import descriptors, datetime_utils

__all__ = ['Response']

_PARAM_RE = re.compile(r'([a-z0-9]+)=(?:"([^"]*)"|([a-z0-9_.-]*))', re.I)
_OK_PARAM_RE = re.compile(r'^[a-z0-9_.-]+$', re.I)




class Response(object):
    """
        Represents a WSGI response
    """

    default_content_type = 'text/html'
    default_charset = 'UTF-8'
    unicode_errors = 'strict'
    default_conditional_response = False

    def __init__(self, body=None, status=None, headerlist=None, app_iter=None,
                 request=None, content_type=None, conditional_response=None,
                 **kw):
        if app_iter is None:
            if body is None:
                body = ''
        elif body is not None:
            raise TypeError(
                "You may only give one of the body and app_iter arguments")
        if status is None:
            self._status = '200 OK'
        else:
            self.status = status
        if headerlist is None:
            self._headerlist = []
        else:
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
        if content_type is None:
            content_type = self.default_content_type
        charset = None
        if 'charset' in kw:
            charset = kw.pop('charset')
        elif self.default_charset:
            if content_type and (content_type == 'text/html'
                                 or content_type.startswith('text/')
                                 or content_type.startswith('application/xml')
                                 or (content_type.startswith('application/')
                                     and content_type.endswith('+xml'))):
                charset = self.default_charset
        if content_type and charset:
            content_type += '; charset=' + charset
        elif self._headerlist and charset:
            self.charset = charset
        if not self._headerlist and content_type:
            self._headerlist.append(('Content-Type', content_type))
        if conditional_response is None:
            self.conditional_response = self.default_conditional_response
        else:
            self.conditional_response = bool(conditional_response)
        if app_iter is not None:
            self._app_iter = app_iter
            self._body = None
        else:
            if isinstance(body, unicode):
                if charset is None:
                    raise TypeError(
                        "You cannot set the body to a unicode value without a charset")
                body = body.encode(charset)
            self._body = body
            if headerlist is None:
                self._headerlist.append(('Content-Length', str(len(body))))
            else:
                self.headers['Content-Length'] = str(len(body))
            self._app_iter = None
        for name, value in kw.iteritems():
            if not hasattr(self.__class__, name):
                # Not a basic attribute
                raise TypeError(
                    "Unexpected keyword: %s=%r" % (name, value))
            setattr(self, name, value)

    def __repr__(self):
        return '<%s at 0x%x %s>' % (
            self.__class__.__name__,
            abs(id(self)),
            self.status)

    def __str__(self, skip_body=False):
        parts = [self.status]
        parts += map('%s: %s'.__mod__, self.headerlist)
        if not skip_body and self.body:
            parts += ['', self.body]
        return '\n'.join(parts)

    def copy(self):
        """Makes a copy of the response"""
        # we need to do this for app_iter to be reusable
        app_iter = list(self.app_iter)
        iter_close(self.app_iter)
        # and this to make sure app_iter instances are different
        self.app_iter = list(app_iter)
        return self.__class__(
            content_type=False,
            status=self._status,
            headerlist=self._headerlist[:],
            app_iter=app_iter,
            conditional_response=self.conditional_response)

    def _status__get(self):
        """
        The status string
        """
        return self._status

    def _status__set(self, value):
        if isinstance(value, unicode):
            # Status messages have to be ASCII safe, so this is OK:
            value = str(value)
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

    status = property(_status__get, _status__set, doc=_status__get.__doc__)

    def _status_int__get(self):
        """
        The status as an integer
        """
        return int(self._status.split()[0])
    def _status_int__set(self, code):
        self._status = '%d %s' % (code, status_reasons[code])
    status_int = property(_status_int__get, _status_int__set, doc=_status_int__get.__doc__)

    status_code = deprecated_property(
        status_int, 'status_code', 'use .status or .status_int instead',
        warning=False)

    def _headerlist__get(self):
        """
        The list of response headers
        """
        return self._headerlist

    def _headerlist__set(self, value):
        self._headers = None
        if not isinstance(value, list):
            if hasattr(value, 'items'):
                value = value.items()
            value = list(value)
        self._headerlist = value

    def _headerlist__del(self):
        self.headerlist = []

    headerlist = property(_headerlist__get, _headerlist__set, _headerlist__del, doc=_headerlist__get.__doc__)

    def _charset__get(self):
        """
        Get/set the charset (in the Content-Type)
        """
        header = self.headers.get('Content-Type')
        if not header:
            return None
        match = CHARSET_RE.search(header)
        if match:
            return match.group(1)
        return None

    def _charset__set(self, charset):
        if charset is None:
            del self.charset
            return
        try:
            header = self.headers.pop('Content-Type')
        except KeyError:
            raise AttributeError(
                "You cannot set the charset when no content-type is defined")
        match = CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        header += '; charset=%s' % charset
        self.headers['Content-Type'] = header

    def _charset__del(self):
        try:
            header = self.headers.pop('Content-Type')
        except KeyError:
            # Don't need to remove anything
            return
        match = CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        self.headers['Content-Type'] = header

    charset = property(_charset__get, _charset__set, _charset__del, doc=_charset__get.__doc__)

    def _content_type__get(self):
        """
        Get/set the Content-Type header (or None), *without* the
        charset or any parameters.

        If you include parameters (or ``;`` at all) when setting the
        content_type, any existing parameters will be deleted;
        otherwise they will be preserved.
        """
        header = self.headers.get('Content-Type')
        if not header:
            return None
        return header.split(';', 1)[0]

    def _content_type__set(self, value):
        if ';' not in value:
            header = self.headers.get('Content-Type', '')
            if ';' in header:
                params = header.split(';', 1)[1]
                value += ';' + params
        self.headers['Content-Type'] = value

    def _content_type__del(self):
        try:
            del self.headers['Content-Type']
        except KeyError:
            pass

    content_type = property(_content_type__get, _content_type__set,
                            _content_type__del, doc=_content_type__get.__doc__)

    def _content_type_params__get(self):
        """
        A dictionary of all the parameters in the content type.

        (This is not a view, set to change, modifications of the dict would not be
        applied otherwise)
        """
        params = self.headers.get('Content-Type', '')
        if ';' not in params:
            return {}
        params = params.split(';', 1)[1]
        result = {}
        for match in _PARAM_RE.finditer(params):
            result[match.group(1)] = match.group(2) or match.group(3) or ''
        return result

    def _content_type_params__set(self, value_dict):
        if not value_dict:
            del self.content_type_params
            return
        params = []
        for k, v in sorted(value_dict.items()):
            if not _OK_PARAM_RE.search(v):
                ## FIXME: I'm not sure what to do with "'s in the parameter value
                ## I think it might be simply illegal
                v = '"%s"' % v.replace('"', '\\"')
            params.append('; %s=%s' % (k, v))
        ct = self.headers.pop('Content-Type', '').split(';', 1)[0]
        ct += ''.join(params)
        self.headers['Content-Type'] = ct

    def _content_type_params__del(self, value):
        self.headers['Content-Type'] = self.headers.get('Content-Type', '').split(';', 1)[0]

    content_type_params = property(
        _content_type_params__get,
        _content_type_params__set,
        _content_type_params__del,
        doc=_content_type_params__get.__doc__
    )

    def _headers__get(self):
        """
        The headers in a dictionary-like object
        """
        if self._headers is None:
            self._headers = HeaderDict.view_list(self.headerlist)
        return self._headers

    def _headers__set(self, value):
        if hasattr(value, 'items'):
            value = value.items()
        self.headerlist = value
        self._headers = None

    headers = property(_headers__get, _headers__set, doc=_headers__get.__doc__)

    def _body__get(self):
        """
        The body of the response, as a ``str``.  This will read in the
        entire app_iter if necessary.
        """
        if self._body is None:
            if self._app_iter is None:
                raise AttributeError("No body has been set")
            try:
                body = self._body = ''.join(self._app_iter)
            finally:
                iter_close(self._app_iter)
            self._app_iter = None
            if self._environ is not None and self._environ['REQUEST_METHOD'] == 'HEAD':
                assert len(body) == 0, "HEAD responses must be empty"
            elif len(body) == 0:
                # if body-length is zero, we assume it's a HEAD response and leave content_length alone
                pass
            elif self.content_length is None:
                self.content_length = len(body)
            elif self.content_length != len(body):
                raise AssertionError(
                    "Content-Length is different from actual app_iter length (%r!=%r)"
                    % (self.content_length, len(body))
                )
        return self._body

    def _body__set(self, value):
        if isinstance(value, unicode):
            raise TypeError(
                "You cannot set Response.body to a unicode object (use Response.unicode_body)")
        if not isinstance(value, str):
            raise TypeError(
                "You can only set the body to a str (not %s)"
                % type(value))
        try:
            if self._body or self._app_iter:
                self.content_md5 = None
        except AttributeError:
            # if setting body early in initialization _body and _app_iter don't exist yet
            pass
        self._body = value
        self.content_length = len(value)
        self._app_iter = None

    def _body__del(self):
        self._body = None
        self.content_length = None
        self._app_iter = None

    body = property(_body__get, _body__set, _body__del, doc=_body__get.__doc__)

    def _body_file__get(self):
        """
        A file-like object that can be used to write to the
        body.  If you passed in a list app_iter, that app_iter will be
        modified by writes.
        """
        return ResponseBodyFile(self)

    def _body_file__del(self):
        del self.body

    body_file = property(_body_file__get, fdel=_body_file__del, doc=_body_file__get.__doc__)

    def write(self, text):
        if isinstance(text, unicode):
            self.unicode_body += text
        else:
            self.body += text

    def _unicode_body__get(self):
        """
        Get/set the unicode value of the body (using the charset of the Content-Type)
        """
        if not self.charset:
            raise AttributeError(
                "You cannot access Response.unicode_body unless charset is set")
        body = self.body
        return body.decode(self.charset, self.unicode_errors)

    def _unicode_body__set(self, value):
        if not self.charset:
            raise AttributeError(
                "You cannot access Response.unicode_body unless charset is set")
        if not isinstance(value, unicode):
            raise TypeError(
                "You can only set Response.unicode_body to a unicode string (not %s)" % type(value))
        self.body = value.encode(self.charset)

    def _unicode_body__del(self):
        del self.body

    unicode_body = property(_unicode_body__get, _unicode_body__set, _unicode_body__del, doc=_unicode_body__get.__doc__)
    #ubody = unicode_body # this alias will work as long as subclasses don't redefine unicode_body
    ubody = property(_unicode_body__get, _unicode_body__set, _unicode_body__del, doc="Alias for unicode_body")

    def _app_iter__get(self):
        """
        Returns the app_iter of the response.

        If body was set, this will create an app_iter from that body
        (a single-item list)
        """
        if self._app_iter is None:
            if self._body is None:
                raise AttributeError("No body or app_iter has been set")
            return [self._body]
        else:
            return self._app_iter

    def _app_iter__set(self, value):
        if self._body is not None:
            # Undo the automatically-set content-length
            self.content_length = None
        self._app_iter = value
        self._body = None

    def _app_iter__del(self):
        self.content_length = None
        self._app_iter = self._body = None

    app_iter = property(_app_iter__get, _app_iter__set, _app_iter__del, doc=_app_iter__get.__doc__)

    def set_cookie(self, key, value='', max_age=None,
                   path='/', domain=None, secure=None, httponly=False,
                   version=None, comment=None, expires=None, overwrite=False):
        """
        Set (add) a cookie for the response
        """
        if isinstance(value, unicode) and self.charset is not None:
            value = '"%s"' % value.encode(self.charset)
        if overwrite:
            self.unset_cookie(key, strict=False)
        cookies = BaseCookie()
        cookies[key] = value
        if isinstance(max_age, timedelta):
            max_age = max_age.seconds + max_age.days*24*60*60
        if max_age is not None and expires is None:
            expires = datetime.utcnow() + timedelta(seconds=max_age)
        if isinstance(expires, timedelta):
            expires = datetime.utcnow() + expires
        if isinstance(expires, datetime):
            expires = '"'+datetime_utils._serialize_cookie_date(expires)+'"'
        for var_name, var_value in [
            ('max-age', max_age),
            ('path', path),
            ('domain', domain),
            ('secure', secure),
            ('HttpOnly', httponly),
            ('version', version),
            ('comment', comment),
            ('expires', expires),
        ]:
            if var_value is not None and var_value is not False:
                cookies[key][var_name] = str(var_value)
        self._add_cookie(cookies)

    def _add_cookie(self, cookie):
        if not isinstance(cookie, str):
            cookie = cookie.output(header='').lstrip()
            if cookie.endswith(';'):
                # Python 2.4 adds a trailing ; to the end, strip it to be
                # consistent with 2.5
                cookie = cookie[:-1]
        if cookie:
            self.headerlist.append(('Set-Cookie', cookie))


    def delete_cookie(self, key, path='/', domain=None):
        """
        Delete a cookie from the client.  Note that path and domain must match
        how the cookie was originally set.

        This sets the cookie to the empty string, and max_age=0 so
        that it should expire immediately.
        """
        self.set_cookie(key, '', path=path, domain=domain,
                        max_age=0, expires=timedelta(days=-5))

    def unset_cookie(self, key, strict=True):
        """
        Unset a cookie with the given name (remove it from the
        response).  If there are multiple cookies (e.g., two cookies
        with the same name and different paths or domains), all such
        cookies will be deleted.
        """
        existing = self.headers.getall('Set-Cookie')
        if not existing:
            if not strict:
                return
            raise KeyError("No cookies at all have been set")
        del self.headers['Set-Cookie']
        found = False
        for header in existing:
            cookies = BaseCookie()
            cookies.load(header)
            if key in cookies:
                found = True
                del cookies[key]
                self._add_cookie(cookies)
            else:
                # this branching is required because Cookie.Morsel.output()
                # strips quotes from expires= parameter, so better use
                # it as is, if it hasn't changed
                self._add_cookie(header)
        if strict and not found:
            raise KeyError(
                "No cookie has been set with the name %r" % key)

    location = header_getter('Location', rfc_section='14.30')

    accept_ranges = header_getter('Accept-Ranges', rfc_section='14.5')

    age = converter(
        header_getter('Age', rfc_section='14.6'),
        descriptors._parse_int_safe, descriptors._serialize_int, 'int')

    allow = converter(
        header_getter('Allow', rfc_section='14.7'),
        descriptors._parse_list, descriptors._serialize_list, 'list')

    _cache_control_obj = None

    def _cache_control__get(self):
        """
        Get/set/modify the Cache-Control header (section `14.9
        <http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.9>`_)
        """
        value = self.headers.get('cache-control', '')
        if self._cache_control_obj is None:
            self._cache_control_obj = CacheControl.parse(value, updates_to=self._update_cache_control, type='response')
            self._cache_control_obj.header_value = value
        if self._cache_control_obj.header_value != value:
            new_obj = CacheControl.parse(value, type='response')
            self._cache_control_obj.properties.clear()
            self._cache_control_obj.properties.update(new_obj.properties)
            self._cache_control_obj.header_value = value
        return self._cache_control_obj

    def _cache_control__set(self, value):
        # This actually becomes a copy
        if not value:
            value = ""
        if isinstance(value, dict):
            value = CacheControl(value, 'response')
        if isinstance(value, unicode):
            value = str(value)
        if isinstance(value, str):
            if self._cache_control_obj is None:
                self.headers['Cache-Control'] = value
                return
            value = CacheControl.parse(value, 'response')
        cache = self.cache_control
        cache.properties.clear()
        cache.properties.update(value.properties)

    def _cache_control__del(self):
        self.cache_control = {}

    def _update_cache_control(self, prop_dict):
        value = serialize_cache_control(prop_dict)
        if not value:
            if 'Cache-Control' in self.headers:
                del self.headers['Cache-Control']
        else:
            self.headers['Cache-Control'] = value

    cache_control = property(_cache_control__get, _cache_control__set, _cache_control__del, doc=_cache_control__get.__doc__)

    def _cache_expires(self, seconds=0, **kw):
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
            if 'last-modified' not in self.headers:
                self.last_modified = datetime.utcnow()
            self.pragma = 'no-cache'
        else:
            cache_control.max_age = seconds
            self.expires = datetime.utcnow() + timedelta(seconds=seconds)
        for name, value in kw.items():
            setattr(cache_control, name, value)

    cache_expires = set_via_call(_cache_expires, descriptors._adapt_cache_expires)

    # FIXME: a special ContentDisposition type would be nice
    content_disposition = header_getter('Content-Disposition',
                                        rfc_section='19.5.1')

    content_encoding = header_getter('Content-Encoding', rfc_section='14.11')

    def encode_content(self, encoding='gzip'):
        """
        Encode the content with the given encoding (only gzip and
        identity are supported).
        """
        if encoding == 'identity':
            self.decode_content()
            return
        if encoding != 'gzip':
            raise ValueError(
                "Unknown encoding: %r" % encoding)
        if self.content_encoding:
            if self.content_encoding == encoding:
                return
            self.decode_content()
        from webob.util.safegzip import GzipFile
        f = StringIO()
        gzip_f = GzipFile(filename='', mode='w', fileobj=f)
        gzip_f.write(self.body)
        gzip_f.close()
        new_body = f.getvalue()
        f.close()
        self.content_encoding = 'gzip'
        self.body = new_body

    def decode_content(self):
        content_encoding = self.content_encoding or 'identity'
        if content_encoding == 'identity':
            return
        if content_encoding != 'gzip':
            raise ValueError(
                "I don't know how to decode the content %s" % content_encoding)
        from webob.util.safegzip import GzipFile
        f = StringIO(self.body)
        gzip_f = GzipFile(filename='', mode='r', fileobj=f)
        new_body = gzip_f.read()
        gzip_f.close()
        f.close()
        self.content_encoding = None
        self.body = new_body

    content_language = converter(
        header_getter('Content-Language', rfc_section='14.12'),
        descriptors._parse_list, descriptors._serialize_list, 'list')

    content_location = header_getter(
        'Content-Location', rfc_section='14.14')

    content_md5 = header_getter(
        'Content-MD5', rfc_section='14.14')

    content_range = converter(
        header_getter('Content-Range', rfc_section='14.16'),
        descriptors._parse_content_range, descriptors._serialize_content_range, 'ContentRange object')

    content_length = converter(
        header_getter('Content-Length', rfc_section='14.17'),
        descriptors._parse_int, descriptors._serialize_int, 'int')

    date = converter(
        header_getter('Date', rfc_section='14.18'),
        datetime_utils._parse_date, datetime_utils._serialize_date, 'HTTP date')

    etag = converter(
        header_getter('ETag', rfc_section='14.19'),
        descriptors._parse_etag_response, descriptors._serialize_etag_response, 'Entity tag')

    def md5_etag(self, body=None, set_content_md5=False):
        """
        Generate an etag for the response object using an MD5 hash of
        the body (the body parameter, or ``self.body`` if not given)

        Sets ``self.etag``
        If ``set_content_md5`` is True sets ``self.content_md5`` as well
        """
        if body is None:
            body = self.body
        try:
            from hashlib import md5
        except ImportError:
            from md5 import md5
        md5_digest = md5(body).digest().encode('base64').replace('\n', '')
        self.etag = md5_digest.strip('=')
        if set_content_md5:
            self.content_md5 = md5_digest

    expires = converter(
        header_getter('Expires', rfc_section='14.21'),
        datetime_utils._parse_date, datetime_utils._serialize_date, 'HTTP date')

    last_modified = converter(
        header_getter('Last-Modified', rfc_section='14.29'),
        datetime_utils._parse_date, datetime_utils._serialize_date, 'HTTP date')

    pragma = header_getter('Pragma', rfc_section='14.32')

    retry_after = converter(
        header_getter('Retry-After', rfc_section='14.37'),
        datetime_utils._parse_date_delta, datetime_utils._serialize_date_delta, 'HTTP date or delta seconds')

    server = header_getter('Server', rfc_section='14.38')

    ## FIXME: I realize response.vary += 'something' won't work.  It should.
    ## Maybe for all listy headers.
    vary = converter(
        header_getter('Vary', rfc_section='14.44'),
        descriptors._parse_list, descriptors._serialize_list, 'list')

    ## FIXME: the standard allows this to be a list of challenges
    www_authenticate = converter(
        header_getter('WWW-Authenticate', rfc_section='14.47'),
        descriptors.parse_auth, descriptors.serialize_auth,
    )



    def _request__get(self):
        """
        Return the request associated with this response if any.
        """
        if self._request is None and self._environ is not None:
            self._request = self.RequestClass(self._environ)
        return self._request

    def _request__set(self, value):
        if value is None:
            del self.request
            return
        if isinstance(value, dict):
            self._environ = value
            self._request = None
        else:
            self._request = value
            self._environ = value.environ

    def _request__del(self):
        self._request = self._environ = None

    request = property(_request__get, _request__set, _request__del, doc=_request__get.__doc__)

    def _environ__get(self):
        """
        Get/set the request environ associated with this response, if
        any.
        """
        return self._environ

    def _environ__set(self, value):
        if value is None:
            del self.environ
        self._environ = value
        self._request = None

    def _environ__del(self):
        self._request = self._environ = None

    environ = property(_environ__get, _environ__set, _environ__del, doc=_environ__get.__doc__)

    def merge_cookies(self, resp):
        """Merge the cookies that were set on this response with the
        given `resp` object (which can be any WSGI application).

        If the `resp` is a :class:`webob.Response` object, then the
        other object will be modified in-place.
        """
        if not self.headers.get('Set-Cookie'):
            return resp
        if isinstance(resp, Response):
            for header in self.headers.getall('Set-Cookie'):
                resp.headers.add('Set-Cookie', header)
            return resp
        else:
            def repl_app(environ, start_response):
                def repl_start_response(status, headers, exc_info=None):
                    headers.extend(self.headers.getall('Set-Cookie'))
                    return start_response(status, headers, exc_info=exc_info)
                return resp(environ, repl_start_response)
            return repl_app

    def __call__(self, environ, start_response):
        """
        WSGI application interface
        """
        if self.conditional_response:
            return self.conditional_response_app(environ, start_response)
        headerlist = self._abs_headerlist(environ)
        start_response(self.status, headerlist)
        if environ['REQUEST_METHOD'] == 'HEAD':
            # Special case here...
            return EmptyResponse(self.app_iter)
        return self.app_iter

    def _abs_headerlist(self, environ):
        """Returns a headerlist, with the Location header possibly
        made absolute given the request environ.
        """
        headerlist = self.headerlist
        for name, value in headerlist:
            if name.lower() == 'location':
                if SCHEME_RE.search(value):
                    break
                new_location = urlparse.urljoin(
                    _request_uri(environ), value)
                headerlist = list(headerlist)
                headerlist[headerlist.index((name, value))] = (name, new_location)
                break
        return headerlist

    _safe_methods = ('GET', 'HEAD')

    def conditional_response_app(self, environ, start_response):
        """
        Like the normal __call__ interface, but checks conditional headers:

        * If-Modified-Since   (304 Not Modified; only on GET, HEAD)
        * If-None-Match       (304 Not Modified; only on GET, HEAD)
        * Range               (406 Partial Content; only on GET, HEAD)
        """
        req = self.RequestClass(environ)
        status304 = False
        headerlist = self._abs_headerlist(environ)
        if req.method in self._safe_methods:
            if req.if_modified_since and self.last_modified and self.last_modified <= req.if_modified_since:
                status304 = True
            if req.if_none_match and self.etag:
                ## FIXME: should a weak match be okay?
                if self.etag in req.if_none_match:
                    status304 = True
                else:
                    # Even if If-Modified-Since matched, if ETag doesn't then reject it
                    status304 = False
        if status304:
            remove_headers = ['content-length', 'content-type']
            headerlist = filter(
                lambda (k,v): HeaderDict.normalize(k) not in remove_headers,
                headerlist
            )
            start_response('304 Not Modified', headerlist)
            return EmptyResponse(self.app_iter)
        if req.method == 'HEAD':
            start_response(self.status, headerlist)
            return EmptyResponse(self.app_iter)
        # FIXME: we should handle HEAD requests with Range
        if (req.range and req.if_range.match_response(self)
            and self.content_range is None
            and req.method == 'GET'
            and self.status_int == 200
            and self.content_length is not None
        ):
            content_range = req.range.content_range(self.content_length)
            # FIXME: we should support If-Range
            if content_range is None:
                iter_close(self.app_iter)
                # FIXME: we should use exc.HTTPRequestRangeNotSatisfiable
                # and let it generate the response body in correct content-type
                error_resp = Response(
                    status_int=416,
                    headers=list(headerlist),
                    content_range = ContentRange(None, None, self.content_length),
                )
                error_resp.body = "Requested range not satisfiable: %s" % req.range
                error_resp.content_type = 'text/plain'
                #error_resp.content_length = None
                return error_resp(environ, start_response)
            else:
                app_iter = self.app_iter_range(content_range.start, content_range.stop)
                if app_iter is not None:
                    partial_resp = Response(
                        status = '206 Partial Content',
                        headers=list(headerlist),
                        content_range=content_range,
                        app_iter=app_iter,
                    )
                    # this should be guaranteed by Range.range_for_length(length)
                    assert content_range.start is not None
                    partial_resp.content_length = content_range.stop - content_range.start
                    return partial_resp(environ, start_response)
        start_response(self.status, headerlist)
        return self.app_iter

    def app_iter_range(self, start, stop):
        """
        Return a new app_iter built from the response app_iter, that
        serves up only the given ``start:stop`` range.
        """
        if self._app_iter is None:
            return [self.body[start:stop]]
        app_iter = self.app_iter
        if hasattr(app_iter, 'app_iter_range'):
            return app_iter.app_iter_range(start, stop)
        return AppIterRange(app_iter, start, stop)



class ResponseBodyFile(object):
    mode = 'wb'
    closed = False

    def __init__(self, response):
        self.response = response

    def __repr__(self):
        return '<body_file for %r>' % self.response

    encoding = property(
        lambda self: self.response.charset,
        doc="The encoding of the file (inherited from response.charset)"
    )

    def write(self, s):
        if isinstance(s, unicode):
            if self.response.charset is None:
                raise TypeError(
                    "You can only write unicode to Response.body_file "
                    "if charset has been set"
                )
            s = s.encode(self.response.charset)
        if not isinstance(s, str):
            raise TypeError(
                "You can only write str to a Response.body_file, not %s"
                % type(s)
            )
        if not isinstance(self.response._app_iter, list):
            body = self.response.body
            if body:
                self.response.app_iter = [body]
            else:
                self.response.app_iter = []
        self.response.app_iter.append(s)

    def writelines(self, seq):
        for item in seq:
            self.write(item)

    def close(self):
        raise NotImplementedError("Response bodies cannot be closed")

    def flush(self):
        pass



class AppIterRange(object):
    """
    Wraps an app_iter, returning just a range of bytes
    """

    def __init__(self, app_iter, start, stop):
        assert start >= 0, "Bad start: %r" % start
        assert stop is None or (stop >= 0 and stop >= start), (
            "Bad stop: %r" % stop)
        self.app_iter = iter(app_iter)
        self._pos = 0 # position in app_iter
        self.start = start
        self.stop = stop

    def __iter__(self):
        return self

    def _skip_start(self):
        start, stop = self.start, self.stop
        for chunk in self.app_iter:
            self._pos += len(chunk)
            if self._pos < start:
                continue
            elif self._pos == start:
                return ''
            else:
                chunk = chunk[start-self._pos:]
                if stop is not None and self._pos > stop:
                    chunk = chunk[:stop-self._pos]
                    assert len(chunk) == stop - start
                return chunk
        else:
            raise StopIteration()


    def next(self):
        if self._pos < self.start:
            # need to skip some leading bytes
            return self._skip_start()
        stop = self.stop
        if stop is not None and self._pos >= stop:
            raise StopIteration

        chunk = self.app_iter.next()
        self._pos += len(chunk)

        if stop is None or self._pos <= stop:
            return chunk
        else:
            return chunk[:stop-self._pos]

    def close(self):
        iter_close(self.app_iter)


class EmptyResponse(object):
    """An empty WSGI response.

    An iterator that immediately stops. Optionally provides a close
    method to close an underlying app_iter it replaces.
    """

    def __init__(self, app_iter=None):
        if app_iter and hasattr(app_iter, 'close'):
            self.close = app_iter.close

    def __iter__(self):
        return self

    def __len__(self):
        return 0

    def next(self):
        raise StopIteration()

def _request_uri(environ):
    """Like wsgiref.url.request_uri, except eliminates :80 ports

    Return the full request URI"""
    url = environ['wsgi.url_scheme']+'://'
    from urllib import quote

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME'] + ':' + environ['SERVER_PORT']
    if url.endswith(':80') and environ['wsgi.url_scheme'] == 'http':
        url = url[:-3]
    elif url.endswith(':443') and environ['wsgi.url_scheme'] == 'https':
        url = url[:-4]

    url += quote(environ.get('SCRIPT_NAME') or '/')
    from urllib import quote
    path_info = quote(environ.get('PATH_INFO',''))
    if not environ.get('SCRIPT_NAME'):
        url += path_info[1:]
    else:
        url += path_info
    return url


def iter_close(iter):
    if hasattr(iter, 'close'):
        iter.close()
