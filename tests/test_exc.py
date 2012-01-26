from webob.request import Request
from webob.dec import wsgify
from webob.exc import no_escape
from webob.exc import strip_tags
from webob.exc import HTTPException
from webob.exc import WSGIHTTPException
from webob.exc import _HTTPMove
from webob.exc import HTTPMethodNotAllowed
from webob.exc import HTTPExceptionMiddleware

from nose.tools import eq_, ok_, assert_equal, assert_raises

@wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        raise HTTPMethodNotAllowed()
    return 'hello!'

def test_noescape_null():
    assert_equal(no_escape(None), '')

def test_noescape_not_basestring():
    assert_equal(no_escape(42), '42')

def test_noescape_unicode():
    class DummyUnicodeObject(object):
        def __unicode__(self):
            return '42'
    duo = DummyUnicodeObject()
    assert_equal(no_escape(duo), '42')

def test_strip_tags_empty():
    assert_equal(strip_tags(''), '')

def test_strip_tags_newline_to_space():
    assert_equal(strip_tags('a\nb'), 'a b')

def test_strip_tags_zaps_carriage_return():
    assert_equal(strip_tags('a\rb'), 'ab')

def test_strip_tags_br_to_newline():
    assert_equal(strip_tags('a<br/>b'), 'a\nb')

def test_strip_tags_zaps_comments():
    assert_equal(strip_tags('a<!--b-->'), 'ab')

def test_strip_tags_zaps_tags():
    assert_equal(strip_tags('foo<bar>baz</bar>'), 'foobaz')

def test_HTTPException():
    import warnings
    _called = []
    _result = object()
    def _response(environ, start_response):
        _called.append((environ, start_response))
        return _result
    environ = {}
    start_response = object()
    exc = HTTPException('testing', _response)
    ok_(exc.wsgi_response is _response)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert(exc.exception is exc)
        assert(len(w) == 1)
    result = exc(environ, start_response)
    ok_(result is result)
    assert_equal(_called, [(environ, start_response)])

def test_exception_with_unicode_data():
    req = Request.blank('/', method='POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_int == 405

def test_WSGIHTTPException_headers():
    exc = WSGIHTTPException(headers=[('Set-Cookie', 'a=1'),
                                     ('Set-Cookie', 'a=2')])
    mixed = exc.headers.mixed()
    assert mixed['set-cookie'] ==  ['a=1', 'a=2']

def test_WSGIHTTPException_w_body_template():
    from string import Template
    TEMPLATE = '$foo: $bar'
    exc = WSGIHTTPException(body_template = TEMPLATE)
    assert_equal(exc.body_template, TEMPLATE)
    ok_(isinstance(exc.body_template_obj, Template))
    eq_(exc.body_template_obj.substitute({'foo': 'FOO', 'bar': 'BAR'}),
        'FOO: BAR')

def test_WSGIHTTPException_w_empty_body():
    class EmptyOnly(WSGIHTTPException):
        empty_body = True
    exc = EmptyOnly(content_type='text/plain', content_length=234)
    ok_('content_type' not in exc.__dict__)
    ok_('content_length' not in exc.__dict__)

def test_WSGIHTTPException___str__():
    exc1 = WSGIHTTPException(detail='Detail')
    eq_(str(exc1), 'Detail')
    class Explain(WSGIHTTPException):
        explanation = 'Explanation'
    eq_(str(Explain()), 'Explanation')

def test_WSGIHTTPException_plain_body_no_comment():
    class Explain(WSGIHTTPException):
        code = '999'
        title = 'Testing'
        explanation = 'Explanation'
    exc = Explain(detail='Detail')
    eq_(exc.plain_body({}),
        '999 Testing\n\nExplanation\n\n Detail  ')

def test_WSGIHTTPException_html_body_w_comment():
    class Explain(WSGIHTTPException):
        code = '999'
        title = 'Testing'
        explanation = 'Explanation'
    exc = Explain(detail='Detail', comment='Comment')
    eq_(exc.html_body({}),
        '<html>\n'
        ' <head>\n'
        '  <title>999 Testing</title>\n'
        ' </head>\n'
        ' <body>\n'
        '  <h1>999 Testing</h1>\n'
        '  Explanation<br /><br />\n'
        'Detail\n'
        '<!-- Comment -->\n\n'
        ' </body>\n'
        '</html>'
       )

def test_WSGIHTTPException_generate_response():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'PUT',
       'HTTP_ACCEPT': 'text/html'
    }
    excep = WSGIHTTPException()
    assert_equal( excep(environ,start_response), [
        b'<html>\n'
        b' <head>\n'
        b'  <title>None None</title>\n'
        b' </head>\n'
        b' <body>\n'
        b'  <h1>None None</h1>\n'
        b'  <br /><br />\n'
        b'\n'
        b'\n\n'
        b' </body>\n'
        b'</html>' ]
    )

def test_WSGIHTTPException_call_w_body():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'PUT'
    }
    excep = WSGIHTTPException()
    excep.body = b'test'
    assert_equal( excep(environ,start_response), [b'test'] )


def test_WSGIHTTPException_wsgi_response():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    excep = WSGIHTTPException()
    assert_equal( excep.wsgi_response(environ,start_response), [] )

def test_WSGIHTTPException_exception_newstyle():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    excep = WSGIHTTPException()
    from webob import exc
    exc.newstyle_exceptions = True
    assert_equal( excep(environ,start_response), [] )

def test_WSGIHTTPException_exception_no_newstyle():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    excep = WSGIHTTPException()
    from webob import exc
    exc.newstyle_exceptions = False
    assert_equal( excep(environ,start_response), [] )

def test_HTTPMove():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    m = _HTTPMove()
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_location_not_none():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    m = _HTTPMove(location='http://example.com')
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_add_slash_and_location():
    def start_response(status, headers, exc_info=None):
        pass
    assert_raises( TypeError, _HTTPMove, location='http://example.com',
                   add_slash=True )

def test_HTTPMove_call_add_slash():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    m = _HTTPMove()
    m.add_slash = True
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_call_query_string():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    m = _HTTPMove()
    m.add_slash = True
    environ[ 'QUERY_STRING' ] = 'querystring'
    environ['PATH_INFO'] = '/'
    assert_equal( m( environ, start_response ), [] )

def test_HTTPExceptionMiddleware_ok():
    def app( environ, start_response ):
        return '123'
    application = app
    m = HTTPExceptionMiddleware(application)
    environ = {}
    start_response = None
    res = m( environ, start_response )
    assert_equal( res, '123' )

def test_HTTPExceptionMiddleware_exception():
    def wsgi_response( environ, start_response):
        return '123'
    def app( environ, start_response ):
        raise HTTPException( None, wsgi_response )
    application = app
    m = HTTPExceptionMiddleware(application)
    environ = {}
    start_response = None
    res = m( environ, start_response )
    assert_equal( res, '123' )

def test_HTTPExceptionMiddleware_exception_exc_info_none():
    class DummySys:
        def exc_info(self):
            return None
    def wsgi_response( environ, start_response):
        return start_response('200 OK', [], exc_info=None)
    def app( environ, start_response ):
        raise HTTPException( None, wsgi_response )
    application = app
    m = HTTPExceptionMiddleware(application)
    environ = {}
    def start_response(status, headers, exc_info):
        pass
    try:
        from webob import exc
        old_sys = exc.sys
        sys = DummySys()
        res = m( environ, start_response )
        assert_equal( res, None )
    finally:
        exc.sys = old_sys
