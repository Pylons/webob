import pytest

from datetime import timedelta

from webob import cookies
from webob.compat import text_
from webob.compat import native_
from webob.compat import PY3

def setup_module(module):
    cookies._should_raise = True

def teardown_module(module):
    cookies._should_raise = False

def test_cookie_empty():
    c = cookies.Cookie() # empty cookie
    assert repr(c) == '<Cookie: []>'

def test_cookie_one_value():
    c = cookies.Cookie('dismiss-top=6')
    vals = list(c.values())
    assert len(vals) == 1
    assert vals[0].name == b'dismiss-top'
    assert vals[0].value == b'6'

def test_cookie_one_value_with_trailing_semi():
    c = cookies.Cookie('dismiss-top=6;')
    vals = list(c.values())
    assert len(vals) == 1
    assert vals[0].name == b'dismiss-top'
    assert vals[0].value == b'6'
    c = cookies.Cookie('dismiss-top=6;')

def test_cookie_escaped_unquoted():
    assert list(cookies.parse_cookie('x=\\040')) == [(b'x', b' ')]

def test_cookie_complex():
    c = cookies.Cookie('dismiss-top=6; CP=null*, '
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,"')
    def d(v):
        return v.decode('ascii')
    c_dict = dict((d(k), d(v.value)) for k, v in c.items())
    assert c_dict == {
        'a': '42,',
        'CP': 'null*',
        'PHPSESSID': '0a539d42abc001cdc762809248d4beed',
        'dismiss-top': '6'
    }

def test_cookie_complex_serialize():
    c = cookies.Cookie('dismiss-top=6; CP=null*, '
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42"')
    assert c.serialize() == 'CP=null*; PHPSESSID=0a539d42abc001cdc762809248d4beed;'\
                            ' a=42; dismiss-top=6'

def test_cookie_load_multiple():
    c = cookies.Cookie('a=1; Secure=true')
    vals = list(c.values())
    assert len(vals) == 1
    assert c[b'a'][b'secure'] == b'true'

def test_cookie_secure():
    c = cookies.Cookie()
    c[text_('foo')] = b'bar'
    c[b'foo'].secure = True
    assert c.serialize() == 'foo=bar; secure'

def test_cookie_httponly():
    c = cookies.Cookie()
    c['foo'] = b'bar'
    c[b'foo'].httponly = True
    assert c.serialize() == 'foo=bar; HttpOnly'

def test_cookie_reserved_keys():
    c = cookies.Cookie('dismiss-top=6; CP=null*; $version=42; a=42')
    assert '$version' not in c
    c = cookies.Cookie('$reserved=42; a=$42')
    assert list(c.keys()) == [b'a']

def test_serialize_cookie_date():
    """
        Testing webob.cookies.serialize_cookie_date.
        Missing scenarios:
            * input value is an str, should be returned verbatim
            * input value is an int, should be converted to timedelta and we
              should continue the rest of the process
    """
    date_one = cookies.serialize_cookie_date(b'Tue, 04-Jan-2011 13:43:50 GMT')
    assert date_one == b'Tue, 04-Jan-2011 13:43:50 GMT'
    date_two = cookies.serialize_cookie_date(text_('Tue, 04-Jan-2011 13:43:50 GMT'))
    assert date_two == b'Tue, 04-Jan-2011 13:43:50 GMT'
    assert cookies.serialize_cookie_date(None) is None
    cdate_delta = cookies.serialize_cookie_date(timedelta(seconds=10))
    cdate_int = cookies.serialize_cookie_date(10)
    assert cdate_delta == cdate_int

def test_ch_unquote():
    assert cookies._unquote(b'"hello world') == b'"hello world'
    assert cookies._unquote(b'hello world') == b'hello world'
    assert cookies._unquote(b'"hello world"') == b'hello world'

    # Spaces are not valid in cookies, we support getting them, but won't
    # support sending them
    with pytest.raises(ValueError):
        cookies._value_quote(b'hello world')

    # quotation mark escaped w/ backslash is unquoted correctly (support
    # pre webob 1.3 cookies)
    assert cookies._unquote(b'"\\""') == b'"'
    # we also are able to unquote the newer \\042 serialization of quotation
    # mark
    assert cookies._unquote(b'"\\042"') == b'"'

    # New cookies can not contain quotes.
    with pytest.raises(ValueError):
        cookies._value_quote(b'"')

    # backslash escaped w/ backslash is unquoted correctly (support
    # pre webob 1.3 cookies)
    assert cookies._unquote(b'"\\\\"') == b'\\'
    # we also are able to unquote the newer \\134 serialization of backslash
    assert cookies._unquote(b'"\\134"') == b'\\'

    # Cookies may not contain a backslash
    with pytest.raises(ValueError):
        cookies._value_quote(b'\\')

    # misc byte escaped as octal
    assert cookies._unquote(b'"\\377"') == b'\xff'

    with pytest.raises(ValueError):
        cookies._value_quote(b'\xff')

    # combination
    assert cookies._unquote(b'"a\\"\\377"') == b'a"\xff'
    with pytest.raises(ValueError):
        cookies._value_quote(b'a"\xff')

def test_cookie_invalid_name():
    c = cookies.Cookie()
    c['La Pe\xc3\xb1a'] = '1'
    assert len(c) == 0

def test_morsel_serialize_with_expires():
    morsel = cookies.Morsel(b'bleh', b'blah')
    morsel.expires = b'Tue, 04-Jan-2011 13:43:50 GMT'
    result = morsel.serialize()
    assert result, 'bleh=blah; expires=Tue, 04-Jan-2011 13:43:50 GMT'

def test_serialize_max_age_timedelta():
    import datetime
    val = datetime.timedelta(86400)
    result = cookies.serialize_max_age(val)
    assert result == b'7464960000'

def test_serialize_max_age_int():
    val = 86400
    result = cookies.serialize_max_age(val)
    assert result == b'86400'

def test_serialize_max_age_str():
    val = '86400'
    result = cookies.serialize_max_age(val)
    assert result == b'86400'

def test_parse_qmark_in_val():
    v = r'x="\"\073\054\""; expires=Sun, 12-Jun-2011 23:16:01 GMT'
    c = cookies.Cookie(v)
    assert c[b'x'].value == b'";,"'
    assert c[b'x'].expires, b'Sun == 12-Jun-2011 23:16:01 GMT'

def test_morsel_repr():
    v = cookies.Morsel(b'a', b'b')
    result = repr(v)
    assert result == "<Morsel: a='b'>"

class TestRequestCookies(object):
    def _makeOne(self, environ):
        from webob.cookies import RequestCookies
        return RequestCookies(environ)

    def test_get_no_cache_key_in_environ_no_http_cookie_header(self):
        environ = {}
        inst = self._makeOne(environ)
        assert inst.get('a') is None
        parsed = environ['webob._parsed_cookies']
        assert parsed == ({}, '')

    def test_get_no_cache_key_in_environ_has_http_cookie_header(self):
        header = 'a=1; b=2'
        environ = {'HTTP_COOKIE': header}
        inst = self._makeOne(environ)
        assert inst.get('a') == '1'
        parsed = environ['webob._parsed_cookies'][0]
        assert parsed['a'] == '1'
        assert parsed['b'] == '2'
        assert environ['HTTP_COOKIE'] == header # no change

    def test_get_cache_key_in_environ_no_http_cookie_header(self):
        environ = {'webob._parsed_cookies': ({}, '')}
        inst = self._makeOne(environ)
        assert inst.get('a') is None
        parsed = environ['webob._parsed_cookies']
        assert parsed == ({}, '')

    def test_get_cache_key_in_environ_has_http_cookie_header(self):
        header = 'a=1; b=2'
        environ = {'HTTP_COOKIE': header, 'webob._parsed_cookies': ({}, '')}
        inst = self._makeOne(environ)
        assert inst.get('a') == '1'
        parsed = environ['webob._parsed_cookies'][0]
        assert parsed['a'] == '1'
        assert parsed['b'] == '2'
        assert environ['HTTP_COOKIE'] == header # no change

    def test_get_missing_with_default(self):
        environ = {}
        inst = self._makeOne(environ)
        assert inst.get('a', '') == ''

    def test___setitem__name_not_string_type(self):
        inst = self._makeOne({})
        with pytest.raises(TypeError):
            inst.__setitem__(None, 1)

    def test___setitem__name_not_encodeable_to_ascii(self):
        name = native_(b'La Pe\xc3\xb1a', 'utf-8')
        inst = self._makeOne({})
        with pytest.raises(TypeError):
            inst.__setitem__(name, 'abc')

    def test___setitem__name_not_rfc2109_valid(self):
        name = '$a'
        inst = self._makeOne({})
        with pytest.raises(TypeError):
            inst.__setitem__(name, 'abc')

    def test___setitem__value_not_string_type(self):
        inst = self._makeOne({})
        with pytest.raises(ValueError):
            inst.__setitem__('a', None)

    def test___setitem__value_not_utf_8_decodeable(self):
        value = text_(b'La Pe\xc3\xb1a', 'utf-8')
        value = value.encode('utf-16')
        inst = self._makeOne({})
        with pytest.raises(ValueError):
            inst.__setitem__('a', value)

    def test__setitem__success_no_existing_headers(self):
        value = native_(b'test_cookie', 'utf-8')
        environ = {}
        inst = self._makeOne(environ)
        inst['a'] = value
        assert environ['HTTP_COOKIE'] == 'a=test_cookie'

    def test__setitem__success_append(self):
        value = native_(b'test_cookie', 'utf-8')
        environ = {'HTTP_COOKIE': 'a=1; b=2'}
        inst = self._makeOne(environ)
        inst['c'] = value
        assert environ['HTTP_COOKIE'] == 'a=1; b=2; c=test_cookie'

    def test__setitem__success_replace(self):
        environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        inst['b'] = 'abc'
        assert environ['HTTP_COOKIE'] == 'a=1; b=abc; c=3'
        inst['c'] = '4'
        assert environ['HTTP_COOKIE'] == 'a=1; b=abc; c=4'

    def test__delitem__fail_no_http_cookie(self):
        environ = {}
        inst = self._makeOne(environ)
        with pytest.raises(KeyError):
            inst.__delitem__('a')
        assert environ == {}

    def test__delitem__fail_with_http_cookie(self):
        environ = {'HTTP_COOKIE': ''}
        inst = self._makeOne(environ)
        with pytest.raises(KeyError):
            inst.__delitem__('a')
        assert environ == {'HTTP_COOKIE': ''}

    def test__delitem__success(self):
        environ = {'HTTP_COOKIE': 'a=1'}
        inst = self._makeOne(environ)
        del inst['a']
        assert environ['HTTP_COOKIE'] == ''
        assert inst._cache == {}

    def test_keys(self):
        environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        assert sorted(list(inst.keys())) == ['a', 'b', 'c']

    def test_values(self):
        val = text_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        assert sorted(list(inst.values())) == ['1', '3', val]

    def test_items(self):
        val = text_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        assert sorted(list(inst.items())) == [('a', '1'), ('b', val), ('c', '3')]

    if not PY3:
        def test_iterkeys(self):
            environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            assert sorted(list(inst.iterkeys())) == ['a', 'b', 'c']

        def test_itervalues(self):
            val = text_(b'La Pe\xc3\xb1a', 'utf-8')
            environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            sorted(list(inst.itervalues())) == ['1', '3', val]

        def test_iteritems(self):
            val = text_(b'La Pe\xc3\xb1a', 'utf-8')
            environ = {'HTTP_COOKIE': 'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            assert sorted(list(inst.iteritems())) == [('a', '1'), ('b', val), ('c', '3')]

    def test___contains__(self):
        environ = {'HTTP_COOKIE': 'a=1'}
        inst = self._makeOne(environ)
        assert 'a' in inst
        assert 'b' not in inst

    def test___iter__(self):
        environ = {'HTTP_COOKIE': 'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        assert sorted(list(iter(inst))) == ['a', 'b', 'c']

    def test___len__(self):
        environ = {'HTTP_COOKIE': 'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        assert len(inst) == 3
        del inst['a']
        assert len(inst) == 2

    def test_clear(self):
        environ = {'HTTP_COOKIE': 'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        inst.clear()
        assert environ['HTTP_COOKIE'] == ''
        assert inst.get('a') is None

    def test___repr__(self):
        environ = {'HTTP_COOKIE': 'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        r = repr(inst)
        assert r.startswith('<RequestCookies (dict-like) with values ')
        assert r.endswith('>')


class TestCookieMakeCookie(object):
    def makeOne(self, name, value, **kw):
        from webob.cookies import make_cookie
        return make_cookie(name, value, **kw)

    def test_make_cookie_max_age(self):
        cookie = self.makeOne('test_cookie', 'value', max_age=500)

        assert 'test_cookie=value' in cookie
        assert 'Max-Age=500;' in cookie
        assert 'expires' in cookie

    def test_make_cookie_max_age_timedelta(self):
        from datetime import timedelta
        cookie = self.makeOne('test_cookie', 'value',
                              max_age=timedelta(seconds=500))

        assert 'test_cookie=value' in cookie
        assert 'Max-Age=500;' in cookie
        assert 'expires' in cookie
        assert 'expires=500' not in cookie

    def test_make_cookie_max_age_str_valid_int(self):
        cookie = self.makeOne('test_cookie', 'value',
                              max_age='500')

        assert 'test_cookie=value' in cookie
        assert 'Max-Age=500;' in cookie
        assert 'expires' in cookie
        assert 'expires=500' not in cookie

    def test_make_cookie_max_age_str_invalid_int(self):
        with pytest.raises(ValueError):
            self.makeOne('test_cookie', 'value', max_age='test')

    def test_make_cookie_comment(self):
        cookie = self.makeOne('test_cookie', 'value', comment='lolwhy')

        assert 'test_cookie=value' in cookie
        assert 'Comment=lolwhy' in cookie

    def test_make_cookie_path(self):
        cookie = self.makeOne('test_cookie', 'value', path='/foo/bar/baz')

        assert 'test_cookie=value' in cookie
        assert 'Path=/foo/bar/baz' in cookie

class CommonCookieProfile(object):
    def makeDummyRequest(self, **kw):
        class Dummy(object):
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)
        d = Dummy(**kw)
        d.response = Dummy()
        d.response.headerlist = list()
        return d

    def makeOneRequest(self):
        request = self.makeDummyRequest(environ=dict())
        request.environ['HTTP_HOST'] = 'www.example.net'
        request.cookies = dict()

        return request


class TestCookieProfile(CommonCookieProfile):
    def makeOne(self, name='uns', **kw):
        if 'request' in kw:
            request = kw['request']
            del kw['request']
        else:
            request = self.makeOneRequest()

        from webob.cookies import CookieProfile
        return CookieProfile(name, **kw)(request)

    def test_cookie_creation(self):
        cookie = self.makeOne()

        from webob.cookies import CookieProfile
        assert isinstance(cookie, CookieProfile)

    def test_cookie_name(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test")

        for cookie in cookie_list:
            assert cookie[1].startswith('uns')
            assert 'uns="";' not in cookie[1]

    def test_cookie_no_request(self):
        from webob.cookies import CookieProfile
        cookie = CookieProfile('uns')

        with pytest.raises(ValueError):
            cookie.get_value()

    def test_get_value_serializer_raises_value_error(self):
        class RaisingSerializer(object):
            def loads(self, val):
                raise ValueError('foo')
        cookie = self.makeOne(serializer=RaisingSerializer())
        assert cookie.get_value() is None

    def test_with_cookies(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = 'InRlc3Qi'
        cookie = self.makeOne(request=request)
        ret = cookie.get_value()

        assert ret == "test"

    def test_with_invalid_cookies(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = 'InRlc3Q'
        cookie = self.makeOne(request=request)
        ret = cookie.get_value()

        assert ret is None

class TestSignedCookieProfile(CommonCookieProfile):
    def makeOne(self, secret='seekrit', salt='salty', name='uns', **kw):
        if 'request' in kw:
            request = kw['request']
            del kw['request']
        else:
            request = self.makeOneRequest()

        from webob.cookies import SignedCookieProfile as CookieProfile
        return CookieProfile(secret, salt, name, **kw)(request)

    def test_cookie_name(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test")

        for cookie in cookie_list:
            assert cookie[1].startswith('uns')
            assert 'uns="";' not in cookie[1]

    def test_cookie_expire(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers(None, max_age=0)

        for cookie in cookie_list:
            assert 'Max-Age=0;' in cookie[1]

    def test_cookie_max_age(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test", max_age=60)

        for cookie in cookie_list:
            assert 'Max-Age=60;' in cookie[1]
            assert 'expires=' in cookie[1]

    def test_cookie_raw(self):
        cookie = self.makeOne()

        cookie_list = cookie.get_headers("test")

        assert isinstance(cookie_list, list)

    def test_set_cookie(self):
        request = self.makeOneRequest()
        cookie = self.makeOne(request=request)

        ret = cookie.set_cookies(request.response, "test")

        assert ret == request.response

    def test_no_cookie(self):
        cookie = self.makeOne()

        ret = cookie.get_value()

        assert ret is None

    def test_with_cookies(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = (
            'FLIoEwZcKG6ITQSqbYcUNnPljwOcGNs25JRVCSoZcx_uX-OA1AhssA-CNeVKpWksQ'
            'a0ktMhuQDdjzmDwgzbptiJ0ZXN0Ig'
            )
        cookie = self.makeOne(request=request)
        ret = cookie.get_value()

        assert ret == "test"

    def test_with_bad_cookie_invalid_base64(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = (
            "gAJVBHRlc3RxAS4KjKfwGmCkliC4ba99rWUdpy_{}riHzK7MQFPsbSgYTgALHa"
            "SHrRkd3lyE8c4w5ruxAKOyj2h5oF69Ix7ERZv_")
        cookie = self.makeOne(request=request)

        val = cookie.get_value()

        assert val is None

    def test_with_bad_cookie_invalid_signature(self):
        request = self.makeOneRequest()
        request.cookies['uns'] = (
            "InRlc3QiFLIoEwZcKG6ITQSqbYcUNnPljwOcGNs25JRVCSoZcx/uX+OA1AhssA"
            "+CNeVKpWksQa0ktMhuQDdjzmDwgzbptg==")
        cookie = self.makeOne(secret='sekrit!', request=request)

        val = cookie.get_value()

        assert val is None

    def test_with_domain(self):
        cookie = self.makeOne(domains=("testing.example.net",))
        ret = cookie.get_headers("test")

        passed = False

        for cookie in ret:
            if 'Domain=testing.example.net' in cookie[1]:
                passed = True

        assert passed
        assert len(ret) == 1

    def test_with_domains(self):
        cookie = self.makeOne(
            domains=("testing.example.net", "testing2.example.net")
            )
        ret = cookie.get_headers("test")

        passed = 0

        for cookie in ret:
            if 'Domain=testing.example.net' in cookie[1]:
                passed += 1
            if 'Domain=testing2.example.net' in cookie[1]:
                passed += 1

        assert passed == 2
        assert len(ret) == 2

    def test_flag_secure(self):
        cookie = self.makeOne(secure=True)
        ret = cookie.get_headers("test")

        for cookie in ret:
            assert '; secure' in cookie[1]

    def test_flag_http_only(self):
        cookie = self.makeOne(httponly=True)
        ret = cookie.get_headers("test")

        for cookie in ret:
            assert '; HttpOnly' in cookie[1]

    def test_cookie_length(self):
        cookie = self.makeOne()

        longstring = 'a' * 4096
        with pytest.raises(ValueError):
            cookie.get_headers(longstring)

    def test_very_long_key(self):
        longstring = 'a' * 1024
        cookie = self.makeOne(secret=longstring)

        cookie.get_headers("test")

def serialize(secret, salt, data):
    import hmac
    import base64
    import json
    from hashlib import sha1
    from webob.compat import bytes_
    salted_secret = bytes_(salt or '', 'utf-8') + bytes_(secret, 'utf-8')
    cstruct = bytes_(json.dumps(data))
    sig = hmac.new(salted_secret, cstruct, sha1).digest()
    return base64.urlsafe_b64encode(sig + cstruct).rstrip(b'=')

class TestSignedSerializer(object):
    def makeOne(self, secret, salt, hashalg='sha1', **kw):
        from webob.cookies import SignedSerializer
        return SignedSerializer(secret, salt, hashalg=hashalg, **kw)

    def test_serialize(self):
        ser = self.makeOne('seekrit', 'salty')

        assert ser.dumps('test') == serialize('seekrit', 'salty', 'test')

    def test_deserialize(self):
        ser = self.makeOne('seekrit', 'salty')

        assert ser.loads(serialize('seekrit', 'salty', 'test')) == 'test'

    def test_with_highorder_secret(self):
        secret = b'\xce\xb1\xce\xb2\xce\xb3\xce\xb4'.decode('utf-8')
        ser = self.makeOne(secret, 'salty')

        assert ser.loads(serialize(secret, 'salty', 'test')) == 'test'

    def test_with_highorder_salt(self):
        salt = b'\xce\xb1\xce\xb2\xce\xb3\xce\xb4'.decode('utf-8')
        ser = self.makeOne('secret', salt)

        assert ser.loads(serialize('secret', salt, 'test')) == 'test'

    # bw-compat with webob <= 1.3.1 where secrets were encoded with latin-1
    def test_with_latin1_secret(self):
        secret = b'La Pe\xc3\xb1a'
        ser = self.makeOne(secret.decode('latin-1'), 'salty')

        assert ser.loads(serialize(secret, 'salty', 'test')), 'test'

    # bw-compat with webob <= 1.3.1 where salts were encoded with latin-1
    def test_with_latin1_salt(self):
        salt = b'La Pe\xc3\xb1a'
        ser = self.makeOne('secret', salt.decode('latin-1'))

        assert ser.loads(serialize('secret', salt, 'test')) == 'test'
