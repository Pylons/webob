import unittest
from webob.request import Request
from webob.response import Response
from webob.dec import wsgify
from webob.compat import bytes_
from webob.compat import text_
from webob.compat import PY3

class DecoratorTests(unittest.TestCase):
    def _testit(self, app, req):
        if isinstance(req, str):
            req = Request.blank(req)
        resp = req.get_response(app)
        return resp

    def test_wsgify(self):
        resp_str = 'hey, this is a test: %s'
        @wsgify
        def test_app(req):
            return bytes_(resp_str % req.url)
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body,
                         bytes_(resp_str % 'http://localhost/a%20url'))
        self.assertEqual(resp.content_length, 45)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_empty_repr(self):
        self.assertTrue('wsgify at' in repr(wsgify()))

    def test_wsgify_args(self):
        resp_str = b'hey hey my my'
        @wsgify(args=(resp_str,))
        def test_app(req, strarg):
            return strarg
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, resp_str)
        self.assertEqual(resp.content_length, 13)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_kwargs(self):
        resp_str = b'hey hey my my'
        @wsgify(kwargs=dict(strarg=resp_str))
        def test_app(req, strarg=''):
            return strarg
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, resp_str)
        self.assertEqual(resp.content_length, 13)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_raise_httpexception(self):
        from webob.exc import HTTPBadRequest
        @wsgify
        def test_app(req):
            raise HTTPBadRequest
        resp = self._testit(test_app, '/a url')
        self.assert_(resp.body.startswith(b'400 Bad Request'))
        self.assertEqual(resp.content_type, 'text/plain')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_wsgify_no___get__(self):
        # use a class instance instead of a fn so we wrap something w/
        # no __get__
        class TestApp(object):
            def __call__(self, req):
                return 'nothing to see here'
        test_app = wsgify(TestApp())
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, b'nothing to see here')
        self.assert_(test_app.__get__(test_app) is test_app)

    def test_wsgify_app_returns_unicode(self):
        def test_app(req):
            return text_('some text')
        test_app = wsgify(test_app)
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, b'some text')

    def test_wsgify_args_no_func(self):
        test_app = wsgify(None, args=(1,))
        self.assertRaises(TypeError, self._testit, test_app, '/a url')

    def test_wsgify_wrong_sig(self):
        @wsgify
        def test_app(req):
            return 'What have you done for me lately?'
        req = dict()
        self.assertRaises(TypeError, test_app, req, 1, 2)
        self.assertRaises(TypeError, test_app, req, 1, key='word')

    def test_wsgify_none_response(self):
        @wsgify
        def test_app(req):
            return
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body, b'')
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.content_length, 0)

    def test_wsgify_get(self):
        resp_str = b"What'choo talkin' about, Willis?"
        @wsgify
        def test_app(req):
            return Response(resp_str)
        resp = test_app.get('/url/path')
        self.assertEqual(resp.body, resp_str)

    def test_wsgify_post(self):
        post_dict = dict(speaker='Robin',
                         words='Holy test coverage, Batman!')
        @wsgify
        def test_app(req):
            return Response('%s: %s' % (req.POST['speaker'],
                                        req.POST['words']))
        resp = test_app.post('/url/path', post_dict)
        self.assertEqual(resp.body, bytes_('%s: %s' % (post_dict['speaker'],
                                                       post_dict['words'])))

    def test_wsgify_request_method(self):
        resp_str = b'Nice body!'
        @wsgify
        def test_app(req):
            self.assertEqual(req.method, 'PUT')
            return Response(req.body)
        resp = test_app.request('/url/path', method='PUT',
                                body=resp_str)
        self.assertEqual(resp.body, resp_str)
        self.assertEqual(resp.content_length, 10)
        self.assertEqual(resp.content_type, 'text/html')

    def test_wsgify_undecorated(self):
        def test_app(req):
            return Response('whoa')
        wrapped_test_app = wsgify(test_app)
        self.assert_(wrapped_test_app.undecorated is test_app)

    def test_wsgify_custom_request(self):
        resp_str = 'hey, this is a test: %s'
        class MyRequest(Request):
            pass
        @wsgify(RequestClass=MyRequest)
        def test_app(req):
            return bytes_(resp_str % req.url)
        resp = self._testit(test_app, '/a url')
        self.assertEqual(resp.body,
                         bytes_(resp_str % 'http://localhost/a%20url'))
        self.assertEqual(resp.content_length, 45)
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')

    def test_middleware(self):
        resp_str = "These are the vars: %s"
        @wsgify.middleware
        def set_urlvar(req, app, **vars):
            req.urlvars.update(vars)
            return app(req)
        from webob.dec import _MiddlewareFactory
        self.assert_(set_urlvar.__class__ is _MiddlewareFactory)
        r = repr(set_urlvar)
        self.assert_('set_urlvar' in r)
        @wsgify
        def show_vars(req):
            return resp_str % (sorted(req.urlvars.items()))
        show_vars2 = set_urlvar(show_vars, a=1, b=2)
        resp = self._testit(show_vars2, '/path')
        self.assertEqual(resp.body, bytes_(resp_str % "[('a', 1), ('b', 2)]"))
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')
        self.assertEqual(resp.content_length, 40)

    def test_unbound_middleware(self):
        @wsgify
        def test_app(req):
            return Response('Say wha!?')
        unbound = wsgify.middleware(None, test_app, some='thing')
        from webob.dec import _UnboundMiddleware
        self.assert_(unbound.__class__ is _UnboundMiddleware)
        self.assertEqual(unbound.kw, dict(some='thing'))
        @unbound
        def middle(req, app, **kw):
            return app(req)
        self.assert_(middle.__class__ is wsgify)
        self.assertTrue('test_app' in repr(unbound))

    def test_unbound_middleware_no_app(self):
        unbound = wsgify.middleware(None, None)
        from webob.dec import _UnboundMiddleware
        self.assert_(unbound.__class__ is _UnboundMiddleware)
        self.assertEqual(unbound.kw, dict())

    def test_classapp(self):
        class HostMap(dict):
            @wsgify
            def __call__(self, req):
                return self[req.host.split(':')[0]]
        app = HostMap()
        app['example.com'] = Response('1')
        app['other.com'] = Response('2')
        resp = Request.blank('http://example.com/').get_response(wsgify(app))
        self.assertEqual(resp.content_type, 'text/html')
        self.assertEqual(resp.charset, 'UTF-8')
        self.assertEqual(resp.content_length, 1)
        self.assertEqual(resp.body, b'1')

    def test_middleware_direct_call(self):
        @wsgify.middleware
        def mw(req, app):
            return 'foo'

        app = mw(Response())
        self.assertEqual(app(Request.blank('/')), 'foo')
