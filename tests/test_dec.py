import unittest

from webob.dec import wsgify
from webob.request import Request
from webob.response import Response
from webob.util import bytes_, text_


class DecoratorTests(unittest.TestCase):
    def _testit(self, app, req):
        if isinstance(req, str):
            req = Request.blank(req)
        resp = req.get_response(app)

        return resp

    def test_wsgify(self):
        resp_str = "hey, this is a test: %s"

        @wsgify
        def test_app(req):
            return bytes_(resp_str % req.url)

        resp = self._testit(test_app, "/a url")
        assert resp.body == bytes_(resp_str % "http://localhost/a%20url")
        assert resp.content_length == 45
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"

    def test_wsgify_empty_repr(self):
        assert "wsgify at" in repr(wsgify())

    def test_wsgify_args(self):
        resp_str = b"hey hey my my"

        @wsgify(args=(resp_str,))
        def test_app(req, strarg):
            return strarg

        resp = self._testit(test_app, "/a url")
        assert resp.body == resp_str
        assert resp.content_length == 13
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"

    def test_wsgify_kwargs(self):
        resp_str = b"hey hey my my"

        @wsgify(kwargs={"strarg": resp_str})
        def test_app(req, strarg=""):
            return strarg

        resp = self._testit(test_app, "/a url")
        assert resp.body == resp_str
        assert resp.content_length == 13
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"

    def test_wsgify_raise_httpexception(self):
        from webob.exc import HTTPBadRequest

        @wsgify
        def test_app(req):
            raise HTTPBadRequest

        resp = self._testit(test_app, "/a url")
        assert resp.body.startswith(b"400 Bad Request")
        assert resp.content_type == "text/plain"
        assert resp.charset == "UTF-8"

    def test_wsgify_no___get__(self):
        # use a class instance instead of a fn so we wrap something w/
        # no __get__
        class TestApp:
            def __call__(self, req):
                return "nothing to see here"

        test_app = wsgify(TestApp())
        resp = self._testit(test_app, "/a url")
        assert resp.body == b"nothing to see here"
        assert test_app.__get__(test_app) is test_app

    def test_wsgify_app_returns_unicode(self):
        def test_app(req):
            return text_("some text")

        test_app = wsgify(test_app)
        resp = self._testit(test_app, "/a url")
        assert resp.body == b"some text"

    def test_wsgify_args_no_func(self):
        test_app = wsgify(None, args=(1,))
        self.assertRaises(TypeError, self._testit, test_app, "/a url")

    def test_wsgify_call_args(self):
        resp_str = "args: %s, kwargs: %s"

        def show_vars(req, *args, **kwargs):
            return bytes_(resp_str % (sorted(args), sorted(kwargs.items())))

        app = wsgify(show_vars, args=("foo", "bar"), kwargs={"a": 1, "b": 2})
        resp = app(Request.blank("/"))

        assert resp == bytes_(resp_str % ("['bar', 'foo']", "[('a', 1), ('b', 2)]"))

    def test_wsgify_call_args_override(self):
        resp_str = "args: %s, kwargs: %s"

        def show_vars(req, *args, **kwargs):
            return bytes_(resp_str % (sorted(args), sorted(kwargs.items())))

        app = wsgify(show_vars, args=("foo", "bar"), kwargs={"a": 1, "b": 2})
        resp = app(Request.blank("/"), "qux", c=3)

        assert resp == bytes_(resp_str % ("['qux']", "[('c', 3)]"))

    def test_wsgify_wrong_sig(self):
        @wsgify
        def test_app(req):
            return "What have you done for me lately?"

        req = {}
        self.assertRaises(TypeError, test_app, req, 1, 2)
        self.assertRaises(TypeError, test_app, req, 1, key="word")

    def test_wsgify_none_response(self):
        @wsgify
        def test_app(req):
            return

        resp = self._testit(test_app, "/a url")
        assert resp.body == b""
        assert resp.content_type == "text/html"
        assert resp.content_length == 0

    def test_wsgify_get(self):
        resp_str = b"What'choo talkin' about, Willis?"

        @wsgify
        def test_app(req):
            return Response(resp_str)

        resp = test_app.get("/url/path")
        assert resp.body == resp_str

    def test_wsgify_post(self):
        post_dict = {"speaker": "Robin", "words": "Holy test coverage, Batman!"}

        @wsgify
        def test_app(req):
            return Response("{}: {}".format(req.POST["speaker"], req.POST["words"]))

        resp = test_app.post("/url/path", post_dict)
        assert resp.body == bytes_("{}: {}".format(post_dict["speaker"], post_dict["words"]))

    def test_wsgify_request_method(self):
        resp_str = b"Nice body!"

        @wsgify
        def test_app(req):
            assert req.method == "PUT"

            return Response(req.body)

        resp = test_app.request("/url/path", method="PUT", body=resp_str)
        assert resp.body == resp_str
        assert resp.content_length == 10
        assert resp.content_type == "text/html"

    def test_wsgify_undecorated(self):
        def test_app(req):
            return Response("whoa")

        wrapped_test_app = wsgify(test_app)
        assert wrapped_test_app.undecorated is test_app

    def test_wsgify_custom_request(self):
        resp_str = "hey, this is a test: %s"

        class MyRequest(Request):
            pass

        @wsgify(RequestClass=MyRequest)
        def test_app(req):
            return bytes_(resp_str % req.url)

        resp = self._testit(test_app, "/a url")
        assert resp.body == bytes_(resp_str % "http://localhost/a%20url")
        assert resp.content_length == 45
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"

    def test_middleware(self):
        resp_str = "These are the vars: %s"

        @wsgify.middleware
        def set_urlvar(req, app, **vars):
            req.urlvars.update(vars)

            return app(req)

        from webob.dec import _MiddlewareFactory

        assert set_urlvar.__class__ is _MiddlewareFactory
        r = repr(set_urlvar)
        assert "set_urlvar" in r

        @wsgify
        def show_vars(req):
            return resp_str % (sorted(req.urlvars.items()))

        show_vars2 = set_urlvar(show_vars, a=1, b=2)
        resp = self._testit(show_vars2, "/path")
        assert resp.body == bytes_(resp_str % "[('a', 1), ('b', 2)]")
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"
        assert resp.content_length == 40

    def test_middleware_call_kwargs(self):
        resp_str = "kwargs: %s"

        @wsgify.middleware
        def set_args(req, app, **kwargs):
            req.urlvars = kwargs

            return req.get_response(app)

        @wsgify
        def show_vars(req):
            return resp_str % sorted(req.urlvars.items())

        app = set_args(show_vars, a=1, b=2)
        resp = app(Request.blank("/"))

        assert resp.body == bytes_(resp_str % "[('a', 1), ('b', 2)]")

    def test_middleware_call_kwargs_override(self):
        resp_str = "kwargs: %s"

        @wsgify.middleware
        def set_args(req, app, **kwargs):
            req.urlvars = kwargs

            return req.get_response(app)

        @wsgify
        def show_vars(req):
            return resp_str % sorted(req.urlvars.items())

        app = set_args(show_vars, a=1, b=2)
        resp = app(Request.blank("/"), c=3)

        assert resp.body == bytes_(resp_str % "[('c', 3)]")

    def test_middleware_as_decorator(self):
        resp_str = "These are the vars: %s"

        @wsgify.middleware
        def set_urlvar(req, app, **vars):
            req.urlvars.update(vars)

            return app(req)

        @set_urlvar(a=1, b=2)
        @wsgify
        def show_vars(req):
            return resp_str % (sorted(req.urlvars.items()))

        resp = self._testit(show_vars, "/path")
        assert resp.body == bytes_(resp_str % "[('a', 1), ('b', 2)]")
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"
        assert resp.content_length == 40

    def test_unbound_middleware(self):
        @wsgify
        def test_app(req):
            return Response("Say wha!?")

        unbound = wsgify.middleware(None, test_app, some="thing")
        from webob.dec import _UnboundMiddleware

        assert unbound.__class__ is _UnboundMiddleware
        assert unbound.kw == {"some": "thing"}

        @unbound
        def middle(req, app, **kw):
            return app(req)

        assert middle.__class__ is wsgify
        assert "test_app" in repr(unbound)

    def test_unbound_middleware_no_app(self):
        unbound = wsgify.middleware(None, None)
        from webob.dec import _UnboundMiddleware

        assert unbound.__class__ is _UnboundMiddleware
        assert unbound.kw == {}

    def test_classapp(self):
        class HostMap(dict):
            @wsgify
            def __call__(self, req):
                return self[req.host.split(":")[0]]

        app = HostMap()
        app["example.com"] = Response("1")
        app["other.com"] = Response("2")
        resp = Request.blank("http://example.com/").get_response(wsgify(app))
        assert resp.content_type == "text/html"
        assert resp.charset == "UTF-8"
        assert resp.content_length == 1
        assert resp.body == b"1"

    def test_middleware_direct_call(self):
        @wsgify.middleware
        def mw(req, app):
            return "foo"

        app = mw(Response())
        assert app(Request.blank("/")) == "foo"
