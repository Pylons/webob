import zlib
import io

from nose.tools import eq_, ok_, assert_raises

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
    eq_(res.body, b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xffKTH\xcaO\xa9\x04\x00\xf6\x86GI\x06\x00\x00\x00')
    res.decode_content()
    assert res.content_encoding is None
    assert res.body == b'a body'
    res.set_cookie('x', text_(b'foo')) # test unicode value
    assert_raises(TypeError, Response, app_iter=iter(['a']),
                  body="somebody")
    del req.environ
    assert_raises(TypeError, Response, charset=None,
                  body=text_(b"unicode body"))
    assert_raises(TypeError, Response, wrong_key='dummy')

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

    assert_raises(ValueError, status_test)

def test_set_response_status_code_generic_reason():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    res.status_code = 299
    assert res.status_code == 299
    assert res.status == '299 Success'


def test_content_type():
    r = Response()
    # default ctype and charset
    eq_(r.content_type, 'text/html')
    eq_(r.charset, 'UTF-8')
    # setting to none, removes the header
    r.content_type = None
    eq_(r.content_type, None)
    eq_(r.charset, None)
    # can set missing ctype
    r.content_type = None
    eq_(r.content_type, None)

def test_init_content_type_w_charset():
    v = 'text/plain;charset=ISO-8859-1'
    eq_(Response(content_type=v).headers['content-type'], v)

def test_init_adds_default_charset_when_not_json():
    content_type = 'text/plain'
    expected = 'text/plain; charset=UTF-8'
    eq_(Response(content_type=content_type).headers['content-type'], expected)

def test_init_no_charset_when_json():
    content_type = 'application/json'
    expected = content_type
    eq_(Response(content_type=content_type).headers['content-type'], expected)

def test_init_keeps_specified_charset_when_json():
    content_type = 'application/json;charset=ISO-8859-1'
    expected = content_type
    eq_(Response(content_type=content_type).headers['content-type'], expected)


def test_cookies():
    res = Response()
    # test unicode value
    res.set_cookie('x', "test")
    # utf8 encoded
    eq_(res.headers.getall('set-cookie'), ['x=test; Path=/'])
    r2 = res.merge_cookies(simple_app)
    r2 = BaseRequest.blank('/').get_response(r2)
    eq_(r2.headerlist,
        [('Content-Type', 'text/html; charset=utf8'),
        ('Set-Cookie', 'x=test; Path=/'),
        ]
    )

def test_unicode_cookies_error_raised():
    res = Response()
    assert_raises(ValueError, Response.set_cookie, res, 'x',
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

        eq_(len(w), 1)
        eq_(issubclass(w[-1].category, RuntimeWarning), True)
        eq_("ValueError" in str(w[-1].message), True)

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

        eq_(len(w), 1)
        eq_(issubclass(w[-1].category, DeprecationWarning), True)
        eq_('Argument "key" was renamed to "name".' in str(w[-1].message), True)

    cookies._should_raise = True

def test_cookies_raises_typeerror():
    res = Response()
    assert_raises(TypeError, res.set_cookie)


def test_http_only_cookie():
    req = Request.blank('/')
    res = req.get_response(Response('blah'))
    res.set_cookie("foo", "foo", httponly=True)
    eq_(res.headers['set-cookie'], 'foo=foo; Path=/; HttpOnly')

def test_headers():
    r = Response()
    tval = 'application/x-test'
    r.headers.update({'content-type': tval})
    eq_(r.headers.getall('content-type'), [tval])
    r.headers.clear()
    assert not r.headerlist

def test_response_copy():
    r = Response(app_iter=iter(['a']))
    r2 = r.copy()
    eq_(r.body, 'a')
    eq_(r2.body, 'a')

def test_response_copy_content_md5():
    res = Response()
    res.md5_etag(set_content_md5=True)
    assert res.content_md5
    res2 = res.copy()
    assert res.content_md5
    assert res2.content_md5
    eq_(res.content_md5, res2.content_md5)

def test_HEAD_closes():
    req = Request.blank('/')
    req.method = 'HEAD'
    app_iter = io.BytesIO(b'foo')
    res = req.get_response(Response(app_iter=app_iter))
    eq_(res.status_code, 200)
    eq_(res.body, b'')
    ok_(app_iter.closed)

def test_HEAD_conditional_response_returns_empty_response():
    req = Request.blank('/',
        method='HEAD',
        if_none_match='none'
    )
    res = Response(conditional_response=True)
    def start_response(status, headerlist):
        pass
    result = res(req.environ, start_response)
    assert not list(result)

def test_HEAD_conditional_response_range_empty_response():
    req = Request.blank('/',
        method = 'HEAD',
        range=(4,5),
    )
    res = Response('Are we not men?', conditional_response=True)
    assert req.get_response(res).body == b''


def test_conditional_response_if_none_match_false():
    req = Request.blank('/', if_none_match='foo')
    resp = Response(app_iter=['foo\n'],
            conditional_response=True, etag='bar')
    resp = req.get_response(resp)
    eq_(resp.status_code, 200)

def test_conditional_response_if_none_match_true():
    req = Request.blank('/', if_none_match='foo')
    resp = Response(app_iter=['foo\n'],
            conditional_response=True, etag='foo')
    resp = req.get_response(resp)
    eq_(resp.status_code, 304)

def test_conditional_response_if_none_match_weak():
    req = Request.blank('/', headers={'if-none-match': '"bar"'})
    req_weak = Request.blank('/', headers={'if-none-match': 'W/"bar"'})
    resp = Response(app_iter=['foo\n'], conditional_response=True, etag='bar')
    resp_weak = Response(app_iter=['foo\n'], conditional_response=True, headers={'etag': 'W/"bar"'})
    for rq in [req, req_weak]:
        for rp in [resp, resp_weak]:
            rq.get_response(rp).status_code == 304

    r2 = Response(app_iter=['foo\n'], conditional_response=True, headers={'etag': '"foo"'})
    r2_weak = Response(app_iter=['foo\n'], conditional_response=True, headers={'etag': 'W/"foo"'})
    req_weak.get_response(r2).status_code == 200
    req.get_response(r2_weak) == 200


def test_conditional_response_if_modified_since_false():
    from datetime import datetime, timedelta
    req = Request.blank('/', if_modified_since=datetime(2011, 3, 17, 13, 0, 0))
    resp = Response(app_iter=['foo\n'], conditional_response=True,
            last_modified=req.if_modified_since-timedelta(seconds=1))
    resp = req.get_response(resp)
    eq_(resp.status_code, 304)

def test_conditional_response_if_modified_since_true():
    from datetime import datetime, timedelta
    req = Request.blank('/', if_modified_since=datetime(2011, 3, 17, 13, 0, 0))
    resp = Response(app_iter=['foo\n'], conditional_response=True,
            last_modified=req.if_modified_since+timedelta(seconds=1))
    resp = req.get_response(resp)
    eq_(resp.status_code, 200)

def test_conditional_response_range_not_satisfiable_response():
    req = Request.blank('/', range='bytes=100-200')
    resp = Response(app_iter=['foo\n'], content_length=4,
            conditional_response=True)
    resp = req.get_response(resp)
    eq_(resp.status_code, 416)
    eq_(resp.content_range.start, None)
    eq_(resp.content_range.stop, None)
    eq_(resp.content_range.length, 4)
    eq_(resp.body, b'Requested range not satisfiable: bytes=100-200')

def test_HEAD_conditional_response_range_not_satisfiable_response():
    req = Request.blank('/', method='HEAD', range='bytes=100-200')
    resp = Response(app_iter=['foo\n'], content_length=4,
            conditional_response=True)
    resp = req.get_response(resp)
    eq_(resp.status_code, 416)
    eq_(resp.content_range.start, None)
    eq_(resp.content_range.stop, None)
    eq_(resp.content_range.length, 4)
    eq_(resp.body, b'')

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
    ok_(res.etag)
    ok_('\n' not in res.etag)
    eq_(res.etag, 'pN8sSTUrEaPRzmurGptqmw')
    eq_(res.content_md5, None)

def test_md5_etag_set_content_md5():
    res = Response()
    body = b'The quick brown fox jumps over the lazy dog'
    res.md5_etag(body, set_content_md5=True)
    eq_(res.content_md5, 'nhB9nTcrtoJr2B01QqQZ1g==')

def test_decode_content_defaults_to_identity():
    res = Response()
    res.body = b'There be dragons'
    res.decode_content()
    eq_(res.body, b'There be dragons')

def test_decode_content_with_deflate():
    res = Response()
    body = b'Hey Hey Hey'
    # Simulate inflate by chopping the headers off
    # the gzip encoded data
    res.body = zlib.compress(body)[2:-4]
    res.content_encoding = 'deflate'
    res.decode_content()
    eq_(res.body, body)
    eq_(res.content_encoding, None)

def test_content_length():
    r0 = Response('x'*10, content_length=10)

    req_head = Request.blank('/', method='HEAD')
    r1 = req_head.get_response(r0)
    eq_(r1.status_code, 200)
    eq_(r1.body, b'')
    eq_(r1.content_length, 10)

    req_get = Request.blank('/')
    r2 = req_get.get_response(r0)
    eq_(r2.status_code, 200)
    eq_(r2.body, b'x'*10)
    eq_(r2.content_length, 10)

    r3 = Response(app_iter=[b'x']*10)
    eq_(r3.content_length, None)
    eq_(r3.body, b'x'*10)
    eq_(r3.content_length, 10)

    r4 = Response(app_iter=[b'x']*10,
                  content_length=20) # wrong content_length
    eq_(r4.content_length, 20)
    assert_raises(AssertionError, lambda: r4.body)

    req_range = Request.blank('/', range=(0,5))
    r0.conditional_response = True
    r5 = req_range.get_response(r0)
    eq_(r5.status_code, 206)
    eq_(r5.body, b'xxxxx')
    eq_(r5.content_length, 5)

def test_app_iter_range():
    req = Request.blank('/', range=(2,5))
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
        eq_(list(res.content_range), [2,5,6])
        eq_(res.body, b'234', (res.body, app_iter))

def test_app_iter_range_inner_method():
    class FakeAppIter:
        def app_iter_range(self, start, stop):
            return 'you win', start, stop
    res = Response(app_iter=FakeAppIter())
    eq_(res.app_iter_range(30, 40), ('you win', 30, 40))

def test_content_type_in_headerlist():
    # Couldn't manage to clone Response in order to modify class
    # attributes safely. Shouldn't classes be fresh imported for every
    # test?
    default_content_type = Response.default_content_type
    Response.default_content_type = None
    try:
        res = Response(headerlist=[('Content-Type', 'text/html')],
                            charset='utf8')
        ok_(res._headerlist)
        eq_(res.charset, 'utf8')
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
    eq_(res.body, res2.body)
    eq_(res.headers, res2.headers)

def test_from_file_w_leading_space_in_header():
    # Make sure the removal of code dealing with leading spaces is safe
    res1 = Response()
    file_w_space = io.BytesIO(
        b'200 OK\n\tContent-Type: text/html; charset=UTF-8')
    res2 = Response.from_file(file_w_space)
    eq_(res1.headers, res2.headers)

def test_file_bad_header():
    file_w_bh = io.BytesIO(b'200 OK\nBad Header')
    assert_raises(ValueError, Response.from_file, file_w_bh)

def test_from_file_not_unicode_headers():
    inp = io.BytesIO(
        b'200 OK\n\tContent-Type: text/html; charset=UTF-8')
    res = Response.from_file(inp)
    eq_(res.headerlist[0][0].__class__, str)

def test_file_with_http_version():
    inp = io.BytesIO(b'HTTP/1.1 200 OK\r\n\r\nSome data...')

    res = Response.from_file(inp)
    eq_(res.status_code, 200)
    eq_(res.status, '200 OK')

def test_file_with_http_version_more_status():
    inp = io.BytesIO(b'HTTP/1.1 404 Not Found\r\n\r\nSome data...')

    res = Response.from_file(inp)
    assert res.status_code == 404
    assert res.status == '404 Not Found'

def test_set_status():
    res = Response()
    res.status = "200"
    eq_(res.status, "200 OK")
    assert_raises(TypeError, setattr, res, 'status', (200,))

def test_set_headerlist():
    res = Response()
    # looks like a list
    res.headerlist = (('Content-Type', 'text/html; charset=UTF-8'),)
    eq_(res.headerlist, [('Content-Type', 'text/html; charset=UTF-8')])
    # has items
    res.headerlist = {'Content-Type': 'text/html; charset=UTF-8'}
    eq_(res.headerlist, [('Content-Type', 'text/html; charset=UTF-8')])
    del res.headerlist
    eq_(res.headerlist, [])

def test_request_uri_no_script_name():
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'HTTP_HOST': 'test.com',
    }
    eq_(_request_uri(environ), 'http://test.com/')

def test_request_uri_https():
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'https',
        'SERVER_NAME': 'test.com',
        'SERVER_PORT': '443',
        'SCRIPT_NAME': '/foobar',
    }
    eq_(_request_uri(environ), 'https://test.com/foobar')

def test_app_iter_range_starts_after_iter_end():
    from webob.response import AppIterRange
    range = AppIterRange(iter([]), start=1, stop=1)
    eq_(list(range), [])

def test_resp_write_app_iter_non_list():
    res = Response(app_iter=(b'a', b'b'))
    eq_(res.content_length, None)
    res.write(b'c')
    eq_(res.body, b'abc')
    eq_(res.content_length, 3)

def test_response_file_body_writelines():
    from webob.response import ResponseBodyFile
    res = Response(app_iter=[b'foo'])
    rbo = ResponseBodyFile(res)
    rbo.writelines(['bar', 'baz'])
    eq_(res.app_iter, [b'foo', b'bar', b'baz'])
    rbo.flush() # noop
    eq_(res.app_iter, [b'foo', b'bar', b'baz'])

def test_response_write_non_str():
    res = Response()
    assert_raises(TypeError, res.write, object())

def test_response_file_body_write_empty_app_iter():
    res = Response('foo')
    res.write('baz')
    eq_(res.app_iter, [b'foo', b'baz'])

def test_response_file_body_write_empty_body():
    res = Response('')
    res.write('baz')
    eq_(res.app_iter, [b'', b'baz'])

def test_response_file_body_close_not_implemented():
    rbo = Response().body_file
    assert_raises(NotImplementedError, rbo.close)

def test_response_file_body_repr():
    rbo = Response().body_file
    rbo.response = 'yo'
    eq_(repr(rbo), "<body_file for 'yo'>")

def test_body_get_is_none():
    res = Response()
    res._app_iter = None
    assert_raises(TypeError, Response, app_iter=iter(['a']),
                  body="somebody")
    assert_raises(AttributeError, res.__getattribute__, 'body')

def test_body_get_is_unicode_notverylong():
    res = Response(app_iter=(text_(b'foo'),))
    assert_raises(TypeError, res.__getattribute__, 'body')

def test_body_get_is_unicode():
    res = Response(app_iter=(['x'] * 51 + [text_(b'x')]))
    assert_raises(TypeError, res.__getattribute__, 'body')

def test_body_set_not_unicode_or_str():
    res = Response()
    assert_raises(TypeError, res.__setattr__, 'body', object())

def test_body_set_unicode():
    res = Response()
    assert_raises(TypeError, res.__setattr__, 'body', text_(b'abc'))

def test_body_set_under_body_doesnt_exist():
    res = Response('abc')
    eq_(res.body, b'abc')
    eq_(res.content_length, 3)

def test_body_del():
    res = Response('123')
    del res.body
    eq_(res.body, b'')
    eq_(res.content_length, 0)

def test_text_get_no_charset():
    res = Response(charset=None)
    assert_raises(AttributeError, res.__getattribute__, 'text')

def test_unicode_body():
    res = Response()
    res.charset = 'utf-8'
    bbody = b'La Pe\xc3\xb1a' # binary string
    ubody = text_(bbody, 'utf-8') # unicode string
    res.body = bbody
    eq_(res.unicode_body, ubody)
    res.ubody = ubody
    eq_(res.body, bbody)
    del res.ubody
    eq_(res.body, b'')

def test_text_get_decode():
    res = Response()
    res.charset = 'utf-8'
    res.body = b'La Pe\xc3\xb1a'
    eq_(res.text, text_(b'La Pe\xc3\xb1a', 'utf-8'))

def test_text_set_no_charset():
    res = Response()
    res.charset = None
    assert_raises(AttributeError, res.__setattr__, 'text', 'abc')

def test_text_set_not_unicode():
    res = Response()
    res.charset = 'utf-8'
    assert_raises(TypeError, res.__setattr__, 'text',
                  b'La Pe\xc3\xb1a')

def test_text_del():
    res = Response('123')
    del res.text
    eq_(res.body, b'')
    eq_(res.content_length, 0)

def test_body_file_del():
    res = Response()
    res.body = b'123'
    eq_(res.content_length, 3)
    eq_(res.app_iter, [b'123'])
    del res.body_file
    eq_(res.body, b'')
    eq_(res.content_length, 0)

def test_write_unicode():
    res = Response()
    res.text = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res.write(text_(b'a'))
    eq_(res.text, text_(b'La Pe\xc3\xb1aa', 'utf-8'))

def test_write_unicode_no_charset():
    res = Response(charset=None)
    assert_raises(TypeError, res.write, text_(b'a'))

def test_write_text():
    res = Response()
    res.body = b'abc'
    res.write(text_(b'a'))
    eq_(res.text, 'abca')

def test_app_iter_del():
    res = Response(
        content_length=3,
        app_iter=['123'],
    )
    del res.app_iter
    eq_(res.body, b'')
    eq_(res.content_length, None)

def test_charset_set_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    assert_raises(AttributeError, res.__setattr__, 'charset', 'utf-8')

def test_charset_del_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    eq_(res._charset__del(), None)

def test_content_type_params_get_no_semicolon_in_content_type_header():
    res = Response()
    res.headers['Content-Type'] = 'foo'
    eq_(res.content_type_params, {})

def test_content_type_params_get_semicolon_in_content_type_header():
    res = Response()
    res.headers['Content-Type'] = 'foo;encoding=utf-8'
    eq_(res.content_type_params, {'encoding':'utf-8'})

def test_content_type_params_set_value_dict_empty():
    res = Response()
    res.headers['Content-Type'] = 'foo;bar'
    res.content_type_params = None
    eq_(res.headers['Content-Type'], 'foo')

def test_content_type_params_set_ok_param_quoting():
    res = Response()
    res.content_type_params = {'a':''}
    eq_(res.headers['Content-Type'], 'text/html; a=""')

def test_set_cookie_overwrite():
    res = Response()
    res.set_cookie('a', '1')
    res.set_cookie('a', '2', overwrite=True)
    eq_(res.headerlist[-1], ('Set-Cookie', 'a=2; Path=/'))

def test_set_cookie_value_is_None():
    res = Response()
    res.set_cookie('a', None)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=0')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_None_and_max_age_is_int():
    res = Response()
    res.set_cookie('a', '1', max_age=100)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=100')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_None_and_max_age_is_timedelta():
    from datetime import timedelta
    res = Response()
    res.set_cookie('a', '1', max_age=timedelta(seconds=100))
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=100')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_not_None_and_max_age_is_None():
    import datetime
    res = Response()
    then = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    res.set_cookie('a', '1', expires=then)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    ok_(val[0] in ('Max-Age=86399', 'Max-Age=86400'))
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_set_cookie_expires_is_timedelta_and_max_age_is_None():
    import datetime
    res = Response()
    then = datetime.timedelta(days=1)
    res.set_cookie('a', '1', expires=then)
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    ok_(val[0] in ('Max-Age=86399', 'Max-Age=86400'))
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=1')
    assert val[3].startswith('expires')

def test_delete_cookie():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a')
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=0')
    eq_(val[1], 'Path=/')
    eq_(val[2], 'a=')
    assert val[3].startswith('expires')

def test_delete_cookie_with_path():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a', path='/abc')
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 4
    val.sort()
    eq_(val[0], 'Max-Age=0')
    eq_(val[1], 'Path=/abc')
    eq_(val[2], 'a=')
    assert val[3].startswith('expires')

def test_delete_cookie_with_domain():
    res = Response()
    res.headers['Set-Cookie'] = 'a=2; Path=/'
    res.delete_cookie('a', path='/abc', domain='example.com')
    eq_(res.headerlist[-1][0], 'Set-Cookie')
    val = [ x.strip() for x in res.headerlist[-1][1].split(';')]
    assert len(val) == 5
    val.sort()
    eq_(val[0], 'Domain=example.com')
    eq_(val[1], 'Max-Age=0')
    eq_(val[2], 'Path=/abc')
    eq_(val[3], 'a=')
    assert val[4].startswith('expires')

def test_unset_cookie_not_existing_and_not_strict():
    res = Response()
    res.unset_cookie('a', strict=False) # no exception


def test_unset_cookie_not_existing_and_strict():
    res = Response()
    assert_raises(KeyError, res.unset_cookie, 'a')

def test_unset_cookie_key_in_cookies():
    res = Response()
    res.headers.add('Set-Cookie', 'a=2; Path=/')
    res.headers.add('Set-Cookie', 'b=3; Path=/')
    res.unset_cookie('a')
    eq_(res.headers.getall('Set-Cookie'), ['b=3; Path=/'])
    res.unset_cookie(text_('b'))
    eq_(res.headers.getall('Set-Cookie'), [])

def test_merge_cookies_no_set_cookie():
    res = Response()
    result = res.merge_cookies('abc')
    eq_(result, 'abc')

def test_merge_cookies_resp_is_Response():
    inner_res = Response()
    res = Response()
    res.set_cookie('a', '1')
    result = res.merge_cookies(inner_res)
    eq_(result.headers.getall('Set-Cookie'), ['a=1; Path=/'])

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
        eq_(headers, [('Set-Cookie', 'a=1; Path=/')])
    result = wsgiapp(environ, dummy_start_response)
    assert result == 'abc'
    assert len(L) == 1
    L[0][1]('200 OK', []) # invoke dummy_start_response assertion

def test_body_get_body_is_None_len_app_iter_is_zero():
    res = Response()
    res._app_iter = io.BytesIO()
    res._body = None
    result = res.body
    eq_(result, b'')

def test_cache_control_get():
    res = Response()
    eq_(repr(res.cache_control), "<CacheControl ''>")
    eq_(res.cache_control.max_age, None)

def test_location():
    res = Response()
    res.location = '/test.html'
    eq_(res.location, '/test.html')
    req = Request.blank('/')
    eq_(req.get_response(res).location, 'http://localhost/test.html')
    res.location = '/test2.html'
    eq_(req.get_response(res).location, 'http://localhost/test2.html')

def test_request_uri_http():
    # covers webob/response.py:1152
    from webob.response import _request_uri
    environ = {
        'wsgi.url_scheme': 'http',
        'SERVER_NAME': 'test.com',
        'SERVER_PORT': '80',
        'SCRIPT_NAME': '/foobar',
    }
    eq_(_request_uri(environ), 'http://test.com/foobar')

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
    eq_(_request_uri(environ), 'http://test.com/foobar')

def test_cache_control_object_max_age_ten():
    res = Response()
    res.cache_control.max_age = 10
    eq_(repr(res.cache_control), "<CacheControl 'max-age=10'>")
    eq_(res.headers['cache-control'], 'max-age=10')

def test_cache_control_set_object_error():
    res = Response()
    assert_raises(AttributeError, setattr, res.cache_control, 'max_stale', 10)

def test_cache_expires_set():
    res = Response()
    res.cache_expires = True
    eq_(repr(res.cache_control),
        "<CacheControl 'max-age=0, must-revalidate, no-cache, no-store'>")

def test_status_code_set():
    res = Response()
    res.status_code = 400
    eq_(res._status, '400 Bad Request')
    res.status_int = 404
    eq_(res._status, '404 Not Found')

def test_cache_control_set_dict():
    res = Response()
    res.cache_control = {'a':'b'}
    eq_(repr(res.cache_control), "<CacheControl 'a=b'>")

def test_cache_control_set_None():
    res = Response()
    res.cache_control = None
    eq_(repr(res.cache_control), "<CacheControl ''>")

def test_cache_control_set_unicode():
    res = Response()
    res.cache_control = text_(b'abc')
    eq_(repr(res.cache_control), "<CacheControl 'abc'>")

def test_cache_control_set_control_obj_is_not_None():
    class DummyCacheControl(object):
        def __init__(self):
            self.header_value = 1
            self.properties = {'bleh':1}
    res = Response()
    res._cache_control_obj = DummyCacheControl()
    res.cache_control = {}
    eq_(res.cache_control.properties, {})

def test_cache_control_del():
    res = Response()
    del res.cache_control
    eq_(repr(res.cache_control), "<CacheControl ''>")

def test_body_file_get():
    res = Response()
    result = res.body_file
    from webob.response import ResponseBodyFile
    eq_(result.__class__, ResponseBodyFile)

def test_body_file_write_no_charset():
    res = Response
    assert_raises(TypeError, res.write, text_('foo'))

def test_body_file_write_unicode_encodes():
    s = text_(b'La Pe\xc3\xb1a', 'utf-8')
    res = Response()
    res.write(s)
    eq_(res.app_iter, [b'', b'La Pe\xc3\xb1a'])

def test_repr():
    res = Response()
    ok_(repr(res).endswith('200 OK>'))

def test_cache_expires_set_timedelta():
    res = Response()
    from datetime import timedelta
    delta = timedelta(seconds=60)
    res.cache_expires(seconds=delta)
    eq_(res.cache_control.max_age, 60)

def test_cache_expires_set_int():
    res = Response()
    res.cache_expires(seconds=60)
    eq_(res.cache_control.max_age, 60)

def test_cache_expires_set_None():
    res = Response()
    res.cache_expires(seconds=None, a=1)
    eq_(res.cache_control.a, 1)

def test_cache_expires_set_zero():
    res = Response()
    res.cache_expires(seconds=0)
    eq_(res.cache_control.no_store, True)
    eq_(res.cache_control.no_cache, '*')
    eq_(res.cache_control.must_revalidate, True)
    eq_(res.cache_control.max_age, 0)
    eq_(res.cache_control.post_check, 0)

def test_encode_content_unknown():
    res = Response()
    assert_raises(AssertionError, res.encode_content, 'badencoding')

def test_encode_content_identity():
    res = Response()
    result = res.encode_content('identity')
    eq_(result, None)

def test_encode_content_gzip_already_gzipped():
    res = Response()
    res.content_encoding = 'gzip'
    result = res.encode_content('gzip')
    eq_(result, None)

def test_encode_content_gzip_notyet_gzipped():
    res = Response()
    res.app_iter = io.BytesIO(b'foo')
    result = res.encode_content('gzip')
    eq_(result, None)
    eq_(res.content_length, 23)
    eq_(res.app_iter, [
        b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff',
        b'K\xcb\xcf\x07\x00',
        b'!es\x8c\x03\x00\x00\x00'
        ])

def test_encode_content_gzip_notyet_gzipped_lazy():
    res = Response()
    res.app_iter = io.BytesIO(b'foo')
    result = res.encode_content('gzip', lazy=True)
    eq_(result, None)
    eq_(res.content_length, None)
    eq_(list(res.app_iter), [
        b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff',
        b'K\xcb\xcf\x07\x00',
        b'!es\x8c\x03\x00\x00\x00'
        ])

def test_encode_content_gzip_buffer_coverage():
    #this test is to provide 100% coverage of
    #.Response.encode_content was necessary in order to get
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
    eq_(result, None)

def test_decode_content_weird():
    res = Response()
    res.content_encoding = 'weird'
    assert_raises(ValueError, res.decode_content)

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
    eq_(res.body, b'abc')

def test__abs_headerlist_location_with_scheme():
    res = Response()
    res.content_encoding = 'gzip'
    res.headerlist = [('Location', 'http:')]
    result = res._abs_headerlist({})
    eq_(result, [('Location', 'http:')])

def test__abs_headerlist_location_no_scheme():
    res = Response()
    res.content_encoding = 'gzip'
    res.headerlist = [('Location', '/abc')]
    result = res._abs_headerlist({'wsgi.url_scheme':'http',
                                  'HTTP_HOST':'example.com:80'})
    eq_(result, [('Location', 'http://example.com/abc')])

def test_response_set_body_file1():
     data  = b'abc'
     file = io.BytesIO(data)
     r = Response(body_file=file)
     assert r.body == data

def test_response_set_body_file2():
    data = b'abcdef'*1024
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
    eq_(res.pragma, None)
    ok_(not res.cache_control.no_cache)
    ok_(not res.cache_control.no_store)
    ok_(not res.cache_control.must_revalidate)
    eq_(res.cache_control.max_age, 1)
