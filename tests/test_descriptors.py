from datetime import tzinfo
from datetime import timedelta

import pytest

from webob.compat import (
    native_,
    text_,
    )

from webob.request import Request

class GMT(tzinfo):
    """UTC"""
    ZERO = timedelta(0)
    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO


class MockDescriptor:
    _val = 'avalue'
    def __get__(self, obj, type=None):
        return self._val
    def __set__(self, obj, val):
        self._val = val
    def __delete__(self, obj):
        self._val = None


def test_environ_getter_docstring():
    from webob.descriptors import environ_getter
    desc = environ_getter('akey')
    assert desc.__doc__ == "Gets and sets the ``akey`` key in the environment."

def test_environ_getter_nodefault_keyerror():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey')
    with pytest.raises(KeyError):
        desc.fget(req)

def test_environ_getter_nodefault_fget():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey')
    desc.fset(req, 'bar')
    assert req.environ['akey'] == 'bar'

def test_environ_getter_nodefault_fdel():
    from webob.descriptors import environ_getter
    desc = environ_getter('akey')
    assert desc.fdel is None

def test_environ_getter_default_fget():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    assert desc.fget(req) == 'the_default'

def test_environ_getter_default_fset():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    desc.fset(req, 'bar')
    assert req.environ['akey'] == 'bar'

def test_environ_getter_default_fset_none():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    desc.fset(req, 'baz')
    desc.fset(req, None)
    assert 'akey' not in req.environ

def test_environ_getter_default_fdel():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    desc.fset(req, 'baz')
    assert 'akey' in req.environ
    desc.fdel(req)
    assert 'akey' not in req.environ

def test_environ_getter_rfc_section():
    from webob.descriptors import environ_getter
    desc = environ_getter('HTTP_X_AKEY', rfc_section='14.3')
    assert desc.__doc__ == "Gets and sets the ``X-Akey`` header "\
        "(`HTTP spec section 14.3 "\
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_)."


def test_upath_property_fget():
    from webob.descriptors import upath_property
    req = Request.blank('/')
    desc = upath_property('akey')
    assert desc.fget(req) == ''

def test_upath_property_fset():
    from webob.descriptors import upath_property
    req = Request.blank('/')
    desc = upath_property('akey')
    desc.fset(req, 'avalue')
    assert desc.fget(req) == 'avalue'

def test_header_getter_doc():
    from webob.descriptors import header_getter
    desc = header_getter('X-Header', '14.3')
    assert('http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3'
           in desc.__doc__)
    assert '``X-Header`` header' in desc.__doc__

def test_header_getter_fget():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    assert desc.fget(resp) is None

def test_header_getter_fset():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue')
    assert desc.fget(resp) == 'avalue'

def test_header_getter_fset_none():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue')
    desc.fset(resp, None)
    assert desc.fget(resp) is None

def test_header_getter_fset_text():
    from webob.compat import text_
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, text_('avalue'))
    assert desc.fget(resp) == 'avalue'

def test_header_getter_fset_text_control_chars():
    from webob.compat import text_
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    with pytest.raises(ValueError):
        desc.fset(resp, text_('\n'))

def test_header_getter_fdel():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue2')
    desc.fdel(resp)
    assert desc.fget(resp) is None

def test_header_getter_unicode_fget_none():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    assert desc.fget(resp) is None

def test_header_getter_unicode_fget():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue')
    assert desc.fget(resp) == 'avalue'

def test_header_getter_unicode_fset_none():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, None)
    assert desc.fget(resp) is None

def test_header_getter_unicode_fset():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue2')
    assert desc.fget(resp) == 'avalue2'

def test_header_getter_unicode_fdel():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    desc.fset(resp, 'avalue3')
    desc.fdel(resp)
    assert desc.fget(resp) is None

def test_converter_not_prop():
    from webob.descriptors import converter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    with pytest.raises(AssertionError):
        converter(
            ('CONTENT_LENGTH', None, '14.13'),
            parse_int_safe, serialize_int,
            'int')

def test_converter_with_name_docstring():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')

    assert 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13' in desc.__doc__
    assert '``Content-Length`` header' in desc.__doc__

def test_converter_with_name_fget():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    assert desc.fget(req) == 666

def test_converter_with_name_fset():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    desc.fset(req, '999')
    assert desc.fget(req) == 999

def test_converter_without_name_fget():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int)
    assert desc.fget(req) == 666

def test_converter_without_name_fset():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int)
    desc.fset(req, '999')
    assert desc.fget(req) == 999

def test_converter_none_for_wrong_type():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', 'sixsixsix', '14.13'),
        parse_int_safe, serialize_int, 'int')
    assert desc.fget(req) is None

def test_converter_delete():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    with pytest.raises(KeyError):
        desc.fdel(req)

def test_list_header():
    from webob.descriptors import list_header
    desc = list_header('CONTENT_LENGTH', '14.13')
    assert type(desc) == property

def test_parse_list_single():
    from webob.descriptors import parse_list
    result = parse_list('avalue')
    assert result == ('avalue',)

def test_parse_list_multiple():
    from webob.descriptors import parse_list
    result = parse_list('avalue,avalue2')
    assert result == ('avalue', 'avalue2')

def test_parse_list_none():
    from webob.descriptors import parse_list
    result = parse_list(None)
    assert result is None

def test_parse_list_unicode_single():
    from webob.descriptors import parse_list
    result = parse_list('avalue')
    assert result == ('avalue',)

def test_parse_list_unicode_multiple():
    from webob.descriptors import parse_list
    result = parse_list('avalue,avalue2')
    assert result == ('avalue', 'avalue2')

def test_serialize_list():
    from webob.descriptors import serialize_list
    result = serialize_list(('avalue', 'avalue2'))
    assert result == 'avalue, avalue2'

def test_serialize_list_string():
    from webob.descriptors import serialize_list
    result = serialize_list('avalue')
    assert result == 'avalue'

def test_serialize_list_unicode():
    from webob.descriptors import serialize_list
    result = serialize_list('avalue')
    assert result == 'avalue'

def test_converter_date():
    import datetime
    from webob.descriptors import converter_date
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    UTC = GMT()
    desc = converter_date(environ_getter(
        "HTTP_DATE", "Tue, 15 Nov 1994 08:12:31 GMT", "14.8"))
    assert desc.fget(req) == datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=UTC)

def test_converter_date_docstring():
    from webob.descriptors import converter_date
    from webob.descriptors import environ_getter
    desc = converter_date(environ_getter(
        "HTTP_DATE", "Tue, 15 Nov 1994 08:12:31 GMT", "14.8"))
    assert 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.8' in desc.__doc__
    assert '``Date`` header' in desc.__doc__


def test_date_header_fget_none():
    from webob import Response
    from webob.descriptors import date_header
    resp = Response('aresponse')
    desc = date_header('HTTP_DATE', "14.8")
    assert desc.fget(resp) is None

def test_date_header_fset_fget():
    import datetime
    from webob import Response
    from webob.descriptors import date_header
    resp = Response('aresponse')
    UTC = GMT()
    desc = date_header('HTTP_DATE', "14.8")
    desc.fset(resp, "Tue, 15 Nov 1994 08:12:31 GMT")
    assert desc.fget(resp) == datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=UTC)

def test_date_header_fdel():
    from webob import Response
    from webob.descriptors import date_header
    resp = Response('aresponse')
    desc = date_header('HTTP_DATE', "14.8")
    desc.fset(resp, "Tue, 15 Nov 1994 08:12:31 GMT")
    desc.fdel(resp)
    assert desc.fget(resp) is None

def test_deprecated_property():
    from webob.descriptors import deprecated_property

    class Foo(object):
        pass
    Foo.attr = deprecated_property('attr', 'attr', 'whatever', '1.2')
    foo = Foo()
    with pytest.raises(DeprecationWarning):
        getattr(foo, 'attr')
    with pytest.raises(DeprecationWarning):
        setattr(foo, 'attr', {})
    with pytest.raises(DeprecationWarning):
        delattr(foo, 'attr')

def test_parse_etag_response():
    from webob.descriptors import parse_etag_response
    etresp = parse_etag_response("etag")
    assert etresp == "etag"

def test_parse_etag_response_quoted():
    from webob.descriptors import parse_etag_response
    etresp = parse_etag_response('"etag"')
    assert etresp == "etag"

def test_parse_etag_response_is_none():
    from webob.descriptors import parse_etag_response
    etresp = parse_etag_response(None)
    assert etresp is None

def test_serialize_etag_response():
    from webob.descriptors import serialize_etag_response
    etresp = serialize_etag_response("etag")
    assert etresp == '"etag"'

def test_serialize_if_range_string():
    from webob.descriptors import serialize_if_range
    val = serialize_if_range("avalue")
    assert val == "avalue"

def test_serialize_if_range_unicode():
    from webob.descriptors import serialize_if_range
    val = serialize_if_range("avalue")
    assert val == "avalue"

def test_serialize_if_range_datetime():
    import datetime
    from webob.descriptors import serialize_if_range
    UTC = GMT()
    val = serialize_if_range(datetime.datetime(1994, 11, 15, 8, 12, 31, tzinfo=UTC))
    assert val, "Tue == 15 Nov 1994 08:12:31 GMT"

def test_serialize_if_range_other():
    from webob.descriptors import serialize_if_range
    val = serialize_if_range(123456)
    assert val == '123456'

def test_parse_range_none():
    from webob.descriptors import parse_range
    assert parse_range(None) is None

def test_parse_range_type():
    from webob.byterange import Range
    from webob.descriptors import parse_range
    val = parse_range("bytes=1-500")
    assert type(val) is type(Range.parse("bytes=1-500"))

def test_parse_range_values():
    from webob.byterange import Range
    range = Range.parse("bytes=1-500")
    assert range.start == 1
    assert range.end == 501

def test_serialize_range_none():
    from webob.descriptors import serialize_range
    val = serialize_range(None)
    assert val is None

def test_serialize_range():
    from webob.descriptors import serialize_range
    val = serialize_range((1, 500))
    assert val == 'bytes=1-499'

def test_parse_int_none():
    from webob.descriptors import parse_int
    val = parse_int(None)
    assert val is None

def test_parse_int_emptystr():
    from webob.descriptors import parse_int
    val = parse_int('')
    assert val is None

def test_parse_int():
    from webob.descriptors import parse_int
    val = parse_int('123')
    assert val == 123

def test_parse_int_invalid():
    from webob.descriptors import parse_int
    with pytest.raises(ValueError):
        parse_int('abc')

def test_parse_int_safe_none():
    from webob.descriptors import parse_int_safe
    assert parse_int_safe(None) is None

def test_parse_int_safe_emptystr():
    from webob.descriptors import parse_int_safe
    assert parse_int_safe('') is None

def test_parse_int_safe():
    from webob.descriptors import parse_int_safe
    assert parse_int_safe('123') == 123

def test_parse_int_safe_invalid():
    from webob.descriptors import parse_int_safe
    assert parse_int_safe('abc') is None

def test_serialize_int():
    from webob.descriptors import serialize_int
    assert serialize_int is str

def test_parse_content_range_none():
    from webob.descriptors import parse_content_range
    assert parse_content_range(None) is None

def test_parse_content_range_emptystr():
    from webob.descriptors import parse_content_range
    assert parse_content_range(' ') is None

def test_parse_content_range_length():
    from webob.byterange import ContentRange
    from webob.descriptors import parse_content_range
    val = parse_content_range("bytes 0-499/1234")
    assert val.length == ContentRange.parse("bytes 0-499/1234").length

def test_parse_content_range_start():
    from webob.byterange import ContentRange
    from webob.descriptors import parse_content_range
    val = parse_content_range("bytes 0-499/1234")
    assert val.start == ContentRange.parse("bytes 0-499/1234").start

def test_parse_content_range_stop():
    from webob.byterange import ContentRange
    from webob.descriptors import parse_content_range
    val = parse_content_range("bytes 0-499/1234")
    assert val.stop == ContentRange.parse("bytes 0-499/1234").stop

def test_serialize_content_range_none():
    from webob.descriptors import serialize_content_range
    assert serialize_content_range(None) == 'None' ### XXX: Seems wrong

def test_serialize_content_range_emptystr():
    from webob.descriptors import serialize_content_range
    assert serialize_content_range('') is None

def test_serialize_content_range_invalid():
    from webob.descriptors import serialize_content_range
    with pytest.raises(ValueError):
        serialize_content_range((1,))

def test_serialize_content_range_asterisk():
    from webob.descriptors import serialize_content_range
    assert serialize_content_range((0, 500)) == 'bytes 0-499/*'

def test_serialize_content_range_defined():
    from webob.descriptors import serialize_content_range
    assert serialize_content_range((0, 500, 1234)) == 'bytes 0-499/1234'

def test_parse_auth_params_leading_capital_letter():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params('Basic Realm=WebOb')
    assert val == {'ealm': 'WebOb'}

def test_parse_auth_params_trailing_capital_letter():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params('Basic realM=WebOb')
    assert val == {}

def test_parse_auth_params_doublequotes():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params('Basic realm="Web Object"')
    assert val == {'realm': 'Web Object'}

def test_parse_auth_params_multiple_values():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params("foo='blah &&234', qop=foo, nonce='qwerty1234'")
    assert val == {'nonce': "'qwerty1234'", 'foo': "'blah &&234'", 'qop': 'foo'}

def test_parse_auth_params_truncate_on_comma():
    from webob.descriptors import parse_auth_params
    val = parse_auth_params("Basic realm=WebOb,this_will_truncate")
    assert val == {'realm': 'WebOb'}

def test_parse_auth_params_emptystr():
    from webob.descriptors import parse_auth_params
    assert parse_auth_params('') == {}

def test_parse_auth_params_bad_whitespace():
    from webob.descriptors import parse_auth_params
    assert parse_auth_params('a= "2 ", b =3, c=4 ') == {
        'a': '2 ',
        'b': '3',
        'c': '4'
    }

def test_authorization2():
    from webob.descriptors import parse_auth_params
    for s, d in [
            ('x=y', {'x': 'y'}),
            ('x="y"', {'x': 'y'}),
            ('x=y,z=z', {'x': 'y', 'z': 'z'}),
            ('x=y, z=z', {'x': 'y', 'z': 'z'}),
            ('x="y",z=z', {'x': 'y', 'z': 'z'}),
            ('x="y", z=z', {'x': 'y', 'z': 'z'}),
            ('x="y,x", z=z', {'x': 'y,x', 'z': 'z'}),
            ]:
        assert parse_auth_params(s) == d

def test_parse_auth_none():
    from webob.descriptors import parse_auth
    assert parse_auth(None) is None

def test_parse_auth_emptystr():
    from webob.descriptors import parse_auth
    assert parse_auth('') == ('', '')

def test_parse_auth_bearer():
    from webob.descriptors import parse_auth
    assert parse_auth('Bearer token').authtype == 'Bearer'
    assert parse_auth('Bearer token').params == 'token'

def test_parse_auth_unknown_nospace():
    from webob.descriptors import parse_auth
    assert parse_auth('NoSpace') == ('NoSpace', '')

def test_parse_auth_known_nospace():
    from webob.descriptors import parse_auth
    assert parse_auth('Digest') == ('Digest', {})

def test_parse_auth_basic():
    from webob.descriptors import parse_auth
    assert parse_auth("Basic realm=WebOb") == ('Basic', 'realm=WebOb')

def test_parse_auth_basic_quoted():
    from webob.descriptors import parse_auth
    assert parse_auth('Basic realm="Web Ob"') == ('Basic', {'realm': 'Web Ob'})

def test_parse_auth_basic_quoted_multiple_unknown():
    from webob.descriptors import parse_auth
    assert parse_auth("foo='blah &&234', qop=foo, nonce='qwerty1234'") == (
        "foo='blah",
        "&&234', qop=foo, nonce='qwerty1234'"
    )

def test_parse_auth_basic_quoted_known_multiple():
    from webob.descriptors import parse_auth
    assert parse_auth("Basic realm='blah &&234', qop=foo, nonce='qwerty1234'") == (
        'Basic',
        "realm='blah &&234', qop=foo, nonce='qwerty1234'"
    )

def test_serialize_auth_none():
    from webob.descriptors import serialize_auth
    assert serialize_auth(None) is None

def test_serialize_auth_emptystr():
    from webob.descriptors import serialize_auth
    assert serialize_auth('') == ''

def test_serialize_auth_str():
    from webob.descriptors import serialize_auth
    assert serialize_auth('some string') == 'some string'

def test_serialize_auth_parsed_emptystr():
    from webob.descriptors import serialize_auth
    assert serialize_auth(('', '')) == ' '

def test_serialize_auth_parsed_unknown_nospace():
    from webob.descriptors import serialize_auth
    assert serialize_auth(('NoSpace', '')) == 'NoSpace '

def test_serialize_auth_parsed_known_nospace():
    from webob.descriptors import serialize_auth
    assert serialize_auth(('Digest', {})) == 'Digest '

def test_serialize_auth_basic_quoted():
    from webob.descriptors import serialize_auth
    val = serialize_auth(('Basic', 'realm="WebOb"'))
    assert val == 'Basic realm="WebOb"'

def test_serialize_auth_digest_multiple():
    from webob.descriptors import serialize_auth
    val = serialize_auth(('Digest', 'realm="WebOb", nonce=abcde12345, qop=foo'))
    flags = val[len('Digest'):]
    result = sorted([ x.strip() for x in flags.split(',') ])
    assert result == ['nonce=abcde12345', 'qop=foo', 'realm="WebOb"']

def test_serialize_auth_digest_tuple():
    from webob.descriptors import serialize_auth
    val = serialize_auth(('Digest', {'realm':'"WebOb"', 'nonce':'abcde12345', 'qop':'foo'}))
    flags = val[len('Digest'):]
    result = sorted([ x.strip() for x in flags.split(',') ])
    assert result == ['nonce="abcde12345"', 'qop="foo"', 'realm=""WebOb""']


_nodefault = object()

class _TestEnvironDecoder(object):
    def _callFUT(self, key, default=_nodefault, rfc_section=None,
                 encattr=None):
        from webob.descriptors import environ_decoder
        if default is _nodefault:
            return environ_decoder(key, rfc_section=rfc_section,
                                   encattr=encattr)
        else:
            return environ_decoder(key, default=default,
                                   rfc_section=rfc_section, encattr=encattr)

    def test_docstring(self):
        desc = self._callFUT('akey')
        assert desc.__doc__ == "Gets and sets the ``akey`` key in the environment."

    def test_nodefault_keyerror(self):
        req = self._makeRequest()
        desc = self._callFUT('akey')
        with pytest.raises(KeyError):
            desc.fget(req)

    def test_nodefault_fget(self):
        req = self._makeRequest()
        desc = self._callFUT('akey')
        desc.fset(req, 'bar')
        assert req.environ['akey'] == 'bar'

    def test_nodefault_fdel(self):
        desc = self._callFUT('akey')
        assert desc.fdel is None

    def test_default_fget(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        assert desc.fget(req) == 'the_default'

    def test_default_fset(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        desc.fset(req, 'bar')
        assert req.environ['akey'] == 'bar'

    def test_default_fset_none(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        desc.fset(req, 'baz')
        desc.fset(req, None)
        assert 'akey' not in req.environ

    def test_default_fdel(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default='the_default')
        desc.fset(req, 'baz')
        assert 'akey' in req.environ
        desc.fdel(req)
        assert 'akey' not in req.environ

    def test_rfc_section(self):
        desc = self._callFUT('HTTP_X_AKEY', rfc_section='14.3')
        assert desc.__doc__ == "Gets and sets the ``X-Akey`` header "\
            "(`HTTP spec section 14.3 "\
            "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_)."

    def test_fset_nonascii(self):
        desc = self._callFUT('HTTP_X_AKEY', encattr='url_encoding')
        req = self._makeRequest()
        desc.fset(req, text_(b'\xc3\xab', 'utf-8'))
        assert req.environ['HTTP_X_AKEY'] == native_(b'\xc3\xab', 'latin-1')

class TestEnvironDecoder(_TestEnvironDecoder):
    def _makeRequest(self):
        from webob.request import BaseRequest
        req = BaseRequest.blank('/')
        return req

    def test_fget_nonascii(self):
        desc = self._callFUT('HTTP_X_AKEY', encattr='url_encoding')
        req = self._makeRequest()
        req.environ['HTTP_X_AKEY'] = native_(b'\xc3\xab')
        result = desc.fget(req)
        assert result == text_(b'\xc3\xab', 'utf-8')

class TestEnvironDecoderLegacy(_TestEnvironDecoder):
    def _makeRequest(self):
        from webob.request import LegacyRequest
        req = LegacyRequest.blank('/')
        return req

    def test_fget_nonascii(self):
        desc = self._callFUT('HTTP_X_AKEY', encattr='url_encoding')
        req = self._makeRequest()
        req.environ['HTTP_X_AKEY'] = native_(b'\xc3\xab', 'latin-1')
        result = desc.fget(req)
        assert result == native_(b'\xc3\xab', 'latin-1')

    def test_default_fget_nonascii(self):
        req = self._makeRequest()
        desc = self._callFUT('akey', default=b'the_default')
        assert desc.fget(req).__class__ == bytes
