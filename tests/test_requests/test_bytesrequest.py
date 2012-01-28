import unittest

from webob.compat import (
    text_type,
    bytes_,
    text_,
    native_,
    PY3,
    )

class TestBytesRequest(unittest.TestCase):
    # tests of methods of a bytesrequest which deal with http environment vars
    def _getTargetClass(self):
        from webob.request import BytesRequest
        return BytesRequest
        
    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_method(self):
        environ = {'REQUEST_METHOD': 'OPTIONS',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.method, b'OPTIONS')

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.http_version, b'1.1')

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.script_name, b'/script')

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_info, b'/path/info')

    def test_content_length_getter(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_length, 1234)

    def test_content_length_setter_w_str(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        req.content_length = '3456'
        self.assertEqual(req.content_length, 3456)

    def test_remote_user(self):
        environ = {'REMOTE_USER': 'phred',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_user, b'phred')

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_addr, b'1.2.3.4')

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.query_string, b'foo=bar&baz=bam')

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_name, b'somehost.tld')

    def test_server_port_getter(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_port, 6666)

    def test_server_port_setter_with_string(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        req.server_port = '6667'
        self.assertEqual(req.server_port, 6667)

    def test_uscript_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertTrue(isinstance(req.uscript_name, text_type))
        result = req.uscript_name
        self.assertEqual(result.__class__, text_type)
        self.assertEqual(result, '/script')

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        result = req.upath_info
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, '/path/info')

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        req.upath_info = text_('/another')
        result = req.upath_info
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, '/another')

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, b'application/xml+foobar')

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, b'application/xml+foobar')

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        self.assertEqual(req.content_type, b'')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        self.assertEqual(req.content_type, b'text/xml')
        self.assertEqual(environ['CONTENT_TYPE'], 'text/xml;charset="utf8"')

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, b'')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, b'')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        self.assertEqual(headers,
                        {'Content-Type': bytes_(CONTENT_TYPE),
                         'Content-Length': b'123'})

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        self.assertEqual(req.headers,
                        {'Qux': b'Spam'})
        self.assertEqual(environ['HTTP_QUX'], native_('Spam'))
        self.assertEqual(environ, {'HTTP_QUX': 'Spam'})

    def test_no_headers_deleter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        def _test():
            del req.headers
        self.assertRaises(AttributeError, _test)

    def test_client_addr_xff_singleval(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, b'192.168.1.1')

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, b'192.168.1.1')

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, b'192.168.1.1')

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, b'192.168.1.2')

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, None)

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'80')

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'80')

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'8888')

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'443')

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'443')

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'8888')

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, b'4333')

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'http://example.com')

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'http://example.com')

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'http://example.com:8888')

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'https://example.com')

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'https://example.com')

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'https://example.com:4333')

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, b'https://example.com:4333')

    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.application_url
        self.assertEqual(app_url.__class__, bytes)
        self.assertEqual(app_url, b'http://localhost/%C3%AB')

    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.path_url
        self.assertEqual(app_url.__class__, bytes)
        self.assertEqual(app_url, b'http://localhost/%C3%AB/%C3%AB')

    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.path
        self.assertEqual(app_url.__class__, bytes)
        self.assertEqual(app_url, b'/%C3%AB/%C3%AB')

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, b'/script/path/info')

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, b'/script/path/info?foo=bar&baz=bam')

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url, b'http://example.com/script/path/info')

    def test_url_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url,
                         b'http://example.com/script/path/info?foo=bar&baz=bam')

    def test_relative_url_to_app_true_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('other/page', True),
                         b'http://example.com/script/other/page')

    def test_relative_url_to_app_true_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('/other/page', True),
                         b'http://example.com/other/page')

    def test_relative_url_to_app_false_other_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('/other/page', False),
                         b'http://example.com/other/page')

    def test_relative_url_to_app_false_other_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.relative_url('other/page', False),
                         b'http://example.com/script/path/other/page')

    def test_path_info_pop_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')

    def test_path_info_pop_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, b'')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_pop_non_empty_no_pattern(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, b'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_non_empty_w_pattern_miss(self):
        import re
        PATTERN = re.compile(b'miss')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path/info')

    def test_path_info_pop_non_empty_w_pattern_hit(self):
        import re
        PATTERN = re.compile(b'path')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, b'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_skips_empty_elements(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '//path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, b'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script//path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_peek_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_peek_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, b'')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/')

    def test_path_info_peek_non_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, b'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path')

    def test_is_xhr_no_header(self):
        req = self._makeOne({})
        self.assertTrue(not req.is_xhr)

    def test_is_xhr_header_miss(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'notAnXMLHTTPRequest'}
        req = self._makeOne(environ)
        self.assertTrue(not req.is_xhr)

    def test_is_xhr_header_hit(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = self._makeOne(environ)
        self.assertTrue(req.is_xhr)

    # host
    def test_host_getter_w_HTTP_HOST(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, b'example.com:8888')

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, b'example.com:8888')

    def test_host_setter(self):
        environ = {}
        req = self._makeOne(environ)
        req.host = 'example.com:8888'
        self.assertEqual(environ['HTTP_HOST'], 'example.com:8888')

    def test_host_deleter_hit(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        del req.host
        self.assertTrue('HTTP_HOST' not in environ)

    def test_host_deleter_miss(self):
        environ = {}
        req = self._makeOne(environ)
        del req.host # doesn't raise

    def test_encget_raises_without_default(self):
        inst = self._makeOne({})
        self.assertRaises(KeyError, inst.encget, 'a')

    def test_encget_doesnt_raises_with_default(self):
        inst = self._makeOne({})
        self.assertEqual(inst.encget('a', None), None)

    def test_encget_with_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a', encattr='url_encoding'), b'\xc3\xab')

    def test_encget_no_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a'), b'\xc3\xab')

    def test_decode_default(self):
        inst = self._makeOne({})
        self.assertEqual(inst.decode_default(None), None)

    def test_decode_default_bytes(self):
        inst = self._makeOne({})
        val = inst.decode_default(b'123')
        self.assertEqual(val.__class__, bytes)
        self.assertEqual(val, bytes_('123'))

    def test_decode_default_text(self):
        inst = self._makeOne({})
        val = inst.decode_default(text_('123'))
        self.assertEqual(val.__class__, bytes)
        self.assertEqual(val, bytes_('123'))

    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        self.assertEqual(result.__class__, bytes)
        self.assertEqual(result, b'http://localhost/%C3%AB/a')

    def test_header_getter(self):
        if PY3:
            val = b'abc'.decode('latin-1')
        else:
            val = b'abc'
        inst = self._makeOne({'HTTP_FLUB':val})
        result = inst.headers['Flub']
        self.assertEqual(result.__class__, bytes)
        self.assertEqual(result, b'abc')

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        self.assertEqual(inst.json_body, {'a':'1'})

    def test_host_get_w_http_host(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        self.assertEqual(result.__class__, bytes)
        self.assertEqual(result, b'example.com')

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        self.assertEqual(result.__class__, bytes)
        self.assertEqual(result, b'example.com:80')

