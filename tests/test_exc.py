import sys
from webob import *
from webob.dec import wsgify
from webob.exc import *
import webob

from nose.tools import assert_true, assert_false, assert_equal, assert_raises

@wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        if sys.version_info > (2,5):
            raise HTTPMethodNotAllowed()
        else:
            raise HTTPMethodNotAllowed().exception
    return 'hello!'

def test_exception_with_unicode_data():
    req = Request.blank('/', method=u'POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_int == 405

def test_WSGIHTTPException_headers():
    exc = WSGIHTTPException(headers=[('Set-Cookie', 'a=1'),
                                     ('Set-Cookie', 'a=2')])
    mixed = exc.headers.mixed()
    assert mixed['set-cookie'] ==  ['a=1', 'a=2']

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
        webob.exc.sys = DummySys()
        res = m( environ, start_response )
        assert_equal( res, None )
    finally:
        exc.sys = old_sys
