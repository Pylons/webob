import zlib
import io

import pytest

from webob.request import BaseRequest
from webob.request import Request
from webob.response import Response
from webob.compat import text_
from webob.compat import bytes_
from webob import cookies

def setup_module(module):
    cookies._should_raise = True

def teardown_module(module):
    cookies._should_raise = False

def simple_app(environ, start_response):
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf8'),
        ])
    return ['OK']

def test_response():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    assert res.status == '200 OK'
    assert res.status_code == 200
    assert res.body == "OK"
    assert res.charset == 'utf8'
    assert res.content_type == 'text/html'
    res.status = 404
    assert res.status == '404 Not Found'
    assert res.status_code == 404
    res.body = b'Not OK'
    assert b''.join(res.app_iter) == b'Not OK'
    res.charset = 'iso8859-1'
    assert res.headers['content-type'] == 'text/html; charset=iso8859-1'
    res.content_type = 'text/xml'
    assert res.headers['content-type'] == 'text/xml; charset=iso8859-1'
    res.headers = {'content-type': 'text/html'}
    assert res.headers['content-type'] == 'text/html'
    assert res.headerlist == [('content-type', 'text/html')]
    res.set_cookie('x', 'y')
    assert res.headers['set-cookie'].strip(';') == 'x=y; Path=/'
    res.set_cookie(text_('x'), text_('y'))
    assert res.headers['set-cookie'].strip(';') == 'x=y; Path=/'
    res = Response('a body', '200 OK', content_type='text/html')
    res.encode_content()
    assert res.content_encoding == 'gzip'
    assert res.body == b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xffKTH\xcaO\xa9\x04\x00\xf6\x86GI\x06\x00\x00\x00'
    res.decode_content()
    assert res.content_encoding is None
    assert res.body == b'a body'
    res.set_cookie('x', text_(b'foo')) # test unicode value
    with pytest.raises(TypeError):
        Response(app_iter=iter(['a']),
                 body="somebody")
    del req.environ
    with pytest.raises(TypeError):
        Response(charset=None,
                 content_type='image/jpeg',
                 body=text_(b"unicode body"))
    with pytest.raises(TypeError):
        Response(wrong_key='dummy')

def test_set_response_status_binary():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status == b'200 OK'
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_set_response_status_str_no_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status = '200'
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_set_response_status_str_generic_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status = '299'
    assert res.status_code == 299
    assert res.status == '299 Success'

def test_set_response_status_code():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status_code = 200
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_set_response_status_bad():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    def status_test():
        res.status = 'ThisShouldFail'

    with pytest.raises(ValueError):
        status_test()

def test_set_response_status_code_generic_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status_code = 299
    assert res.status_code == 299
    assert res.status == '299 Success'

def test_content_type():
    r = Response()
    # default ctype and charset
    assert r.content_type == 'text/html'
    assert r.charset == 'UTF-8'
    # setting to none, removes the header
    r.content_type = None
    assert r.content_type is None
    assert r.charset is None
    # can set missing ctype
    r.content_type = None
    assert r.content_type is None

def test_init_content_type_w_charset():
    v = 'text/plain;charset=ISO-8859-1'
    assert Response(content_type=v).headers['content-type'] == v

def test_init_adds_default_charset_when_not_json():
    content_type = 'text/plain'
    expected = 'text/plain; charset=UTF-8'
    assert Response(content_type=content_type).headers['content-type'] == expected

def test_init_no_charset_when_json():
    content_type = 'application/json'
    expected = content_type
    assert Response(content_type=content_type).headers['content-type'] == expected

def test_init_keeps_specified_charset_when_json():
    content_type = 'application/json;charset=ISO-8859-1'
    expected = content_type
    assert Response(content_type=content_type).headers['content-type'] == expected

def test_set_charset_fails_when_json():
    content_type = 'application/json'
    expected = content_type
    res = Response(content_type=content_type)
    res.charset = 'utf-8'
    assert res.headers['content-type'] == expected
    res.content_type_params = {'charset': 'utf-8'}
    assert res.headers['content-type'] == expected


def test_cookies():
    res = Response()
    # test unicode value
    res.set_cookie('x', "test")
    # utf8 encoded
    assert res.headers.getall('set-cookie') == ['x=test; Path=/']
    r2 = res.merge_cookies(simple_app)
    r2 = BaseRequest.blank('/').get_response(r2)
    assert r2.headerlist == [
        ('Content-Type', 'text/html; charset=utf8'),
        ('Set-Cookie', 'x=test; Path=/'),
        ]

def test_unicode_cookies_error_raised():
    res = Response()
    with pytest.raises(ValueError):
        Response.set_cookie(
            res,
            'x',
            text_(b'\N{BLACK SQUARE}', 'unicode_escape'))

def test_unicode_cookies_warning_issued():
    import warnings

    cookies._should_raise = False

    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Trigger a warning.

        res = Response()
        res.set_cookie('x', text_(b'\N{BLACK SQUARE}', 'unicode_escape'))

        assert len(w) == 1
        assert issubclass(w[-1].category, RuntimeWarning) is True
        assert "ValueError" in str(w[-1].message)

    cookies._should_raise = True

# Remove in version 1.7
def test_cookies_warning_issued_backwards_compat():
    import warnings

    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Trigger a warning.

        res = Response()
        res.set_cookie(key='x', value='test')

        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning) is True
        assert 'Argument "key" was renamed to "name".' in str(w[-1].message)

    cookies._should_raise = True

def test_cookies_raises_typeerror():
    res = Response()
    with pytest.raises(TypeError):
        res.set_cookie()

def test_http_only_cookie():
    req = Request.blank('/')
    res = req.get_response(Response('blah'))
    res.set_cookie("foo", "foo", httponly=True)
    assert res.headers['set-cookie'] == 'foo=foo; Path=/; HttpOnly'

def test_headers():
    r = Response()
    tval = 'application/x-test'
    r.headers.update({'content-type': tval})
    assert r.headers.getall('content-type') == [tval]
    r.headers.clear()
    assert not r.headerlist

def test_response_copy():
    r = Response(app_iter=iter(['a']))
    r2 = r.copy()
    assert r.body == 'a'
    assert r2.body == 'a'

def test_response_copy_content_md5():
    res = Response()
    res.md5_etag(set_content_md5=True)
    assert res.content_md5
    res2 = res.copy()
    assert res.content_md5
    assert res2.content_md5
    assert res.content_md5 == res2.content_md5

def test_HEAD_closes():
    req = Request.blank('/')
    req.method = 'HEAD'
    app_iter = io.BytesIO(b'foo')
    res = req.get_response(Response(app_iter=app_iter))
    assert res.status_code == 200
    assert res.body == b''
    assert app_iter.closed

def test_HEAD_conditional_response_returns_empty_response():
    req = Request.blank('/', method='HEAD', if_none_match='none')
    res = Response(conditional_response=True)
    def start_response(status, headerlist):
        pass
    result = res(req.environ, start_response)
    assert not list(result)

def test_HEAD_conditional_response_range_empty_response():
    req = Request.blank('/', method='HEAD', range=(4, 5))
    res = Response('Are we not men?', conditional_response=True)
    assert req.get_response(res).body == b''


def test_conditional_response_if_none_match_false():
    req = Request.blank('/', if_none_match='foo')
    resp = Response(app_iter=['foo\n'], conditional_response=True, etag='bar')
    resp = req.get_response(resp)
    assert resp.status_code == 200

def test_conditional_response_if_none_match_true():
    req = Request.blank('/', if_none_match='foo')
    resp = Response(app_iter=['foo\n'], conditional_response=True, etag='foo')
    resp = req.get_response(resp)
    assert resp.status_code == 304

def test_conditional_response_if_none_match_weak():
    req = Request.blank('/', headers={'if-none-match': '"bar"'})
    req_weak = Request.blank('/', headers={'if-none-match': 'W/"bar"'})
    resp = Response(app_iter=['foo\n'], conditional_response=True, etag='bar')
    resp_weak = Response(app_iter=['foo\n'],
                         conditional_response=True, headers={'etag': 'W/"bar"'})
    for rq in [req, req_weak]:
        for rp in [resp, resp_weak]:
            rq.get_response(rp).status_code == 304

    r2 = Response(app_iter=['foo\n'],
                  conditional_response=True,
                  headers={'etag': '"foo"'})
    r2_weak = Response(app_iter=['foo\n'],
                       conditional_response=True,
                       headers={'etag': 'W/"foo"'})
    req_weak.get_response(r2).status_code == 200
    req.get_response(r2_weak) == 200


def test_conditional_response_if_modified_since_false():
    from datetime import datetime, timedelta
    req = Request.blank('/', if_modified_since=datetime(2011, 3, 17, 13, 0, 0))
    resp = Response(app_iter=['foo\n'], conditional_response=True,
                    last_modified=req.if_modified_since - timedelta(seconds=1))
    resp = req.get_response(resp)
    assert resp.status_code == 304

def test_conditional_response_if_modified_since_true():
    from datetime import datetime, timedelta
    req = Request.blank('/', if_modified_since=datetime(2011, 3, 17, 13, 0, 0))
    resp = Response(app_iter=['foo\n'], conditional_response=True,
                    last_modified=req.if_modified_since + timedelta(seconds=1))
    resp = req.get_response(resp)
    assert resp.status_code == 200

def test_conditional_response_range_not_satisfiable_response():
    req = Request.blank('/', range='bytes=100-200')
    resp = Response(app_iter=['foo\n'], content_length=4, conditional_response=True)
    resp = req.get_response(resp)
    assert resp.status_code == 416
    assert resp.content_range.start is None
    assert resp.content_range.stop is None
    assert resp.content_range.length == 4
    assert resp.body == b'Requested range not satisfiable: bytes=100-200'

def test_HEAD_conditional_response_range_not_satisfiable_response():
    req = Request.blank('/', method='HEAD', range='bytes=100-200')
    resp = Response(app_iter=['foo\n'], content_length=4, conditional_response=True)
    resp = req.get_response(resp)
    assert resp.status_code == 416
    assert resp.content_range.start is None
    assert resp.content_range.stop is None
    assert resp.content_range.length == 4
    assert resp.body == b''

def test_md5_etag():
    res = Response()
    res.body = b"""\
In A.D. 2101
War was beginning.
Captain: What happen ?
Mechanic: Somebody set up us the bomb.
Operator: We get signal.
Captain: What !
Operator: Main screen turn on.
Captain: It's You !!
Cats: How are you gentlemen !!
Cats: All your base are belong to us.
Cats: You are on the way to destruction.
Captain: What you say !!
Cats: You have no chance to survive make your time.
Cats: HA HA HA HA ....
Captain: Take off every 'zig' !!
Captain: You know what you doing.
Captain: Move 'zig'.
Captain: For great justice."""
    res.md5_etag()
    assert res.etag
    assert '\n' not in res.etag
    assert res.etag == 'pN8sSTUrEaPRzmurGptqmw'
    assert res.content_md5 is None

def test_md5_etag_set_content_md5():
    res = Response()
    body = b'The quick brown fox jumps over the lazy dog'
    res.md5_etag(body, set_content_md5=True)
    assert res.content_md5 == 'nhB9nTcrtoJr2B01QqQZ1g=='

def test_decode_content_defaults_to_identity():
    res = Response()
    res.body = b'There be dragons'
    res.decode_content()
    assert res.body == b'There be dragons'

def test_decode_content_with_deflate():
    res = Response()
    body = b'Hey Hey Hey'
    # Simulate inflate by chopping the headers off
    # the gzip encoded data
    res.body = zlib.compress(body)[2:-4]
    res.content_encoding = 'deflate'
    res.decode_content()
    assert res.body == body
    assert res.content_encoding is None

def test_content_length():
    r0 = Response('x' * 10, content_length=10)

    req_head = Request.blank('/', method='HEAD')
    r1 = req_head.get_response(r0)
    assert r1.status_code == 200
    assert r1.body == b''
    assert r1.content_length == 10

    req_get = Request.blank('/')
    r2 = req_get.get_response(r0)
    assert r2.status_code == 200
    assert r2.body == b'x' * 10
    assert r2.content_length == 10

    r3 = Response(app_iter=[b'x'] * 10)
    assert r3.content_length is None
    assert r3.body == b'x' * 10
    assert r3.content_length == 10

    r4 = Response(app_iter=[b'x'] * 10,
                  content_length=20) # wrong content_length
    assert r4.content_length == 20
    with pytest.raises(AssertionError):
        r4.body

    req_range = Request.blank('/', range=(0, 5))
    r0.conditional_response = True
    r5 = req_range.get_response(r0)
    assert r5.status_code == 206
    assert r5.body == b'xxxxx'
    assert r5.content_length == 5

def test_app_iter_range():
    req = Request.blank('/', range=(2, 5))
    for app_iter in [
        [b'012345'],
        [b'0', b'12345'],
        [b'0', b'1234', b'5'],
        [b'01', b'2345'],
        [b'01', b'234', b'5'],
        [b'012', b'34', b'5'],
        [b'012', b'3', b'4', b'5'],
        [b'012', b'3', b'45'],
        [b'0', b'12', b'34', b'5'],
        [b'0', b'12', b'345'],
    ]:
        r = Response(
            app_iter=app_iter,
            content_length=6,
            conditional_response=True,
        )
        res = req.get_response(r)
        assert list(res.content_range) == [2, 5, 6]
        assert res.body, b'234'

def test_app_iter_range_inner_method():
    class FakeAppIter:
        def app_iter_range(self, start, stop):
            return 'you win', start, stop
    res = Response(app_iter=FakeAppIter())
    assert res.app_iter_range(30, 40), ('you win', 30 == 40)

def test_has_body():
    empty = Response()
    assert not empty.has_body

    with_list = Response(app_iter=['1'])
    assert with_list.has_body

    with_empty_list = Response(app_iter=[b''])
    assert not with_empty_list.has_body

    with_body = Response(body='Seomthing')
    assert with_body.has_body

    with_none_app_iter = Response(app_iter=None)
    assert not with_none_app_iter.has_body

    with_none_body = Response(body=None)
    assert not with_none_body.has_body

    # key feature: has_body should not read app_iter
    app_iter = iter(['1', '2'])
    not_iterating = Response(app_iter=app_iter)
    assert not_iterating.has_body
    assert next(app_iter) == '1'

    # messed with private attribute but method should nonetheless not
    # return True
    messing_with_privates = Response()
    messing_with_privates._app_iter = None
    assert not messing_with_privates.has_body

def test_content_type_in_headerlist():
    # Couldn't manage to clone Response in order to modify class
    # attributes safely. Shouldn't classes be fresh imported for every
    # test?
    default_content_type = Response.default_content_type
    Response.default_content_type = None
    try:
        res = Response(headerlist=[('Content-Type', 'text/html')], charset='utf8')
        assert res._headerlist
        assert res.charset == 'utf8'
    finally:
        Response.default_content_type = default_content_type

def test_str_crlf():
    res = Response('test')
    assert '\r\n' in str(res)

def test_from_file():
    res = Response('test')
    inp = io.BytesIO(bytes_(str(res)))
    equal_resp(res, inp)

def test_from_file2():
    res = Response(app_iter=iter([b'test ', b'body']),
                   content_type='text/plain')
    inp = io.BytesIO(bytes_(str(res)))
    equal_resp(res, inp)

def test_from_text_file():
    res = Response('test')
    inp = io.StringIO(text_(str(res), 'utf-8'))
    equal_resp(res, inp)
    res = Response(app_iter=iter([b'test ', b'body']),
                   content_type='text/plain')
    inp = io.StringIO(text_(str(res), 'utf-8'))
    equal_resp(res, inp)

def equal_resp(res, inp):
    res2 = Response.from_file(inp)
    assert res.body == res2.body
    assert res.headers == res2.headers

def test_from_file_w_leading_space_in_header():
    # Make sure the removal of code dealing with leading spaces is safe
    res1 = Response()
    file_w_space = io.BytesIO(
        b'200 OK\n\tContent-Type: text/html; charset=UTF-8')
    res2 = Response.from_file(file_w_space)
    assert res1.headers == res2.headers

def test_file_bad_header():
    file_w_bh = io.BytesIO(b'200 OK\nBad Header')
    with pytest.raises(ValueError):
        Response.from_file(file_w_bh)

def test_from_file_not_unicode_headers():
    inp = io.BytesIO(
        b'200 OK\n\tContent-Type: text/html; charset=UTF-8')
    res = Response.from_file(inp)
    assert res.headerlist[0][0].__class__ == str

def test_file_with_http_version():
    inp = io.BytesIO(b'HTTP/1.1 200 OK\r\n\r\nSome data...')

    res = Response.from_file(inp)
    assert res.status_code == 200
    assert res.status == '200 OK'

def test_file_with_http_version_more_status():
    inp = io.BytesIO(b'HTTP/1.1 404 Not Found\r\n\r\nSome data...')

    res = Response.from_file(inp)
    assert res.status_code == 404
    assert res.status == '404 Not Found'

def test_set_status():
    res = Response()
    res.status = "200"
    assert res.status == "200 OK"
    with pytest.raises(TypeError):
        setattr(res, 'status', (200,))

def test_set_headerlist():
    res = Response()
    # looks like a list
    res.headerlist = (('Content-Type', 'text/html; charset=UTF-8'),)
    assert res.headerlist == [('Content-Type', 'text/html; charset=UTF-8')]

    # has items
    res.headerlist = {'Content-Type': 'text/html; charset=UTF-8'}
    assert res.headerlist == [('Content-Type', 'text/html; charset=UTF-8')]

    del res.headerlist
    assert res.headerlist == []

def test_request_uri_no_script_name():
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'HTTP_HOST': 'test.com',
    }
    assert _request_uri(environ) == 'http://test.com/'

def test_request_uri_https():
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'https',
        'SERVER_NAME': 'test.com',
        'SERVER_PORT': '443',
        'SCRIPT_NAME': '/foobar',
    }
    assert _request_uri(environ) == 'https://test.com/foobar'

def test_app_iter_range_starts_after_iter_end():
    from webob.response import AppIterRange
    range = AppIterRange(iter([]), start=1, stop=1)
    assert list(range) == []

def test_resp_write_app_iter_non_list():
    res = Response(app_iter=(b'a', b'b'))
    assert res.content_length is None
    res.write(b'c')
    assert res.body == b'abc'
    assert res.content_length == 3

def test_response_file_body_writelines():
    from webob.response import ResponseBodyFile
    res = Response(app_iter=[b'foo'])
    rbo = ResponseBodyFile(res)
    rbo.writelines(['bar', 'baz'])
    assert res.app_iter == [b'foo', b'bar', b'baz']
    rbo.flush() # noop
    assert res.app_iter, [b'foo', b'bar', b'baz']

def test_response_write_non_str():
    res = Response()
    with pytest.raises(TypeError):
        res.write(object())

def test_response_file_body_write_empty_app_iter():
    res = Response('foo')
    res.write('baz')
    assert res.app_iter == [b'foo', b'baz']

def test_response_file_body_write_empty_body():
    res = Response('')
    res.write('baz')
    assert res.app_iter == [b'', b'baz']

def test_response_file_body_close_not_implemented():
    rbo = Response().body_file
    with pytest.raises(NotImplementedError):
        rbo.close()

def test_response_file_body_repr():
    rbo = Response().body_file
    rbo.response = 'yo'
    assert repr(rbo) == "<body_file for 'yo'>"

def test_body_get_is_none():
    res = Response()
    res._app_iter = None
    with pytest.raises(TypeError):
        Response(app_iter=iter(['a']), body="somebody")
    with pytest.raises(AttributeError):
        res.__getattribute__('body')

def test_body_get_is_unicode_notverylong():
    res = Response(app_iter=(text_(b'foo'),))
    with pytest.raises(TypeError):
        res.__getattribute__('body')

def test_body_get_is_unicode():
    res = Response(app_iter=(['x'] * 51 + [text_(b'x')]))
    with pytest.raises(TypeError):
        res.__getattribute__('body')

def test_body_set_not_unicode_or_str():
    res = Response()
    with pytest.raises(TypeError):
        res.__setattr__('body', object())

def test_body_set_unicode():
    res = Response()
    with pytest.raises(TypeError):
        res.__setattr__('body', text_(b'abc'))

def test_body_set_under_body_doesnt_exist():
    res = Response('abc')
    assert res.body == b'abc'
    assert res.content_length == 3

def test_body_del():
    res = Response('123')
    del res.body
    assert res.body == b''
    assert res.content_length == 0

def test_text_get_no_charset():
    res = Response(charset=None)
    with pytest.raises(AttributeError):
        res.__getattribute__('text')

def test_unicode_body():
    res = Response()
    res.charset = 'utf-8'
    bbody = b'La Pe\xc3\xb1a' # binary string
    ubody = text_(bbody, 'utf-8') # unicode string
    res.body = bbody
    assert res.unicode_body == ubody
    res.ubody = ubody
    assert res.body == bbody
    del res.ubody
    assert res.body == b''

def test_text_get_decode():
    res = Response()
    res.charset = 'utf-8'
    res.body = b'La Pe\xc3\xb1a'
    assert res.text, text_(b'La Pe\xc3\xb1a' == 'utf-8')

def test_text_set_no_charset():
    res = Response()
    res.charset = None
    with pytest.raises(AttributeError):
        res.__setattr__('text', 'abc')

def test_text_set_not_unicode():
    res = Response()
    res.charset = 'utf-8'
    with pytest.raises(TypeError):
        res.__setattr__('text',
                        b'La Pe\xc3\xb1a')

def test_text_del():
    res = Response('123')
    del res.text
    assert res.body == b''
    assert res.content_length == 0

def test_body_file_del():
    res = Response()
    res.body = b'123'
    assert res.content_length == 3
    assert res.app_iter == [b'123']
    del res.body_file
    assert res.body == b''
    assert res.content_length == 0

def test_write_unicode():
    res = Response()
    res.text = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res.write(text_(b'a'))
    assert res.text, text_(b'La Pe\xc3\xb1aa' == 'utf-8')

def test_write_unicode_no_charset():
    res = Response(charset=None)
    with pytest.raises(TypeError):
        res.write(text_(b'a'))

def test_write_text():
    res = Response()
    res.body = b'abc'
    res.write(text_(b'a'))
    assert res.text == 'abca'

def test_app_iter_del():
    res = Response(
        content_length=3,
        app_iter=['123'],
    )
    del res.app_iter
    assert res.body == b''
    assert res.content_length is None

def test_charset_set_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    with pytest.raises(AttributeError):
        res.__setattr__('charset', 'utf-8')

def test_charset_del_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    assert res._charset__del() is None

def test_content_type_params_get_no_semicolon_in_content_type_header():
    res = Response()
    res.headers['Content-Type'] = 'foo'
    assert res.content_type_params == {}

def test_content_type_params_get_semicolon_in_content_type_header():
    res = Response()
    res.headers['Content-Type'] = 'foo;encoding=utf-8'
    assert res.content_type_params == {'encoding': 'utf-8'}

def test_content_type_params_set_value_dict_empty():
    res = Response()
    res.headers['Content-Type'] = 'foo;bar'
    res.content_type_params = None
    assert res.headers['Content-Type'] == 'foo'

def test_content_type_params_set_ok_param_quoting():
    res = Response()
    res.content_type_params = {'a': ''}
    assert res.headers['Content-Type'] == 'text/html; a=""'

def test_set_cookie_overwrite():
    res = Response()
    res.set_cookie('a', '1')
    res.set_cookie('a', '2', overwrite=True)
    assert res.headerlist[-1] == ('Set-Cookie', 'a=2; Path=/')

def test_set_cookie_value_is_None():
    res = Response()
    res.set_cookie('a', None)
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] == 'Max-Age=0'
    assert val[1] == 'Path=/'
    assert val[2] == 'a='
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_None_and_max_age_is_int():
    res = Response()
    res.set_cookie('a', '1', max_age=100)
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] == 'Max-Age=100'
    assert val[1] == 'Path=/'
    assert val[2] == 'a=1'
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_None_and_max_age_is_timedelta():
    from datetime import timedelta
    res = Response()
    res.set_cookie('a', '1', max_age=timedelta(seconds=100))
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] == 'Max-Age=100'
    assert val[1] == 'Path=/'
    assert val[2] == 'a=1'
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_not_None_and_max_age_is_None():
    import datetime
    res = Response()
    then = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    res.set_cookie('a', '1', expires=then)
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] in ('Max-Age=86399', 'Max-Age=86400')
    assert val[1] == 'Path=/'
    assert val[2] == 'a=1'
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_timedelta_and_max_age_is_None():
    import datetime
    res = Response()
    then = datetime.timedelta(days=1)
    res.set_cookie('a', '1', expires=then)
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] in ('Max-Age=86399', 'Max-Age=86400')
    assert val[1] == 'Path=/'
    assert val[2] == 'a=1'
    assert val[3].startswith('expires')

def test_delete_cookie():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a')
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] == 'Max-Age=0'
    assert val[1] == 'Path=/'
    assert val[2] == 'a='
    assert val[3].startswith('expires')

def test_delete_cookie_with_path():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a', path='/abc')
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    assert val[0] == 'Max-Age=0'
    assert val[1] == 'Path=/abc'
    assert val[2] == 'a='
    assert val[3].startswith('expires')

def test_delete_cookie_with_domain():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a', path='/abc', domain='example.com')
    assert res.headerlist[-1][0] == 'Set-Cookie'
    val = [x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 5
    val.sort()
    assert val[0] == 'Domain=example.com'
    assert val[1] == 'Max-Age=0'
    assert val[2] == 'Path=/abc'
    assert val[3] == 'a='
    assert val[4].startswith('expires')

def test_unset_cookie_not_existing_and_not_strict():
    res = Response()
    res.unset_cookie('a', strict=False) # no exception


def test_unset_cookie_not_existing_and_strict():
    res = Response()
    with pytest.raises(KeyError):
        res.unset_cookie('a')

def test_unset_cookie_key_in_cookies():
    res = Response()
    res.headers.add('Set-Cookie', 'a=2; Path=/')
    res.headers.add('Set-Cookie', 'b=3; Path=/')
    res.unset_cookie('a')
    assert res.headers.getall('Set-Cookie') == ['b=3; Path=/']
    res.unset_cookie(text_('b'))
    assert res.headers.getall('Set-Cookie') == []

def test_merge_cookies_no_set_cookie():
    res = Response()
    result = res.merge_cookies('abc')
    assert result == 'abc'

def test_merge_cookies_resp_is_Response():
    inner_res = Response()
    res = Response()
    res.set_cookie('a', '1')
    result = res.merge_cookies(inner_res)
    assert result.headers.getall('Set-Cookie') == ['a=1; Path=/']

def test_merge_cookies_resp_is_wsgi_callable():
    L = []
    def dummy_wsgi_callable(environ, start_response):
        L.append((environ, start_response))
        return 'abc'
    res = Response()
    res.set_cookie('a', '1')
    wsgiapp = res.merge_cookies(dummy_wsgi_callable)
    environ = {}
    def dummy_start_response(status, headers, exc_info=None):
        assert headers, [('Set-Cookie' == 'a=1; Path=/')]
    result = wsgiapp(environ, dummy_start_response)
    assert result == 'abc'
    assert len(L) == 1
    L[0][1]('200 OK', []) # invoke dummy_start_response assertion

def test_body_get_body_is_None_len_app_iter_is_zero():
    res = Response()
    res._app_iter = io.BytesIO()
    res._body = None
    result = res.body
    assert result == b''

def test_cache_control_get():
    res = Response()
    assert repr(res.cache_control) == "<CacheControl ''>"
    assert res.cache_control.max_age is None

def test_location():
    res = Response()
    res.location = '/test.html'
    assert res.location == '/test.html'
    req = Request.blank('/')
    assert req.get_response(res).location == 'http://localhost/test.html'
    res.location = '/test2.html'
    assert req.get_response(res).location == 'http://localhost/test2.html'

def test_request_uri_http():
    # covers webob/response.py:1152
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'SERVER_NAME': 'test.com',
        'SERVER_PORT': '80',
        'SCRIPT_NAME': '/foobar',
    }
    assert _request_uri(environ) == 'http://test.com/foobar'

def test_request_uri_no_script_name2():
    # covers webob/response.py:1160
    # There is a test_request_uri_no_script_name in test_response.py, but it
    # sets SCRIPT_NAME.
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'HTTP_HOST': 'test.com',
        'PATH_INFO': '/foobar',
    }
    assert _request_uri(environ) == 'http://test.com/foobar'

def test_cache_control_object_max_age_ten():
    res = Response()
    res.cache_control.max_age = 10
    assert repr(res.cache_control) == "<CacheControl 'max-age=10'>"
    assert res.headers['cache-control'] == 'max-age=10'

def test_cache_control_set_object_error():
    res = Response()
    with pytest.raises(AttributeError):
        setattr(res.cache_control, 'max_stale', 10)

def test_cache_expires_set():
    res = Response()
    res.cache_expires = True
    assert repr(res.cache_control) == "<CacheControl 'max-age=0, must-revalidate, no-cache, no-store'>"

def test_status_code_set():
    res = Response()
    res.status_code = 400
    assert res._status == '400 Bad Request'
    res.status_int = 404
    assert res._status == '404 Not Found'

def test_cache_control_set_dict():
    res = Response()
    res.cache_control = {'a': 'b'}
    assert repr(res.cache_control) == "<CacheControl 'a=b'>"

def test_cache_control_set_None():
    res = Response()
    res.cache_control = None
    assert repr(res.cache_control) == "<CacheControl ''>"

def test_cache_control_set_unicode():
    res = Response()
    res.cache_control = text_(b'abc')
    assert repr(res.cache_control) == "<CacheControl 'abc'>"

def test_cache_control_set_control_obj_is_not_None():
    class DummyCacheControl(object):
        def __init__(self):
            self.header_value = 1
            self.properties = {'bleh': 1}
    res = Response()
    res._cache_control_obj = DummyCacheControl()
    res.cache_control = {}
    assert res.cache_control.properties == {}

def test_cache_control_del():
    res = Response()
    del res.cache_control
    assert repr(res.cache_control) == "<CacheControl ''>"

def test_body_file_get():
    res = Response()
    result = res.body_file
    from webob.response import ResponseBodyFile
    assert result.__class__ == ResponseBodyFile

def test_body_file_write_no_charset():
    res = Response
    with pytest.raises(TypeError):
        res.write(text_('foo'))

def test_body_file_write_unicode_encodes():
    s = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res = Response()
    res.write(s)
    assert res.app_iter, [b'' == b'La Pe\xc3\xb1a']

def test_repr():
    res = Response()
    assert repr(res).endswith('200 OK>')

def test_cache_expires_set_timedelta():
    res = Response()
    from datetime import timedelta
    delta = timedelta(seconds=60)
    res.cache_expires(seconds=delta)
    assert res.cache_control.max_age == 60

def test_cache_expires_set_int():
    res = Response()
    res.cache_expires(seconds=60)
    assert res.cache_control.max_age == 60

def test_cache_expires_set_None():
    res = Response()
    res.cache_expires(seconds=None, a=1)
    assert res.cache_control.a == 1

def test_cache_expires_set_zero():
    res = Response()
    res.cache_expires(seconds=0)
    assert res.cache_control.no_store is True
    assert res.cache_control.no_cache == '*'
    assert res.cache_control.must_revalidate is True
    assert res.cache_control.max_age == 0
    assert res.cache_control.post_check == 0

def test_encode_content_unknown():
    res = Response()
    with pytest.raises(AssertionError):
        res.encode_content('badencoding')

def test_encode_content_identity():
    res = Response()
    result = res.encode_content('identity')
    assert result is None

def test_encode_content_gzip_already_gzipped():
    res = Response()
    res.content_encoding = 'gzip'
    result = res.encode_content('gzip')
    assert result is None

def test_encode_content_gzip_notyet_gzipped():
    res = Response()
    res.app_iter = io.BytesIO(b'foo')
    result = res.encode_content('gzip')
    assert result is None
    assert res.content_length == 23
    assert res.app_iter == [
        b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff',
        b'K\xcb\xcf\x07\x00',
        b'!es\x8c\x03\x00\x00\x00'
        ]

def test_encode_content_gzip_notyet_gzipped_lazy():
    res = Response()
    res.app_iter = io.BytesIO(b'foo')
    result = res.encode_content('gzip', lazy=True)
    assert result is None
    assert res.content_length is None
    assert list(res.app_iter) == [
        b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff',
        b'K\xcb\xcf\x07\x00',
        b'!es\x8c\x03\x00\x00\x00'
        ]

def test_encode_content_gzip_buffer_coverage():
    # this test is to provide 100% coverage of
    # Response.encode_content was necessary in order to get
    # request https://github.com/Pylons/webob/pull/85 into upstream
    res = Response()
    DATA = b"abcdefghijklmnopqrstuvwxyz0123456789" * 1000000
    res.app_iter = io.BytesIO(DATA)
    res.encode_content('gzip')
    result = list(res.app_iter)
    assert len(b"".join(result)) < len(DATA)

def test_decode_content_identity():
    res = Response()
    res.content_encoding = 'identity'
    result = res.decode_content()
    assert result is None

def test_decode_content_weird():
    res = Response()
    res.content_encoding = 'weird'
    with pytest.raises(ValueError):
        res.decode_content()

def test_decode_content_gzip():
    from gzip import GzipFile
    io_ = io.BytesIO()
    gzip_f = GzipFile(filename='', mode='w', fileobj=io_)
    gzip_f.write(b'abc')
    gzip_f.close()
    body = io_.getvalue()
    res = Response()
    res.content_encoding = 'gzip'
    res.body = body
    res.decode_content()
    assert res.body == b'abc'

def test__abs_headerlist_location_with_scheme():
    res = Response()
    res.content_encoding = 'gzip'
    res.headerlist = [('Location', 'http:')]
    result = res._abs_headerlist({})
    assert result, [('Location' == 'http:')]

def test__abs_headerlist_location_no_scheme():
    res = Response()
    res.content_encoding = 'gzip'
    res.headerlist = [('Location', '/abc')]
    result = res._abs_headerlist({'wsgi.url_scheme': 'http',
                                  'HTTP_HOST': 'example.com:80'})
    assert result == [('Location', 'http://example.com/abc')]

def test_response_set_body_file1():
    data = b'abc'
    file = io.BytesIO(data)
    r = Response(body_file=file)
    assert r.body == data

def test_response_set_body_file2():
    data = b'abcdef' * 1024
    file = io.BytesIO(data)
    r = Response(body_file=file)
    assert r.body == data

def test_response_json_body():
    r = Response(json_body={'a': 1})
    assert r.body == b'{"a":1}', repr(r.body)
    assert r.content_type == 'application/json'
    r = Response()
    r.json_body = {"b": 1}
    assert r.content_type == 'text/html'
    del r.json_body
    assert r.body == b''

def test_cache_expires_set_zero_then_nonzero():
    res = Response()
    res.cache_expires(seconds=0)
    res.cache_expires(seconds=1)
    assert res.pragma is None
    assert not res.cache_control.no_cache
    assert not res.cache_control.no_store
    assert not res.cache_control.must_revalidate
    assert res.cache_control.max_age == 1
