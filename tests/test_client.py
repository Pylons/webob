import unittest
import io
import socket

class TestSendRequest(unittest.TestCase):
    def _getTargetClass(self):
        from webob.client import SendRequest
        return SendRequest

    def _makeOne(self, **kw):
        cls = self._getTargetClass()
        return cls(**kw)

    def _makeEnviron(self, extra=None):
        environ = {
            'wsgi.url_scheme':'http',
            'SERVER_NAME':'localhost',
            'HTTP_HOST':'localhost:80',
            'SERVER_PORT':'80',
            'wsgi.input':io.BytesIO(),
            'CONTENT_LENGTH':0,
            'REQUEST_METHOD':'GET',
            }
        if extra is not None:
            environ.update(extra)
        return environ

    def test___call___unknown_scheme(self):
        environ = self._makeEnviron({'wsgi.url_scheme':'abc'})
        inst = self._makeOne()
        self.assertRaises(ValueError, inst, environ, None)

    def test___call___gardenpath(self):
        environ = self._makeEnviron()
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])

    def test___call___no_servername_no_http_host(self):
        environ = self._makeEnviron()
        del environ['SERVER_NAME']
        del environ['HTTP_HOST']
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        self.assertRaises(ValueError, inst, environ, None)

    def test___call___no_servername_colon_not_in_host_http(self):
        environ = self._makeEnviron()
        del environ['SERVER_NAME']
        environ['HTTP_HOST'] = 'localhost'
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_PORT'], '80')

    def test___call___no_servername_colon_not_in_host_https(self):
        environ = self._makeEnviron()
        del environ['SERVER_NAME']
        environ['HTTP_HOST'] = 'localhost'
        environ['wsgi.url_scheme'] = 'https'
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPSConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(environ['SERVER_NAME'], 'localhost')
        self.assertEqual(environ['SERVER_PORT'], '443')

    def test___call___no_content_length(self):
        environ = self._makeEnviron()
        del environ['CONTENT_LENGTH']
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])

    def test___call___with_webob_client_timeout_and_timeout_supported(self):
        environ = self._makeEnviron()
        environ['webob.client.timeout'] = 10
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(conn_factory.kw, {'timeout':10})

    def test___call___bad_content_length(self):
        environ = self._makeEnviron({'CONTENT_LENGTH':'abc'})
        response = DummyResponse('msg')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])

    def test___call___with_socket_timeout(self):
        environ = self._makeEnviron()
        response = socket.timeout()
        response.msg = 'msg'
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '504 Gateway Timeout')
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertTrue(list(iterable)[0].startswith(b'504'))

    def test___call___with_socket_error_neg2(self):
        environ = self._makeEnviron()
        response = socket.error(-2)
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '502 Bad Gateway')
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertTrue(list(iterable)[0].startswith(b'502'))

    def test___call___with_socket_error_ENODATA(self):
        import errno
        environ = self._makeEnviron()
        if not hasattr(errno, 'ENODATA'):
            # no ENODATA on win
            return
        response = socket.error(errno.ENODATA)
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '502 Bad Gateway')
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertTrue(list(iterable)[0].startswith(b'502'))

    def test___call___with_socket_error_unknown(self):
        environ = self._makeEnviron()
        response = socket.error('nope')
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '502 Bad Gateway')
            inst.start_response_called = True
        self.assertRaises(socket.error, inst, environ, start_response)

    def test___call___nolength(self):
        environ = self._makeEnviron()
        response = DummyResponse('msg', None)
        conn_factory = DummyConnectionFactory(response)
        inst = self._makeOne(HTTPConnection=conn_factory)
        def start_response(status, headers):
            self.assertEqual(status, '200 OK')
            self.assertEqual(headers, [])
            inst.start_response_called = True
        iterable = inst(environ, start_response)
        self.assertTrue(inst.start_response_called)
        self.assertEqual(list(iterable), [b'foo'])
        self.assertEqual(response.length, None)

class DummyMessage(object):
    def __init__(self, msg):
        self.msg = msg
        self.headers = self._headers = {}

class DummyResponse(object):
    def __init__(self, msg, headerval='10'):
        self.msg = DummyMessage(msg)
        self.status = '200'
        self.reason = 'OK'
        self.headerval = headerval

    def getheader(self, name):
        return self.headerval

    def read(self, length=None):
        self.length = length
        return b'foo'

class DummyConnectionFactory(object):
    def __init__(self, result=None):
        self.result = result
        self.closed = False

    def __call__(self, hostport, **kw):
        self.hostport = hostport
        self.kw = kw
        self.request = DummyRequestFactory(hostport, **kw)
        return self

    def getresponse(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def close(self):
        self.closed = True

class DummyRequestFactory(object):
    def __init__(self, hostport, **kw):
        self.hostport = hostport
        self.kw = kw

    def __call__(self, method, path, body, headers):
        return self
