import collections
import unittest, warnings
from webob.request import Request
from webob.request import BaseRequest
from webob.datetime_utils import UTC
from webob.compat import text_type
from webob.compat import bytes_
from webob.compat import text_
from io import BytesIO
from io import StringIO

_marker = object()

warnings.showwarning = lambda *args, **kw: None

class BaseRequestTests(unittest.TestCase):
    def test_ctor_environ_getter_raises_WTF(self):
        self.assertRaises(TypeError, Request, {}, environ_getter=object())

    def test_ctor_wo_environ_raises_WTF(self):
        self.assertRaises(TypeError, Request, None)

    def test_ctor_w_environ(self):
        environ = {}
        req = BaseRequest(environ)
        self.assertEqual(req.environ, environ)

    def test_ctor_w_non_utf8_charset(self):
        environ = {}
        self.assertRaises(DeprecationWarning, BaseRequest, environ,
                          charset='latin-1')

    def test_ctor_w_unicode_errors(self):
        with warnings.catch_warnings(record=True) as w:
            BaseRequest({}, unicode_errors=True)
        self.assertEqual(len(w), 1)

    def test_ctor_w_decode_param_names(self):
        with warnings.catch_warnings(record=True) as w:
            BaseRequest({}, decode_param_names=True)
        self.assertEqual(len(w), 1)

    def test_body_file_getter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = BaseRequest(environ)
        self.assert_(req.body_file is not INPUT)

    def test_body_file_getter_seekable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
            'webob.is_body_seekable': True,
        }
        req = BaseRequest(environ)
        self.assert_(req.body_file is INPUT)

    def test_body_file_getter_cache(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = BaseRequest(environ)
        self.assert_(req.body_file is req.body_file)

    def test_body_file_getter_unreadable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'REQUEST_METHOD': 'FOO'}
        req = BaseRequest(environ)
        assert req.body_file_raw is INPUT
        assert req.body_file is not INPUT
        assert req.body_file.read() == b''

    def test_body_file_setter_w_string(self):
        req = BaseRequest.blank('/')
        self.assertRaises(DeprecationWarning, setattr, req, 'body_file', b'foo')

    def test_body_file_setter_non_string(self):
        BEFORE = BytesIO(b'before')
        AFTER =  BytesIO(b'after')
        environ = {'wsgi.input': BEFORE,
                   'CONTENT_LENGTH': len('before'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = BaseRequest(environ)
        req.body_file = AFTER
        self.assert_(req.body_file is AFTER)
        self.assertEqual(req.content_length, None)

    def test_body_file_deleter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
                   'CONTENT_LENGTH': len(body),
                   'REQUEST_METHOD': 'POST',
                  }
        req = BaseRequest(environ)
        del req.body_file
        self.assertEqual(req.body_file.getvalue(), b'')
        self.assertEqual(req.content_length, 0)

    def test_body_file_raw(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST',
                  }
        req = BaseRequest(environ)
        self.assert_(req.body_file_raw is INPUT)

    def test_body_file_seekable_input_not_seekable(self):
        data = b'input'
        INPUT = BytesIO(data)
        INPUT.seek(1, 0) # consume
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': False,
                   'CONTENT_LENGTH': len(data)-1,
                   'REQUEST_METHOD': 'POST',
                  }
        req = BaseRequest(environ)
        seekable = req.body_file_seekable
        self.assert_(seekable is not INPUT)
        self.assertEqual(seekable.getvalue(), b'nput')

    def test_body_file_seekable_input_is_seekable(self):
        INPUT = BytesIO(b'input')
        INPUT.seek(1, 0) # consume
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input')-1,
                   'REQUEST_METHOD': 'POST',
                  }
        req = BaseRequest(environ)
        seekable = req.body_file_seekable
        self.assert_(seekable is INPUT)

    def test_scheme(self):
        environ = {'wsgi.url_scheme': 'something:',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.scheme, 'something:')

    def test_method(self):
        environ = {'REQUEST_METHOD': 'OPTIONS',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.method, 'OPTIONS')

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.http_version, '1.1')

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.script_name, '/script')

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.path_info, '/path/info')

    def test_content_length_getter(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.content_length, 1234)

    def test_content_length_setter_w_str(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = BaseRequest(environ)
        req.content_length = '3456'
        self.assertEqual(req.content_length, 3456)

    def test_remote_user(self):
        environ = {'REMOTE_USER': 'phred',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.remote_user, 'phred')

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.remote_addr, '1.2.3.4')

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.query_string, 'foo=bar&baz=bam')

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.server_name, 'somehost.tld')

    def test_server_port_getter(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.server_port, 6666)

    def test_server_port_setter_with_string(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = BaseRequest(environ)
        req.server_port = '6667'
        self.assertEqual(req.server_port, 6667)

    def test_uscript_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = BaseRequest(environ)
        self.assert_(isinstance(req.uscript_name, text_type))
        self.assertEqual(req.uscript_name, '/script')

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        self.assert_(isinstance(req.upath_info, text_type))
        self.assertEqual(req.upath_info, '/path/info')

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        req.upath_info = text_('/another')
        self.assert_(isinstance(req.upath_info, text_type))
        self.assertEqual(req.upath_info, '/another')

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = BaseRequest(environ)
        req.content_type = None
        self.assertEqual(req.content_type, '')
        self.assert_('CONTENT_TYPE' not in environ)

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = BaseRequest(environ)
        req.content_type = 'text/xml'
        self.assertEqual(req.content_type, 'text/xml')
        self.assertEqual(environ['CONTENT_TYPE'], 'text/xml;charset="utf8"')

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = BaseRequest(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assert_('CONTENT_TYPE' not in environ)

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = BaseRequest(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assert_('CONTENT_TYPE' not in environ)

    def test_headers_getter_miss(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = BaseRequest(environ)
        headers = req.headers
        self.assertEqual(headers,
                        {'Content-Type': CONTENT_TYPE,
                         'Content-Length': '123'})
        self.assertEqual(req._headers, headers)

    def test_headers_getter_hit(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = BaseRequest(environ)
        req._headers = {'Foo': 'Bar'}
        self.assertEqual(req.headers,
                        {'Foo': 'Bar'})

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = BaseRequest(environ)
        req._headers = {'Foo': 'Bar'}
        req.headers = {'Qux': 'Spam'}
        self.assertEqual(req.headers,
                        {'Qux': 'Spam'})

    def test_no_headers_deleter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = BaseRequest(environ)
        def _test():
            del req.headers
        self.assertRaises(AttributeError, _test)

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'http://example.com:8888')

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_application_url(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.application_url, 'http://example.com/script')

    def test_path_url(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.path_url, 'http://example.com/script/path/info')

    def test_path(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.path, '/script/path/info')

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.path_qs, '/script/path/info')

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.path_qs, '/script/path/info?foo=bar&baz=bam')

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.url, 'http://example.com/script/path/info')

    def test_url_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.url,
                         'http://example.com/script/path/info?foo=bar&baz=bam')

    def test_relative_url_to_app_true_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.relative_url('other/page', True),
                         'http://example.com/script/other/page')

    def test_relative_url_to_app_true_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.relative_url('/other/page', True),
                         'http://example.com/other/page')

    def test_relative_url_to_app_false_other_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.relative_url('/other/page', False),
                         'http://example.com/other/page')

    def test_relative_url_to_app_false_other_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.relative_url('other/page', False),
                         'http://example.com/script/path/other/page')

    def test_path_info_pop_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = BaseRequest(environ)
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
        req = BaseRequest(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, '')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/')
        self.assertEqual(environ['PATH_INFO'], '')

    def test_path_info_pop_non_empty_no_pattern(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_non_empty_w_pattern_miss(self):
        import re
        PATTERN = re.compile('miss')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, None)
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path/info')

    def test_path_info_pop_non_empty_w_pattern_hit(self):
        import re
        PATTERN = re.compile('path')
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = BaseRequest(environ)
        popped = req.path_info_pop(PATTERN)
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script/path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_pop_skips_empty_elements(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '//path/info',
                  }
        req = BaseRequest(environ)
        popped = req.path_info_pop()
        self.assertEqual(popped, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script//path')
        self.assertEqual(environ['PATH_INFO'], '/info')

    def test_path_info_peek_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = BaseRequest(environ)
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
        req = BaseRequest(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, '')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/')

    def test_path_info_peek_non_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path',
                  }
        req = BaseRequest(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, 'path')
        self.assertEqual(environ['SCRIPT_NAME'], '/script')
        self.assertEqual(environ['PATH_INFO'], '/path')

    def test_urlvars_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.urlvars, {'foo': 'bar'})

    def test_urlvars_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.urlvars, {'foo': 'bar'})

    def test_urlvars_getter_wo_keys(self):
        environ = {}
        req = BaseRequest(environ)
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))

    def test_urlvars_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = BaseRequest(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['paste.urlvars'], {'baz': 'bam'})
        self.assert_('wsgiorg.routing_args' not in environ)

    def test_urlvars_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = BaseRequest(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {'baz': 'bam'}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlvars_setter_wo_keys(self):
        environ = {}
        req = BaseRequest(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {'baz': 'bam'}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlvars_deleter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = BaseRequest(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assert_('paste.urlvars' not in environ)
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))

    def test_urlvars_deleter_w_wsgiorg_key_non_empty_tuple(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = BaseRequest(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], (('a', 'b'), {}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlvars_deleter_w_wsgiorg_key_empty_tuple(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = BaseRequest(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlvars_deleter_wo_keys(self):
        environ = {}
        req = BaseRequest(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlargs_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.urlargs, ())

    def test_urlargs_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.urlargs, ('a', 'b'))

    def test_urlargs_getter_wo_keys(self):
        environ = {}
        req = BaseRequest(environ)
        self.assertEqual(req.urlargs, ())
        self.assert_('wsgiorg.routing_args' not in environ)

    def test_urlargs_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = BaseRequest(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {'foo': 'bar'}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlargs_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = BaseRequest(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {'foo': 'bar'}))

    def test_urlargs_setter_wo_keys(self):
        environ = {}
        req = BaseRequest(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {}))
        self.assert_('paste.urlvars' not in environ)

    def test_urlargs_deleter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = BaseRequest(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertEqual(environ['wsgiorg.routing_args'],
                         ((), {'foo': 'bar'}))

    def test_urlargs_deleter_w_wsgiorg_key_empty(self):
        environ = {'wsgiorg.routing_args': ((), {}),
                  }
        req = BaseRequest(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assert_('paste.urlvars' not in environ)
        self.assert_('wsgiorg.routing_args' not in environ)

    def test_urlargs_deleter_wo_keys(self):
        environ = {}
        req = BaseRequest(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assert_('paste.urlvars' not in environ)
        self.assert_('wsgiorg.routing_args' not in environ)

    def test_cookies_empty_environ(self):
        req = BaseRequest({})
        self.assertEqual(req.cookies, {})

    def test_cookies_is_mutable(self):
        req = BaseRequest({})
        cookies = req.cookies
        cookies['a'] = '1'
        self.assertEqual(req.cookies['a'], '1')

    def test_cookies_w_webob_parsed_cookies_matching_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b', {'a': 'b'}),
        }
        req = BaseRequest(environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    def test_cookies_w_webob_parsed_cookies_mismatched_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b;c=d', {'a': 'b', 'c': 'd'}),
        }
        req = BaseRequest(environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    def test_set_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = BaseRequest(environ)
        req.cookies = {'a':'1', 'b': '2'}
        self.assertEqual(req.cookies, {'a': '1', 'b':'2'})
        rcookies = [x.strip() for x in environ['HTTP_COOKIE'].split(';')]
        self.assertEqual(sorted(rcookies), ['a=1', 'b=2'])

    def test_is_xhr_no_header(self):
        req = BaseRequest({})
        self.assert_(not req.is_xhr)

    def test_is_xhr_header_miss(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'notAnXMLHTTPRequest'}
        req = BaseRequest(environ)
        self.assert_(not req.is_xhr)

    def test_is_xhr_header_hit(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = BaseRequest(environ)
        self.assert_(req.is_xhr)

    # host
    def test_host_getter_w_HTTP_HOST(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = BaseRequest(environ)
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = BaseRequest(environ)
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_setter(self):
        environ = {}
        req = BaseRequest(environ)
        req.host = 'example.com:8888'
        self.assertEqual(environ['HTTP_HOST'], 'example.com:8888')

    def test_host_deleter_hit(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = BaseRequest(environ)
        del req.host
        self.assert_('HTTP_HOST' not in environ)

    def test_host_deleter_miss(self):
        environ = {}
        req = BaseRequest(environ)
        del req.host # doesn't raise

    # body
    def test_body_getter(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = BaseRequest(environ)
        self.assertEqual(req.body, b'input')
        self.assertEqual(req.content_length, len(b'input'))
    def test_body_setter_None(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(b'input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = BaseRequest(environ)
        req.body = None
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)
        self.assert_(req.is_body_seekable)
    def test_body_setter_non_string_raises(self):
        req = BaseRequest({})
        def _test():
            req.body = object()
        self.assertRaises(TypeError, _test)
    def test_body_setter_value(self):
        BEFORE = BytesIO(b'before')
        environ = {'wsgi.input': BEFORE,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('before'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = BaseRequest(environ)
        req.body = b'after'
        self.assertEqual(req.body, b'after')
        self.assertEqual(req.content_length, len(b'after'))
        self.assert_(req.is_body_seekable)
    def test_body_deleter_None(self):
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(data),
                   'REQUEST_METHOD': 'POST',
                  }
        req = BaseRequest(environ)
        del req.body
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)
        self.assert_(req.is_body_seekable)

    # POST
    def test_POST_not_POST_or_PUT(self):
        from webob.multidict import NoVars
        environ = {'REQUEST_METHOD': 'GET',
                  }
        req = BaseRequest(environ)
        result = req.POST
        self.assert_(isinstance(result, NoVars))
        self.assert_(result.reason.startswith('Not a form request'))

    def test_POST_existing_cache_hit(self):
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'POST',
                   'webob._parsed_post_vars': ({'foo': 'bar'}, INPUT),
                  }
        req = BaseRequest(environ)
        result = req.POST
        self.assertEqual(result, {'foo': 'bar'})

    def test_PUT_missing_content_type(self):
        from webob.multidict import NoVars
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'PUT',
                  }
        req = BaseRequest(environ)
        result = req.POST
        self.assert_(isinstance(result, NoVars))
        self.assert_(result.reason.startswith('Not an HTML form submission'))

    def test_PUT_bad_content_type(self):
        from webob.multidict import NoVars
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'PUT',
                   'CONTENT_TYPE': 'text/plain',
                  }
        req = BaseRequest(environ)
        result = req.POST
        self.assert_(isinstance(result, NoVars))
        self.assert_(result.reason.startswith('Not an HTML form submission'))

    def test_POST_multipart(self):
        BODY_TEXT = (
            b'------------------------------deb95b63e42a\n'
            b'Content-Disposition: form-data; name="foo"\n'
            b'\n'
            b'foo\n'
            b'------------------------------deb95b63e42a\n'
            b'Content-Disposition: form-data; name="bar"; filename="bar.txt"\n'
            b'Content-type: application/octet-stream\n'
            b'\n'
            b'these are the contents of the file "bar.txt"\n'
            b'\n'
            b'------------------------------deb95b63e42a--\n')
        INPUT = BytesIO(BODY_TEXT)
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'REQUEST_METHOD': 'POST',
                   'CONTENT_TYPE': 'multipart/form-data; '
                      'boundary=----------------------------deb95b63e42a',
                   'CONTENT_LENGTH': len(BODY_TEXT),
                  }
        req = BaseRequest(environ)
        result = req.POST
        self.assertEqual(result['foo'], 'foo')
        bar = result['bar']
        self.assertEqual(bar.name, 'bar')
        self.assertEqual(bar.filename, 'bar.txt')
        self.assertEqual(bar.file.read(),
                         b'these are the contents of the file "bar.txt"\n')

    # GET
    def test_GET_reflects_query_string(self):
        environ = {
            'QUERY_STRING': 'foo=123',
        }
        req = BaseRequest(environ)
        result = req.GET
        self.assertEqual(result, {'foo': '123'})
        req.query_string = 'foo=456'
        result = req.GET
        self.assertEqual(result, {'foo': '456'})
        req.query_string = ''
        result = req.GET
        self.assertEqual(result, {})

    def test_GET_updates_query_string(self):
        req = BaseRequest({})
        result = req.query_string
        self.assertEqual(result, '')
        req.GET['foo'] = '123'
        result = req.query_string
        self.assertEqual(result, 'foo=123')
        del req.GET['foo']
        result = req.query_string
        self.assertEqual(result, '')

    # postvars
    # queryvars
    # is_xhr
    # params

    # cookies
    def test_cookies_wo_webob_parsed_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = Request.blank('/', environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    # copy

    def test_copy_get(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = Request.blank('/', environ)
        clone = req.copy_get()
        for k, v in req.environ.items():
            if k in ('CONTENT_LENGTH', 'webob.is_body_seekable'):
                self.assert_(k not in clone.environ)
            elif k == 'wsgi.input':
                self.assert_(clone.environ[k] is not v)
            else:
                self.assertEqual(clone.environ[k], v)

    def test_remove_conditional_headers_accept_encoding(self):
        req = Request.blank('/')
        req.accept_encoding='gzip,deflate'
        req.remove_conditional_headers()
        self.assertEqual(bool(req.accept_encoding), False)

    def test_remove_conditional_headers_if_modified_since(self):
        from datetime import datetime
        req = Request.blank('/')
        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        req.remove_conditional_headers()
        self.assertEqual(req.if_modified_since, None)

    def test_remove_conditional_headers_if_none_match(self):
        req = Request.blank('/')
        req.if_none_match = 'foo'
        assert req.if_none_match
        req.remove_conditional_headers()
        assert not req.if_none_match

    def test_remove_conditional_headers_if_range(self):
        req = Request.blank('/')
        req.if_range = 'foo, bar'
        req.remove_conditional_headers()
        self.assertEqual(bool(req.if_range), False)

    def test_remove_conditional_headers_range(self):
        req = Request.blank('/')
        req.range = 'bytes=0-100'
        req.remove_conditional_headers()
        self.assertEqual(req.range, None)

    def test_is_body_readable_POST(self):
        req = Request.blank('/', environ={'REQUEST_METHOD':'POST'})
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_GET(self):
        req = Request.blank('/', environ={'REQUEST_METHOD':'GET'})
        self.assertFalse(req.is_body_readable)

    def test_is_body_readable_unknown_method_and_content_length(self):
        req = Request.blank('/', environ={'REQUEST_METHOD':'WTF'})
        req.content_length = 10
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_special_flag(self):
        req = Request.blank('/', environ={'REQUEST_METHOD':'WTF',
                                          'webob.is_body_readable': True})
        self.assertTrue(req.is_body_readable)


    # is_body_seekable
    # make_body_seekable
    # copy_body
    # make_tempfile
    # remove_conditional_headers
    # accept
    # accept_charset
    # accept_encoding
    # accept_language
    # authorization

    # cache_control
    def test_cache_control_reflects_environ(self):
        environ = {
            'HTTP_CACHE_CONTROL': 'max-age=5',
        }
        req = BaseRequest(environ)
        result = req.cache_control
        self.assertEqual(result.properties, {'max-age': 5})
        req.environ.update(HTTP_CACHE_CONTROL='max-age=10')
        result = req.cache_control
        self.assertEqual(result.properties, {'max-age': 10})
        req.environ.update(HTTP_CACHE_CONTROL='')
        result = req.cache_control
        self.assertEqual(result.properties, {})

    def test_cache_control_updates_environ(self):
        environ = {}
        req = BaseRequest(environ)
        req.cache_control.max_age = 5
        result = req.environ['HTTP_CACHE_CONTROL']
        self.assertEqual(result, 'max-age=5')
        req.cache_control.max_age = 10
        result = req.environ['HTTP_CACHE_CONTROL']
        self.assertEqual(result, 'max-age=10')
        req.cache_control = None
        result = req.environ['HTTP_CACHE_CONTROL']
        self.assertEqual(result, '')
        del req.cache_control
        self.assert_('HTTP_CACHE_CONTROL' not in req.environ)

    def test_cache_control_set_dict(self):
        environ = {}
        req = BaseRequest(environ)
        req.cache_control = {'max-age': 5}
        result = req.cache_control
        self.assertEqual(result.max_age, 5)

    def test_cache_control_set_object(self):
        from webob.cachecontrol import CacheControl
        environ = {}
        req = BaseRequest(environ)
        req.cache_control = CacheControl({'max-age': 5}, type='request')
        result = req.cache_control
        self.assertEqual(result.max_age, 5)

    def test_cache_control_gets_cached(self):
        environ = {}
        req = BaseRequest(environ)
        self.assert_(req.cache_control is req.cache_control)

    #if_match
    #if_none_match

    #date
    #if_modified_since
    #if_unmodified_since
    #if_range
    #max_forwards
    #pragma
    #range
    #referer
    #referrer
    #user_agent
    #__repr__
    #__str__
    #from_file

    #call_application
    def test_call_application_calls_application(self):
        environ = {}
        req = BaseRequest(environ)
        def application(environ, start_response):
            start_response('200 OK', [('content-type', 'text/plain')])
            return ['...\n']
        status, headers, output = req.call_application(application)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')

    def test_call_application_provides_write(self):
        environ = {}
        req = BaseRequest(environ)
        def application(environ, start_response):
            write = start_response('200 OK', [('content-type', 'text/plain')])
            write('...\n')
            return []
        status, headers, output = req.call_application(application)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')

    def test_call_application_closes_iterable_when_mixed_with_write_calls(self):
        environ = {
            'test._call_application_called_close': False
        }
        req = BaseRequest(environ)
        def application(environ, start_response):
            write = start_response('200 OK', [('content-type', 'text/plain')])
            class AppIter(object):
                def __iter__(self):
                    yield '...\n'
                def close(self):
                    environ['test._call_application_called_close'] = True
            write('...\n')
            return AppIter()
        status, headers, output = req.call_application(application)
        self.assertEqual(''.join(output), '...\n...\n')
        self.assertEqual(environ['test._call_application_called_close'], True)

    def test_call_application_raises_exc_info(self):
        environ = {}
        req = BaseRequest(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                import sys
                exc_info = sys.exc_info()
            start_response('200 OK', [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        self.assertRaises(RuntimeError, req.call_application, application)

    def test_call_application_returns_exc_info(self):
        environ = {}
        req = BaseRequest(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                import sys
                exc_info = sys.exc_info()
            start_response('200 OK', [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        status, headers, output, exc_info = req.call_application(application, True)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')
        self.assertEqual(exc_info[0], RuntimeError)

    #get_response
    def test_blank__method_subtitution(self):
        request = BaseRequest.blank('/', environ={'REQUEST_METHOD': 'PUT'})
        self.assertEqual(request.method, 'PUT')

        request = BaseRequest.blank(
            '/', environ={'REQUEST_METHOD': 'PUT'}, POST={})
        self.assertEqual(request.method, 'PUT')

        request = BaseRequest.blank(
            '/', environ={'REQUEST_METHOD': 'HEAD'}, POST={})
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_in_env(self):
        request = BaseRequest.blank(
            '/', environ={'CONTENT_TYPE': 'application/json'})
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = BaseRequest.blank(
            '/', environ={'CONTENT_TYPE': 'application/json'}, POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_in_headers(self):
        request = BaseRequest.blank(
            '/', headers={'Content-type': 'application/json'})
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = BaseRequest.blank(
            '/', headers={'Content-Type': 'application/json'}, POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_as_kw(self):
        request = BaseRequest.blank('/', content_type='application/json')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = BaseRequest.blank('/', content_type='application/json',
                                         POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__str_post_data_for_unsupported_ctype(self):
        self.assertRaises(ValueError,
                          BaseRequest.blank,
                          '/', content_type='application/json', POST={})

    def test_blank__post_urlencoded(self):
        request = Request.blank('/', POST={'first':1, 'second':2})
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type,
                         'application/x-www-form-urlencoded')
        self.assertEqual(request.body, b'first=1&second=2')
        self.assertEqual(request.content_length, 16)

    def test_blank__post_multipart(self):
        request = Request.blank(
            '/', POST={'first':'1', 'second':'2'},
            content_type='multipart/form-data; boundary=boundary')
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type, 'multipart/form-data')
        expected = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="first"\r\n\r\n'
            b'1\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="second"\r\n\r\n'
            b'2\r\n'
            b'--boundary--')
        self.assertEqual(request.body, expected)
        self.assertEqual(request.content_length, 139)

    def test_blank__post_files(self):
        import cgi
        from webob.request import _get_multipart_boundary
        POST = {'first':('filename1', BytesIO(b'1')),
                       'second':('filename2', '2'),
                       'third': '3'}
        request = Request.blank('/', POST=POST)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type, 'multipart/form-data')
        boundary = bytes_(
            _get_multipart_boundary(request.headers['content-type']))
        body_norm = request.body.replace(boundary, b'boundary')
        expected = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="first"; filename="filename1"\r\n\r\n'
            b'1\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="second"; filename="filename2"\r\n\r\n'
            b'2\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="third"\r\n\r\n'
            b'3\r\n'
            b'--boundary--'
            )
        self.assertEqual(body_norm, expected)
        self.assertEqual(request.content_length, 294)
        self.assertTrue(isinstance(request.POST['first'], cgi.FieldStorage))
        self.assertTrue(isinstance(request.POST['second'], cgi.FieldStorage))
        self.assertEqual(request.POST['first'].value, b'1')
        self.assertEqual(request.POST['second'].value, b'2')
        self.assertEqual(request.POST['third'], '3')

    def test_blank__post_file_w_wrong_ctype(self):
        self.assertRaises(
            ValueError, Request.blank, '/', POST={'first':('filename1', '1')},
            content_type='application/x-www-form-urlencoded')

    #from_bytes
    def test_from_bytes_extra_data(self):
        from webob import BaseRequest
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type')
        self.assertRaises(ValueError, BaseRequest.from_bytes,
                _test_req_copy+b'EXTRA!')

    #as_bytes
    def test_as_bytes_skip_body(self):
        from webob import BaseRequest
        req = BaseRequest.from_bytes(_test_req)
        body = req.as_string(skip_body=True)
        self.assertEqual(body.count(b'\r\n\r\n'), 0)
        self.assertEqual(req.as_bytes(skip_body=337), req.as_bytes())
        body = req.as_bytes(337-1).split(b'\r\n\r\n', 1)[1]
        self.assertEqual(body, b'<body skipped (len=337)>')

    def test_as_string_skip_body(self):
        from webob import BaseRequest
        req = BaseRequest.from_string(_test_req)
        body = req.as_string(skip_body=True)
        self.assertEqual(body.count(b'\r\n\r\n'), 0)
        self.assertEqual(req.as_string(skip_body=337), req.as_string())
        body = req.as_string(337-1).split(b'\r\n\r\n', 1)[1]
        self.assertEqual(body, b'<body skipped (len=337)>')

    def test_adhoc_attrs_set(self):
        req = Request.blank('/')
        req.foo = 1
        self.assertEqual(req.environ['webob.adhoc_attrs'], {'foo': 1})

    def test_adhoc_attrs_set_nonadhoc(self):
        req = Request.blank('/', environ={'webob.adhoc_attrs':{}})
        req.request_body_tempfile_limit = 1
        self.assertEqual(req.environ['webob.adhoc_attrs'], {})

    def test_adhoc_attrs_get(self):
        req = Request.blank('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        self.assertEqual(req.foo, 1)

    def test_adhoc_attrs_get_missing(self):
        req = Request.blank('/')
        self.assertRaises(AttributeError, getattr, req, 'some_attr')

    def test_adhoc_attrs_del(self):
        req = Request.blank('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        del req.foo
        self.assertEqual(req.environ['webob.adhoc_attrs'], {})

    def test_adhoc_attrs_del_missing(self):
        req = Request.blank('/')
        self.assertRaises(AttributeError, delattr, req, 'some_attr')

class RequestTests_functional(unittest.TestCase):

    def test_gets(self):
        request = Request.blank('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        self.assertEqual(status, '200 OK')
        res = b''.join(app_iter)
        self.assert_(b'Hello' in res)
        self.assert_(b"MultiDict([])" in res)
        self.assert_(b"post is <NoVars: Not a form request>" in res)

    def test_gets_with_query_string(self):
        request = Request.blank('/?name=george')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"MultiDict" in res)
        self.assert_(b"'name'" in res)
        self.assert_(b"'george'" in res)
        self.assert_(b"Val is " in res)

    def test_language_parsing1(self):
        request = Request.blank('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"The languages are: []" in res)

    def test_language_parsing2(self):
        request = Request.blank(
            '/', headers={'Accept-Language': 'da, en-gb;q=0.8'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"languages are: ['da', 'en-gb']" in res)

    def test_language_parsing3(self):
        request = Request.blank(
            '/',
            headers={'Accept-Language': 'en-gb;q=0.8, da'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"languages are: ['da', 'en-gb']" in res)

    def test_mime_parsing1(self):
        request = Request.blank(
            '/',
            headers={'Accept':'text/html'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"accepttypes is: text/html" in res)

    def test_mime_parsing2(self):
        request = Request.blank(
            '/',
            headers={'Accept':'application/xml'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"accepttypes is: application/xml" in res)

    def test_mime_parsing3(self):
        request = Request.blank(
            '/',
            headers={'Accept':'application/xml,*/*'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assert_(b"accepttypes is: application/xml" in res)

    def test_accept_best_match(self):
        accept = Request.blank('/').accept
        self.assert_(not accept)
        self.assert_(not Request.blank('/', headers={'Accept': ''}).accept)
        req = Request.blank('/', headers={'Accept':'text/plain'})
        self.assert_(req.accept)
        self.assertRaises(ValueError, req.accept.best_match, ['*/*'])
        req = Request.blank('/', accept=['*/*','text/*'])
        self.assertEqual(
            req.accept.best_match(['application/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'application/x-foo']),
            'text/plain')
        req = Request.blank('/', accept=['text/plain', 'message/*'])
        self.assertEqual(
            req.accept.best_match(['message/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'message/x-foo']),
            'text/plain')

    def test_from_mimeparse(self):
        # http://mimeparse.googlecode.com/svn/trunk/mimeparse.py
        supported = ['application/xbel+xml', 'application/xml']
        tests = [('application/xbel+xml', 'application/xbel+xml'),
                ('application/xbel+xml; q=1', 'application/xbel+xml'),
                ('application/xml; q=1', 'application/xml'),
                ('application/*; q=1', 'application/xbel+xml'),
                ('*/*', 'application/xbel+xml')]

        for accept, get in tests:
            req = Request.blank('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/xbel+xml', 'text/xml']
        tests = [('text/*;q=0.5,*/*; q=0.1', 'text/xml'),
                ('text/html,application/atom+xml; q=0.9', None)]

        for accept, get in tests:
            req = Request.blank('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/json', 'text/html']
        tests = [
            ('application/json, text/javascript, */*', 'application/json'),
            ('application/json, text/html;q=0.9', 'application/json'),
        ]

        for accept, get in tests:
            req = Request.blank('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        offered = ['image/png', 'application/xml']
        tests = [
            ('image/png', 'image/png'),
            ('image/*', 'image/png'),
            ('image/*, application/xml', 'application/xml'),
        ]

        for accept, get in tests:
            req = Request.blank('/', accept=accept)
            self.assertEqual(req.accept.best_match(offered), get)

    def test_headers(self):
        headers = {
            'If-Modified-Since': 'Sat, 29 Oct 1994 19:43:31 GMT',
            'Cookie': 'var1=value1',
            'User-Agent': 'Mozilla 4.0 (compatible; MSIE)',
            'If-None-Match': '"etag001", "etag002"',
            'X-Requested-With': 'XMLHttpRequest',
            }
        request = Request.blank('/?foo=bar&baz', headers=headers)
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        for thing in (
            'if_modified_since: ' +
                'datetime.datetime(1994, 10, 29, 19, 43, 31, tzinfo=UTC)',
            "user_agent: 'Mozilla",
            'is_xhr: True',
            "cookies is <RequestCookies",
            'var1',
            'value1',
            'params is NestedMultiDict',
            'foo',
            'bar',
            'baz',
            'if_none_match: <ETag etag001 or etag002>',
            ):
            self.assert_(bytes_(thing) in res)

    def test_bad_cookie(self):
        req = Request.blank('/')
        req.headers['Cookie'] = '070-it-:><?0'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = 'foo=bar'
        self.assertEqual(req.cookies, {'foo': 'bar'})
        req.headers['Cookie'] = '...'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = '=foo'
        self.assertEqual(req.cookies, {})
        req.headers['Cookie'] = ('dismiss-top=6; CP=null*; '
            'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
        self.assertEqual(req.cookies, {
            'CP':           'null*',
            'PHPSESSID':    '0a539d42abc001cdc762809248d4beed',
            'a':            '42',
            'dismiss-top':  '6'
        })
        req.headers['Cookie'] = 'fo234{=bar blub=Blah'
        self.assertEqual(req.cookies, {'blub': 'Blah'})

    def test_cookie_quoting(self):
        req = Request.blank('/')
        req.headers['Cookie'] = 'foo="?foo"; Path=/'
        self.assertEqual(req.cookies, {'foo': '?foo'})

    def test_path_quoting(self):
        path = '/:@&+$,/bar'
        req = Request.blank(path)
        self.assertEqual(req.path, path)
        self.assert_(req.url.endswith(path))

    def test_params(self):
        req = Request.blank('/?a=1&b=2')
        req.method = 'POST'
        req.body = b'b=3'
        self.assertEqual(list(req.params.items()),
                         [('a', '1'), ('b', '2'), ('b', '3')])
        new_params = req.params.copy()
        self.assertEqual(list(new_params.items()),
                         [('a', '1'), ('b', '2'), ('b', '3')])
        new_params['b'] = '4'
        self.assertEqual(list(new_params.items()), [('a', '1'), ('b', '4')])
        # The key name is \u1000:
        req = Request.blank('/?%E1%80%80=x')
        val = text_type(b'\u1000', 'unicode_escape')
        self.assert_(val in list(req.GET.keys()))
        self.assertEqual(req.GET[val], 'x')

    def test_copy_body(self):
        req = Request.blank('/', method='POST', body=b'some text',
                            request_body_tempfile_limit=1)
        old_body_file = req.body_file_raw
        req.copy_body()
        self.assert_(req.body_file_raw is not old_body_file)
        req = Request.blank('/', method='POST',
                body_file=UnseekableInput(b'0123456789'), content_length=10)
        self.assert_(not hasattr(req.body_file_raw, 'seek'))
        old_body_file = req.body_file_raw
        req.make_body_seekable()
        self.assert_(req.body_file_raw is not old_body_file)
        self.assertEqual(req.body, b'0123456789')
        old_body_file = req.body_file
        req.make_body_seekable()
        self.assert_(req.body_file_raw is old_body_file)
        self.assert_(req.body_file is old_body_file)

    def test_broken_seek(self):
        # copy() should work even when the input has a broken seek method
        req = Request.blank('/', method='POST',
                body_file=UnseekableInputWithSeek(b'0123456789'),
                content_length=10)
        self.assert_(hasattr(req.body_file_raw, 'seek'))
        self.assertRaises(IOError, req.body_file_raw.seek, 0)
        old_body_file = req.body_file
        req2 = req.copy()
        self.assert_(req2.body_file_raw is req2.body_file is not old_body_file)
        self.assertEqual(req2.body, b'0123456789')

    def test_set_body(self):
        from webob import BaseRequest
        req = BaseRequest.blank('/', method='PUT', body=b'foo')
        self.assert_(req.is_body_seekable)
        self.assertEqual(req.body, b'foo')
        self.assertEqual(req.content_length, 3)
        del req.body
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)

    def test_broken_clen_header(self):
        # if the UA sends "content_length: ..' header (the name is wrong)
        # it should not break the req.headers.items()
        req = Request.blank('/')
        req.environ['HTTP_CONTENT_LENGTH'] = '0'
        req.headers.items()

    def test_nonstr_keys(self):
        # non-string env keys shouldn't break req.headers
        req = Request.blank('/')
        req.environ[1] = 1
        req.headers.items()


    def test_authorization(self):
        req = Request.blank('/')
        req.authorization = 'Digest uri="/?a=b"'
        self.assertEqual(req.authorization, ('Digest', {'uri': '/?a=b'}))

    def test_authorization2(self):
        from webob.descriptors import parse_auth_params
        for s, d in [
            ('x=y', {'x': 'y'}),
            ('x="y"', {'x': 'y'}),
            ('x=y,z=z', {'x': 'y', 'z': 'z'}),
            ('x=y, z=z', {'x': 'y', 'z': 'z'}),
            ('x="y",z=z', {'x': 'y', 'z': 'z'}),
            ('x="y", z=z', {'x': 'y', 'z': 'z'}),
            ('x="y,x", z=z', {'x': 'y,x', 'z': 'z'}),
        ]:
            self.assertEqual(parse_auth_params(s), d)


    def test_from_file(self):
        req = Request.blank('http://example.com:8000/test.html?params')
        inp = BytesIO(req.as_bytes())
        self.equal_req(req, inp)

        req = Request.blank('http://example.com/test2')
        req.method = 'POST'
        req.body = b'test=example'
        inp = BytesIO(req.as_bytes())
        self.equal_req(req, inp)

    def test_from_file_text(self):
        req = Request.blank('http://example.com:8000/test.html?params')
        inp = StringIO(req.as_text())
        self.equal_req(req, inp)

        req = Request.blank('http://example.com/test2')
        req.method = 'POST'
        req.body = b'test=example'
        inp = StringIO(req.as_text())
        self.equal_req(req, inp)

    def test_req_kw_none_val(self):
        request = Request({}, content_length=None)
        self.assert_('content-length' not in request.headers)
        self.assert_('content-type' not in request.headers)

    def test_env_keys(self):
        req = Request.blank('/')
        # SCRIPT_NAME can be missing
        del req.environ['SCRIPT_NAME']
        self.assertEqual(req.script_name, '')
        self.assertEqual(req.uscript_name, '')

    def test_repr_nodefault(self):
        from webob.request import NoDefault
        nd = NoDefault
        self.assertEqual(repr(nd), '(No Default)')

    def test_request_noenviron_param(self):
        # Environ is a a mandatory not null param in Request.
        self.assertRaises(TypeError, Request, environ=None)

    def test_unexpected_kw(self):
        # Passed an attr in kw that does not exist in the class, should
        # raise an error
        # Passed an attr in kw that does exist in the class, should be ok
        self.assertRaises(TypeError,
                          Request, {'a':1}, this_does_not_exist=1)
        r = Request({'a':1}, server_name='127.0.0.1')
        self.assertEqual(getattr(r, 'server_name', None), '127.0.0.1')

    def test_conttype_set_del(self):
        # Deleting content_type attr from a request should update the
        # environ dict
        # Assigning content_type should replace first option of the environ
        # dict
        r = Request({'a':1}, **{'content_type':'text/html'})
        self.assert_('CONTENT_TYPE' in r.environ)
        self.assert_(hasattr(r, 'content_type'))
        del r.content_type
        self.assert_('CONTENT_TYPE' not in r.environ)
        a = Request({'a':1},
                content_type='charset=utf-8;application/atom+xml;type=entry')
        self.assert_(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')
        a.content_type = 'charset=utf-8'
        self.assert_(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')

    def test_headers2(self):
        # Setting headers in init and later with a property, should update
        # the info
        headers = {'Host': 'www.example.com',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '115',
                'Connection': 'keep-alive',
                'Cache-Control': 'max-age=0'}
        r = Request({'a':1}, headers=headers)
        for i in headers.keys():
            self.assert_(i in r.headers and
                'HTTP_'+i.upper().replace('-', '_') in r.environ)
        r.headers = {'Server':'Apache'}
        self.assertEqual(list(r.environ.keys()), ['a',  'HTTP_SERVER'])

    def test_host_url(self):
        # Request has a read only property host_url that combines several
        # keys to create a host_url
        a = Request({'wsgi.url_scheme':'http'}, **{'host':'www.example.com'})
        self.assertEqual(a.host_url, 'http://www.example.com')
        a = Request({'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                                'server_port':5000})
        self.assertEqual(a.host_url, 'http://localhost:5000')
        a = Request({'wsgi.url_scheme':'https'}, **{'server_name':'localhost',
                                                    'server_port':443})
        self.assertEqual(a.host_url, 'https://localhost')

    def test_path_info_p(self):
        # Peek path_info to see what's coming
        # Pop path_info until there's nothing remaining
        a = Request({'a':1}, **{'path_info':'/foo/bar','script_name':''})
        self.assertEqual(a.path_info_peek(), 'foo')
        self.assertEqual(a.path_info_pop(), 'foo')
        self.assertEqual(a.path_info_peek(), 'bar')
        self.assertEqual(a.path_info_pop(), 'bar')
        self.assertEqual(a.path_info_peek(), None)
        self.assertEqual(a.path_info_pop(), None)

    def test_urlvars_property(self):
        # Testing urlvars setter/getter/deleter
        a = Request({'wsgiorg.routing_args':((),{'x':'y'}),
                    'paste.urlvars':{'test':'value'}})
        a.urlvars = {'hello':'world'}
        self.assert_('paste.urlvars' not in a.environ)
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ((), {'hello':'world'}))
        del a.urlvars
        self.assert_('wsgiorg.routing_args' not in a.environ)
        a = Request({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlvars, {'test':'value'})
        a.urlvars = {'hello':'world'}
        self.assertEqual(a.environ['paste.urlvars'], {'hello':'world'})
        del a.urlvars
        self.assert_('paste.urlvars' not in a.environ)

    def test_urlargs_property(self):
        # Testing urlargs setter/getter/deleter
        a = Request({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlargs, ())
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {'test':'value'}))
        a = Request({'a':1})
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {}))
        del a.urlargs
        self.assert_('wsgiorg.routing_args' not in a.environ)

    def test_host_property(self):
        # Testing host setter/getter/deleter
        a = Request({'wsgi.url_scheme':'http'}, server_name='localhost',
                                                server_port=5000)
        self.assertEqual(a.host, "localhost:5000")
        a.host = "localhost:5000"
        self.assert_('HTTP_HOST' in a.environ)
        del a.host
        self.assert_('HTTP_HOST' not in a.environ)

    def test_body_property(self):
        # Testing body setter/getter/deleter plus making sure body has a
        # seek method
        #a = Request({'a':1}, **{'CONTENT_LENGTH':'?'})
        # I cannot think of a case where somebody would put anything else
        # than a # numerical value in CONTENT_LENGTH, Google didn't help
        # either
        #self.assertEqual(a.body, '')
        # I need to implement a not seekable stringio like object.

        import string
        class DummyIO(object):
            def __init__(self, txt):
                self.txt = txt
            def read(self, n=-1):
                return self.txt[0:n]
        limit = BaseRequest.request_body_tempfile_limit
        len_strl = limit // len(string.ascii_letters) + 1
        r = Request({'a':1, 'REQUEST_METHOD': 'POST'},
                    body_file=DummyIO(bytes_(string.ascii_letters) * len_strl))
        self.assertEqual(len(r.body), len(string.ascii_letters*len_strl)-1)
        self.assertRaises(TypeError,
                          setattr, r, 'body', text_('hello world'))
        r.body = None
        self.assertEqual(r.body, b'')
        r = Request({'a':1}, method='PUT', body_file=DummyIO(
            bytes_(string.ascii_letters)))
        self.assert_(not hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assert_(hasattr(r.body_file_raw, 'seek'))
        r = Request({'a':1}, method='PUT',
                    body_file=BytesIO(bytes_(string.ascii_letters)))
        self.assert_(hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assert_(hasattr(r.body_file_raw, 'seek'))

    def test_repr_invalid(self):
        # If we have an invalid WSGI environ, the repr should tell us.
        from webob import BaseRequest
        req = BaseRequest({'CONTENT_LENGTH':'0', 'body':''})
        self.assert_(repr(req).endswith('(invalid WSGI environ)>'))

    def test_from_garbage_file(self):
        # If we pass a file with garbage to from_file method it should
        # raise an error plus missing bits in from_file method
        io = BytesIO(b'hello world')

        from webob import BaseRequest
        self.assertRaises(ValueError,
                          BaseRequest.from_file, io)
        val_file = BytesIO(
            b"GET /webob/ HTTP/1.1\n"
            b"Host: pythonpaste.org\n"
            b"User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13)"
            b"Gecko/20101206 Ubuntu/10.04 (lucid) Firefox/3.6.13\n"
            b"Accept: "
            b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;"
            b"q=0.8\n"
            b"Accept-Language: en-us,en;q=0.5\n"
            b"Accept-Encoding: gzip,deflate\n"
            b"Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
            # duplicate on purpose
            b"Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\n"
            b"Keep-Alive: 115\n"
            b"Connection: keep-alive\n"
        )
        req = BaseRequest.from_file(val_file)
        self.assert_(isinstance(req, BaseRequest))
        self.assert_(not repr(req).endswith('(invalid WSGI environ)>'))
        val_file = BytesIO(
            b"GET /webob/ HTTP/1.1\n"
            b"Host pythonpaste.org\n"
        )
        self.assertRaises(ValueError, BaseRequest.from_file, val_file)

    def test_from_bytes(self):
        # A valid request without a Content-Length header should still read
        # the full body.
        # Also test parity between as_string and from_bytes / from_file.
        import cgi
        from webob import BaseRequest
        req = BaseRequest.from_bytes(_test_req)
        self.assert_(isinstance(req, BaseRequest))
        self.assert_(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assert_('\n' not in req.http_version or '\r' in req.http_version)
        self.assert_(',' not in req.host)
        self.assert_(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assert_(b'foo' in req.body)
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        self.assert_(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assert_(isinstance(bar, cgi.FieldStorage))
        self.assertEqual(bar.type, 'application/octet-stream')
        bar.file.seek(0)
        self.assertEqual(bar.file.read(), bar_contents)
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type'
            )
        self.assertEqual(req.as_bytes(), _test_req_copy)

        req2 = BaseRequest.from_bytes(_test_req2)
        self.assert_('host' not in req2.headers)
        self.assertEqual(req2.as_bytes(), _test_req2.rstrip())
        self.assertRaises(ValueError,
                          BaseRequest.from_bytes, _test_req2 + b'xx')

    def test_from_text(self):
        import cgi
        from webob import BaseRequest
        req = BaseRequest.from_text(text_(_test_req, 'utf-8'))
        self.assert_(isinstance(req, BaseRequest))
        self.assert_(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assert_('\n' not in req.http_version or '\r' in req.http_version)
        self.assert_(',' not in req.host)
        self.assert_(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assert_(b'foo' in req.body)
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        self.assert_(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assert_(isinstance(bar, cgi.FieldStorage))
        self.assertEqual(bar.type, 'application/octet-stream')
        bar.file.seek(0)
        self.assertEqual(bar.file.read(), bar_contents)
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type'
            )
        self.assertEqual(req.as_bytes(), _test_req_copy)

        req2 = BaseRequest.from_bytes(_test_req2)
        self.assert_('host' not in req2.headers)
        self.assertEqual(req2.as_bytes(), _test_req2.rstrip())
        self.assertRaises(ValueError,
                          BaseRequest.from_bytes, _test_req2 + b'xx')

    def test_blank(self):
        # BaseRequest.blank class method
        from webob import BaseRequest
        self.assertRaises(ValueError, BaseRequest.blank,
                    'www.example.com/foo?hello=world', None,
                    'www.example.com/foo?hello=world')
        self.assertRaises(ValueError, BaseRequest.blank,
                    'gopher.example.com/foo?hello=world', None,
                    'gopher://gopher.example.com')
        req = BaseRequest.blank('www.example.com/foo?hello=world', None,
                                'http://www.example.com')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:80')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/foo')
        self.assertEqual(req.environ.get('QUERY_STRING', None),
                         'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        req = BaseRequest.blank('www.example.com/secure?hello=world', None,
                                'https://www.example.com/secure')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:443')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/secure')
        self.assertEqual(req.environ.get('QUERY_STRING', None), 'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.environ.get('SCRIPT_NAME', None), '/secure')
        self.assertEqual(req.environ.get('SERVER_NAME', None),
                         'www.example.com')
        self.assertEqual(req.environ.get('SERVER_PORT', None), '443')

    def test_environ_from_url(self):
        # Generating an environ just from an url plus testing environ_add_POST
        from webob.request import environ_add_POST
        from webob.request import environ_from_url
        self.assertRaises(TypeError, environ_from_url,
                    'http://www.example.com/foo?bar=baz#qux')
        self.assertRaises(TypeError, environ_from_url,
                    'gopher://gopher.example.com')
        req = environ_from_url('http://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:80')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '80')
        req = environ_from_url('https://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')
        environ_add_POST(req, None)
        self.assert_('CONTENT_TYPE' not in req)
        self.assert_('CONTENT_LENGTH' not in req)
        environ_add_POST(req, {'hello':'world'})
        self.assert_(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'POST')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')
        self.assertEqual(req.get('CONTENT_LENGTH', None),'11')
        self.assertEqual(req.get('CONTENT_TYPE', None),
                         'application/x-www-form-urlencoded')
        self.assertEqual(req['wsgi.input'].read(), b'hello=world')

    def test_environ_from_url_highorder_path_info(self):
        from webob.request import environ_from_url
        env = environ_from_url('/%E6%B5%81')
        self.assertEqual(env['PATH_INFO'], '/\xe6\xb5\x81')
        request = Request(env)
        self.assertEqual(request.path_info, '/\xe6\xb5\x81')
        self.assertEqual(request.upath_info,
                         b'/\xe6\xb5\x81'.decode('utf8')) # u'/\u6d41'


    def test_post_does_not_reparse(self):
        # test that there's no repetitive parsing is happening on every
        # req.POST access
        req = Request.blank('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        f0 = req.body_file_raw
        post1 = req.POST
        f1 = req.body_file_raw
        self.assert_(f1 is not f0)
        post2 = req.POST
        f2 = req.body_file_raw
        self.assert_(post1 is post2)
        self.assert_(f1 is f2)


    def test_middleware_body(self):
        def app(env, sr):
            sr('200 OK', [])
            return [env['wsgi.input'].read()]

        def mw(env, sr):
            req = Request(env)
            data = req.body_file.read()
            resp = req.get_response(app)
            resp.headers['x-data'] = data
            return resp(env, sr)

        req = Request.blank('/', method='PUT', body=b'abc')
        resp = req.get_response(mw)
        self.assertEqual(resp.body, b'abc')
        self.assertEqual(resp.headers['x-data'], b'abc')

    def test_body_file_noseek(self):
        req = Request.blank('/', method='PUT', body=b'abc')
        lst = [req.body_file.read(1) for i in range(3)]
        self.assertEqual(lst, [b'a', b'b', b'c'])

    def test_cgi_escaping_fix(self):
        req = Request.blank('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        self.assertEqual(list(req.POST.keys()), ['%20%22"'])
        req.body_file.read()
        self.assertEqual(list(req.POST.keys()), ['%20%22"'])

    def test_content_type_none(self):
        r = Request.blank('/', content_type='text/html')
        self.assertEqual(r.content_type, 'text/html')
        r.content_type = None

    def test_body_file_seekable(self):
        r = Request.blank('/', method='POST')
        r.body_file = BytesIO(b'body')
        self.assertEqual(r.body_file_seekable.read(), b'body')

    def test_request_init(self):
        # port from doctest (docs/reference.txt)
        req = Request.blank('/article?id=1')
        self.assertEqual(req.environ['HTTP_HOST'], 'localhost:80')
        self.assertEqual(req.environ['PATH_INFO'], '/article')
        self.assertEqual(req.environ['QUERY_STRING'], 'id=1')
        self.assertEqual(req.environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(req.environ['SCRIPT_NAME'], '')
        self.assertEqual(req.environ['SERVER_NAME'], 'localhost')
        self.assertEqual(req.environ['SERVER_PORT'], '80')
        self.assertEqual(req.environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assert_(hasattr(req.environ['wsgi.errors'], 'write') and
                     hasattr(req.environ['wsgi.errors'], 'flush'))
        self.assert_(hasattr(req.environ['wsgi.input'], 'next') or
                     hasattr(req.environ['wsgi.input'], '__next__'))
        self.assertEqual(req.environ['wsgi.multiprocess'], False)
        self.assertEqual(req.environ['wsgi.multithread'], False)
        self.assertEqual(req.environ['wsgi.run_once'], False)
        self.assertEqual(req.environ['wsgi.url_scheme'], 'http')
        self.assertEqual(req.environ['wsgi.version'], (1, 0))

        # Test body
        self.assert_(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, b'')
        req.method = 'PUT'
        req.body = b'test'
        self.assert_(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, b'test')

        # Test method & URL
        self.assertEqual(req.method, 'PUT')
        self.assertEqual(req.scheme, 'http')
        self.assertEqual(req.script_name, '') # The base of the URL
        req.script_name = '/blog'  # make it more interesting
        self.assertEqual(req.path_info, '/article')
        # Content-Type of the request body
        self.assertEqual(req.content_type, '')
        # The auth'ed user (there is none set)
        self.assert_(req.remote_user is None)
        self.assert_(req.remote_addr is None)
        self.assertEqual(req.host, 'localhost:80')
        self.assertEqual(req.host_url, 'http://localhost')
        self.assertEqual(req.application_url, 'http://localhost/blog')
        self.assertEqual(req.path_url, 'http://localhost/blog/article')
        self.assertEqual(req.url, 'http://localhost/blog/article?id=1')
        self.assertEqual(req.path, '/blog/article')
        self.assertEqual(req.path_qs, '/blog/article?id=1')
        self.assertEqual(req.query_string, 'id=1')
        self.assertEqual(req.relative_url('archive'),
                         'http://localhost/blog/archive')

        # Doesn't change request
        self.assertEqual(req.path_info_peek(), 'article')
        # Does change request!
        self.assertEqual(req.path_info_pop(), 'article')
        self.assertEqual(req.script_name, '/blog/article')
        self.assertEqual(req.path_info, '')

        # Headers
        req.headers['Content-Type'] = 'application/x-www-urlencoded'
        self.assertEqual(sorted(req.headers.items()),
                         [('Content-Length', '4'),
                          ('Content-Type', 'application/x-www-urlencoded'),
                          ('Host', 'localhost:80')])
        self.assertEqual(req.environ['CONTENT_TYPE'],
                         'application/x-www-urlencoded')

    def test_request_query_and_POST_vars(self):
        # port from doctest (docs/reference.txt)

        # Query & POST variables
        from webob.multidict import MultiDict
        from webob.multidict import NestedMultiDict
        from webob.multidict import NoVars
        from webob.multidict import GetDict
        req = Request.blank('/test?check=a&check=b&name=Bob')
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        self.assertEqual(req.GET, GET)
        self.assertEqual(req.GET['check'], 'b')
        self.assertEqual(req.GET.getall('check'), ['a', 'b'])
        self.assertEqual(list(req.GET.items()),
                         [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        self.assert_(isinstance(req.POST, NoVars))
        # NoVars can be read like a dict, but not written
        self.assertEqual(list(req.POST.items()), [])
        req.method = 'POST'
        req.body = b'name=Joe&email=joe@example.com'
        self.assertEqual(req.POST,
                         MultiDict([('name', 'Joe'),
                                    ('email', 'joe@example.com')]))
        self.assertEqual(req.POST['name'], 'Joe')

        self.assert_(isinstance(req.params, NestedMultiDict))
        self.assertEqual(list(req.params.items()),
                         [('check', 'a'),
                          ('check', 'b'),
                          ('name', 'Bob'),
                          ('name', 'Joe'),
                          ('email', 'joe@example.com')])
        self.assertEqual(req.params['name'], 'Bob')
        self.assertEqual(req.params.getall('name'), ['Bob', 'Joe'])

    def test_request_put(self):
        from datetime import datetime
        from webob import Response
        from webob import UTC
        from webob.acceptparse import MIMEAccept
        from webob.byterange import Range
        from webob.etag import ETagMatcher
        from webob.multidict import MultiDict
        from webob.multidict import GetDict
        req = Request.blank('/test?check=a&check=b&name=Bob')
        req.method = 'PUT'
        req.body = b'var1=value1&var2=value2&rep=1&rep=2'
        req.environ['CONTENT_LENGTH'] = str(len(req.body))
        req.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        self.assertEqual(req.GET, GET)
        self.assertEqual(req.POST, MultiDict(
                                [('var1', 'value1'),
                                 ('var2', 'value2'),
                                 ('rep', '1'),
                                 ('rep', '2')]))
        self.assertEqual(
            list(req.GET.items()),
            [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        # Unicode
        req.charset = 'utf8'
        self.assertEqual(list(req.GET.items()),
                         [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        # Cookies
        req.headers['Cookie'] = 'test=value'
        self.assert_(isinstance(req.cookies, collections.MutableMapping))
        self.assertEqual(list(req.cookies.items()), [('test', 'value')])
        req.charset = None
        self.assertEqual(req.cookies, {'test': 'value'})

        # Accept-* headers
        self.assert_('text/html' in req.accept)
        req.accept = 'text/html;q=0.5, application/xhtml+xml;q=1'
        self.assert_(isinstance(req.accept, MIMEAccept))
        self.assert_('text/html' in req.accept)

        self.assertRaises(DeprecationWarning, req.accept.first_match, ['text/html'])
        self.assertEqual(req.accept.best_match(['text/html',
                                                'application/xhtml+xml']),
                         'application/xhtml+xml')

        req.accept_language = 'es, pt-BR'
        self.assertEqual(req.accept_language.best_match(['es']), 'es')

        # Conditional Requests
        server_token = 'opaque-token'
        # shouldn't return 304
        self.assert_(not server_token in req.if_none_match)
        req.if_none_match = server_token
        self.assert_(isinstance(req.if_none_match, ETagMatcher))
        # You *should* return 304
        self.assert_(server_token in req.if_none_match)
        # if_none_match should use weak matching
        weak_token = 'W/"%s"' % server_token
        req.if_none_match = weak_token
        assert req.headers['if-none-match'] == weak_token
        self.assert_(server_token in req.if_none_match)


        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        self.assertEqual(req.headers['If-Modified-Since'],
                         'Sun, 01 Jan 2006 12:00:00 GMT')
        server_modified = datetime(2005, 1, 1, 12, 0, tzinfo=UTC)
        self.assert_(req.if_modified_since)
        self.assert_(req.if_modified_since >= server_modified)

        self.assert_(not req.if_range)
        self.assert_(Response(etag='some-etag', last_modified=datetime(2005, 1, 1, 12, 0))
            in req.if_range)
        req.if_range = 'opaque-etag'
        self.assert_(Response(etag='other-etag') not in req.if_range)
        self.assert_(Response(etag='opaque-etag') in req.if_range)

        res = Response(etag='opaque-etag')
        self.assert_(res in req.if_range)

        req.range = 'bytes=0-100'
        self.assert_(isinstance(req.range, Range))
        self.assertEqual(tuple(req.range), (0, 101))
        cr = req.range.content_range(length=1000)
        self.assertEqual(tuple(cr), (0, 101, 1000))

        self.assert_(server_token in req.if_match)
        # No If-Match means everything is ok
        req.if_match = server_token
        self.assert_(server_token in req.if_match)
        # Still OK
        req.if_match = 'other-token'
        # Not OK, should return 412 Precondition Failed:
        self.assert_(not server_token in req.if_match)

    def test_call_WSGI_app(self):
        req = Request.blank('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'Hi!']
        self.assertEqual(req.call_application(wsgi_app),
                         ('200 OK', [('Content-type', 'text/plain')],
                          [b'Hi!']))

        res = req.get_response(wsgi_app)
        from webob.response import Response
        self.assert_(isinstance(res, Response))
        self.assertEqual(res.status, '200 OK')
        from webob.headers import ResponseHeaders
        self.assert_(isinstance(res.headers, ResponseHeaders))
        self.assertEqual(list(res.headers.items()),
                         [('Content-type', 'text/plain')])
        self.assertEqual(res.body, b'Hi!')

    def test_get_response_catch_exc_info_true(self):
        req = Request.blank('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'Hi!']
        res = req.get_response(wsgi_app, catch_exc_info=True)
        from webob.response import Response
        self.assert_(isinstance(res, Response))
        self.assertEqual(res.status, '200 OK')
        from webob.headers import ResponseHeaders
        self.assert_(isinstance(res.headers, ResponseHeaders))
        self.assertEqual(list(res.headers.items()),
                         [('Content-type', 'text/plain')])
        self.assertEqual(res.body, b'Hi!')

    def equal_req(self, req, inp):
        req2 = Request.from_file(inp)
        self.assertEqual(req.url, req2.url)
        headers1 = dict(req.headers)
        headers2 = dict(req2.headers)
        self.assertEqual(int(headers1.get('Content-Length', '0')),
            int(headers2.get('Content-Length', '0')))
        if 'Content-Length' in headers1:
            del headers1['Content-Length']
        if 'Content-Length' in headers2:
            del headers2['Content-Length']
        self.assertEqual(headers1, headers2)
        req_body = req.body
        req2_body = req2.body
        self.assertEqual(req_body, req2_body)


def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    request = Request(environ)
    request.remote_user = 'bob'
    return [ bytes_(x) for x in [
        'Hello world!\n',
        'The get is %r' % request.GET,
        ' and Val is %s\n' % repr(request.GET.get('name')),
        'The languages are: %s\n' % list(request.accept_language),
        'The accepttypes is: %s\n' %
            request.accept.best_match(['application/xml', 'text/html']),
        'post is %r\n' % request.POST,
        'params is %r\n' % request.params,
        'cookies is %r\n' % request.cookies,
        'body: %r\n' % request.body,
        'method: %s\n' % request.method,
        'remote_user: %r\n' % request.environ['REMOTE_USER'],
        'host_url: %r; application_url: %r; path_url: %r; url: %r\n' %
            (request.host_url,
             request.application_url,
             request.path_url,
             request.url),
        'urlvars: %r\n' % request.urlvars,
        'urlargs: %r\n' % (request.urlargs, ),
        'is_xhr: %r\n' % request.is_xhr,
        'if_modified_since: %r\n' % request.if_modified_since,
        'user_agent: %r\n' % request.user_agent,
        'if_none_match: %r\n' % request.if_none_match,
        ]]

_cgi_escaping_body = '''--boundary
Content-Disposition: form-data; name="%20%22""


--boundary--'''

def _norm_req(s):
    return b'\r\n'.join(s.strip().replace(b'\r', b'').split(b'\n'))

_test_req = b"""
POST /webob/ HTTP/1.0
Accept: */*
Cache-Control: max-age=0
Content-Type: multipart/form-data; boundary=----------------------------deb95b63e42a
Host: pythonpaste.org
User-Agent: UserAgent/1.0 (identifier-version) library/7.0 otherlibrary/0.8

------------------------------deb95b63e42a
Content-Disposition: form-data; name="foo"

foo
------------------------------deb95b63e42a
Content-Disposition: form-data; name="bar"; filename="bar.txt"
Content-type: application/octet-stream

these are the contents of the file 'bar.txt'

------------------------------deb95b63e42a--
"""

_test_req2 = b"""
POST / HTTP/1.0
Content-Length: 0

"""

_test_req = _norm_req(_test_req)
_test_req2 = _norm_req(_test_req2) + b'\r\n'

class UnseekableInput(object):
    def __init__(self, data):
        self.data = data
        self.pos = 0
    def read(self, size=-1):
        if size == -1:
            t = self.data[self.pos:]
            self.pos = len(self.data)
            return t
        else:
            assert(self.pos + size <= len(self.data))
            t = self.data[self.pos:self.pos+size]
            self.pos += size
            return t

class UnseekableInputWithSeek(UnseekableInput):
    def seek(self, pos, rel=0):
        raise IOError("Invalid seek!")


class FakeCGIBodyTests(unittest.TestCase):
    def test_encode_multipart_value_type_options(self):
        from cgi import FieldStorage
        from webob.request import BaseRequest, FakeCGIBody
        from webob.multidict import MultiDict
        multipart_type = 'multipart/form-data; boundary=foobar'
        from io import BytesIO
        body = (
            b'--foobar\r\n'
            b'Content-Disposition: form-data; name="bananas"; filename="bananas.txt"\r\n'
            b'Content-type: text/plain; charset="utf-9"\r\n'
            b'\r\n'
            b"these are the contents of the file 'bananas.txt'\r\n"
            b'\r\n'
            b'--foobar--')
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank('/').environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD='POST')
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        self.assertEqual(vars['bananas'].__class__, FieldStorage)
        fake_body = FakeCGIBody(vars, multipart_type)
        self.assertEqual(fake_body.read(), body)

    def test_encode_multipart_no_boundary(self):
        from webob.request import FakeCGIBody
        self.assertRaises(ValueError, FakeCGIBody, {}, 'multipart/form-data')

    def test_repr(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        body.read(1)
        import re
        self.assertEqual(
            re.sub(r'\b0x[0-9a-f]+\b', '<whereitsat>', repr(body)),
            "<FakeCGIBody at <whereitsat> viewing {'bananas': 'ba...nas'}>",
        )

    def test_fileno(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        self.assertEqual(body.fileno(), None)

    def test_iter(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        self.assertEqual(list(body), [
            b'--foobar\r\n',
            b'Content-Disposition: form-data; name="bananas"\r\n',
            b'\r\n',
            b'bananas\r\n',
            b'--foobar--',
         ])

    def test_readline(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        self.assertEqual(body.readline(), b'--foobar\r\n')
        self.assertEqual(
            body.readline(),
            b'Content-Disposition: form-data; name="bananas"\r\n')
        self.assertEqual(body.readline(), b'\r\n')
        self.assertEqual(body.readline(), b'bananas\r\n')
        self.assertEqual(body.readline(), b'--foobar--')
        # subsequent calls to readline will return ''

    def test_read_bad_content_type(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'}, 'application/jibberjabber')
        self.assertRaises(AssertionError, body.read)

    def test_read_urlencoded(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'application/x-www-form-urlencoded')
        self.assertEqual(body.read(), b'bananas=bananas')


class Test_cgi_FieldStorage__repr__patch(unittest.TestCase):
    def _callFUT(self, fake):
        from webob.request import _cgi_FieldStorage__repr__patch
        return _cgi_FieldStorage__repr__patch(fake)

    def test_with_file(self):
        class Fake(object):
            name = 'name'
            file = 'file'
            filename = 'filename'
            value = 'value'
        fake = Fake()
        result = self._callFUT(fake)
        self.assertEqual(result, "FieldStorage('name', 'filename')")

    def test_without_file(self):
        class Fake(object):
            name = 'name'
            file = None
            filename = 'filename'
            value = 'value'
        fake = Fake()
        result = self._callFUT(fake)
        self.assertEqual(result, "FieldStorage('name', 'filename', 'value')")


class TestLimitedLengthFile(unittest.TestCase):
    def _makeOne(self, file, maxlen):
        from webob.request import LimitedLengthFile
        return LimitedLengthFile(file, maxlen)

    def test_fileno(self):
        class DummyFile(object):
            def fileno(self):
                return 1
        dummyfile = DummyFile()
        inst = self._makeOne(dummyfile, 0)
        self.assertEqual(inst.fileno(), 1)

