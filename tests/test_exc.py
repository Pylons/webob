import webob
import webob.exc
import webob.dec

@webob.dec.wsgify
def method_not_allowed_app(req):
    if req.method != 'GET':
        raise webob.exc.HTTPMethodNotAllowed()
    return 'hello!'

def test_exception_with_unicode_data():
    req = webob.Request.blank('/', method=u'POST')
    res = req.get_response(method_not_allowed_app)
    assert res.status_int == 405
