from webob import Request
from webtest import TestApp
from nose.tools import eq_, ok_, assert_raises

def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    request = Request(environ)
    request.remote_user = 'bob'
    return [
        'Hello world!\n',
        'The get is %r' % request.GET,
        ' and Val is %s\n' % request.GET.get('name'),
        'The languages are: %s\n' % request.accept_language.best_matches('en-US'),
        'The accepttypes is: %s\n' % request.accept.best_match(['application/xml', 'text/html']),
        'post is %r\n' % request.POST,
        'params is %r\n' % request.params,
        'cookies is %r\n' % request.cookies,
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
    print res
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
    assert "languages are: ['da', 'en-gb', 'en', 'en-US']" in res

    res = app.get('/', headers={'Accept-Language':'en-gb;q=0.8, da, en;q=0.7'})
    assert "languages are: ['da', 'en-gb', 'en', 'en-US']" in res

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

def test_copy():
    req = Request.blank('/', method='POST', body='some text', request_body_tempfile_limit=1)
    old_body_file = req.body_file
    req.copy_body()
    assert req.body_file is not old_body_file
    req = Request.blank('/', method='POST', body_file=UnseekableInput('0123456789'), content_length=10)
    assert not hasattr(req.body_file, 'seek')
    old_body_file = req.body_file
    req.make_body_seekable()
    assert req.body_file is not old_body_file
    assert req.body == '0123456789'
    old_body_file = req.body_file
    req.make_body_seekable()
    assert req.body_file is old_body_file


