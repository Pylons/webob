import webob
import webob.exc

class wsgify(object):

    RequestClass = webob.Request
    ResponseClass = webob.Response
    request_attrs = {}
    force_wsgi = False
    add_urlvars = False
    add_call_args = ()
    add_keyword_args = {}
    normalize_exceptions = False
    normalize_3xx_exceptions = False
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
            name = getattr(self.func, 'func_name', None)
            if name is None:
                name = repr(self.func)
            else:
                module = getattr(self.func, 'func_globals', {}).get('__name__')
                if module and module != '__main__':
                    name = '%s.%s' % (module, name)
            args = [name]
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

    @property
    def undecorated(self):
        return self.func

    def __call__(self, *args, **kw):
        if self.func is None:
            if not args or len(args) > 1 or kw:
                raise TypeError('wsgiapp is unbound; you must call it with a function')
            return self.__class__(args[0], **self._instance_args)
        elif self.force_wsgi:
            if kw or len(args) != 2:
                raise TypeError(
                    "Incorrect WSGI signature: *%r, **%r" % (args, kw))
            return self.wsgi_app(*args, **kw)
        else:
            return self.call(*args, **kw)

    def call(self, *args, **kw):
        """Call the function like normal, normalizing the response if
        asked for
        """
        if 'normalize_exceptions' in kw:
            normalize_exceptions = kw.pop('normalize_exceptions')
        else:
            normalize_exceptions = self.normalize_exceptions
        if 'normalize_3xx_exceptions' in kw:
            normalize_3xx_exceptions = kw.pop('normalize_3xx_exceptions')
        else:
            normalize_3xx_exceptions = self.normalize_3xx_exceptions
        resp = self.func(*args, **kw)
        req = args[0]
        resp = self.normalize_response(req, resp, normalize_exceptions=normalize_exceptions,
                                       normalize_3xx_exceptions=normalize_3xx_exceptions)
        return resp

    def __get__(self, obj, type=None):
        if hasattr(obj, '__get__'):
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
            handle_exception = Exception
        else:
            handle_exception = None
        try:
            resp = self.apply(req)
        except webob.exc.HTTPException, resp:
            pass
        except handle_exception, e:
            resp = self.handle_exception(req, e)
            if resp is None:
                raise
        resp = self.normalize_response(req, resp)
        if hasattr(resp, 'wsgi_app'):
            resp = resp.wsgi_app
        return resp(environ, start_response)

    def normalize_response(self, req, resp,
                           normalize_exceptions=False,
                           normalize_3xx_exceptions=False):
        if resp is None:
            resp = req.response
        elif isinstance(resp, basestring):
            body = resp
            resp = req.response
            resp.write(body)
        if resp is not req.response:
            resp = req.response.merge_cookies(resp)
        if normalize_exceptions:
            if hasattr(resp, 'wsgi_response'):
                resp = resp.wsgi_response
            status_int = int(resp.status.split(None, 1)[0])
            if (status_int >= 400
                or (normalize_3xx_exceptions and status_int >= 300)):
                exc_class = webob.exc.status_map.get(
                    status_int,
                    webob.exc.WSGIHTTPException)
                exc_resp = exc_class(
                    code=resp.status,
                    headerlist=resp.headerlist,
                    app_iter=resp.app_iter)
                raise exc_resp.exception
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
            new_kw = self.add_keyword_args.copy()
            new_kw.update(kw)
            kw = new_kw
        return self.call(*args, **kw)

    @classmethod
    def unwrap(cls, wsgi_app, **kw):
        """Takes a WSGI application and gives it a calling signature
        similar to a wrapped function (``resp = func(req)``)"""
        if hasattr(wsgi_app, 'wsgi_app'):
            wsgi_app = wsgi_app.wsgi_app
        def method(req):
            status, headerlist, app_iter = req.call_application(wsgi_app)
            return cls.ResponseClass(
                status=status,
                headerlist=headerlist,
                app_iter=app_iter)
        return cls(method, **kw)

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
        if 'unwrap_args' in kw:
            unwrap_args = kw.pop('unwrap_args')
        else:
            unwrap_args = {}
        if middle_func is None:
            def middleware_decorator(func):
                return cls.middleware(middle_func, app=app, **kw)
            return middleware_decorator
        if app is None:
            def middleware_factory(app, **config):
                new_kw = kw.copy()
                new_kw['add_keyword_args'] = config
                return cls.middleware(middle_func, app, **new_kw)
            return middleware_factory
        if not isinstance(app, cls):
            if not unwrap_args and hasattr(app, 'wsgi_app'):
                app = app.wsgi_app
            app = cls.unwrap(app, **unwrap_args)
        return cls(middle_func, middleware_wraps=app, **kw)

