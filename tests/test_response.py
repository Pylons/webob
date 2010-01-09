from StringIO import StringIO
from nose.tools import eq_, ok_, assert_raises
from webob import *
from webob import BaseRequest

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
    assert res.body == '\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xffKTH\xcaO\xa9\x04\x00\xf6\x86GI\x06\x00\x00\x00'
    res.decode_content()
    assert res.content_encoding is None
    assert res.body == 'a body'

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
