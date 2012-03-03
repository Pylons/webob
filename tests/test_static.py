from datetime import date, datetime
from os.path import getmtime
import tempfile
from time import gmtime
import os
import string
import unittest

from nose.tools import eq_

from webob import static
from webob.compat import bytes_
from webob.request import Request, environ_from_url


def test_dataapp():
    def exec_app(app, *args, **kw):
        req = Request(environ_from_url('/'), *args, **kw)
        resp = req.get_response(app)
        if req.method == 'HEAD':
            resp._app_iter = ()
        return resp

    def _check_foo(r, status, body):
        eq_(r.status_int, status)
        eq_(r.accept_ranges, 'bytes')
        eq_(r.content_type, 'application/octet-stream')
        eq_(r.content_length, 3)
        eq_(r.body, bytes_(body))

    app = static.DataApp(b'foo')
    _check_foo(exec_app(app), 200, 'foo')
    _check_foo(exec_app(app, method='HEAD'), 200, '')
    eq_(exec_app(app, method='POST').status_int, 405)


def test_dataapp_last_modified():
    app = static.DataApp(b'data', last_modified=date(2005,1,1))

    req1 = Request(environ_from_url('/'), if_modified_since=date(2000,1,1))
    resp1 = req1.get_response(app)
    eq_(resp1.status_int, 200)
    eq_(resp1.content_length, 4)

    req2 = Request(environ_from_url('/'), if_modified_since=date(2010,1,1))
    resp2 = req2.get_response(app)
    eq_(resp2.status_int, 304)
    eq_(resp2.content_length, None)
    eq_(resp2.body, b'')

    app.body = b'update'

    resp3 = req1.get_response(app)
    eq_(resp3.status_int, 200)
    eq_(resp3.content_length, 6)
    eq_(resp3.body, b'update')

    resp4 = req2.get_response(app)
    eq_(resp4.status_int, 200)
    eq_(resp4.content_length, 6)
    eq_(resp4.body, b'update')


class TestFileApp(unittest.TestCase):
    def setUp(self):
        fp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        self.tempfile = fp.name
        fp.write(b"import this\n")
        fp.close()

    def tearDown(self):
        os.unlink(self.tempfile)

    def test_fileapp(self):
        app = static.FileApp(self.tempfile)
        req1 = Request(environ_from_url('/'))
        resp1 = req1.get_response(app)
        eq_(resp1.content_type, 'text/x-python')
        eq_(resp1.charset, 'UTF-8')
        eq_(resp1.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        self.assertNotEqual(None, app.cached_response)
        app._max_cache_size = 0
        app.update(force=True)
        resp2 = req1.get_response(app)
        eq_(resp2.content_type, 'text/x-python')
        eq_(resp2.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        req3 = Request(environ_from_url('/'), range=(7, 11))
        resp3 = req3.get_response(app)
        eq_(resp3.status_int, 206)
        eq_(tuple(resp3.content_range)[:2], (7, 11))
        eq_(resp3.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))
        eq_(resp3.body, b'this')
