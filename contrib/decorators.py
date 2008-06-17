from webob import Request, Response
from webob.exc import HTTPException

import new

class webob_wrap(object):
    def __new__(cls, *args, **kw):
        if not args:
            return lambda func: webob_wrap(func, **kw)
        else:
            return super(webob_wrap, cls).__new__(cls, *args, **kw)

    def __init__(self, __func=None, **kw):
        self.func = __func
        self._original_kw = kw.copy()
        self.default_request_charset = kw.pop('default_request_charset', 'UTF-8')
        self.kw = kw
        self._key = str(id(self))

    def __call__(self, environ, start_response):
        req = Request(environ)
        if req.charset is None:
            req.charset = self.default_request_charset
        try:
            app = self.func(req, **self.kw)
            if app is None:
                app = HTTPNotFound()
        except HTTPException, exc:
            app = exc
        return app(environ, start_response)

    def __get__(self, owner, instance):
        wrapped = getattr(instance, self._key, None)
        if wrapped is None:
            bound = new.instancemethod(self.func, owner, instance)
            wrapped = webob_wrap(bound, **self._original_kw)
            setattr(instance, self._key, wrapped)
        return wrapped

    def __repr__(self):
        kwstr = ', '.join('%s=%r' % (name, val) for (name, val) in self._original_kw.iteritems())
        return '%s(%r, %s)' % (self.__class__.__name__, self.func, kwstr)


def webob_middleware(middleware):
    def wrapper(app, **kw):
        @webob_wrap
        def middleware_app(req):
            return middleware(req, app, **kw)
        return middleware_app
    return wrapper

def webob_postprocessor(processor):
    @webob_middleware
    def postprocessor_middleware(req, app, no_range=True, decode_content=True, **kw):
        if no_range:
            req.range = req.if_range = None
        resp = req.get_response(app)
        if resp._app_iter or resp._body:
            if decode_content:
                resp.decode_content()
            processor(resp, **kw)
        return resp
    return postprocessor_middleware

if __name__ == '__main__':
    def test(app, url='/'):
        return Request.blank(url).get_response(app)

    @webob_wrap(x=1)
    def app(req, x):
        return Response(str(x))

    print app
    assert test(app).body == '1'

    class App(object):
        def __init__(self, val):
            self.val = str(val)

        @webob_wrap(default_request_charset='ASCII')
        def __call__(self, req):
            return Response(self.val)

    assert test(App('123')).body == '123'
