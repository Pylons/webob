import unittest


class RequestTests(unittest.TestCase):

    def test_gets(self):
        from webtest import TestApp
        app = TestApp(simpleapp)
        res = app.get('/')
        self.assert_('Hello' in res)
        self.assert_("get is GET([])" in res)
        self.assert_("post is <NoVars: Not a form request>" in res)

        res = app.get('/?name=george')
        res.mustcontain("get is GET([('name', 'george')])")
        res.mustcontain("Val is george")

    def test_language_parsing(self):
        from webtest import TestApp
        app = TestApp(simpleapp)
        res = app.get('/')
        self.assert_("The languages are: ['en-US']" in res)

        res = app.get('/',
                      headers={'Accept-Language': 'da, en-gb;q=0.8, en;q=0.7'})
        self.assert_("languages are: ['da', 'en-gb', 'en-US']" in res)

        res = app.get('/',
                      headers={'Accept-Language': 'en-gb;q=0.8, da, en;q=0.7'})
        self.assert_("languages are: ['da', 'en-gb', 'en-US']" in res)

    def test_mime_parsing(self):
        from webtest import TestApp
        app = TestApp(simpleapp)
        res = app.get('/', headers={'Accept':'text/html'})
        self.assert_("accepttypes is: text/html" in res)

        res = app.get('/', headers={'Accept':'application/xml'})
        self.assert_("accepttypes is: application/xml" in res)

        res = app.get('/', headers={'Accept':'application/xml,*/*'})
        self.assert_("accepttypes is: application/xml" in res)

    def test_accept_best_match(self):
        from webob import Request
        self.assert_(not Request.blank('/').accept)
        self.assert_(not Request.blank('/', headers={'Accept': ''}).accept)
        req = Request.blank('/', headers={'Accept':'text/plain'})
        self.assert_(req.accept)
        self.assertRaises(ValueError, req.accept.best_match, ['*/*'])
        req = Request.blank('/', accept=['*/*','text/*'])
        self.assertEqual(
            req.accept.best_match(['application/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'application/x-foo']),
            'text/plain')
        req = Request.blank('/', accept=['text/plain', 'message/*'])
        self.assertEqual(
            req.accept.best_match(['message/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'message/x-foo']),
            'text/plain')

    def test_from_mimeparse(self):
        # http://mimeparse.googlecode.com/svn/trunk/mimeparse.py
        from webob import Request
        supported = ['application/xbel+xml', 'application/xml']
        tests = [('application/xbel+xml', 'application/xbel+xml'),
                ('application/xbel+xml; q=1', 'application/xbel+xml'),
                ('application/xml; q=1', 'application/xml'),
                ('application/*; q=1', 'application/xbel+xml'),
                ('*/*', 'application/xbel+xml')]

        for accept, get in tests:
            req = Request.blank('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/xbel+xml', 'text/xml']
        tests = [('text/*;q=0.5,*/*; q=0.1', 'text/xml'),
                ('text/html,application/atom+xml; q=0.9', None)]

        for accept, get in tests:
            req = Request.blank('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/json', 'text/html']
        tests = [
            ('application/json, text/javascript, */*', 'application/json'),
            ('application/json, text/html;q=0.9', 'application/json'),
        ]

        for accept, get in tests:
            req = Request.blank('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        offered = ['image/png', 'application/xml']
        tests = [
            ('image/png', 'image/png'),
            ('image/*', 'image/png'),
            ('image/*, application/xml', 'application/xml'),
        ]

        for accept, get in tests:
            req = Request.blank('/', accept=accept)
            self.assertEqual(req.accept.best_match(offered), get)

    def test_headers(self):
        from webtest import TestApp
        app = TestApp(simpleapp)
        headers = {
            'If-Modified-Since': 'Sat, 29 Oct 1994 19:43:31 GMT',
            'Cookie': 'var1=value1',
            'User-Agent': 'Mozilla 4.0 (compatible; MSIE)',
            'If-None-Match': '"etag001", "etag002"',
            'X-Requested-With': 'XMLHttpRequest',
            }
        res = app.get('/?foo=bar&baz', headers=headers)
        res.mustcontain(
            'if_modified_since: ' +
                'datetime.datetime(1994, 10, 29, 19, 43, 31, tzinfo=UTC)',
            "user_agent: 'Mozilla",
            'is_xhr: True',
            "cookies is {'var1': 'value1'}",
            "params is NestedMultiDict([('foo', 'bar'), ('baz', '')])",
            "if_none_match: <ETag etag001 or etag002>",
            )

    def test_bad_cookie(self):
        from webob import Request
        req = Request.blank('/')
        req.headers['Cookie'] = '070-it-:><?0'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = 'foo=bar'
        self.assertEqual(req.cookies, {'foo': 'bar'})
        req.headers['Cookie'] = '...'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = '=foo'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = ('dismiss-top=6; CP=null*; '
            'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
        self.assertEqual(req.cookies, {
            'CP':           u'null*',
            'PHPSESSID':    u'0a539d42abc001cdc762809248d4beed',
            'a':            u'42',
            'dismiss-top':  u'6'
        })
        req.headers['Cookie'] = 'fo234{=bar blub=Blah'
        self.assertEqual(req.cookies, {'blub': 'Blah'})

    def test_cookie_quoting(self):
        from webob import Request
        req = Request.blank('/')
        req.headers['Cookie'] = 'foo="?foo"; Path=/'
        self.assertEqual(req.cookies, {'foo': '?foo'})

    def test_path_quoting(self):
        from webob import Request
        path = '/:@&+$,/bar'
        req = Request.blank(path)
        self.assertEqual(req.path, path)
        self.assert_(req.url.endswith(path))

    def test_params(self):
        from webob import Request
        req = Request.blank('/?a=1&b=2')
        req.method = 'POST'
        req.body = 'b=3'
        self.assertEqual(req.params.items(),
                         [('a', '1'), ('b', '2'), ('b', '3')])
        new_params = req.params.copy()
        self.assertEqual(new_params.items(),
                         [('a', '1'), ('b', '2'), ('b', '3')])
        new_params['b'] = '4'
        self.assertEqual(new_params.items(), [('a', '1'), ('b', '4')])
        # The key name is \u1000:
        req = Request.blank('/?%E1%80%80=x',
                            decode_param_names=True, charset='UTF-8')
        self.assert_(req.decode_param_names)
        self.assert_(u'\u1000' in req.GET.keys())
        self.assertEqual(req.GET[u'\u1000'], 'x')

    def test_copy_body(self):
        from webob import Request
        req = Request.blank('/', method='POST', body='some text',
                            request_body_tempfile_limit=1)
        old_body_file = req.body_file_raw
        req.copy_body()
        self.assert_(req.body_file_raw is not old_body_file)
        req = Request.blank('/', method='POST',
                body_file=UnseekableInput('0123456789'), content_length=10)
        self.assert_(not hasattr(req.body_file_raw, 'seek'))
        old_body_file = req.body_file_raw
        req.make_body_seekable()
        self.assert_(req.body_file_raw is not old_body_file)
        self.assertEqual(req.body, '0123456789')
        old_body_file = req.body_file
        req.make_body_seekable()
        self.assert_(req.body_file_raw is old_body_file)
        self.assert_(req.body_file is old_body_file)

    def test_broken_seek(self):
        # copy() should work even when the input has a broken seek method
        from webob import Request
        req = Request.blank('/', method='POST',
                body_file=UnseekableInputWithSeek('0123456789'),
                content_length=10)
        self.assert_(hasattr(req.body_file_raw, 'seek'))
        self.assertRaises(IOError, req.body_file_raw.seek, 0)
        old_body_file = req.body_file
        req2 = req.copy()
        self.assert_(req2.body_file_raw is req2.body_file is not old_body_file)
        self.assertEqual(req2.body, '0123456789')

    def test_set_body(self):
        from webob import BaseRequest
        req = BaseRequest.blank('/', body='foo')
        self.assert_(req.is_body_seekable)
        self.assertEqual(req.body, 'foo')
        self.assertEqual(req.content_length, 3)
        del req.body
        self.assertEqual(req.body, '')
        self.assertEqual(req.content_length, 0)

    def test_broken_clen_header(self):
        # if the UA sends "content_length: ..' header (the name is wrong)
        # it should not break the req.headers.items()
        from webob import Request
        req = Request.blank('/')
        req.environ['HTTP_CONTENT_LENGTH'] = '0'
        req.headers.items()

    def test_nonstr_keys(self):
        # non-string env keys shouldn't break req.headers
        from webob import Request
        req = Request.blank('/')
        req.environ[1] = 1
        req.headers.items()


    def test_authorization(self):
        from webob import Request
        req = Request.blank('/')
        req.authorization = 'Digest uri="/?a=b"'
        self.assertEqual(req.authorization, ('Digest', {'uri': '/?a=b'}))

    def test_authorization2(self):
        from webob.descriptors import parse_auth_params
        for s, d in [
            ('x=y', {'x': 'y'}),
            ('x="y"', {'x': 'y'}),
            ('x=y,z=z', {'x': 'y', 'z': 'z'}),
            ('x=y, z=z', {'x': 'y', 'z': 'z'}),
            ('x="y",z=z', {'x': 'y', 'z': 'z'}),
            ('x="y", z=z', {'x': 'y', 'z': 'z'}),
            ('x="y,x", z=z', {'x': 'y,x', 'z': 'z'}),
        ]:
            self.assertEqual(parse_auth_params(s), d)


    def test_from_file(self):
        from webob import Request
        req = Request.blank('http://example.com:8000/test.html?params')
        self.equal_req(req)

        req = Request.blank('http://example.com/test2')
        req.method = 'POST'
        req.body = 'test=example'
        self.equal_req(req)

    def test_req_kw_none_val(self):
        from webob import Request
        request = Request({}, content_length=None)
        self.assert_('content-length' not in request.headers)
        self.assert_('content-type' not in request.headers)

    def test_env_keys(self):
        from webob import Request
        req = Request.blank('/')
        # SCRIPT_NAME can be missing
        del req.environ['SCRIPT_NAME']
        self.assertEqual(req.script_name, '')
        self.assertEqual(req.uscript_name, u'')

    def test_repr_nodefault(self):
        from webob.request import NoDefault
        nd = NoDefault
        self.assertEqual(repr(nd), '(No Default)')

    def test_request_noenviron_param(self):
        # Environ is a a mandatory not null param in Request.
        from webob import Request
        self.assertRaises(TypeError, Request, environ=None)

    def test_environ_getter(self):
        # Parameter environ_getter in Request is no longer valid and
        # should raise an error in case it's used
        from webob import Request
        class env(object):
            def __init__(self, env):
                self.env = env
            def env_getter(self):
                return self.env
        self.assertRaises(ValueError,
                          Request, environ_getter=env({'a':1}).env_getter)

    def test_unicode_errors(self):
        # Passing unicode_errors != NoDefault should assign value to
        # dictionary['unicode_errors'], else not
        from webob.request import NoDefault
        from webob import Request
        r = Request({'a':1}, unicode_errors='strict')
        self.assert_('unicode_errors' in r.__dict__)
        r = Request({'a':1}, unicode_errors=NoDefault)
        self.assert_('unicode_errors' not in r.__dict__)

    def test_charset_deprecation(self):
        # Any class that inherits from BaseRequest cannot define a
        # default_charset attribute.
        # Any class that inherits from BaseRequest cannot define a
        # charset attr that is instance of str
        from webob import BaseRequest
        from webob.request import AdhocAttrMixin
        class NewRequest(BaseRequest):
            default_charset = 'utf-8'
            def __init__(self, environ, **kw):
                super(NewRequest, self).__init__(environ, **kw)
        self.assertRaises(DeprecationWarning, NewRequest, {'a':1})
        class NewRequest(BaseRequest):
            charset = 'utf-8'
            def __init__(self, environ, **kw):
                super(NewRequest, self).__init__(environ, **kw)
        self.assertRaises(DeprecationWarning, NewRequest, {'a':1})
        class NewRequest(AdhocAttrMixin, BaseRequest):
            default_charset = 'utf-8'
            def __init__(self, environ, **kw):
                super(NewRequest, self).__init__(environ, **kw)
        self.assertRaises(DeprecationWarning, NewRequest, {'a':1})
        class NewRequest(AdhocAttrMixin, BaseRequest):
            charset = 'utf-8'
            def __init__(self, environ, **kw):
                super(NewRequest, self).__init__(environ, **kw)
        self.assertRaises(DeprecationWarning, NewRequest, {'a':1})

    def test_unexpected_kw(self):
        # Passed an attr in kw that does not exist in the class, should
        # raise an error
        # Passed an attr in kw that does exist in the class, should be ok
        from webob import Request
        self.assertRaises(TypeError,
                          Request, {'a':1}, this_does_not_exist=1)
        r = Request({'a':1}, **{'charset':'utf-8', 'server_name':'127.0.0.1'})
        self.assertEqual(getattr(r, 'charset', None), 'utf-8')
        self.assertEqual(getattr(r, 'server_name', None), '127.0.0.1')

    def test_body_file_setter(self):
        # If body_file is passed and it's instance of str, we define
        # environ['wsgi.input'] and content_length. Plus, while deleting the
        # attribute, we should get '' and 0 respectively
        from webob import Request
        r = Request({'a':1}, **{'body_file':'hello world'})
        self.assertEqual(r.environ['wsgi.input'].getvalue(), 'hello world')
        self.assertEqual(int(r.environ['CONTENT_LENGTH']), len('hello world'))
        del r.body_file
        self.assertEqual(r.environ['wsgi.input'].getvalue(), '')
        self.assertEqual(int(r.environ['CONTENT_LENGTH']), 0)

    def test_conttype_set_del(self):
        # Deleting content_type attr from a request should update the
        # environ dict
        # Assigning content_type should replace first option of the environ
        # dict
        from webob import Request
        r = Request({'a':1}, **{'content_type':'text/html'})
        self.assert_('CONTENT_TYPE' in r.environ)
        self.assert_(hasattr(r, 'content_type'))
        del r.content_type
        self.assert_('CONTENT_TYPE' not in r.environ)
        a = Request({'a':1},
                content_type='charset=utf-8;application/atom+xml;type=entry')
        self.assert_(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')
        a.content_type = 'charset=utf-8'
        self.assert_(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')

    def test_headers2(self):
        # Setting headers in init and later with a property, should update
        # the info
        from webob import Request
        headers = {'Host': 'www.example.com',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '115',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0'}
        r = Request({'a':1}, headers=headers)
        for i in headers.keys():
            self.assert_(i in r.headers and
                'HTTP_'+i.upper().replace('-', '_') in r.environ)
        r.headers = {'Server':'Apache'}
        self.assertEqual(r.environ.keys(), ['a',  'HTTP_SERVER'])

    def test_host_url(self):
        # Request has a read only property host_url that combines several
        # keys to create a host_url
        from webob import Request
        a = Request({'wsgi.url_scheme':'http'}, **{'host':'www.example.com'})
        self.assertEqual(a.host_url, 'http://www.example.com')
        a = Request({'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                                'server_port':5000})
        self.assertEqual(a.host_url, 'http://localhost:5000')
        a = Request({'wsgi.url_scheme':'https'}, **{'server_name':'localhost',
                                                    'server_port':443})
        self.assertEqual(a.host_url, 'https://localhost')

    def test_path_info_p(self):
        # Peek path_info to see what's coming
        # Pop path_info until there's nothing remaining
        from webob import Request
        a = Request({'a':1}, **{'path_info':'/foo/bar','script_name':''})
        self.assertEqual(a.path_info_peek(), 'foo')
        self.assertEqual(a.path_info_pop(), 'foo')
        self.assertEqual(a.path_info_peek(), 'bar')
        self.assertEqual(a.path_info_pop(), 'bar')
        self.assertEqual(a.path_info_peek(), None)
        self.assertEqual(a.path_info_pop(), None)

    def test_urlvars_property(self):
        # Testing urlvars setter/getter/deleter
        from webob import Request
        a = Request({'wsgiorg.routing_args':((),{'x':'y'}),
                    'paste.urlvars':{'test':'value'}})
        a.urlvars = {'hello':'world'}
        self.assert_('paste.urlvars' not in a.environ)
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ((), {'hello':'world'}))
        del a.urlvars
        self.assert_('wsgiorg.routing_args' not in a.environ)
        a = Request({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlvars, {'test':'value'})
        a.urlvars = {'hello':'world'}
        self.assertEqual(a.environ['paste.urlvars'], {'hello':'world'})
        del a.urlvars
        self.assert_('paste.urlvars' not in a.environ)

    def test_urlargs_property(self):
        # Testing urlargs setter/getter/deleter
        from webob import Request
        a = Request({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlargs, ())
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {'test':'value'}))
        a = Request({'a':1})
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {}))
        del a.urlargs
        self.assert_('wsgiorg.routing_args' not in a.environ)

    def test_host_property(self):
        # Testing host setter/getter/deleter
        from webob import Request
        a = Request({'wsgi.url_scheme':'http'}, server_name='localhost',
                                                server_port=5000)
        self.assertEqual(a.host, "localhost:5000")
        a.host = "localhost:5000"
        self.assert_('HTTP_HOST' in a.environ)
        del a.host
        self.assert_('HTTP_HOST' not in a.environ)

    def test_body_property(self):
        # Testing body setter/getter/deleter plus making sure body has a
        # seek method
        #a = Request({'a':1}, **{'CONTENT_LENGTH':'?'})
        # I cannot think of a case where somebody would put anything else
        # than a # numerical value in CONTENT_LENGTH, Google didn't help
        # either
        #self.assertEqual(a.body, '')
        # I need to implement a not seekable stringio like object.
        import string
        from webob import Request
        from webob import BaseRequest
        from cStringIO import StringIO
        class DummyIO(object):
            def __init__(self, txt):
                self.txt = txt
            def read(self, n=-1):
                return self.txt[0:n]
        limit = BaseRequest.request_body_tempfile_limit
        len_strl = limit / len(string.letters) + 1
        r = Request({'a':1}, body_file=DummyIO(string.letters * len_strl))
        self.assertEqual(len(r.body), len(string.letters*len_strl)-1)
        self.assertRaises(TypeError,
                          setattr, r, 'body', unicode('hello world'))
        r.body = None
        self.assertEqual(r.body, '')
        r = Request({'a':1}, body_file=DummyIO(string.letters))
        self.assert_(not hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assert_(hasattr(r.body_file_raw, 'seek'))
        r = Request({'a':1}, body_file=StringIO(string.letters))
        self.assert_(hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assert_(hasattr(r.body_file_raw, 'seek'))

    def test_repr_invalid(self):
        # If we have an invalid WSGI environ, the repr should tell us.
        from webob import BaseRequest
        req = BaseRequest({'CONTENT_LENGTH':'0', 'body':''})
        self.assert_(repr(req).endswith('(invalid WSGI environ)>'))

    def test_from_garbage_file(self):
        # If we pass a file with garbage to from_file method it should
        # raise an error plus missing bits in from_file method
        from cStringIO import StringIO
        from webob import BaseRequest
        self.assertRaises(ValueError,
                          BaseRequest.from_file, StringIO('hello world'))
        val_file = StringIO(
            "GET /webob/ HTTP/1.1\n"
            "Host: pythonpaste.org\n"
            "User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13)"
            "Gecko/20101206 Ubuntu/10.04 (lucid) Firefox/3.6.13\n"
            "Accept: "
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;"
            "q=0.8\n"
            "Accept-Language: en-us,en;q=0.5\n"
            "Accept-Encoding: gzip,deflate\n"
            "Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
            # duplicate on purpose
            "Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
            "Keep-Alive: 115\n"
            "Connection: keep-alive\n"
        )
        req = BaseRequest.from_file(val_file)
        self.assert_(isinstance(req, BaseRequest))
        self.assert_(not repr(req).endswith('(invalid WSGI environ)>'))
        val_file = StringIO(
            "GET /webob/ HTTP/1.1\n"
            "Host pythonpaste.org\n"
        )
        self.assertRaises(ValueError, BaseRequest.from_file, val_file)

    def test_from_string(self):
        # A valid request without a Content-Length header should still read
        # the full body.
        # Also test parity between as_string and from_string / from_file.
        import cgi
        from webob import BaseRequest
        req = BaseRequest.from_string(_test_req)
        self.assert_(isinstance(req, BaseRequest))
        self.assert_(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assert_('\n' not in req.http_version or '\r' in req.http_version)
        self.assert_(',' not in req.host)
        self.assert_(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assert_('foo' in req.body)
        bar_contents = "these are the contents of the file 'bar.txt'\r\n"
        self.assert_(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assert_(isinstance(bar, cgi.FieldStorage))
        self.assertEqual(bar.type, 'application/octet-stream')
        bar.file.seek(0)
        self.assertEqual(bar.file.read(), bar_contents)
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace('Content-Type',
                            'Content-Length: 337\r\nContent-Type')
        self.assertEqual(str(req), _test_req_copy)

        req2 = BaseRequest.from_string(_test_req2)
        self.assert_('host' not in req2.headers)
        self.assertEqual(str(req2), _test_req2.rstrip())
        self.assertRaises(ValueError,
                          BaseRequest.from_string, _test_req2 + 'xx')


    def test_blank(self):
        # BaseRequest.blank class method
        from webob import BaseRequest
        self.assertRaises(ValueError, BaseRequest.blank,
                    'www.example.com/foo?hello=world', None,
                    'www.example.com/foo?hello=world')
        self.assertRaises(ValueError, BaseRequest.blank,
                    'gopher.example.com/foo?hello=world', None,
                    'gopher://gopher.example.com')
        req = BaseRequest.blank('www.example.com/foo?hello=world', None,
                                'http://www.example.com')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:80')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/foo')
        self.assertEqual(req.environ.get('QUERY_STRING', None),
                         'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        req = BaseRequest.blank('www.example.com/secure?hello=world', None,
                                'https://www.example.com/secure')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:443')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/secure')
        self.assertEqual(req.environ.get('QUERY_STRING', None), 'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.environ.get('SCRIPT_NAME', None), '/secure')
        self.assertEqual(req.environ.get('SERVER_NAME', None),
                         'www.example.com')
        self.assertEqual(req.environ.get('SERVER_PORT', None), '443')

    def test_environ_from_url(self):
        # Generating an environ just from an url plus testing environ_add_POST
        from webob.request import environ_add_POST
        from webob.request import environ_from_url
        self.assertRaises(TypeError, environ_from_url,
                    'http://www.example.com/foo?bar=baz#qux')
        self.assertRaises(TypeError, environ_from_url,
                    'gopher://gopher.example.com')
        req = environ_from_url('http://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:80')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '80')
        req = environ_from_url('https://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')
        environ_add_POST(req, None)
        self.assert_('CONTENT_TYPE' not in req)
        self.assert_('CONTENT_LENGTH' not in req)
        environ_add_POST(req, {'hello':'world'})
        self.assert_(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'POST')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')
        self.assertEqual(req.get('CONTENT_LENGTH', None),'11')
        self.assertEqual(req.get('CONTENT_TYPE', None),
                         'application/x-www-form-urlencoded')
        self.assertEqual(req['wsgi.input'].read(), 'hello=world')


    def test_post_does_not_reparse(self):
        # test that there's no repetitive parsing is happening on every
        # req.POST access
        from webob import Request
        req = Request.blank('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        f0 = req.body_file_raw
        post1 = req.str_POST
        f1 = req.body_file_raw
        self.assert_(f1 is not f0)
        post2 = req.str_POST
        f2 = req.body_file_raw
        self.assert_(post1 is post2)
        self.assert_(f1 is f2)


    def test_middleware_body(self):
        from webob import Request
        def app(env, sr):
            sr('200 OK', [])
            return [env['wsgi.input'].read()]

        def mw(env, sr):
            req = Request(env)
            data = req.body_file.read()
            resp = req.get_response(app)
            resp.headers['x-data'] = data
            return resp(env, sr)

        req = Request.blank('/', method='PUT', body='abc')
        resp = req.get_response(mw)
        self.assertEqual(resp.body, 'abc')
        self.assertEqual(resp.headers['x-data'], 'abc')

    def test_body_file_noseek(self):
        from webob import Request
        req = Request.blank('/', method='PUT', body='abc')
        lst = [req.body_file.read(1) for i in range(3)]
        self.assertEqual(lst, ['a','b','c'])

    def test_cgi_escaping_fix(self):
        from webob import Request
        req = Request.blank('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        self.assertEqual(req.POST.keys(), ['%20%22"'])
        req.body_file.read()
        self.assertEqual(req.POST.keys(), ['%20%22"'])

    def test_content_type_none(self):
        from webob import Request
        r = Request.blank('/', content_type='text/html')
        self.assertEqual(r.content_type, 'text/html')
        r.content_type = None
        
    def test_charset_in_content_type(self):
        from webob import Request
        r = Request({'CONTENT_TYPE':'text/html;charset=ascii'})
        r.charset = 'shift-jis'
        self.assertEqual(r.charset, 'shift-jis')
        
    def test_body_file_seekable(self):
        from cStringIO import StringIO
        from webob import Request
        r = Request.blank('/')
        r.body_file = StringIO('body')
        self.assertEqual(r.body_file_seekable.read(), 'body')

    def test_request_init(self):
        # port from doctest (docs/reference.txt)
        from webob import Request
        req = Request.blank('/article?id=1')
        self.assertEqual(req.environ['HTTP_HOST'], 'localhost:80')
        self.assertEqual(req.environ['PATH_INFO'], '/article')
        self.assertEqual(req.environ['QUERY_STRING'], 'id=1')
        self.assertEqual(req.environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(req.environ['SCRIPT_NAME'], '')
        self.assertEqual(req.environ['SERVER_NAME'], 'localhost')
        self.assertEqual(req.environ['SERVER_PORT'], '80')
        self.assertEqual(req.environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assert_(isinstance(req.environ['wsgi.errors'], file))
        self.assert_(hasattr(req.environ['wsgi.input'], 'next'))
        self.assertEqual(req.environ['wsgi.multiprocess'], False)
        self.assertEqual(req.environ['wsgi.multithread'], False)
        self.assertEqual(req.environ['wsgi.run_once'], False)
        self.assertEqual(req.environ['wsgi.url_scheme'], 'http')
        self.assertEqual(req.environ['wsgi.version'], (1, 0))

        # Test body
        self.assert_(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, '')
        req.body = 'test'
        self.assert_(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, 'test')

        # Test method & URL
        self.assertEqual(req.method, 'GET')
        self.assertEqual(req.scheme, 'http')
        self.assertEqual(req.script_name, ''  # The base of the URL)
        req.script_name = '/blog'  # make it more interesting
        self.assertEqual(req.path_info, '/article')
        # Content-Type of the request body
        self.assertEqual(req.content_type, '')
        # The auth'ed user (there is none set)
        self.assert_(req.remote_user is None)
        self.assert_(req.remote_addr is None)
        self.assertEqual(req.host, 'localhost:80')
        self.assertEqual(req.host_url, 'http://localhost')
        self.assertEqual(req.application_url, 'http://localhost/blog')
        self.assertEqual(req.path_url, 'http://localhost/blog/article')
        self.assertEqual(req.url, 'http://localhost/blog/article?id=1')
        self.assertEqual(req.path, '/blog/article')
        self.assertEqual(req.path_qs, '/blog/article?id=1')
        self.assertEqual(req.query_string, 'id=1')
        self.assertEqual(req.relative_url('archive'),
                         'http://localhost/blog/archive')

        # Doesn't change request
        self.assertEqual(req.path_info_peek(), 'article')
        # Does change request!
        self.assertEqual(req.path_info_pop(), 'article')
        self.assertEqual(req.script_name, '/blog/article')
        self.assertEqual(req.path_info, '')

        # Headers
        req.headers['Content-Type'] = 'application/x-www-urlencoded'
        self.assertEqual(sorted(req.headers.items()),
                         [('Content-Length', '4'),
                          ('Content-Type', 'application/x-www-urlencoded'),
                          ('Host', 'localhost:80')])
        self.assertEqual(req.environ['CONTENT_TYPE'],
                         'application/x-www-urlencoded')

    def test_request_query_and_POST_vars(self):
        # port from doctest (docs/reference.txt)

        # Query & POST variables
        from webob import Request
        req = Request.blank('/test?check=a&check=b&name=Bob')
        from webob.multidict import TrackableMultiDict
        GET = TrackableMultiDict([('check', 'a'),
                                  ('check', 'b'),
                                  ('name', 'Bob')])
        self.assertEqual(req.str_GET, GET)
        self.assertEqual(req.str_GET['check'], 'b')
        self.assertEqual(req.str_GET.getall('check'), ['a', 'b'])
        self.assertEqual(req.str_GET.items(),
                         [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        from webob.multidict import NoVars
        self.assert_(isinstance(req.str_POST, NoVars))
        # NoVars can be read like a dict, but not written
        self.assertEqual(req.str_POST.items(), [])
        req.method = 'POST'
        req.body = 'name=Joe&email=joe@example.com'
        from webob.multidict import MultiDict
        self.assertEqual(req.str_POST,
                         MultiDict([('name', 'Joe'),
                                    ('email', 'joe@example.com')]))
        self.assertEqual(req.str_POST['name'], 'Joe')

        from webob.multidict import NestedMultiDict
        self.assert_(isinstance(req.str_params, NestedMultiDict))
        self.assertEqual(req.str_params.items(),
                         [('check', 'a'),
                          ('check', 'b'),
                          ('name', 'Bob'),
                          ('name', 'Joe'),
                          ('email', 'joe@example.com')])
        self.assertEqual(req.str_params['name'], 'Bob')
        self.assertEqual(req.str_params.getall('name'), ['Bob', 'Joe'])

    def test_request_put(self):
        from webob import Request
        from webob.multidict import MultiDict
        from webob.multidict import TrackableMultiDict
        req = Request.blank('/test?check=a&check=b&name=Bob')
        req.method = 'PUT'
        req.body = 'var1=value1&var2=value2&rep=1&rep=2'
        req.environ['CONTENT_LENGTH'] = str(len(req.body))
        req.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        GET = TrackableMultiDict([('check', 'a'),
                                  ('check', 'b'),
                                  ('name', 'Bob')])
        self.assertEqual(req.str_GET, GET)
        self.assertEqual(req.str_POST, MultiDict()
                                [('var1', 'value1'),
                                 ('var2', 'value2'),
                                 ('rep', '1'),
                                 ('rep', '2')])

        # Unicode
        req.charset = 'utf8'
        from webob.multidict import UnicodeMultiDict
        self.assert_(isinstance(req.GET, UnicodeMultiDict))
        self.assertEqual(req.GET.items(),
                         [('check', u'a'), ('check', u'b'), ('name', u'Bob')])

        # Cookies
        req.headers['Cookie'] = 'test=value'
        self.assert_(isinstance(req.cookies, UnicodeMultiDict))
        self.assertEqual(req.cookies.items(), [('test', u'value')])
        req.charset = None
        self.assertEqual(req.str_cookies, {'test': 'value'})

        # Accept-* headers
        self.assert_('text/html' in req.accept)
        req.accept = 'text/html;q=0.5, application/xhtml+xml;q=1'
        from webob.acceptparse import MIMEAccept
        self.assert_(isinstance(req.accept, MIMEAccept))
        self.assert_('text/html' in req.accept)

        self.assertEqual(req.accept.first_match(['text/html',
                                    'application/xhtml+xml']), 'text/html')
        self.assertEqual(req.accept.best_match(['text/html',
                                                'application/xhtml+xml']),
                         'application/xhtml+xml')
        self.assertEqual(req.accept.best_matches(),
                         ['application/xhtml+xml', 'text/html'])

        req.accept_language = 'es, pt-BR'
        self.assertEqual(req.accept_language.best_matches('en-US'),
                         ['es', 'pt-BR', 'en-US'])
        self.assertEqual(req.accept_language.best_matches('es'), ['es'])

        # Conditional Requests
        server_token = 'opaque-token'
        # shouldn't return 304
        self.assert_(not server_token in req.if_none_match)
        req.if_none_match = server_token
        from webob.etag import ETagMatcher
        self.assert_(isinstance(req.if_none_match, ETagMatcher))
        # You *should* return 304
        self.assert_(server_token in req.if_none_match)

        from webob import UTC
        from datetime import datetime
        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        self.assertEqual(req.headers['If-Modified-Since'],
                         'Sun, 01 Jan 2006 12:00:00 GMT')
        server_modified = datetime(2005, 1, 1, 12, 0, tzinfo=UTC)
        self.assert_(req.if_modified_since)
        self.assert_(req.if_modified_since >= server_modified)

        from webob.etag import _NoIfRange
        self.assert_(isinstance(req.if_range, _NoIfRange))
        self.assert_(req.if_range.match(etag='some-etag',
                     last_modified=datetime(2005, 1, 1, 12, 0)))
        req.if_range = 'opaque-etag'
        self.assert_(not req.if_range.match(etag='other-etag'))
        self.assert_(req.if_range.match(etag='opaque-etag'))

        from webob import Response
        res = Response(etag='opaque-etag')
        self.assert_(req.if_range.match_response(res))

        req.range = 'bytes=0-100'
        from webob.byterange import Range
        self.assert_(isinstance(req.range, Range))
        self.assertEqual(req.range.ranges, [(0, 101)])
        cr = req.range.content_range(length=1000)
        self.assertEqual((cr.start, cr.stop, cr.length), (0, 101, 1000))

        self.assert_(server_token in req.if_match)
        # No If-Match means everything is ok
        req.if_match = server_token
        self.assert_(server_token in req.if_match)
        # Still OK
        req.if_match = 'other-token'
        # Not OK, should return 412 Precondition Failed:
        self.assert_(not server_token in req.if_match)

    def equal_req(self, req):
        from cStringIO import StringIO
        from webob import Request
        input = StringIO(str(req))
        req2 = Request.from_file(input)
        self.assertEqual(req.url, req2.url)
        headers1 = dict(req.headers)
        headers2 = dict(req2.headers)
        self.assertEqual(int(headers1.get('Content-Length', '0')),
            int(headers2.get('Content-Length', '0')))
        if 'Content-Length' in headers1:
            del headers1['Content-Length']
        if 'Content-Length' in headers2:
            del headers2['Content-Length']
        self.assertEqual(headers1, headers2)
        self.assertEqual(req.body, req2.body)


def simpleapp(environ, start_response):
    from webob import Request
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    request = Request(environ)
    request.remote_user = 'bob'
    return [
        'Hello world!\n',
        'The get is %r' % request.str_GET,
        ' and Val is %s\n' % request.str_GET.get('name'),
        'The languages are: %s\n' %
            request.accept_language.best_matches('en-US'),
        'The accepttypes is: %s\n' %
            request.accept.best_match(['application/xml', 'text/html']),
        'post is %r\n' % request.str_POST,
        'params is %r\n' % request.str_params,
        'cookies is %r\n' % request.str_cookies,
        'body: %r\n' % request.body,
        'method: %s\n' % request.method,
        'remote_user: %r\n' % request.environ['REMOTE_USER'],
        'host_url: %r; application_url: %r; path_url: %r; url: %r\n' %
            (request.host_url,
             request.application_url,
             request.path_url,
             request.url),
        'urlvars: %r\n' % request.urlvars,
        'urlargs: %r\n' % (request.urlargs, ),
        'is_xhr: %r\n' % request.is_xhr,
        'if_modified_since: %r\n' % request.if_modified_since,
        'user_agent: %r\n' % request.user_agent,
        'if_none_match: %r\n' % request.if_none_match,
        ]



_cgi_escaping_body = '''--boundary
Content-Disposition: form-data; name="%20%22""


--boundary--'''

def _norm_req(s):
    return '\r\n'.join(s.strip().replace('\r','').split('\n'))

_test_req = """
POST /webob/ HTTP/1.0
Accept: */*
Cache-Control: max-age=0
Content-Type: multipart/form-data; boundary=----------------------------deb95b63e42a
Host: pythonpaste.org
User-Agent: UserAgent/1.0 (identifier-version) library/7.0 otherlibrary/0.8

------------------------------deb95b63e42a
Content-Disposition: form-data; name="foo"

foo
------------------------------deb95b63e42a
Content-Disposition: form-data; name="bar"; filename="bar.txt"
Content-type: application/octet-stream

these are the contents of the file 'bar.txt'

------------------------------deb95b63e42a--
"""

_test_req2 = """
POST / HTTP/1.0
Content-Length: 0

"""

_test_req = _norm_req(_test_req)
_test_req2 = _norm_req(_test_req2) + '\r\n'

class UnseekableInput(object):
    def __init__(self, data):
        self.data = data
        self.pos = 0
    def read(self, size=-1):
        if size == -1:
            t = self.data[self.pos:]
            self.pos = len(self.data)
            return t
        else:
            self.assert_(self.pos + size <= len(self.data))
            t = self.data[self.pos:self.pos+size]
            self.pos += size
            return t

class UnseekableInputWithSeek(UnseekableInput):
    def seek(self, pos, rel=0):
        raise IOError("Invalid seek!")
