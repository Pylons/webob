from wsgiref.simple_server import make_server, WSGIRequestHandler
import threading
from webob import Request, Response
from webob.dec import wsgify

base_url = 'http://127.0.0.1:28594'


class SilentRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def start_server(app, requests=1, interface='127.0.0.1', port=28594):
    def run_server():
        server = make_server(interface, port, app, handler_class=SilentRequestHandler)
        for i in range(requests):
            server.handle_request()
        server.server_close()
    t = threading.Thread(target=run_server)
    t.daemon = True
    t.start()
    return t


@wsgify
def simple_app(req):
    data = {'headers': dict(req.headers),
            'body': req.text,
            'method': req.method,
            }
    return Response(json=data)


def test_client():
    req = Request.blank(base_url)
    resp = req.send()
    assert resp.status_code == 502, resp.status
    start_server(simple_app)
    req = Request.blank(base_url, method='POST', content_type='application/json',
                        json={'test': 1})
    resp = req.send()
    assert resp.status_code == 200, resp.status
    assert resp.json['headers']['Content-Type'] == 'application/json'
    assert resp.json['method'] == 'POST'


@wsgify
def cookie_app(req):
    resp = Response('test')
    resp.headers.add('Set-Cookie', 'a=b')
    resp.headers.add('Set-Cookie', 'c=d')
    return resp


def test_client_cookies():
    req = Request.blank(base_url)
    start_server(cookie_app)
    resp = req.send()
    assert resp.headers.getall('Set-Cookie') == ['a=b', 'c=d']
