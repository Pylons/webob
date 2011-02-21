from webob import Request, BaseRequest
from webob.request import (
    NoDefault, AdhocAttrMixin, environ_from_url, environ_add_POST
)
from webtest import TestApp
from nose.tools import eq_, ok_, assert_raises, assert_false
from cStringIO import StringIO
import string

def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    request = Request(environ)
    request.remote_user = 'bob'
    return [
        'Hello world!\n',
        'The get is %r' % request.str_GET,
        ' and Val is %s\n' % request.str_GET.get('name'),
        'The languages are: %s\n' % request.accept_language.best_matches('en-US'),
        'The accepttypes is: %s\n' % request.accept.best_match(['application/xml', 'text/html']),
        'post is %r\n' % request.str_POST,
        'params is %r\n' % request.str_params,
        'cookies is %r\n' % request.str_cookies,
        'body: %r\n' % request.body,
        'method: %s\n' % request.method,
        'remote_user: %r\n' % request.environ['REMOTE_USER'],
        'host_url: %r; application_url: %r; path_url: %r; url: %r\n' % (request.host_url, request.application_url, request.path_url, request.url),
        'urlvars: %r\n' % request.urlvars,
        'urlargs: %r\n' % (request.urlargs, ),
        'is_xhr: %r\n' % request.is_xhr,
        'if_modified_since: %r\n' % request.if_modified_since,
        'user_agent: %r\n' % request.user_agent,
        'if_none_match: %r\n' % request.if_none_match,
        ]

def test_gets():
    app = TestApp(simpleapp)
    res = app.get('/')
    assert 'Hello' in res
    assert "get is GET([])" in res
    assert "post is <NoVars: Not a form request>" in res

    res = app.get('/?name=george')
    res.mustcontain("get is GET([('name', 'george')])")
    res.mustcontain("Val is george")

def test_language_parsing():
    app = TestApp(simpleapp)
    res = app.get('/')
    assert "The languages are: ['en-US']" in res

    res = app.get('/', headers={'Accept-Language':'da, en-gb;q=0.8, en;q=0.7'})
    assert "languages are: ['da', 'en-gb', 'en-US']" in res

    res = app.get('/', headers={'Accept-Language':'en-gb;q=0.8, da, en;q=0.7'})
    assert "languages are: ['da', 'en-gb', 'en-US']" in res

def test_mime_parsing():
    app = TestApp(simpleapp)
    res = app.get('/', headers={'Accept':'text/html'})
    assert "accepttypes is: text/html" in res

    res = app.get('/', headers={'Accept':'application/xml'})
    assert "accepttypes is: application/xml" in res

    res = app.get('/', headers={'Accept':'application/xml,*/*'})
    assert "accepttypes is: application/xml" in res, res


def test_accept_best_match():
    assert not Request.blank('/').accept
    assert not Request.blank('/', headers={'Accept': ''}).accept
    req = Request.blank('/', headers={'Accept':'text/plain'})
    ok_(req.accept)
    assert_raises(ValueError, req.accept.best_match, ['*/*'])
    req = Request.blank('/', accept=['*/*','text/*'])
    eq_(req.accept.best_match(['application/x-foo', 'text/plain']), 'text/plain')
    eq_(req.accept.best_match(['text/plain', 'application/x-foo']), 'text/plain')
    req = Request.blank('/', accept=['text/plain', 'message/*'])
    eq_(req.accept.best_match(['message/x-foo', 'text/plain']), 'text/plain')
    eq_(req.accept.best_match(['text/plain', 'message/x-foo']), 'text/plain')

def test_from_mimeparse():
    # http://mimeparse.googlecode.com/svn/trunk/mimeparse.py
    supported = ['application/xbel+xml', 'application/xml']
    tests = [('application/xbel+xml', 'application/xbel+xml'),
             ('application/xbel+xml; q=1', 'application/xbel+xml'),
             ('application/xml; q=1', 'application/xml'),
             ('application/*; q=1', 'application/xbel+xml'),
             ('*/*', 'application/xbel+xml')]

    for accept, get in tests:
        req = Request.blank('/', headers={'Accept':accept})
        assert req.accept.best_match(supported) == get, (
            '%r generated %r instead of %r for %r' % (accept, req.accept.best_match(supported), get, supported))

    supported = ['application/xbel+xml', 'text/xml']
    tests = [('text/*;q=0.5,*/*; q=0.1', 'text/xml'),
             ('text/html,application/atom+xml; q=0.9', None)]

    for accept, get in tests:
        req = Request.blank('/', headers={'Accept':accept})
        assert req.accept.best_match(supported) == get, (
            'Got %r instead of %r for %r' % (req.accept.best_match(supported), get, supported))

    supported = ['application/json', 'text/html']
    tests = [('application/json, text/javascript, */*', 'application/json'),
             ('application/json, text/html;q=0.9', 'application/json')]

    for accept, get in tests:
        req = Request.blank('/', headers={'Accept':accept})
        assert req.accept.best_match(supported) == get, (
            '%r generated %r instead of %r for %r' % (accept, req.accept.best_match(supported), get, supported))

    offered = ['image/png', 'application/xml']
    tests = [
        ('image/png', 'image/png'),
        ('image/*', 'image/png'),
        ('image/*, application/xml', 'application/xml'),
    ]

    for accept, get in tests:
        req = Request.blank('/', accept=accept)
        eq_(req.accept.best_match(offered), get)

def test_headers():
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
        'if_modified_since: datetime.datetime(1994, 10, 29, 19, 43, 31, tzinfo=UTC)',
        "user_agent: 'Mozilla",
        'is_xhr: True',
        "cookies is {'var1': 'value1'}",
        "params is NestedMultiDict([('foo', 'bar'), ('baz', '')])",
        "if_none_match: <ETag etag001 or etag002>",
        )

def test_bad_cookie():
    req = Request.blank('/')
    req.headers['Cookie'] = '070-it-:><?0'
    assert req.cookies == {}
    req.headers['Cookie'] = 'foo=bar'
    assert req.cookies == {'foo': 'bar'}
    req.headers['Cookie'] = '...'
    assert req.cookies == {}
    req.headers['Cookie'] = '=foo'
    assert req.cookies == {}
    req.headers['Cookie'] = 'dismiss-top=6; CP=null*; PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42'
    eq_(req.cookies, {
        'CP':           u'null*',
        'PHPSESSID':    u'0a539d42abc001cdc762809248d4beed',
        'a':            u'42',
        'dismiss-top':  u'6'
    })
    req.headers['Cookie'] = 'fo234{=bar blub=Blah'
    assert req.cookies == {'blub': 'Blah'}

def test_cookie_quoting():
    req = Request.blank('/')
    req.headers['Cookie'] = 'foo="?foo"; Path=/'
    assert req.cookies == {'foo': '?foo'}

def test_params():
    req = Request.blank('/?a=1&b=2')
    req.method = 'POST'
    req.body = 'b=3'
    assert req.params.items() == [('a', '1'), ('b', '2'), ('b', '3')]
    new_params = req.params.copy()
    assert new_params.items() == [('a', '1'), ('b', '2'), ('b', '3')]
    new_params['b'] = '4'
    assert new_params.items() == [('a', '1'), ('b', '4')]
    # The key name is \u1000:
    req = Request.blank('/?%E1%80%80=x', decode_param_names=True, charset='UTF-8')
    assert req.decode_param_names
    assert u'\u1000' in req.GET.keys()
    assert req.GET[u'\u1000'] == 'x'

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
            assert self.pos + size <= len(self.data), (
                "Attempt to read past end (length=%s, position=%s, reading %s bytes)"
                % (len(self.data), self.pos, size))
            t = self.data[self.pos:self.pos+size]
            self.pos += size
            return t

def test_copy_body():
    req = Request.blank('/', method='POST', body='some text', request_body_tempfile_limit=1)
    old_body_file = req.body_file_raw
    req.copy_body()
    assert req.body_file_raw is not old_body_file
    req = Request.blank('/', method='POST', body_file=UnseekableInput('0123456789'), content_length=10)
    assert not hasattr(req.body_file_raw, 'seek')
    old_body_file = req.body_file_raw
    req.make_body_seekable()
    assert req.body_file_raw is not old_body_file
    assert req.body == '0123456789'
    old_body_file = req.body_file
    req.make_body_seekable()
    assert req.body_file_raw is old_body_file
    assert req.body_file is old_body_file

class UnseekableInputWithSeek(UnseekableInput):
    def seek(self, pos, rel=0):
        raise IOError("Invalid seek!")

def test_broken_seek():
    # copy() should work even when the input has a broken seek method
    req = Request.blank('/', method='POST', body_file=UnseekableInputWithSeek('0123456789'), content_length=10)
    assert hasattr(req.body_file_raw, 'seek')
    assert_raises(IOError, req.body_file_raw.seek, 0)
    old_body_file = req.body_file
    req2 = req.copy()
    assert req2.body_file_raw is req2.body_file is not old_body_file
    assert req2.body == '0123456789'

def test_set_body():
    req = BaseRequest.blank('/', body='foo')
    assert req.is_body_seekable
    eq_(req.body, 'foo')
    eq_(req.content_length, 3)
    del req.body
    eq_(req.body, '')
    eq_(req.content_length, 0)



def test_broken_clen_header():
    # if the UA sends "content_length: ..' header (the name is wrong)
    # it should not break the req.headers.items()
    req = Request.blank('/')
    req.environ['HTTP_CONTENT_LENGTH'] = '0'
    req.headers.items()


def test_nonstr_keys():
    # non-string env keys shouldn't break req.headers
    req = Request.blank('/')
    req.environ[1] = 1
    req.headers.items()


def test_authorization():
    req = Request.blank('/')
    req.authorization = 'Digest uri="/?a=b"'
    assert req.authorization == ('Digest', {'uri': '/?a=b'})

def test_authorization2():
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
        eq_(parse_auth_params(s), d)


def test_from_file():
    req = Request.blank('http://example.com:8000/test.html?params')
    equal_req(req)

    req = Request.blank('http://example.com/test2')
    req.method = 'POST'
    req.body = 'test=example'
    equal_req(req)

def equal_req(req):
    input = StringIO(str(req))
    req2 = Request.from_file(input)
    eq_(req.url, req2.url)
    headers1 = dict(req.headers)
    headers2 = dict(req2.headers)
    eq_(int(headers1.get('Content-Length', '0')),
        int(headers2.get('Content-Length', '0')))
    if 'Content-Length' in headers1:
        del headers1['Content-Length']
    if 'Content-Length' in headers2:
        del headers2['Content-Length']
    eq_(headers1, headers2)
    eq_(req.body, req2.body)

def test_req_kw_none_val():
    assert 'content-length' not in Request({}, content_length=None).headers
    assert 'content-type' not in Request({}, content_type=None).headers

def test_env_keys():
    req = Request.blank('/')
    # SCRIPT_NAME can be missing
    del req.environ['SCRIPT_NAME']
    eq_(req.script_name, '')
    eq_(req.uscript_name, u'')

def test_repr_nodefault():
    nd = NoDefault
    eq_(repr(nd), '(No Default)')

def test_request_noenviron_param():
    """Environ is a a mandatory not null param in Request"""
    assert_raises(TypeError, Request, environ=None)

def test_environ_getter():
    """
    Parameter environ_getter in Request is no longer valid and should raise
    an error in case it's used
    """
    class env(object):
        def __init__(self, env):
            self.env = env
        def env_getter(self):
            return self.env
    assert_raises(ValueError, Request, environ_getter=env({'a':1}).env_getter)

def test_unicode_errors():
    """
    Passing unicode_errors != NoDefault should assign value to
    dictionary['unicode_errors'], else not
    """
    r = Request({'a':1}, unicode_errors='strict')
    ok_('unicode_errors' in r.__dict__)
    r = Request({'a':1}, unicode_errors=NoDefault)
    ok_('unicode_errors' not in r.__dict__)

def test_charset_deprecation():
    """
    Any class that inherits from BaseRequest cannot define a default_charset
    attribute.
    Any class that inherits from BaseRequest cannot define a charset attr
    that is instance of str
    """
    class NewRequest(BaseRequest):
        default_charset = 'utf-8'
        def __init__(self, environ, **kw):
            super(NewRequest, self).__init__(environ, **kw)
    assert_raises(DeprecationWarning, NewRequest, {'a':1})
    class NewRequest(BaseRequest):
        charset = 'utf-8'
        def __init__(self, environ, **kw):
            super(NewRequest, self).__init__(environ, **kw)
    assert_raises(DeprecationWarning, NewRequest, {'a':1})
    class NewRequest(AdhocAttrMixin, BaseRequest):
        default_charset = 'utf-8'
        def __init__(self, environ, **kw):
            super(NewRequest, self).__init__(environ, **kw)
    assert_raises(DeprecationWarning, NewRequest, {'a':1})
    class NewRequest(AdhocAttrMixin, BaseRequest):
        charset = 'utf-8'
        def __init__(self, environ, **kw):
            super(NewRequest, self).__init__(environ, **kw)
    assert_raises(DeprecationWarning, NewRequest, {'a':1})

def test_unexpected_kw():
    """
    Passed an attr in kw that does not exist in the class, should raise an
    error
    Passed an attr in kw that does exist in the class, should be ok
    """
    assert_raises(TypeError, Request, {'a':1}, **{'this_does_not_exist':1})
    r = Request({'a':1}, **{'charset':'utf-8', 'server_name':'127.0.0.1'})
    eq_(getattr(r, 'charset', None), 'utf-8')
    eq_(getattr(r, 'server_name', None), '127.0.0.1')

def test_body_file_setter():
    """"
    If body_file is passed and it's instance of str, we define
    environ['wsgi.input'] and content_length. Plus, while deleting the
    attribute, we should get '' and 0 respectively
    """
    r = Request({'a':1}, **{'body_file':'hello world'})
    eq_(r.environ['wsgi.input'].getvalue(), 'hello world')
    eq_(int(r.environ['CONTENT_LENGTH']), len('hello world'))
    del r.body_file
    eq_(r.environ['wsgi.input'].getvalue(), '')
    eq_(int(r.environ['CONTENT_LENGTH']), 0)

def test_conttype_set_del():
    """
    Deleting content_type attr from a request should update the environ dict
    Assigning content_type should replace first option of the environ dict
    """
    r = Request({'a':1}, **{'content_type':'text/html'})
    ok_('CONTENT_TYPE' in r.environ)
    ok_(hasattr(r, 'content_type'))
    del r.content_type
    ok_('CONTENT_TYPE' not in r.environ)
    a = Request({'a':1},**{'content_type':'charset=utf-8;application/atom+xml;type=entry'})
    ok_(a.environ['CONTENT_TYPE']=='charset=utf-8;application/atom+xml;type=entry')
    a.content_type = 'charset=utf-8'
    ok_(a.environ['CONTENT_TYPE']=='charset=utf-8;application/atom+xml;type=entry')

def test_headers():
    """
    Setting headers in init and later with a property, should update the info
    """
    headers = {'Host': 'www.example.com',
               'Accept-Language': 'en-us,en;q=0.5',
               'Accept-Encoding': 'gzip,deflate',
               'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
               'Keep-Alive': '115',
               'Connection': 'keep-alive',
               'Cache-Control': 'max-age=0'}
    r = Request({'a':1}, headers=headers)
    for i in headers.keys():
        ok_(i in r.headers and
            'HTTP_'+i.upper().replace('-', '_') in r.environ)
    r.headers = {'Server':'Apache'}
    eq_(r.environ.keys(), ['a',  'HTTP_SERVER'])

def test_host_url():
    """
    Request has a read only property host_url that combines several keys to
    create a host_url
    """
    a = Request({'wsgi.url_scheme':'http'}, **{'host':'www.example.com'})
    eq_(a.host_url, 'http://www.example.com')
    a = Request({'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                               'server_port':5000})
    eq_(a.host_url, 'http://localhost:5000')
    a = Request({'wsgi.url_scheme':'https'}, **{'server_name':'localhost',
                                                'server_port':443})
    eq_(a.host_url, 'https://localhost')

def test_path_info_p():
    """
    Peek path_info to see what's coming
    Pop path_info until there's nothing remaining
    """
    a = Request({'a':1}, **{'path_info':'/foo/bar','script_name':''})
    eq_(a.path_info_peek(), 'foo')
    eq_(a.path_info_pop(), 'foo')
    eq_(a.path_info_peek(), 'bar')
    eq_(a.path_info_pop(), 'bar')
    eq_(a.path_info_peek(), None)
    eq_(a.path_info_pop(), None)

def test_urlvars_property():
    """
    Testing urlvars setter/getter/deleter
    """
    a = Request({'wsgiorg.routing_args':((),{'x':'y'}),
                 'paste.urlvars':{'test':'value'}})
    a.urlvars = {'hello':'world'}
    ok_('paste.urlvars' not in a.environ)
    eq_(a.environ['wsgiorg.routing_args'], ((), {'hello':'world'}))
    del a.urlvars
    ok_('wsgiorg.routing_args' not in a.environ)
    a = Request({'paste.urlvars':{'test':'value'}})
    eq_(a.urlvars, {'test':'value'})
    a.urlvars = {'hello':'world'}
    eq_(a.environ['paste.urlvars'], {'hello':'world'})
    del a.urlvars
    ok_('paste.urlvars' not in a.environ)

def test_urlargs_property():
    """
    Testing urlargs setter/getter/deleter
    """
    a = Request({'paste.urlvars':{'test':'value'}})
    eq_(a.urlargs, ())
    a.urlargs = {'hello':'world'}
    eq_(a.environ['wsgiorg.routing_args'], ({'hello':'world'},
                                            {'test':'value'}))
    a = Request({'a':1})
    a.urlargs = {'hello':'world'}
    eq_(a.environ['wsgiorg.routing_args'], ({'hello':'world'}, {}))
    del a.urlargs
    ok_('wsgiorg.routing_args' not in a.environ)

def test_host_property():
    """
    Testing host setter/getter/deleter
    """
    a = Request({'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                               'server_port':5000})
    eq_(a.host, "localhost:5000")
    a.host = "localhost:5000"
    ok_('HTTP_HOST' in a.environ)
    del a.host
    ok_('HTTP_HOST' not in a.environ)

def test_body_property():
    """
    Testing body setter/getter/deleter plus making sure body has a seek method
    """
    #a = Request({'a':1}, **{'CONTENT_LENGTH':'?'})
    # I cannot think of a case where somebody would put anything else than a
    # numerical value in CONTENT_LENGTH, Google didn't help either
    #eq_(a.body, '')
    # I need to implement a not seekable stringio like object.
    class DummyIO(object):
        def __init__(self, txt):
            self.txt = txt
        def read(self, n=-1):
            return self.txt[0:n]
    len_strl = BaseRequest.request_body_tempfile_limit/len(string.letters)+1
    r = Request({'a':1}, **{'body_file':DummyIO(string.letters*len_strl)})
    eq_(len(r.body), len(string.letters*len_strl)-1)
    assert_raises(TypeError, setattr, r, 'body', unicode('hello world'))
    r.body = None
    eq_(r.body, '')
    r = Request({'a':1}, **{'body_file':DummyIO(string.letters)})
    assert not hasattr(r.body_file_raw, 'seek')
    r.make_body_seekable()
    assert hasattr(r.body_file_raw, 'seek')
    r = Request({'a':1}, **{'body_file':StringIO(string.letters)})
    assert hasattr(r.body_file_raw, 'seek')
    r.make_body_seekable()
    assert hasattr(r.body_file_raw, 'seek')

def test_repr_invalid():
    """If we have an invalid WSGI environ, the repr should tell us"""
    req = BaseRequest({'CONTENT_LENGTH':'0', 'body':''})
    ok_(repr(req).endswith('(invalid WSGI environ)>'))

def test_from_file():
    """If we pass a file with garbage to from_file method it should raise an
    error plus missing bits in from_file method
    """
    assert_raises(ValueError, BaseRequest.from_file, StringIO('hello world'))
    val_file = StringIO(
        "GET /webob/ HTTP/1.1\n"
        "Host: pythonpaste.org\n"
        "User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13)"
        "Gecko/20101206 Ubuntu/10.04 (lucid) Firefox/3.6.13\n"
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;"
        "q=0.8\n"
        "Accept-Language: en-us,en;q=0.5\n"
        "Accept-Encoding: gzip,deflate\n"
        "Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
        # duplicate on porpouse
        "Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
        "Keep-Alive: 115\n"
        "Connection: keep-alive\n"
    )
    req = BaseRequest.from_file(val_file)
    assert isinstance(req, BaseRequest)
    assert_false(repr(req).endswith('(invalid WSGI environ)>'))
    val_file = StringIO(
        "GET /webob/ HTTP/1.1\n"
        "Host pythonpaste.org\n"
    )
    assert_raises(ValueError, BaseRequest.from_file, val_file)


def test_blank():
    """BaseRequest.blank class method"""
    assert_raises(ValueError, BaseRequest.blank,
                  'www.example.com/foo?hello=world', None,
                  'www.example.com/foo?hello=world')
    assert_raises(ValueError, BaseRequest.blank,
                  'gopher.example.com/foo?hello=world', None,
                  'gopher://gopher.example.com')
    req = BaseRequest.blank('www.example.com/foo?hello=world', None,
                            'http://www.example.com')
    ok_(req.environ.get('HTTP_HOST', None)== 'www.example.com:80' and
        req.environ.get('PATH_INFO', None)== 'www.example.com/foo' and
        req.environ.get('QUERY_STRING', None)== 'hello=world' and
        req.environ.get('REQUEST_METHOD', None)== 'GET')
    req = BaseRequest.blank('www.example.com/secure?hello=world', None,
                            'https://www.example.com/secure')
    ok_(req.environ.get('HTTP_HOST', None)== 'www.example.com:443' and
        req.environ.get('PATH_INFO', None)== 'www.example.com/secure' and
        req.environ.get('QUERY_STRING', None)== 'hello=world' and
        req.environ.get('REQUEST_METHOD', None)== 'GET' and
        req.environ.get('SCRIPT_NAME', None)== '/secure' and
        req.environ.get('SERVER_NAME', None)== 'www.example.com' and
        req.environ.get('SERVER_PORT', None)== '443')

def test_environ_from_url():
    """Generating an environ just from an url plus testing environ_add_POST"""
    assert_raises(TypeError, environ_from_url,
                  'http://www.example.com/foo?bar=baz#qux')
    assert_raises(TypeError, environ_from_url,
                  'gopher://gopher.example.com')
    req = environ_from_url('http://www.example.com/foo?bar=baz')
    ok_(req.get('HTTP_HOST', None)== 'www.example.com:80' and
        req.get('PATH_INFO', None)== '/foo' and
        req.get('QUERY_STRING', None)== 'bar=baz' and
        req.get('REQUEST_METHOD', None)== 'GET' and
        req.get('SCRIPT_NAME', None)== '' and
        req.get('SERVER_NAME', None)== 'www.example.com' and
        req.get('SERVER_PORT', None)== '80')
    req = environ_from_url('https://www.example.com/foo?bar=baz')
    ok_(req.get('HTTP_HOST', None)== 'www.example.com:443' and
        req.get('PATH_INFO', None)== '/foo' and
        req.get('QUERY_STRING', None)== 'bar=baz' and
        req.get('REQUEST_METHOD', None)== 'GET' and
        req.get('SCRIPT_NAME', None)== '' and
        req.get('SERVER_NAME', None)== 'www.example.com' and
        req.get('SERVER_PORT', None)== '443')
    environ_add_POST(req, None)
    assert_false('CONTENT_TYPE' in req and 'CONTENT_LENGTH' in req)
    environ_add_POST(req, {'hello':'world'})
    ok_(req.get('HTTP_HOST', None)== 'www.example.com:443' and
        req.get('PATH_INFO', None)== '/foo' and
        req.get('QUERY_STRING', None)== 'bar=baz' and
        req.get('REQUEST_METHOD', None)== 'POST' and
        req.get('SCRIPT_NAME', None)== '' and
        req.get('SERVER_NAME', None)== 'www.example.com' and
        req.get('SERVER_PORT', None)== '443' and
        req.get('CONTENT_LENGTH', None)=='11' and
        req.get('CONTENT_TYPE', None)=='application/x-www-form-urlencoded')
    eq_(req['wsgi.input'].read(), 'hello=world')


def test_post_does_not_reparse():
    # test that there's no repetitive parsing is happening on every req.POST access
    req = Request.blank('/',
        content_type='multipart/form-data; boundary=boundary',
        POST=_cgi_escaping_body
    )
    f0 = req.body_file_raw
    post1 = req.str_POST
    f1 = req.body_file_raw
    assert f1 is not f0
    post2 = req.str_POST
    f2 = req.body_file_raw
    assert post1 is post2
    assert f1 is f2




def test_cgi_escaping_fix():
    req = Request.blank('/',
        content_type='multipart/form-data; boundary=boundary',
        POST=_cgi_escaping_body
    )
    eq_(req.POST.keys(), [' "'])
    req.body_file.read()
    eq_(req.POST.keys(), [' "'])

_cgi_escaping_body = '''--boundary
Content-Disposition: form-data; name="%20%22"


--boundary--'''


