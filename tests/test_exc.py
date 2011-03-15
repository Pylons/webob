from webob.request import Request
from webob.dec import wsgify
from webob.exc import sys
from webob.exc import no_escape
from webob.exc import strip_tags
from webob.exc import HTTPException 
from webob.exc import WSGIHTTPException
from webob.exc import HTTPError
from webob.exc import HTTPRedirection
from webob.exc import HTTPRedirection
from webob.exc import HTTPOk
from webob.exc import HTTPCreated
from webob.exc import HTTPAccepted
from webob.exc import HTTPNonAuthoritativeInformation
from webob.exc import HTTPNoContent
from webob.exc import HTTPResetContent
from webob.exc import HTTPPartialContent
from webob.exc import _HTTPMove
from webob.exc import HTTPMultipleChoices
from webob.exc import HTTPMovedPermanently
from webob.exc import HTTPFound
from webob.exc import HTTPSeeOther
from webob.exc import HTTPNotModified
from webob.exc import HTTPUseProxy
from webob.exc import HTTPTemporaryRedirect
from webob.exc import HTTPClientError
from webob.exc import HTTPBadRequest
from webob.exc import HTTPUnauthorized
from webob.exc import HTTPPaymentRequired
from webob.exc import HTTPForbidden
from webob.exc import HTTPNotFound
from webob.exc import HTTPMethodNotAllowed
from webob.exc import HTTPNotAcceptable
from webob.exc import HTTPProxyAuthenticationRequired
from webob.exc import HTTPRequestTimeout
from webob.exc import HTTPConflict
from webob.exc import HTTPGone
from webob.exc import HTTPLengthRequired
from webob.exc import HTTPPreconditionFailed
from webob.exc import HTTPRequestEntityTooLarge
from webob.exc import HTTPRequestURITooLong
from webob.exc import HTTPUnsupportedMediaType
from webob.exc import HTTPRequestRangeNotSatisfiable
from webob.exc import HTTPExpectationFailed
from webob.exc import HTTPUnprocessableEntity
from webob.exc import HTTPLocked
from webob.exc import HTTPFailedDependency
from webob.exc import HTTPServerError
from webob.exc import HTTPInternalServerError
from webob.exc import HTTPNotImplemented
from webob.exc import HTTPBadGateway
from webob.exc import HTTPServiceUnavailable
from webob.exc import HTTPGatewayTimeout
from webob.exc import HTTPVersionNotSupported
from webob.exc import HTTPInsufficientStorage
from webob.exc import HTTPExceptionMiddleware

from nose.tools import assert_equal

@wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        if sys.version_info > (2,5):
            raise HTTPMethodNotAllowed()
        else:
            raise HTTPMethodNotAllowed().exception
    return 'hello!'

def test_noescape_null():
    assert no_escape(None) == ''

def test_exception_with_unicode_data():
    req = Request.blank('/', method=u'POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_int == 405

def test_WSGIHTTPException_headers():
    exc = WSGIHTTPException(headers=[('Set-Cookie', 'a=1'),
                                     ('Set-Cookie', 'a=2')])
    mixed = exc.headers.mixed()
    assert mixed['set-cookie'] ==  ['a=1', 'a=2']

def test_HTTPMove():
    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD'
    }
    m = _HTTPMove()
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
