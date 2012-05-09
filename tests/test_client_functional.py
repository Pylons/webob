import time
import urllib
from webob import Request, Response
from webob.dec import wsgify
from webob.client import SendRequest
from .test_in_wsgiref import serve
from nose.tools import assert_raises


@wsgify
def simple_app(req):
    data = {'headers': dict(req.headers),
            'body': req.text,
            'method': req.method,
            }
    return Response(json=data)


def test_client(client_app=None):
    with serve(simple_app) as server:
        req = Request.blank(server.url, method='POST', content_type='application/json',
                            json={'test': 1})
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status
        assert resp.json['headers']['Content-Type'] == 'application/json'
        assert resp.json['method'] == 'POST'
        # Test that these values get filled in:
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status
        req = Request.blank(server.url)
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        assert req.send(client_app).status_code == 200
        req.headers['Host'] = server.url.lstrip('http://')
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status
        del req.environ['SERVER_NAME']
        del req.environ['SERVER_PORT']
        del req.headers['Host']
        assert req.environ.get('SERVER_NAME') is None
        assert req.environ.get('SERVER_PORT') is None
        assert req.environ.get('HTTP_HOST') is None
        assert_raises(ValueError, req.send, client_app)
        req = Request.blank(server.url)
        req.environ['CONTENT_LENGTH'] = 'not a number'
        assert req.send(client_app).status_code == 200


def no_length_app(environ, start_response):
    start_response('200 OK', [('Content-type', 'text/plain')])
    return [b'ok']


def test_no_content_length(client_app=None):
    with serve(no_length_app) as server:
        req = Request.blank(server.url)
        resp = req.send(client_app)
        assert resp.status_code == 200, resp.status


@wsgify
def cookie_app(req):
    resp = Response('test')
    resp.headers.add('Set-Cookie', 'a=b')
    resp.headers.add('Set-Cookie', 'c=d')
    resp.headerlist.append(('X-Crazy', 'value\r\n  continuation'))
    return resp


def test_client_cookies(client_app=None):
    with serve(cookie_app) as server:
        req = Request.blank(server.url + '/?test')
        resp = req.send(client_app)
        assert resp.headers.getall('Set-Cookie') == ['a=b', 'c=d']
        assert resp.headers['X-Crazy'] == 'value, continuation', repr(resp.headers['X-Crazy'])


@wsgify
def slow_app(req):
    time.sleep(2)
    return Response('ok')


def test_client_slow(client_app=None):
    if client_app is None:
        client_app = SendRequest()
    if not client_app._timeout_supported(client_app.HTTPConnection):
        # timeout isn't supported
        return
    with serve(slow_app) as server:
        req = Request.blank(server.url)
        req.environ['webob.client.timeout'] = 0.1
        resp = req.send(client_app)
        assert resp.status_code == 504, resp.status
