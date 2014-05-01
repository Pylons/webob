from webob.request import Request
from nose.tools import eq_ as eq, assert_raises
from webob.compat import bytes_

def test_request_no_method():
    assert Request({}).method == 'GET'

def test_request_read_no_content_length():
    req, input = _make_read_tracked_request(b'abc', 'FOO')
    assert req.content_length is None
    assert req.body == b''
    assert not input.was_read

def test_request_read_no_content_length_POST():
    req, input = _make_read_tracked_request(b'abc', 'POST')
    assert req.content_length is None
    assert req.body == b'abc'
    assert input.was_read

def test_request_read_no_flag_but_content_length_is_present():
    req, input = _make_read_tracked_request(b'abc')
    req.content_length = 3
    assert req.body == b'abc'
    assert input.was_read

def test_request_read_no_content_length_but_flagged_readable():
    req, input = _make_read_tracked_request(b'abc')
    req.is_body_readable = True
    assert req.body == b'abc'
    assert input.was_read

def test_request_read_after_setting_body_file():
    req = _make_read_tracked_request()[0]
    input = req.body_file = ReadTracker(b'abc')
    assert req.content_length is None
    assert not req.is_body_seekable
    assert req.body == b'abc'
    # reading body made the input seekable and set the clen
    assert req.content_length == 3
    assert req.is_body_seekable
    assert input.was_read

def test_request_readlines():
    req = Request.blank('/', POST='a\n'*3)
    req.is_body_seekable = False
    eq(req.body_file.readlines(), [b'a\n'] * 3)

def test_request_delete_with_body():
    req = Request.blank('/', method='DELETE')
    assert not req.is_body_readable
    req.body = b'abc'
    assert req.is_body_readable
    assert req.body_file.read() == b'abc'


def _make_read_tracked_request(data='', method='PUT'):
    input = ReadTracker(data)
    env = {
        'REQUEST_METHOD': method,
        'wsgi.input': input,
    }
    return Request(env), input

class ReadTracker(object):
    """
        Helper object to determine if the input was read or not
    """
    def __init__(self, data):
        self.data = data
        self.was_read = False
    def read(self, size=-1):
        if size < 0:
            size = len(self.data)
        assert size == len(self.data)
        self.was_read = True
        return self.data


def test_limited_length_file_repr():
    req = Request.blank('/', POST='x')
    req.body_file_raw = 'dummy'
    req.is_body_seekable = False
    eq(repr(req.body_file.raw), "<LimitedLengthFile('dummy', maxlen=1)>")

def test_request_wrong_clen(is_seekable=False):
    tlen = 1<<20
    req = Request.blank('/', POST='x'*tlen)
    eq(req.content_length, tlen)
    req.body_file = _Helper_test_request_wrong_clen(req.body_file)
    eq(req.content_length, None)
    req.content_length = tlen + 100
    req.is_body_seekable = is_seekable
    eq(req.content_length, tlen+100)
    # this raises AssertionError if the body reading
    # trusts content_length too much
    assert_raises(IOError, req.copy_body)

def test_request_wrong_clen_seekable():
    test_request_wrong_clen(is_seekable=True)

class _Helper_test_request_wrong_clen(object):
    def __init__(self, f):
        self.f = f
        self.file_ended = False

    def read(self, *args):
        r = self.f.read(*args)
        if not r:
            if self.file_ended:
                raise AssertionError("Reading should stop after first empty string")
            self.file_ended = True
        return r


def test_disconnect_detection_cgi():
    data = 'abc'*(1<<20)
    req = Request.blank('/', POST={'file':('test-file', data)})
    req.is_body_seekable = False
    req.POST # should not raise exceptions

def test_disconnect_detection_hinted_readline():
    data = 'abc'*(1<<20)
    req = Request.blank('/', POST=data)
    req.is_body_seekable = False
    line = req.body_file.readline(1<<16)
    assert line
    assert bytes_(data).startswith(line)



def test_charset_in_content_type():
    # should raise no exception
    req = Request({
        'REQUEST_METHOD': 'POST',
        'QUERY_STRING':'a=b',
        'CONTENT_TYPE':'text/html;charset=ascii'
    })
    eq(req.charset, 'ascii')
    eq(dict(req.GET), {'a': 'b'})
    eq(dict(req.POST), {})
    req.charset = 'ascii' # no exception
    assert_raises(DeprecationWarning, setattr, req, 'charset', 'utf-8')

    # again no exception
    req = Request({
        'REQUEST_METHOD': 'POST',
        'QUERY_STRING':'a=b',
        'CONTENT_TYPE':'multipart/form-data;charset=ascii'
    })
    eq(req.charset, 'ascii')
    eq(dict(req.GET), {'a': 'b'})
    assert_raises(DeprecationWarning, getattr, req, 'POST')




def test_json_body_invalid_json():
    request = Request.blank('/', POST=b'{')
    assert_raises(ValueError, getattr, request, 'json_body')

def test_json_body_valid_json():
    request = Request.blank('/', POST=b'{"a":1}')
    eq(request.json_body, {'a':1})

def test_json_body_alternate_charset():
    import json
    body = (b'\xff\xfe{\x00"\x00a\x00"\x00:\x00 \x00"\x00/\x00\\\x00u\x006\x00d\x004\x001\x00'
        b'\\\x00u\x008\x008\x004\x00c\x00\\\x00u\x008\x00d\x008\x00b\x00\\\x00u\x005\x002\x00'
        b'b\x00f\x00"\x00}\x00'
    )
    request = Request.blank('/', POST=body)
    request.content_type = 'application/json; charset=utf-16'
    s = request.json_body['a']
    eq(s.encode('utf8'), b'/\xe6\xb5\x81\xe8\xa1\x8c\xe8\xb6\x8b\xe5\x8a\xbf')

def test_json_body_GET_request():
    request = Request.blank('/')
    assert_raises(ValueError, getattr, request, 'json_body')

def test_non_ascii_body_params():
    body = b'test=%D1%82%D0%B5%D1%81%D1%82'
    req = Request.blank('/', POST=body)
    # acessing params parses request body
    req.params
    # accessing body again makes the POST dict serialize again
    # make sure it can handle the non-ascii characters in the query
    eq(req.body, body)
