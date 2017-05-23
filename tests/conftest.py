import pytest
import threading
import random
import logging
from contextlib import contextmanager

from wsgiref.simple_server import make_server
from wsgiref.simple_server import WSGIRequestHandler
from wsgiref.simple_server import WSGIServer
from wsgiref.simple_server import ServerHandler

log = logging.getLogger(__name__)
ServerHandler.handle_error = lambda: None


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args):
        pass

class QuietServer(WSGIServer):
    def handle_error(self, req, addr):
        pass

def _make_test_server(app):
    maxport = ((1 << 16) - 1)

    # we'll make 3 attempts to find a free port

    for i in range(3, 0, -1):
        try:
            port = random.randint(maxport // 2, maxport)
            server = make_server(
                'localhost',
                port,
                app,
                server_class=QuietServer,
                handler_class=QuietHandler,
            )
            server.timeout = 5
            return server
        except:
            if i == 1:
                raise


@pytest.fixture
def serve():
    @contextmanager
    def _serve(app):
        server = _make_test_server(app)
        try:
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

    return _serve
