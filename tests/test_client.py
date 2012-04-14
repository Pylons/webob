from wsgiref.simple_server import make_server, WSGIRequestHandler
import threading
from webob import Request, Response
from webob.dec import wsgify
from webob.client import SendRequest


class SilentRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def start_server(app, requests=1, interface='127.0.0.1', port=0):
    def run_server():
        for i in range(requests):
            server.handle_request()
        server.server_close()
    server = make_server(interface, port, app, handler_class=SilentRequestHandler)
    port = server.socket.getsockname()[1]
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    return ('http://%s:%s' % (interface, port), t)


@wsgify
def simple_app(req):
    data = {'headers': dict(req.headers),
            'body': req.text,
            'method': req.method,
            }
    return Response(json=data)


def test_client(client_app=None):
    url, t = start_server(simple_app)
    req = Request.blank(url, method='POST', content_type='application/json',
                        json={'test': 1})
    resp = req.send()
    t.join()
    assert resp.status_code == 200, resp.status
    assert resp.json['headers']['Content-Type'] == 'application/json'
    assert resp.json['method'] == 'POST'
    req = Request.blank(url)
    resp = req.send()
    assert resp.status_code == 502, resp.status


@wsgify
def cookie_app(req):
    resp = Response('test')
    resp.headers.add('Set-Cookie', 'a=b')
    resp.headers.add('Set-Cookie', 'c=d')
    return resp


def test_client_cookies(client_app=None):
    url, t = start_server(cookie_app)
    req = Request.blank(url)
    resp = req.send(client_app)
    t.join()
    assert resp.headers.getall('Set-Cookie') == ['a=b', 'c=d']


def test_client_urllib3():
    try:
        import urllib3
    except:
        return
    test_client(SendRequest.with_urllib3())
