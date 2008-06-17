from webob import Request, Response
from webob.exc import HTTPException

import new
import inspect

class WrapperBase(object):
    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_min_init_args'):
            init_args, _, _, init_defaults = inspect.getargspec(cls.__init__)
            cls._min_init_args = len(init_args) - len(init_defaults or ()) - 1
        if len(args) < cls._min_init_args:
            return lambda *newargs: cls(*(args+newargs), **kw)
        else:
            inst = super(WrapperBase, cls).__new__(cls, *args, **kw)
            inst._key = str(id(inst))
            inst._original_args = list(args)
            inst._original_kw = kw.copy()
            return inst

    def __repr__(self):
        args = []
        for arg in self._original_args:
            args.append(repr(arg))
        for name, val in self._original_kw.iteritems():
            args.append('%s=%r' % (name, val))
        return '%s(%s)' % (self.__class__.__name__, ', '.join(args))

    def __get__(self, owner, instance):
        wrapped = getattr(instance, self._key, None)
        if wrapped is None:
            bound = new.instancemethod(self.func, owner, instance)
            wrapped = self.__class__(bound, **self._original_kw)
            setattr(instance, self._key, wrapped)
        return wrapped


class webob_wrap(WrapperBase):
    def __init__(self, func, default_request_charset='UTF-8', **kw):
        self.func = func
        self.default_request_charset = default_request_charset
        self.kw = kw

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


class webob_middleware(WrapperBase):
    def __init__(self, mwfunc, next_app, **kw):
        self.mwfunc = mwfunc
        self.next_app = next_app
        self.kw = kw

    @webob_wrap
    def __call__(self, req):
        return self.mwfunc(req, self.next_app, **self.kw)


class webob_postprocessor(WrapperBase):
    def __init__(self, postprocessor, next_app, no_range=True, decode_content=True, **kw):
        self.postprocessor = postprocessor
        self.next_app = next_app
        self.no_range = no_range
        self.decode_content = decode_content
        self.kw = kw

    @webob_wrap
    def __call__(self, req):
        if self.no_range:
            req.range = req.if_range = None
        resp = req.get_response(self.next_app)
        if resp._app_iter or resp._body:
            if self.decode_content:
                resp.decode_content()
            self.postprocessor(resp, **self.kw)
        return resp


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

    @webob_middleware
    def mw(req, app):
        r = req.get_response(app)
        r.md5_etag()
        return r

    mwa = mw(app)
    mwr = test(mwa)
    print mw, mwa
    assert mwr.body == '1'
    assert mwr.etag is not None

    @webob_postprocessor
    def double(r):
        r.body += r.body

    #print double
    #print double.__call__
    dapp = double(app)
    print dapp
    assert test(dapp).body == '11'
