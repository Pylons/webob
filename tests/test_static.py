from pasteob import *
from pasteob.fileapp import *

from pasteob.test import *
from mext.test import *

from os.path import getmtime
from time import gmtime
from datetime import date, datetime

def _check_foo(r, status, body):
    eq(r.status_int, status)
    eq(r.accept_ranges, 'bytes')
    eq(r.content_type, 'application/octet-stream')
    eq(r.content_length, 3)
    eq(r.body, body)

def test_dataapp():
    app = DataApp('foo')
    _check_foo(test(app), 200, 'foo')
    _check_foo(test(app, method='HEAD'), 200, '')
    eq(test(app, method='POST').status_int, 405)

def test_dataapp_last_modified():
    app = DataApp('data', last_modified=date(2005,1,1))

    req1 = Request('/', if_modified_since=date(2000,1,1))
    resp1 = app << req1
    eq(resp1.status_int, 200)
    eq(resp1.content_length, 4)

    req2 = Request('/', if_modified_since=date(2010,1,1))
    resp2 = app << req2
    eq(resp2.status_int, 304)
    eq(resp2.content_length, None)
    eq(resp2.body, '')

    app.body = 'update'

    resp3 = app << req1
    eq(resp3.status_int, 200)
    eq(resp3.content_length, 6)
    eq(resp3.body, 'update')

    resp4 = app << req2
    eq(resp4.status_int, 200)
    eq(resp4.content_length, 6)
    eq(resp4.body, 'update')

    print resp1
    print resp2


def test_fileapp():
    app = FileApp(__file__)
    req1 = Request('/')
    resp1 = app << req1
    eq(resp1.content_type, 'text/x-python')
    eq(resp1.charset, 'UTF-8')
    eq(resp1.last_modified.timetuple(), gmtime(getmtime(__file__)))

    assert app.cached_response is not None
    app._max_cache_size = 0
    app.update(force=True)
    resp2 = app << req1
    eq(resp2.content_type, 'text/x-python')
    eq(resp2.last_modified.timetuple(), gmtime(getmtime(__file__)))

    req3 = Request('/', range=(5,10))
    resp3 = app << req3
    eq(resp3.status_int, 206)
    eq(tuple(resp3.content_range)[:2], (5,10))
    eq(resp3.last_modified.timetuple(), gmtime(getmtime(__file__)))
    eq(resp3.body, 'paste')

test_fileapp()
