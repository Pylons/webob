"""
Decorators to wrap functions to make them WSGI applications.

The main decorator :class:`wsgify` adds a ``.wsgi_app`` attribute to a
function that is a WSGI application for that function.
:class:`wsgiwrap` turns the function into a WSGI application (not as
an attribute).
"""

import webob
import webob.exc

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
                     and (name != 'add_keyword_args' or self.middleware_wraps is None)])
        my_name = self.__class__.__name__
        if self.middleware_wraps is not None:
            my_name = '%s.middleware' % my_name
        r = '%s(%s)' % (
            my_name, ', '.join(args))
        if self.middleware_wraps:
            args = [repr(self.middleware_wraps)]
            if self.add_keyword_args:
                args.extend(['%s=%r' % (name, value) for name, value in sorted(self.add_keyword_args.items())])
            r += '(%s)' % ', '.join(args)
        return r

    # To match @decorator:
    @property
    def undecorated(self):
        return self.func

    def __call__(self, req, *args, **kw):
        if self.func is None:
            func = req
            if not func or args or kw:
                raise TypeError('wsgiapp is unbound; you must call it with a function')
            return self.__class__(func, **self._instance_args)
        elif self.force_wsgi:
            if kw or len(args) != 1:
                raise TypeError(
                    "Incorrect WSGI signature: %r(%s)" % (self, _format_args(req, *args, **kw)))
            return self.wsgi_app(req, args[0])
        else:
            return self.call(req, *args, **kw)

    def call(self, req, *args, **kw):
        """Call the function like normal, normalizing the response if
        asked for
        """
        try:
            resp = self.func(req, *args, **kw)
        except TypeError:
            assert 0, '%r(%s)->%r' % (self.func, _format_args(req, *args, **kw), self.wsgi_app)
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
            _format_args(*args, **self.kw))
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
            _format_args(self.middleware, **self.kw))
    def __call__(self, app, **config):
        kw = self.kw.copy()
        kw['add_keyword_args'] = config
        return self.wrapper_class.middleware(self.middleware, app, **kw)

def _func_name(func):
    """Returns the string name of a function, or method, as best it can"""
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

def _format_args(*args, **kw):
    all = [repr(arg) for arg in args]
    all.extend(['%s=%r' % (name, value) for name, value in sorted(kw.items())])
    return ', '.join(all)
    
