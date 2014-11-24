from webob.middleware import forwarded
from webob import BaseRequest
from nose.tools import assert_raises


def test_parse_forwarded():
    assert (forwarded.parse('for="_gazonk"') ==
            [{'for': '_gazonk'}])
    assert (forwarded.parse('For="[2001:db8:cafe::17]:4711"') ==
            [{'for': '[2001:db8:cafe::17]:4711'}])
    assert (forwarded.parse('for=192.0.2.60;proto=http;by=203.0.113.43') ==
            [{'for': '192.0.2.60', 'proto': 'http', 'by': '203.0.113.43'}])
    assert (forwarded.parse('for=192.0.2.43, for=198.51.100.17') ==
            [{'for': '192.0.2.43'}, {'for': '198.51.100.17'}])
    assert (forwarded.parse(
        'for=192.0.2.43;by=203.0.113.43 , for=198.51.100.17') ==
            [{'for': '192.0.2.43', 'by': '203.0.113.43'},
             {'for': '198.51.100.17'}])


def test_parse_forwarded_empty():
    assert (forwarded.parse('') ==
            [])


def test_parse_forwarded_illegal_whitespace():
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for =_something')
    # a ForwardedError is a ValueError
    assert_raises(ValueError,
                  forwarded.parse, 'for =_something')
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for= _something')
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for=_something; by=192.51.100.17')


def test_parse_forwarded_illegal_token():
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'illegal=_something')


def test_parse_forwarded_illegal_duplicate_token():
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for=_something;for=_other')


def test_parse_forwarded_illegal_quoted_value():
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for="_gazonk')
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for=_gazonk"')
    assert_raises(forwarded.ForwardedError,
                  forwarded.parse, 'for=_gazonk""')


def test_forwarded_handler_host():
    def handle(request):
        assert request.host == 'www.example.com'
        assert request.host_port == '80'
        assert request.host_url == 'http://www.example.com'
        assert request.application_url == 'http://www.example.com'
        assert request.path_url == 'http://www.example.com/foo'
        assert request.url == 'http://www.example.com/foo'
        assert request.relative_url('bar') == 'http://www.example.com/bar'
        assert request.domain == 'www.example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Forwarded': 'host=www.example.com'}))


def test_forwarded_handler_host_port():
    def handle(request):
        assert request.host == 'www.example.com:8080'
        assert request.host_port == '8080'
        assert request.host_url == 'http://www.example.com:8080'
        assert request.application_url == 'http://www.example.com:8080'
        assert request.path_url == 'http://www.example.com:8080/foo'
        assert request.url == 'http://www.example.com:8080/foo'
        assert request.relative_url('bar') == 'http://www.example.com:8080/bar'
        assert request.domain == 'www.example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Forwarded': 'host=www.example.com:8080'}))


def test_forwarded_handler_proto():
    def handle(request):
        assert request.host == 'www.example.com'
        assert request.host_port == '443'
        assert request.scheme == 'https'
        assert request.host_url == 'https://www.example.com'
        assert request.application_url == 'https://www.example.com'
        assert request.path_url == 'https://www.example.com/foo'
        assert request.url == 'https://www.example.com/foo'
        assert request.relative_url('bar') == 'https://www.example.com/bar'
        assert request.domain == 'www.example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Forwarded': 'host=www.example.com;proto=https'}))


def test_forwarded_handler_multiple():
    def handle(request):
        assert request.host == 'b.example.com'
        assert request.host_port == '80'
        assert request.host_url == 'http://b.example.com'
        assert request.application_url == 'http://b.example.com'
        assert request.path_url == 'http://b.example.com/foo'
        assert request.url == 'http://b.example.com/foo'
        assert request.relative_url('bar') == 'http://b.example.com/bar'
        assert request.domain == 'b.example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Forwarded': 'host=a.example.com, host=b.example.com'}))


def test_forwarded_handler_only_proto():
    def handle(request):
        assert request.scheme == 'https'
        assert request.host == 'example.com'
        assert request.host_port == '443'
        assert request.host_url == 'https://example.com'
        assert request.application_url == 'https://example.com'
        assert request.path_url == 'https://example.com/foo'
        assert request.url == 'https://example.com/foo'
        assert request.relative_url('bar') == 'https://example.com/bar'
        assert request.domain == 'example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Host': 'example.com', 'Forwarded': 'proto=https'}))


def test_forwarded_handler_empty_header():
    def handle(request):
        assert request.scheme == 'http'
        assert request.host == 'example.com'
        assert request.host_port == '80'
        assert request.host_url == 'http://example.com'
        assert request.application_url == 'http://example.com'
        assert request.path_url == 'http://example.com/foo'
        assert request.url == 'http://example.com/foo'
        assert request.relative_url('bar') == 'http://example.com/bar'
        assert request.domain == 'example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Host': 'example.com', 'Forwarded': ''}))


def test_forwarded_handler_missing_header():
    def handle(request):
        assert request.scheme == 'http'
        assert request.host == 'example.com'
        assert request.host_port == '80'
        assert request.host_url == 'http://example.com'
        assert request.application_url == 'http://example.com'
        assert request.path_url == 'http://example.com/foo'
        assert request.url == 'http://example.com/foo'
        assert request.relative_url('bar') == 'http://example.com/bar'
        assert request.domain == 'example.com'

    wrapped_handle = forwarded.handler_factory(handle)

    wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Host': 'example.com'}))


def test_forwarded_handler_error():
    def handle(request):
        pass

    wrapped_handle = forwarded.handler_factory(handle)

    response = wrapped_handle(BaseRequest.blank(
        '/foo',
        headers={'Forwarded': 'blah=www.example.com'}))

    assert response.status_code == 400
