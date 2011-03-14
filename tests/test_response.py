import sys
if sys.version >= '2.7':
    from io import BytesIO as StringIO
else:
    from cStringIO import StringIO

from nose.tools import eq_, ok_, assert_raises

from webob import BaseRequest, Request, Response

def simple_app(environ, start_response):
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf8'),
        ])
    return ['OK']

def test_response():
    req = BaseRequest.blank('/')
    res = req.get_response(simple_app)
    assert res.status == '200 OK'
    assert res.status_int == 200
    assert res.body == "OK"
    assert res.charset == 'utf8'
    assert res.content_type == 'text/html'
    res.status = 404
    assert res.status == '404 Not Found'
    assert res.status_int == 404
    res.body = 'Not OK'
    assert ''.join(res.app_iter) == 'Not OK'
    res.charset = 'iso8859-1'
    assert res.headers['content-type'] == 'text/html; charset=iso8859-1'
    res.content_type = 'text/xml'
    assert res.headers['content-type'] == 'text/xml; charset=iso8859-1'
    res.headers = {'content-type': 'text/html'}
    assert res.headers['content-type'] == 'text/html'
    assert res.headerlist == [('content-type', 'text/html')]
    res.set_cookie('x', 'y')
    assert res.headers['set-cookie'].strip(';') == 'x=y; Path=/'
    res = Response('a body', '200 OK', content_type='text/html')
    res.encode_content()
    assert res.content_encoding == 'gzip'
    eq_(res.body, '\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xffKTH\xcaO\xa9\x04\x00\xf6\x86GI\x06\x00\x00\x00')
    res.decode_content()
    assert res.content_encoding is None
    assert res.body == 'a body'
    res.set_cookie('x', u'foo') # test unicode value
    assert_raises(TypeError, Response, app_iter=iter(['a']),
                  body="somebody")
    del req.environ
    eq_(Response(request=req)._environ, req)
    eq_(Response(request=req)._request, None)
    assert_raises(TypeError, Response, charset=None,
                  body=u"unicode body")
    assert_raises(TypeError, Response, wrong_key='dummy')

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

def test_cookies():
    res = Response()
    res.set_cookie('x', u'\N{BLACK SQUARE}') # test unicode value
    eq_(res.headers.getall('set-cookie'), ['x="\\342\\226\\240"; Path=/']) # uft8 encoded
    r2 = res.merge_cookies(simple_app)
    r2 = BaseRequest.blank('/').get_response(r2)
    eq_(r2.headerlist,
        [('Content-Type', 'text/html; charset=utf8'),
        ('Set-Cookie', 'x="\\342\\226\\240"; Path=/'),
        ]
    )

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

def test_response_copy():
    r = Response(app_iter=iter(['a']))
    r2 = r.copy()
    eq_(r.body, 'a')
    eq_(r2.body, 'a')

def test_HEAD_closes():
    req = Request.blank('/')
    req.method = 'HEAD'
    app_iter = StringIO('foo')
    res = req.get_response(Response(app_iter=app_iter))
    eq_(res.status_int, 200)
    eq_(res.body, '')
    ok_(app_iter.closed)

def test_content_length():
    r0 = Response('x'*10, content_length=10)

    req_head = Request.blank('/', method='HEAD')
    r1 = req_head.get_response(r0)
    eq_(r1.status_int, 200)
    eq_(r1.body, '')
    eq_(r1.content_length, 10)

    req_get = Request.blank('/')
    r2 = req_get.get_response(r0)
    eq_(r2.status_int, 200)
    eq_(r2.body, 'x'*10)
    eq_(r2.content_length, 10)

    r3 = Response(app_iter=['x']*10)
    eq_(r3.content_length, None)
    eq_(r3.body, 'x'*10)
    eq_(r3.content_length, 10)

    r4 = Response(app_iter=['x']*10, content_length=20) # wrong content_length
    eq_(r4.content_length, 20)
    assert_raises(AssertionError, lambda: r4.body)

    req_range = Request.blank('/', range=(0,5))
    r0.conditional_response = True
    r5 = req_range.get_response(r0)
    eq_(r5.status_int, 206)
    eq_(r5.body, 'xxxxx')
    eq_(r5.content_length, 5)

def test_app_iter_range():
    req = Request.blank('/', range=(2,5))
    for app_iter in [
        ['012345'],
        ['0', '12345'],
        ['0', '1234', '5'],
        ['01', '2345'],
        ['01', '234', '5'],
        ['012', '34', '5'],
        ['012', '3', '4', '5'],
        ['012', '3', '45'],
        ['0', '12', '34', '5'],
        ['0', '12', '345'],
    ]:
        r = Response(
            app_iter=app_iter,
            content_length=6,
            conditional_response=True,
        )
        res = req.get_response(r)
        eq_(list(res.content_range), [2,5,6])
        eq_(res.body, '234', 'body=%r; app_iter=%r' % (res.body, app_iter))

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

def test_from_file():
    res = Response('test')
    equal_resp(res)
    res = Response(app_iter=iter(['test ', 'body']),
                    content_type='text/plain')
    equal_resp(res)

def equal_resp(res):
    input_ = StringIO(str(res))
    res2 = Response.from_file(input_)
    eq_(res.body, res2.body)
    eq_(res.headers, res2.headers)

def test_from_file_w_leading_space_in_header():
    # Make sure the removal of code dealing with leading spaces is safe
    res1 = Response()
    file_w_space = StringIO('200 OK\n\tContent-Type: text/html; charset=UTF-8')
    res2 = Response.from_file(file_w_space)
    eq_(res1.headers, res2.headers)

def test_file_bad_header():
    file_w_bh = StringIO('200 OK\nBad Header')
    assert_raises(ValueError, Response.from_file, file_w_bh)

def test_set_status():
    res = Response()
    res.status = u"OK 200"
    eq_(res.status, "OK 200")
    assert_raises(TypeError, setattr, res, 'status', float(200))

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
        'SCRIPT_NAME': '/foobar',
    }
    eq_(_request_uri(environ), 'http://test.com/foobar')

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

def test_response_file_body_flush_is_no_op():
    from webob.response import ResponseBodyFile
    rbo = ResponseBodyFile(None)
    rbo.flush()

def test_response_file_body_writelines():
    from webob.response import ResponseBodyFile
    class FakeResponse:
        pass
    res = FakeResponse()
    res._app_iter = res.app_iter = ['foo']
    rbo = ResponseBodyFile(res)
    rbo.writelines(['bar', 'baz'])
    eq_(res.app_iter, ['foo', 'bar', 'baz'])

def test_response_file_body_write_non_str():
    from webob.response import ResponseBodyFile
    class FakeResponse:
        pass
    res = FakeResponse()
    rbo = ResponseBodyFile(res)
    assert_raises(TypeError, rbo.write, object())

def test_response_file_body_write_empty_app_iter():
    from webob.response import ResponseBodyFile
    class FakeResponse:
        pass
    res = FakeResponse()
    res._app_iter = res.app_iter = None
    res.body = 'foo'
    rbo = ResponseBodyFile(res)
    rbo.write('baz')
    eq_(res.app_iter, ['foo', 'baz'])

def test_response_file_body_close_not_implemented():
    from webob.response import ResponseBodyFile
    rbo = ResponseBodyFile(None)
    assert_raises(NotImplementedError, rbo.close)

def test_response_file_body_repr():
    from webob.response import ResponseBodyFile
    rbo = ResponseBodyFile('yo')
    eq_(repr(rbo), "<body_file for 'yo'>")

def test_body_get_is_none():
    res = Response()
    res._body = None
    res._app_iter = None
    assert_raises(TypeError, Response, app_iter=iter(['a']),
                  body="somebody")
    assert_raises(AttributeError, res.__getattribute__, 'body')

def test_body_get_is_unicode_notverylong():
    res = Response()
    res._app_iter = u'foo'
    res._body = None
    assert_raises(ValueError, res.__getattribute__, 'body')
    
def test_body_get_is_unicode_verylong():
    res = Response()
    res._app_iter = u'x' * 51
    res._body = None
    assert_raises(ValueError, res.__getattribute__, 'body')
    
def test_body_set_not_unicode_or_str():
    res = Response()
    assert_raises(TypeError, res.__setattr__, 'body', object())
    
def test_body_set_under_body_doesnt_exist():
    res = Response()
    del res._body
    res.body = 'abc'
    eq_(res._body, 'abc')
    eq_(res.content_length, 3)
    eq_(res._app_iter, None)
    
def test_body_del():
    res = Response()
    res._body = '123'
    res.content_length = 3
    res._app_iter = ()
    del res.body
    eq_(res._body, None)
    eq_(res.content_length, None)
    eq_(res._app_iter, None)
    
def test_unicode_body_get_no_charset():
    res = Response()
    res.charset = None
    assert_raises(AttributeError, res.__getattribute__, 'unicode_body')

def test_unicode_body_get_decode():
    res = Response()
    res.charset = 'utf-8'
    res.body = 'La Pe\xc3\xb1a'
    eq_(res.unicode_body, unicode('La Pe\xc3\xb1a', 'utf-8'))
    
def test_unicode_body_set_no_charset():
    res = Response()
    res.charset = None
    assert_raises(AttributeError, res.__setattr__, 'unicode_body', 'abc')

def test_unicode_body_set_not_unicode():
    res = Response()
    res.charset = 'utf-8'
    assert_raises(TypeError, res.__setattr__, 'unicode_body',
                  'La Pe\xc3\xb1a')

def test_unicode_body_del():
    res = Response()
    res._body = '123'
    res.content_length = 3
    res._app_iter = ()
    del res.unicode_body
    eq_(res._body, None)
    eq_(res.content_length, None)
    eq_(res._app_iter, None)

def test_body_file_del():
    res = Response()
    res._body = '123'
    res.content_length = 3
    res._app_iter = ()
    del res.body_file
    eq_(res._body, None)
    eq_(res.content_length, None)
    eq_(res._app_iter, None)

def test_write_unicode():
    res = Response()
    res.unicode_body = unicode('La Pe\xc3\xb1a', 'utf-8')
    res.write(u'a')
    eq_(res.unicode_body, unicode('La Pe\xc3\xb1aa', 'utf-8'))

def test_write_text():
    res = Response()
    res.body = 'abc'
    res.write(u'a')
    eq_(res.unicode_body, 'abca')

def test_app_iter_get_app_iter_is_None():
    res = Response()
    res._app_iter = None
    res._body = None
    assert_raises(AttributeError, res.__getattribute__, 'app_iter')

def test_app_iter_del():
    res = Response()
    res.content_length = 3
    res._app_iter = ['123']
    del res.app_iter
    eq_(res._app_iter, None)
    eq_(res._body, None)
    eq_(res.content_length, None)
    
    
def test_charset_set_charset_is_None():
    res = Response()
    res.charset = 'utf-8'
    res._app_iter = ['123']
    del res.app_iter
    eq_(res._app_iter, None)
    eq_(res._body, None)
    eq_(res.content_length, None)
    
def test_charset_set_no_content_type_header():
    res = Response()
    res.headers.pop('Content-Type', None)
    assert_raises(AttributeError, res.__setattr__, 'charset', 'utf-8')
