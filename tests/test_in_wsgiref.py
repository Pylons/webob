"""
Test actual request/response cycle in the presence of Request.copy()
and other methods that can potentially hang.

Daniel Holth <dholth@fastmail.fm>
"""

from webob import Request, Response
from wsgiref.simple_server import make_server
from threading import Thread

import random
import urllib2
import logging

log = logging.getLogger(__name__)

def serve(server):
    server.timeout = 1
    server.handle_request()

def Application(fut):
    def application(environ, start_response):
        r = Request(environ)
        fut(r)
        log.debug('copied request')
        return Response(content_type="text/plain", body="Success!")(environ, start_response)
    return application

def do_request(fut):
    """Make a request to a wsgiref.simple_server and attempt to call
    fut(request) in the application. Succeed if the operation does not
    time out."""

    app = Application(fut)

    TRIES=3 # in case the random port is in use.
    for i in range(TRIES):
        try:
            port = random.randint(((1<<16)-1)/2, (1<<16)-1)            
            server = make_server('localhost', port, app)
        except:
            if i == (TRIES-1):
                raise

    worker = Thread(target=serve, args=(server,))
    worker.daemon = True
    worker.start()

    try:
        assert urllib2.urlopen("http://localhost:%d/" % port, timeout=2).read() == "Success!"
    finally:
        server.socket.close()
        worker.join(1)
        if worker.is_alive():
            log.debug('worker is hanged')

def test_in_wsgiref():
    def body_file_read(self):
        return self.body_file.read()
    def body_file_read_0(self):
        return self.body_file.read(0)
    def make_body_seekable(self):
        return self.make_body_seekable()
    for fut in [Request.copy, body_file_read, body_file_read_0, make_body_seekable]:
        yield (do_request, fut)

