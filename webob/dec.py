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

    # The class to use for requests:
    RequestClass = webob.Request
    # Bind these attributes to the request object when the request
    # comes in:
    request_attrs = {}
    # Replaces the function with a WSGI application instead of just
    # attaching .wsgi_app:
    force_wsgi = False
    # If true, then **req.urlvars are added to the signature
    add_urlvars = False
    # Positional arguments to add to the function call:
    add_call_args = ()
    # Keyword arguments to add to the function call:
    add_keyword_args = {}
    # When this is middleware that wraps an application:
    middleware_wraps = None
    # When this is used as an instantiator:
    _instantiate_class = None

    def __init__(self, func=None, **kw):
        """Decorate `func` as a WSGI application

        If `func` is None, then this is a lazy binding of ``**kw`` and
        the resulting object is a decorator for the func, like::

            @wsgify(add_urlvars=True)
            def app(req, *args, **kw):
                return Response(...)

        Note that the resulting object *is not itself a WSGI application*.
        Instead it has an attribute ``.wsgi_app`` which is a WSGI
        application.  Unless you set ``.force_wsgi=True``, which makes it a
        WSGI application (i.e., ``__call__`` acts as a WSGI application).
        """
        self.func = func
        if func is not None:
            for attr in ('__name__', 'func_name', 'func_doc', '__doc__'):
                if hasattr(func, attr):
                    setattr(self, attr, getattr(func, attr))
        self._instance_args = kw
        for name, value in kw.iteritems():
            if not hasattr(self, name):
                raise TypeError("Unexpected argument: %s" % name)
            setattr(self, name, value)

    def __repr__(self):
        if self.func is None:
            args = []
        else:
            args = [_func_name(self.func)]
        args.extend(['%s=%r' % (name, value) for name, value in sorted(self._instance_args.items())
                     if name != 'middleware_wraps'
                     and (name != 'add_keyword_args' or self.middleware_wraps is None)
                     and (name != '_instantiate_class')])
        my_name = self.__class__.__name__
        if self.middleware_wraps is not None:
            my_name = '%s.middleware' % my_name
        if self._instantiate_class is not None:
            my_name = '%s.instantiator' % my_name
        r = '%s(%s)' % (
            my_name, ', '.join(args))
        if self.middleware_wraps:
            args = [repr(self.middleware_wraps)]
            if self.add_keyword_args:
                args.extend(['%s=%r' % (name, value) for name, value in sorted(self.add_keyword_args.items())])
            r += '(%s)' % ', '.join(args)
        if self._instantiate_class is not None and self._instantiate_class is not True:
            r = '<%s bound to %s>' % (r, _func_name(self._instantiate_class))
        return r

    # To match @decorator:
    @property
    def undecorated(self):
        return self.func

    def __call__(self, req, *args, **kw):
        if self._instantiate_class is not None:
            return self.wsgi_app(req, args[0])
        if self.func is None:
            func = req
            if not func or args or kw:
                raise TypeError('wsgiapp is unbound; you must call it with a function')
            return self.__class__(func, **self._instance_args)
        elif self.force_wsgi:
            if kw or len(args) != 1:
                raise TypeError(
                    "Incorrect WSGI signature: %r(%s)" % (self, _format_args((req,)+args, kw)))
            return self.wsgi_app(req, args[0])
        else:
            return self.call(req, *args, **kw)

    def call(self, req, *args, **kw):
        """Call the function like normal, normalizing the response if
        asked for
        """
        if self._instantiate_class is None:
            args = (req,)+args
            func = self.func
        else:
            if self._instantiate_class is True:
                raise TypeError('%r called with no bound class (did you add it to a new-style class?'
                                % self)
            func = self._instantiate_class(req)
        resp = func(*args, **kw)
        resp = self.normalize_response(req, resp)
        return resp

    def __get__(self, obj, type=None):
        if hasattr(self.func, '__get__'):
            return self.__class__(self.func.__get__(obj, type), **self._instance_args)
        else:
            return self

    def wsgi_app(self, environ, start_response):
        """The WSGI calling signature for this wrapped function"""
        req = self.RequestClass(environ, **self.request_attrs)
        req.response = req.ResponseClass()
        req.response.request = req
        # Hacky, but I think it improves the traceback: (?)
        if self.handle_exception:
            handle_exception = Exception # Catches all (well, most) exceptions
        else:
            handle_exception = None      # Catches no exceptions
        try:
            resp = self.apply(req)
        except webob.exc.HTTPException, resp:
            pass # the exception is the new response
        except handle_exception, e:
            resp = self.handle_exception(req, e)
            if resp is None:
                raise
        resp = self.normalize_response(req, resp)
        if hasattr(resp, 'wsgi_app'):
            # Allows chaining return values
            resp = resp.wsgi_app
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

    # Optional exception handler:
    handle_exception = None

    def apply(self, req):
        """For use by subclasses to override the calling signature"""
        args = (req,)
        if self.middleware_wraps:
            args += (self.middleware_wraps,)
        if self.add_call_args:
            args += tuple(self.add_call_args)
        if self.add_urlvars:
            args = args + tuple(req.urlargs)
            kw = req.urlvars
        else:
            kw = {}
        if self.add_keyword_args:
            kw.update(self.add_keyword_args)
        return self.call(*args, **kw)

    @classmethod
    def reverse(cls, wsgi_app):
        """Takes a WSGI application and gives it a calling signature
        similar to a wrapped function (``resp = func(req)``)"""
        if hasattr(wsgi_app, 'wsgi_app'):
            wsgi_app = wsgi_app.wsgi_app
        def method(req):
            return req.get_response(wsgi_app)
        return cls(method)

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
        if hasattr(app, 'wsgi_app'):
            app = app.wsgi_app
        if 'reverse_args' in kw:
            reverse_args = kw.pop('reverse_args')
        else:
            reverse_args = {}
        app = cls.reverse(app, **reverse_args)
        return cls(middle_func, middleware_wraps=app, **kw)

    @classmethod
    def instantiator(cls, **kw):
        """Give a class a descriptor that will instantiate the class
        with a request object, then call the instance with no
        arguments.

        Use this like::

            class MyClass(object):
                def __init__(self, req):
                    self.req = req
                def __call__(self):
                    return Response('whatever')
                wsgi_app = wsgify.instantiator()

        Then ``MyClass.wsgi_app`` will be an application that will
        instantiate the class *for every request*.  You can use settings
        like ``add_urlvars`` with ``wsgify.instantiate``, and these will
        effect how ``__call__`` is invoked.
        """
        return _Instantiator(cls, kw)

class wsgiwrap(wsgify):
    force_wsgi = True

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

class classapp(object):
    def __init__(self, klass, construction_method=None, call_method='__call__'):
        """This turns a class into a WSGI application."""
        self.klass = klass
        self.construction_method = construction_method
        self.call_method = call_method
    def __repr__(self):
        args = {}
        if self.construction_method is not None:
            args['construction_method'] = self.construction_method
        if self.call_method != '__call__':
            args['call_method'] = self.call_method
        return 'classapp(%s%s)' % (_func_name(self.klass),
                                   _format_args(obj=self, names='construction_method call_method',
                                                defaults=dict(construction_method=None, call_method='__call__'),
                                                leading_comma=True))
    @wsgify
    def __call__(self, req):
        if self.construction_method is None:
            instantiator = self.klass
        else:
            instantiator = getattr(self.klass, self.construction_method)
        instance = instantiator(req)
        method = getattr(instance, self.call_method)
        return method()

