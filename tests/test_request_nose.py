from webob import Request


def test_request_read_no_content_length():
    req, input = _make_read_tracked_request('abc')
    assert req.content_length is None
    assert req.body == ''
    assert not input.was_read

def test_request_read_no_flag_but_content_length_is_present():
    req, input = _make_read_tracked_request('abc')
    req.content_length = 3
    assert req.body == 'abc'
    assert input.was_read

def test_request_read_no_content_length_but_flagged_readable():
    req, input = _make_read_tracked_request('abc')
    req.is_body_readable = True
    assert req.body == 'abc'
    assert input.was_read

def test_request_read_after_setting_body_file():
    req = _make_read_tracked_request()[0]
    input = req.body_file = ReadTracker('abc')
    assert req.content_length is None
    assert not req.is_body_seekable
    assert req.body == 'abc'
    # reading body made the input seekable and set the clen
    assert req.content_length == 3
    assert req.is_body_seekable
    assert input.was_read


def _make_read_tracked_request(data=''):
    input = ReadTracker(data)
    env = {
        'HTTP_METHOD': 'PUT',
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
