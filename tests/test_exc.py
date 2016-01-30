import json

from webob.request import Request
from webob.dec import wsgify
from webob import exc as webob_exc

from nose.tools import eq_, ok_, assert_equal, assert_raises

@wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        raise webob_exc.HTTPMethodNotAllowed()
    return 'hello!'

def test_noescape_null():
    assert_equal(webob_exc.no_escape(None), '')

def test_noescape_not_basestring():
    assert_equal(webob_exc.no_escape(42), '42')

def test_noescape_unicode():
    class DummyUnicodeObject(object):
        def __unicode__(self):
            return '42'
    duo = DummyUnicodeObject()
    assert_equal(webob_exc.no_escape(duo), '42')

def test_strip_tags_empty():
    assert_equal(webob_exc.strip_tags(''), '')

def test_strip_tags_newline_to_space():
    assert_equal(webob_exc.strip_tags('a\nb'), 'a b')

def test_strip_tags_zaps_carriage_return():
    assert_equal(webob_exc.strip_tags('a\rb'), 'ab')

def test_strip_tags_br_to_newline():
    assert_equal(webob_exc.strip_tags('a<br/>b'), 'a\nb')

def test_strip_tags_zaps_comments():
    assert_equal(webob_exc.strip_tags('a<!--b-->'), 'ab')

def test_strip_tags_zaps_tags():
    assert_equal(webob_exc.strip_tags('foo<bar>baz</bar>'), 'foobaz')

def test_HTTPException():
    import warnings
    _called = []
    _result = object()
    def _response(environ, start_response):
        _called.append((environ, start_response))
        return _result
    environ = {}
    start_response = object()
    exc = webob_exc.HTTPException('testing', _response)
    ok_(exc.wsgi_response is _response)
    result = exc(environ, start_response)
    ok_(result is result)
    assert_equal(_called, [(environ, start_response)])

def test_exception_with_unicode_data():
    req = Request.blank('/', method='POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_code == 405

def test_WSGIHTTPException_headers():
    exc = webob_exc.WSGIHTTPException(headers=[('Set-Cookie', 'a=1'),
                                     ('Set-Cookie', 'a=2')])
    mixed = exc.headers.mixed()
    assert mixed['set-cookie'] ==  ['a=1', 'a=2']

def test_WSGIHTTPException_w_body_template():
    from string import Template
    TEMPLATE = '$foo: $bar'
    exc = webob_exc.WSGIHTTPException(body_template = TEMPLATE)
    assert_equal(exc.body_template, TEMPLATE)
    ok_(isinstance(exc.body_template_obj, Template))
    eq_(exc.body_template_obj.substitute({'foo': 'FOO', 'bar': 'BAR'}),
        'FOO: BAR')

def test_WSGIHTTPException_w_empty_body():
    class EmptyOnly(webob_exc.WSGIHTTPException):
        empty_body = True
    exc = EmptyOnly(content_type='text/plain', content_length=234)
    ok_('content_type' not in exc.__dict__)
    ok_('content_length' not in exc.__dict__)

def test_WSGIHTTPException___str__():
    exc1 = webob_exc.WSGIHTTPException(detail='Detail')
    eq_(str(exc1), 'Detail')
    class Explain(webob_exc.WSGIHTTPException):
        explanation = 'Explanation'
    eq_(str(Explain()), 'Explanation')

def test_WSGIHTTPException_plain_body_no_comment():
    class Explain(webob_exc.WSGIHTTPException):
        code = '999'
        title = 'Testing'
        explanation = 'Explanation'
    exc = Explain(detail='Detail')
    eq_(exc.plain_body({}),
        '999 Testing\n\nExplanation\n\n Detail  ')

def test_WSGIHTTPException_html_body_w_comment():
    class Explain(webob_exc.WSGIHTTPException):
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

def test_WSGIHTTPException_json_body_no_comment():
    class ValidationError(webob_exc.WSGIHTTPException):
        code = '422'
        title = 'Validation Failed'
        explanation = 'Validation of an attribute failed.'

    exc = ValidationError(detail='Attribute "xyz" is invalid.')
    body = exc.json_body({})
    eq_(json.loads(body), {
        "code": "422 Validation Failed",
        "title": "Validation Failed",
        "message": "Validation of an attribute failed.<br /><br />\nAttribute"
                   ' "xyz" is invalid.\n\n',
    })

def test_WSGIHTTPException_respects_application_json():
    class ValidationError(webob_exc.WSGIHTTPException):
        code = '422'
        title = 'Validation Failed'
        explanation = 'Validation of an attribute failed.'
    def start_response(status, headers, exc_info=None):
        pass

    exc = ValidationError(detail='Attribute "xyz" is invalid.')
    resp = exc.generate_response(environ={
        'wsgi.url_scheme': 'HTTP',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
        'REQUEST_METHOD': 'PUT',
        'HTTP_ACCEPT': 'application/json',
    }, start_response=start_response)
    eq_(json.loads(resp[0].decode('utf-8')), {
        "code": "422 Validation Failed",
        "title": "Validation Failed",
        "message": "Validation of an attribute failed.<br /><br />\nAttribute"
                   ' "xyz" is invalid.\n\n',
    })

def test_WSGIHTTPException_allows_custom_json_formatter():
    def json_formatter(body, status, title, environ):
        return {"fake": True}
    class ValidationError(webob_exc.WSGIHTTPException):
        code = '422'
        title = 'Validation Failed'
        explanation = 'Validation of an attribute failed.'

    exc = ValidationError(detail='Attribute "xyz" is invalid.',
                          json_formatter=json_formatter)
    body = exc.json_body({})
    eq_(json.loads(body), {"fake": True})

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
    excep = webob_exc.WSGIHTTPException()
    assert_equal( excep(environ,start_response), [
        b'<html>\n'
        b' <head>\n'
        b'  <title>500 Internal Server Error</title>\n'
        b' </head>\n'
        b' <body>\n'
        b'  <h1>500 Internal Server Error</h1>\n'
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
    excep = webob_exc.WSGIHTTPException()
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
    excep = webob_exc.WSGIHTTPException()
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
    excep = webob_exc.WSGIHTTPException()
    webob_exc.newstyle_exceptions = True
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
    excep = webob_exc.WSGIHTTPException()
    webob_exc.newstyle_exceptions = False
    assert_equal( excep(environ,start_response), [] )

def test_HTTPOk_head_of_proxied_head():
    # first set up a response to a HEAD request
    HELLO_WORLD = "Hi!\n"
    CONTENT_TYPE = "application/hello"
    def head_app(environ, start_response):
        """An application object that understands HEAD"""
        status = '200 OK'
        response_headers = [('Content-Type', CONTENT_TYPE),
                            ('Content-Length', len(HELLO_WORLD))]
        start_response(status, response_headers)

        if environ['REQUEST_METHOD'] == 'HEAD':
            return []
        else:
            return [HELLO_WORLD]

    def verify_response(resp, description):
        assert_equal(resp.content_type, CONTENT_TYPE, description)
        assert_equal(resp.content_length, len(HELLO_WORLD), description)
        assert_equal(resp.body, b'', description)

    req = Request.blank('/', method='HEAD')
    resp1 = req.get_response(head_app)
    verify_response(resp1, "first response")

    # Copy the response like a proxy server would.
    # Copying an empty body has set content_length
    # so copy the headers only afterwards.
    resp2 = webob_exc.status_map[resp1.status_int](request=req)
    resp2.body = resp1.body
    resp2.headerlist = resp1.headerlist
    verify_response(resp2, "copied response")

    # evaluate it again
    resp3 = req.get_response(resp2)
    verify_response(resp3, "evaluated copy")

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
    m = webob_exc._HTTPMove()
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
    m = webob_exc._HTTPMove(location='http://example.com')
    assert_equal( m( environ, start_response ), [] )

def test_HTTPMove_location_newlines():
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'HEAD',
       'PATH_INFO': '/',
    }
    assert_raises(ValueError, webob_exc._HTTPMove,
            location='http://example.com\r\nX-Test: false')

def test_HTTPMove_add_slash_and_location():
    def start_response(status, headers, exc_info=None):
        pass
    assert_raises( TypeError, webob_exc._HTTPMove, location='http://example.com',
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
    m = webob_exc._HTTPMove()
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
    m = webob_exc._HTTPMove()
    m.add_slash = True
    environ[ 'QUERY_STRING' ] = 'querystring'
    environ['PATH_INFO'] = '/'
    assert_equal( m( environ, start_response ), [] )

def test_HTTPFound_unused_environ_variable():
    class Crashy(object):
        def __str__(self):
            raise Exception('I crashed!')

    def start_response(status, headers, exc_info=None):
        pass
    environ = {
       'wsgi.url_scheme': 'HTTP',
       'SERVER_NAME': 'localhost',
       'SERVER_PORT': '80',
       'REQUEST_METHOD': 'GET',
       'PATH_INFO': '/',
       'HTTP_ACCEPT': 'text/html',
       'crashy': Crashy()
    }

    m = webob_exc._HTTPMove(location='http://www.example.com')
    assert_equal( m( environ, start_response ), [
        b'<html>\n'
        b' <head>\n'
        b'  <title>500 Internal Server Error</title>\n'
        b' </head>\n'
        b' <body>\n'
        b'  <h1>500 Internal Server Error</h1>\n'
        b'  The resource has been moved to '
        b'<a href="http://www.example.com">'
        b'http://www.example.com</a>;\n'
        b'you should be redirected automatically.\n' 
        b'\n\n'
        b' </body>\n'
        b'</html>' ] 
    )

def test_HTTPExceptionMiddleware_ok():
    def app( environ, start_response ):
        return '123'
    application = app
    m = webob_exc.HTTPExceptionMiddleware(application)
    environ = {}
    start_response = None
    res = m( environ, start_response )
    assert_equal( res, '123' )

def test_HTTPExceptionMiddleware_exception():
    def wsgi_response( environ, start_response):
        return '123'
    def app( environ, start_response ):
        raise webob_exc.HTTPException( None, wsgi_response )
    application = app
    m = webob_exc.HTTPExceptionMiddleware(application)
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
        raise webob_exc.HTTPException( None, wsgi_response )
    application = app
    m = webob_exc.HTTPExceptionMiddleware(application)
    environ = {}
    def start_response(status, headers, exc_info):
        pass
    try:
        old_sys = webob_exc.sys
        sys = DummySys()
        res = m( environ, start_response )
        assert_equal( res, None )
    finally:
        webob_exc.sys = old_sys

def test_status_map_is_deterministic():
    for code, cls in (
        (200, webob_exc.HTTPOk),
        (201, webob_exc.HTTPCreated),
        (202, webob_exc.HTTPAccepted),
        (203, webob_exc.HTTPNonAuthoritativeInformation),
        (204, webob_exc.HTTPNoContent),
        (205, webob_exc.HTTPResetContent),
        (206, webob_exc.HTTPPartialContent),
        (300, webob_exc.HTTPMultipleChoices),
        (301, webob_exc.HTTPMovedPermanently),
        (302, webob_exc.HTTPFound),
        (303, webob_exc.HTTPSeeOther),
        (304, webob_exc.HTTPNotModified),
        (305, webob_exc.HTTPUseProxy),
        (307, webob_exc.HTTPTemporaryRedirect),
        (308, webob_exc.HTTPPermanentRedirect),
        (400, webob_exc.HTTPBadRequest),
        (401, webob_exc.HTTPUnauthorized),
        (402, webob_exc.HTTPPaymentRequired),
        (403, webob_exc.HTTPForbidden),
        (404, webob_exc.HTTPNotFound),
        (405, webob_exc.HTTPMethodNotAllowed),
        (406, webob_exc.HTTPNotAcceptable),
        (407, webob_exc.HTTPProxyAuthenticationRequired),
        (408, webob_exc.HTTPRequestTimeout),
        (409, webob_exc.HTTPConflict),
        (410, webob_exc.HTTPGone),
        (411, webob_exc.HTTPLengthRequired),
        (412, webob_exc.HTTPPreconditionFailed),
        (413, webob_exc.HTTPRequestEntityTooLarge),
        (414, webob_exc.HTTPRequestURITooLong),
        (415, webob_exc.HTTPUnsupportedMediaType),
        (416, webob_exc.HTTPRequestRangeNotSatisfiable),
        (417, webob_exc.HTTPExpectationFailed),
        (422, webob_exc.HTTPUnprocessableEntity),
        (423, webob_exc.HTTPLocked),
        (424, webob_exc.HTTPFailedDependency),
        (428, webob_exc.HTTPPreconditionRequired),
        (429, webob_exc.HTTPTooManyRequests),
        (431, webob_exc.HTTPRequestHeaderFieldsTooLarge),
        (451, webob_exc.HTTPUnavailableForLegalReasons),
        (500, webob_exc.HTTPInternalServerError),
        (501, webob_exc.HTTPNotImplemented),
        (502, webob_exc.HTTPBadGateway),
        (503, webob_exc.HTTPServiceUnavailable),
        (504, webob_exc.HTTPGatewayTimeout),
        (505, webob_exc.HTTPVersionNotSupported),
        (511, webob_exc.HTTPNetworkAuthenticationRequired),
    ):
        assert webob_exc.status_map[code] == cls
