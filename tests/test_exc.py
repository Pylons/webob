import sys
from webob import *
from webob.dec import wsgify
from webob.exc import *

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
