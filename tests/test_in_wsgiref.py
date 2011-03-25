from webob import Request, Response
import sys, logging, threading, random, urllib2

log = logging.getLogger(__name__)

def _make_test_app(test_op):
    def app(env, sr):
        req = Request(env)
        log.debug('starting test operation: %s', test_op)
        test_op(req)
        log.debug('done')
        r = Response("ok")
        return r(env, sr)
    return app

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

def _test_request(op):
    """Make a request to a wsgiref.simple_server and attempt to call
    op(req) in the application. Succeed if the operation does not
    time out."""
    app = _make_test_app(op)
    server = _make_test_server(app)
    worker = threading.Thread(target=server.handle_request)
    worker.setDaemon(True)
    worker.start()
    url = "http://localhost:%d/" % server.server_port
    try:
        resp = urllib2.urlopen(url, timeout=3)
        assert resp.read() == "ok"
    finally:
        server.socket.close()
        worker.join(1)
        if worker.isAlive():
            log.debug('worker is hanged')

if sys.version >= '2.6':
    def test_in_wsgiref():
        """
            Test actual request/response cycle in the presence of Request.copy()
            and other methods that can potentially hang.
        """
        yield (_test_request, lambda req: req.copy())
        yield (_test_request, lambda req: req.body_file.read())
        yield (_test_request, lambda req: req.body_file.read(0))
        yield (_test_request, lambda req: req.make_body_seekable())


    if __name__ == '__main__':
        for t,a in test_in_wsgiref():
            t(a)

