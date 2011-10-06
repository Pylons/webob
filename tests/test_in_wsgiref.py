import sys
import logging
import threading
import random
import socket
import cgi
from webob.request import Request
from webob.response import Response
from webob.compat import url_open
from webob.compat import bytes_
from webob.compat import reraise
from webob.compat import Queue
from webob.compat import Empty
from contextlib import contextmanager
from nose.tools import assert_raises
from nose.tools import eq_ as eq
from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIRequestHandler
from wsgiref.simple_server import WSGIServer
from wsgiref.simple_server import ServerHandler

log = logging.getLogger(__name__)

def test_request_reading():
    """
        Test actual request/response cycle in the presence of Request.copy()
        and other methods that can potentially hang.
    """
    with serve(_test_app_req_reading) as server:
        for key in _test_ops_req_read:
            resp = url_open(server.url+key, timeout=3)
            assert resp.read() == b"ok"

def _test_app_req_reading(env, sr):
    req = Request(env)
    log.debug('starting test operation: %s', req.path_info)
    test_op = _test_ops_req_read[req.path_info]
    test_op(req)
    log.debug('done')
    r = Response("ok")
    return r(env, sr)

_test_ops_req_read = {
    '/copy': lambda req: req.copy(),
    '/read-all': lambda req: req.body_file.read(),
    '/read-0': lambda req: req.body_file.read(0),
    '/make-seekable': lambda req: req.make_body_seekable()
}




# TODO: remove server logging for interrupted requests
# TODO: test interrupted body directly

def test_interrupted_request():
    with serve(_test_app_req_interrupt) as server:
        for path in _test_ops_req_interrupt:
            _send_interrupted_req(server, path)
            try:
                res = _global_res.get(timeout=1)
            except Empty:
                raise AssertionError("Error during test %s", path)
            if res is not None:
                print("Error during test:", path)
                reraise(res)

_global_res = Queue()

def _test_app_req_interrupt(env, sr):
    target_cl = 100000
    try:
        req = Request(env)
        cl = req.content_length
        if cl != target_cl:
            raise AssertionError(
                'request.content_length is %s instead of %s' % (cl, target_cl))
        op = _test_ops_req_interrupt[req.path_info]
        log.info("Running test: %s", req.path_info)
        assert_raises(IOError, op, req)
    except:
        _global_res.put(sys.exc_info())
    else:
        _global_res.put(None)
        sr('200 OK', [])
        return []

def _req_int_cgi(req):
    assert req.body_file.read(0) == b''
    #req.environ.setdefault('CONTENT_LENGTH', '0')
    d = cgi.FieldStorage(
        fp=req.body_file,
        environ=req.environ,
    )

def _req_int_readline(req):
    try:
        eq(req.body_file.readline(), b'a=b\n')
    except IOError:
        # too early to detect disconnect
        raise AssertionError("False disconnect alert")
    req.body_file.readline()


_test_ops_req_interrupt = {
    '/copy': lambda req: req.copy(),
    '/read-body': lambda req: req.body,
    '/read-post': lambda req: req.POST,
    '/read-all': lambda req: req.body_file.read(),
    '/read-too-much': lambda req: req.body_file.read(1<<22),
    '/readline': _req_int_readline,
    '/readlines': lambda req: req.body_file.readlines(),
    '/read-cgi': _req_int_cgi,
    '/make-seekable': lambda req: req.make_body_seekable()
}


def _send_interrupted_req(server, path='/'):
    sock = socket.socket()
    sock.connect(('localhost', server.server_port))
    f = sock.makefile('wb')
    f.write(bytes_(_interrupted_req % path))
    f.flush()
    f.close()
    sock.close()

_interrupted_req = (
    "POST %s HTTP/1.0\r\n"
    "content-type: application/x-www-form-urlencoded\r\n"
    "content-length: 100000\r\n"
    "\r\n"
)
_interrupted_req += 'a=b\nz='+'x'*10000


@contextmanager
def serve(app):
    server = _make_test_server(app)
    try:
        #worker = threading.Thread(target=server.handle_request)
        worker = threading.Thread(target=server.serve_forever)
        worker.setDaemon(True)
        worker.start()
        server.url = "http://localhost:%d" % server.server_port
        log.debug("server started on %s", server.url)
        yield server
    finally:
        log.debug("shutting server down")
        server.shutdown()
        worker.join(1)
        if worker.isAlive():
            log.warning('worker is hanged')
        else:
            log.debug("server stopped")


class QuietHanlder(WSGIRequestHandler):
    def log_request(self, *args):
        pass

ServerHandler.handle_error = lambda: None

class QuietServer(WSGIServer):
    def handle_error(self, req, addr):
        pass

def _make_test_server(app):
    maxport = ((1<<16)-1)
    # we'll make 3 attempts to find a free port
    for i in range(3, 0, -1):
        try:
            port = random.randint(maxport//2, maxport)
            server = make_server('localhost', port, app,
                server_class=QuietServer,
                handler_class=QuietHanlder
            )
            server.timeout = 5
            return server
        except:
            if i == 1:
                raise



if __name__ == '__main__':
    #test_request_reading()
    test_interrupted_request()

