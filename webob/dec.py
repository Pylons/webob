"""
Decorators to wrap functions to make them WSGI applications.

The main decorator :class:`wsgify` adds a ``.wsgi_app`` attribute to a
function that is a WSGI application for that function.
:class:`wsgiwrap` turns the function into a WSGI application (not as
an attribute).
"""

import webob
import webob.exc
from types import ClassType

__all__ = ['wsgify', 'wsgiwrap']

class wsgiwrap(object):
    RequestClass = webob.Request
    middleware_wraps = None
    add_keyword_args = None

    def __init__(self, func=None, RequestClass=None, middleware_wraps=None,
                 add_keyword_args=None):
        self.func = func
        if RequestClass is not None:
            self.RequestClass = RequestClass
        if middleware_wraps is not None:
            self.middleware_wraps = middleware_wraps
        if add_keyword_args is not None:
            self.add_keyword_args = add_keyword_args

    def __repr__(self):
        kw = {}
        if self.RequestClass is not self.__class__.RequestClass:
            kw['RequestClass'] = self.RequestClass
        if self.middleware_wraps is not None:
            kw['middleware_wraps'] = self.middleware_wraps
        if self.add_keyword_args is not None:
            kw['add_keyword_args'] = self.add_keyword_args
        if self.func is not None:
            args = (self.func,)
        else:
            args = ()
        return '%s(%s)' % (self.__class__.__name__, _format_args(args, kw))

    @property
    def undecorated(self):
        return self.func

    def __call__(self, req, *args, **kw):
        if self.func is None:
            func = req
            if not func or args or kw:
                raise TypeError('wsgiapp is unbound; you must call it with a function')
            return self._clone(func)
        if type(req) is dist:
            # A WSGI call
            if len(args) != 1 or kw:
                raise TypeError(
                    "Improper WSGI call signature: %r(%s)"
                    % (self, _format_args((req,)+args, kw)))
            return self.wsgi_app(req, args[0])
        return self.func(req, *args, **kw)

    def _clone(self, new_func):
        return self.__class__(new_func, RequestClass=self.__dict__.get('RequestClass'),
                              middleware_wraps=self.__dict__.get('middleware_wraps'),
                              add_keyword_args=self.__dict__.get('add_keyword_args'))

    def __get__(self, obj, type=None):
        if hasattr(self.func, '__get__'):
            return self._clone(self.func.__get__(obj, type))
        else:
            return self

    def wsgi_app(self, environ, start_response):
        req = self.RequestClass(environ)
        req.response = req.ResponseClass()
        req.response.request = req
        try:
            resp = self.apply(req)
        except webob.exc.HTTPException, resp:
            pass # the exception is the new response
        resp = self.normalize_response(req, resp)
        return resp(environ, start_response)

    def normalize_response(self, req, resp):
        if resp is None:
            ## FIXME: I'm not sure this is a good idea?
            resp = req.response
        elif isinstance(resp, basestring):
            body = resp
            resp = req.response
            resp.write(body)
        if resp is not req.response:
            resp = req.response.merge_cookies(resp)
        return resp

    def apply(self, req):
        args = (req,)
        if self.middleware_wraps:
            args += (self.middleware_wraps,)
        return self.func(*args)

    @classmethod
    def middleware(cls, middle_func=None, app=None, **kw):
        """Wrap a function as middleware, to create either a new
        application (if you pass in `app`) or middleware factory (a
        function that takes an `app`).

        Use this like::

            @wsgify.middleware
            def set_user(req, app, username):
                req.remote_user = username
                return app(req)

            app = set_user(app, username='bob')
        """
        if middle_func is None:
            return _UnboundMiddleware(cls, app, kw)
        if app is None:
            return _MiddlewareFactory(cls, middle_func, kw)
        return cls(middle_func, middleware_wraps=app, **kw)

class _UnboundMiddleware(object):
    def __init__(self, wrapper_class, app, kw):
        self.wrapper_class = wrapper_class
        self.app = app
        self.kw = kw
    def __repr__(self):
        if self.app:
            args = (self.app,)
        else:
            args = ()
        return '%s.middleware(%s)' % (
            self.wrapper_class.__name__,
            _format_args(args, self.kw))
    def __call__(self, func, app=None):
        if app is not None:
            app = self.app
        return self.wrapper_class.middleware(func, app=app, **self.kw)

class _MiddlewareFactory(object):
    def __init__(self, wrapper_class, middleware, kw):
        self.wrapper_class = wrapper_class
        self.middleware = middleware
        self.kw = kw
    def __repr__(self):
        return '%s.middleware(%s)' % (
            self.wrapper_class.__name__,
            _format_args((self.middleware,), self.kw))
    def __call__(self, app, **config):
        kw = self.kw.copy()
        kw['add_keyword_args'] = config
        return self.wrapper_class.middleware(self.middleware, app, **kw)


class _UnboundMiddleware(object):
    def __init__(self, wrapper_class, app, kw):
        self.wrapper_class = wrapper_class
        self.app = app
        self.kw = kw
    def __repr__(self):
        if self.app:
            args = (self.app,)
        else:
            args = ()
        return '%s.middleware(%s)' % (
            self.wrapper_class.__name__,
            _format_args(args, self.kw))
    def __call__(self, func, app=None):
        if app is not None:
            app = self.app
        return self.wrapper_class.middleware(func, app=app, **self.kw)

class _MiddlewareFactory(object):
    def __init__(self, wrapper_class, middleware, kw):
        self.wrapper_class = wrapper_class
        self.middleware = middleware
        self.kw = kw
    def __repr__(self):
        return '%s.middleware(%s)' % (
            self.wrapper_class.__name__,
            _format_args((self.middleware,), self.kw))
    def __call__(self, app, **config):
        kw = self.kw.copy()
        kw['add_keyword_args'] = config
        return self.wrapper_class.middleware(self.middleware, app, **kw)

class _Instantiator(object):
    def __init__(self, wsgify_class, wsgify_kw):
        self.wsgify_class = wsgify_class
        self.wsgify_kw = wsgify_kw
    def __get__(self, obj, type=None):
        if obj is not None:
            return self.wsgify_class(obj, **self.wsgify_kw)
        else:
            return self.wsgify_class(_instantiate_class=type, **self.wsgify_kw)

def _func_name(func):
    """Returns the string name of a function, or method, as best it can"""
    if isinstance(func, (type, ClassType)):
        name = func.__name__
        if func.__module__ not in ('__main__', '__builtin__'):
            name = '%s.%s' % (func.__module__, name)
        return name
    name = getattr(func, 'func_name', None)
    if name is None:
        name = repr(func)
    else:
        name_self = getattr(func, 'im_self', None)
        if name_self is not None:
            name = '%r.%s' % (name_self, name)
        else:
            name_class = getattr(func, 'im_class', None)
            if name_class is not None:
                name = '%s.%s' % (name_class.__name__, name)
        module = getattr(func, 'func_globals', {}).get('__name__')
        if module and module != '__main__':
            name = '%s.%s' % (module, name)
    return name

def _format_args(args=(), kw=None, leading_comma=False, obj=None, names=None, defaults=None):
    if kw is None:
        kw = {}
    all = [repr(arg) for arg in args]
    if names is not None:
        assert obj is not None
        kw = {}
        if isinstance(names, basestring):
            names = names.split()
        for name in names:
            kw[name] = getattr(obj, name)
    if defaults is not None:
        kw = kw.copy()
        for name, value in defaults.items():
            if name in kw and value == kw[name]:
                del kw[name]
    all.extend(['%s=%r' % (name, value) for name, value in sorted(kw.items())])
    result = ', '.join(all)
    if result and leading_comma:
        result = ', ' + result
    return result

