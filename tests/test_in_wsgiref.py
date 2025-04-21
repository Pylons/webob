import logging
from queue import Empty, Queue
import socket
import sys
from urllib.request import urlopen as url_open

import multipart
import pytest

from webob.request import Request
from webob.response import Response
from webob.util import bytes_

log = logging.getLogger(__name__)


@pytest.mark.usefixtures("serve")
def test_request_reading(serve):
    """
    Test actual request/response cycle in the presence of Request.copy()
    and other methods that can potentially hang.
    """
    with serve(_test_app_req_reading) as server:
        for key in _test_ops_req_read:
            resp = url_open(server.url + key, timeout=3)
            assert resp.read() == b"ok"


def _test_app_req_reading(env, sr):
    req = Request(env)
    log.debug("starting test operation: %s", req.path_info)
    test_op = _test_ops_req_read[req.path_info]
    test_op(req)
    log.debug("done")
    r = Response("ok")

    return r(env, sr)


_test_ops_req_read = {
    "/copy": lambda req: req.copy(),
    "/read-all": lambda req: req.body_file.read(),
    "/read-0": lambda req: req.body_file.read(0),
    "/make-seekable": lambda req: req.make_body_seekable(),
}


@pytest.mark.usefixtures("serve")
def test_interrupted_request(serve):
    with serve(_test_app_req_interrupt) as server:
        for path in _test_ops_req_interrupt:
            _send_interrupted_req(server, path)
            try:
                res = _global_res.get(timeout=1)
            except Empty:
                raise AssertionError("Error during test %s", path)

            if res is not None:
                print("Error during test:", path)
                raise res[0](res[1]).with_traceback(res[2])


_global_res = Queue()


def _test_app_req_interrupt(env, sr):
    target_cl = 100000
    try:
        req = Request(env)
        cl = req.content_length

        if cl != target_cl:
            raise AssertionError(
                f"request.content_length is {cl} instead of {target_cl}"
            )
        op = _test_ops_req_interrupt[req.path_info]
        log.info("Running test: %s", req.path_info)
        with pytest.raises(IOError):
            op(req)
    except BaseException:
        _global_res.put(sys.exc_info())
    else:
        _global_res.put(None)
        sr("200 OK", [])

        return []


def _req_int_cgi(req):
    assert req.body_file.read(0) == b""
    multipart.MultipartParser(req.body_file, "foobar").parts()


def _req_int_readline(req):
    try:
        assert req.body_file.readline() == b"a=b\n"
    except OSError:
        # too early to detect disconnect
        raise AssertionError("False disconnect alert")
    req.body_file.readline()


_test_ops_req_interrupt = {
    "/copy": lambda req: req.copy(),
    "/read-body": lambda req: req.body,
    "/read-post": lambda req: req.POST,
    "/read-all": lambda req: req.body_file.read(),
    "/read-too-much": lambda req: req.body_file.read(1 << 22),
    "/readline": _req_int_readline,
    "/readlines": lambda req: req.body_file.readlines(),
    "/read-cgi": _req_int_cgi,
    "/make-seekable": lambda req: req.make_body_seekable(),
}


def _send_interrupted_req(server, path="/"):
    sock = socket.socket()
    sock.connect(("localhost", server.server_port))
    f = sock.makefile("wb")
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
_interrupted_req += "a=b\nz=" + "x" * 10000
