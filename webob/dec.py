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

class wsgify(object):
    RequestClass = webob.Request

    def __init__(self, func=None, RequestClass=None,
                 args=(), kwargs=None, middleware_wraps=None):
        self.func = func
        if (RequestClass is not None
            and RequestClass is not self.RequestClass):
            self.RequestClass = RequestClass
        self.args = tuple(args)
        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs
        self.middleware_wraps = middleware_wraps

    def __repr__(self):
        if self.func is None:
            args = []
        else:
            args = [_func_name(self.func)]
        if self.RequestClass is not self.__class__.RequestClass:
            args.append('RequestClass=%r' % self.RequestClass)
        if self.args:
            args.append('args=%r' % self.args)
        my_name = self.__class__.__name__
        if self.middleware_wraps is not None:
            my_name = '%s.middleware' % my_name
        else:
            if self.kwargs:
                args.append('kwargs=%r' % self.kwargs)
        r = '%s(%s)' % (my_name, ', '.join(args))
        if self.middleware_wraps is not None:
            args = [repr(self.middleware_wraps)]
            if self.kwargs:
                args.extend(['%s=%r' % (name, value)
                             for name, value in sorted(self.kwargs.items())])
            r += '(%s)' % ', '.join(args)
        return r

    def __get__(self, obj, type=None):
        if hasattr(self.func, '__get__'):
            return self.clone(self.func.__get__(obj, type))
        else:
            return self

    def __call__(self, req, *args, **kw):
        func = self.func
        if func is None:
            if args or kw:
                raise TypeError(
                    "Unbound %s can only be called with the function it will wrap"
                    % self.__class__.__name__)
            func = req
            return self.clone(func)
        if isinstance(req, dict):
            if len(args) != 1 or kw:
                raise TypeError(
                    "Calling %r as a WSGI app with the wrong signature")
            environ = req
            start_response = args[0]
            req = self.RequestClass(environ)
            req.response = req.ResponseClass()
            req.response.request = req
            try:
                args = self.args
                if self.middleware_wraps:
                    args = (self.middleware_wraps,) + args
                resp = self.func(req, *args, **self.kwargs)
            except webob.exc.HTTPException, resp:
                pass
            if resp is None:
                ## FIXME: I'm not sure what this should be?
                resp = req.response
            elif isinstance(resp, basestring):
                body = resp
                resp = req.response
                resp.write(body)
            if resp is not req.response:
                resp = req.response.merge_cookies(resp)
            return resp(environ, start_response)
        else:
            return self.func(req, *args, **kw)

    def clone(self, func=None, **kw):
        kwargs = {}
        if func is not None:
            kwargs['func'] = func
        if self.RequestClass is not self.__class__.RequestClass:
            kwargs['RequestClass'] = self.RequestClass
        if self.args:
            kwargs['args'] = self.args
        if self.kwargs:
            kwargs['kwargs'] = self.kwargs
        kwargs.update(kw)
        return self.__class__(**kwargs)

    # To match @decorator:
    @property
    def undecorated(self):
        return self.func

    @classmethod
    def middleware(cls, middle_func=None, app=None, **kw):
        if middle_func is None:
            return _UnboundMiddleware(cls, app, kw)
        if app is None:
            return _MiddlewareFactory(cls, middle_func, kw)
        return cls(middle_func, middleware_wraps=app, kwargs=kw)

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
        if app is None:
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
        kw.update(config)
        return self.wrapper_class.middleware(self.middleware, app, **kw)

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

