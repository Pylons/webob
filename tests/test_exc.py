import webob
import webob.exc
import webob.dec

import sys

@webob.dec.wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        if sys.version_info > (2,5):
            raise webob.exc.HTTPMethodNotAllowed()
        else:
            raise webob.exc.HTTPMethodNotAllowed().exception
    return 'hello!'

def test_exception_with_unicode_data():
    req = webob.Request.blank('/', method=u'POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_int == 405
