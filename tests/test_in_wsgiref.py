from __future__ import with_statement
from webob import Request, Response
import sys, logging, threading, random, urllib2
from contextlib import contextmanager

log = logging.getLogger(__name__)

__test__ = (sys.version >= '2.6') # skip these tests on py2.5




def test_request_reading():
    """
        Test actual request/response cycle in the presence of Request.copy()
        and other methods that can potentially hang.
    """
    with serve(_test_app) as server:
        for key in _test_ops:
            resp = urllib2.urlopen(server.url+key, timeout=3)
            assert resp.read() == "ok"

def _test_app(env, sr):
    req = Request(env)
    log.debug('starting test operation: %s', req.path_info)
    test_op = _test_ops[req.path_info]
    test_op(req)
    log.debug('done')
    r = Response("ok")
    return r(env, sr)

_test_ops = {
    '/copy': lambda req: req.copy(),
    '/read-all': lambda req: req.body_file.read(),
    '/read-0': lambda req: req.body_file.read(0),
    '/make-seekable': lambda req: req.make_body_seekable()
}







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

def _make_test_server(app):
    from wsgiref.simple_server import make_server, WSGIRequestHandler
    class NoLogHanlder(WSGIRequestHandler):
        def log_request(self, *args):
            pass
    maxport = ((1<<16)-1)
    # we'll make 3 attempts to find a free port
    for i in range(3, 0, -1):
        try:
            port = random.randint(maxport/2, maxport)
            server = make_server('localhost', port, app,
                handler_class=NoLogHanlder
            )
            server.timeout = 5
            return server
        except:
            if i == 1:
                raise



if __name__ == '__main__':
    test_in_wsgiref()

