import collections
import sys
import unittest
import warnings

from io import (
    BytesIO,
    StringIO,
    )

from webob.compat import (
    bytes_,
    native_,
    text_type,
    text_,
    PY3,
    )

class TestRequestCommon(unittest.TestCase):
    # unit tests of non-bytes-vs-text-specific methods of request object
    def _getTargetClass(self):
        from webob.request import Request
        return Request
        
    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_ctor_environ_getter_raises_WTF(self):
        self.assertRaises(TypeError, self._makeOne, {}, environ_getter=object())

    def test_ctor_wo_environ_raises_WTF(self):
        self.assertRaises(TypeError, self._makeOne, None)

    def test_ctor_w_environ(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.environ, environ)

    def test_ctor_w_non_utf8_charset(self):
        environ = {}
        self.assertRaises(DeprecationWarning, self._makeOne, environ,
                          charset='latin-1')

    def test_scheme(self):
        environ = {'wsgi.url_scheme': 'something:',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.scheme, 'something:')

    def test_body_file_getter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file is not INPUT)

    def test_body_file_getter_seekable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
            'webob.is_body_seekable': True,
        }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file is INPUT)

    def test_body_file_getter_cache(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file is req.body_file)

    def test_body_file_getter_unreadable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'REQUEST_METHOD': 'FOO'}
        req = self._makeOne(environ)
        assert req.body_file_raw is INPUT
        assert req.body_file is not INPUT
        assert req.body_file.read() == b''

    def test_body_file_setter_w_bytes(self):
        req = self._blankOne('/')
        self.assertRaises(DeprecationWarning, setattr, req, 'body_file', b'foo')

    def test_body_file_setter_non_bytes(self):
        BEFORE = BytesIO(b'before')
        AFTER =  BytesIO(b'after')
        environ = {'wsgi.input': BEFORE,
                   'CONTENT_LENGTH': len('before'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body_file = AFTER
        self.assertTrue(req.body_file is AFTER)
        self.assertEqual(req.content_length, None)

    def test_body_file_deleter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT,
                   'CONTENT_LENGTH': len(body),
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        del req.body_file
        self.assertEqual(req.body_file.getvalue(), b'')
        self.assertEqual(req.content_length, 0)

    def test_body_file_raw(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        self.assertTrue(req.body_file_raw is INPUT)

    def test_body_file_seekable_input_not_seekable(self):
        data = b'input'
        INPUT = BytesIO(data)
        INPUT.seek(1, 0) # consume
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': False,
                   'CONTENT_LENGTH': len(data)-1,
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        seekable = req.body_file_seekable
        self.assertTrue(seekable is not INPUT)
        self.assertEqual(seekable.getvalue(), b'nput')

    def test_body_file_seekable_input_is_seekable(self):
        INPUT = BytesIO(b'input')
        INPUT.seek(1, 0) # consume
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input')-1,
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        seekable = req.body_file_seekable
        self.assertTrue(seekable is INPUT)

    def test_urlvars_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlvars, {'foo': 'bar'})

    def test_urlvars_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlvars, {'foo': 'bar'})

    def test_urlvars_getter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))

    def test_urlvars_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['paste.urlvars'], {'baz': 'bam'})
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_urlvars_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {'baz': 'bam'}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_setter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        self.assertEqual(req.urlvars, {'baz': 'bam'})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {'baz': 'bam'}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_deleter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertTrue('paste.urlvars' not in environ)
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))

    def test_urlvars_deleter_w_wsgiorg_key_non_empty_tuple(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], (('a', 'b'), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_deleter_w_wsgiorg_key_empty_tuple(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlvars_deleter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        del req.urlvars
        self.assertEqual(req.urlvars, {})
        self.assertEqual(environ['wsgiorg.routing_args'], ((), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlargs_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlargs, ())

    def test_urlargs_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.urlargs, ('a', 'b'))

    def test_urlargs_getter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.urlargs, ())
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_urlargs_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {'foo': 'bar'}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlargs_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {'foo': 'bar'}))

    def test_urlargs_setter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        self.assertEqual(req.urlargs, ('a', 'b'))
        self.assertEqual(environ['wsgiorg.routing_args'],
                         (('a', 'b'), {}))
        self.assertTrue('paste.urlvars' not in environ)

    def test_urlargs_deleter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertEqual(environ['wsgiorg.routing_args'],
                         ((), {'foo': 'bar'}))

    def test_urlargs_deleter_w_wsgiorg_key_empty(self):
        environ = {'wsgiorg.routing_args': ((), {}),
                  }
        req = self._makeOne(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertTrue('paste.urlvars' not in environ)
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_urlargs_deleter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        del req.urlargs
        self.assertEqual(req.urlargs, ())
        self.assertTrue('paste.urlvars' not in environ)
        self.assertTrue('wsgiorg.routing_args' not in environ)

    def test_cookies_empty_environ(self):
        req = self._makeOne({})
        self.assertEqual(req.cookies, {})

    def test_cookies_is_mutable(self):
        req = self._makeOne({})
        cookies = req.cookies
        cookies['a'] = '1'
        self.assertEqual(req.cookies['a'], '1')

    def test_cookies_w_webob_parsed_cookies_matching_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b', {'a': 'b'}),
        }
        req = self._makeOne(environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    def test_cookies_w_webob_parsed_cookies_mismatched_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b;c=d', {'a': 'b', 'c': 'd'}),
        }
        req = self._makeOne(environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    def test_set_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._makeOne(environ)
        req.cookies = {'a':'1', 'b': '2'}
        self.assertEqual(req.cookies, {'a': '1', 'b':'2'})
        rcookies = [x.strip() for x in environ['HTTP_COOKIE'].split(';')]
        self.assertEqual(sorted(rcookies), ['a=1', 'b=2'])

    # body
    def test_body_getter(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.body, b'input')
        self.assertEqual(req.content_length, len(b'input'))

    def test_body_setter_None(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(b'input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body = None
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)
        self.assertTrue(req.is_body_seekable)

    def test_body_setter_non_string_raises(self):
        req = self._makeOne({})
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
        req = self._makeOne(environ)
        req.body = b'after'
        self.assertEqual(req.body, b'after')
        self.assertEqual(req.content_length, len(b'after'))
        self.assertTrue(req.is_body_seekable)

    def test_body_deleter_None(self):
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(data),
                   'REQUEST_METHOD': 'POST',
                  }
        req = self._makeOne(environ)
        del req.body
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)
        self.assertTrue(req.is_body_seekable)

    # POST
    def test_POST_not_POST_or_PUT(self):
        from webob.multidict import NoVars
        environ = {'REQUEST_METHOD': 'GET',
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertTrue(isinstance(result, NoVars))
        self.assertTrue(result.reason.startswith('Not a form request'))

    def test_POST_existing_cache_hit(self):
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'POST',
                   'webob._parsed_post_vars': ({'foo': 'bar'}, INPUT),
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertEqual(result, {'foo': 'bar'})

    def test_PUT_missing_content_type(self):
        from webob.multidict import NoVars
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'PUT',
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertTrue(isinstance(result, NoVars))
        self.assertTrue(result.reason.startswith('Not an HTML form submission'))

    def test_PUT_bad_content_type(self):
        from webob.multidict import NoVars
        data = b'input'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'PUT',
                   'CONTENT_TYPE': 'text/plain',
                  }
        req = self._makeOne(environ)
        result = req.POST
        self.assertTrue(isinstance(result, NoVars))
        self.assertTrue(result.reason.startswith('Not an HTML form submission'))

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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
        result = req.GET
        self.assertEqual(result, {'foo': '123'})
        req.query_string = 'foo=456'
        result = req.GET
        self.assertEqual(result, {'foo': '456'})
        req.query_string = ''
        result = req.GET
        self.assertEqual(result, {})

    def test_GET_updates_query_string(self):
        req = self._makeOne({})
        result = req.query_string
        self.assertEqual(result, '')
        req.GET['foo'] = '123'
        result = req.query_string
        self.assertEqual(result, 'foo=123')
        del req.GET['foo']
        result = req.query_string
        self.assertEqual(result, '')

    # cookies
    def test_cookies_wo_webob_parsed_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._blankOne('/', environ)
        self.assertEqual(req.cookies, {'a': 'b'})

    # copy
    def test_copy_get(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._blankOne('/', environ)
        clone = req.copy_get()
        for k, v in req.environ.items():
            if k in ('CONTENT_LENGTH', 'webob.is_body_seekable'):
                self.assertTrue(k not in clone.environ)
            elif k == 'wsgi.input':
                self.assertTrue(clone.environ[k] is not v)
            else:
                self.assertEqual(clone.environ[k], v)

    def test_remove_conditional_headers_accept_encoding(self):
        req = self._blankOne('/')
        req.accept_encoding='gzip,deflate'
        req.remove_conditional_headers()
        self.assertEqual(bool(req.accept_encoding), False)

    def test_remove_conditional_headers_if_modified_since(self):
        from webob.datetime_utils import UTC
        from datetime import datetime
        req = self._blankOne('/')
        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        req.remove_conditional_headers()
        self.assertEqual(req.if_modified_since, None)

    def test_remove_conditional_headers_if_none_match(self):
        req = self._blankOne('/')
        req.if_none_match = 'foo'
        assert req.if_none_match
        req.remove_conditional_headers()
        assert not req.if_none_match

    def test_remove_conditional_headers_if_range(self):
        req = self._blankOne('/')
        req.if_range = 'foo, bar'
        req.remove_conditional_headers()
        self.assertEqual(bool(req.if_range), False)

    def test_remove_conditional_headers_range(self):
        req = self._blankOne('/')
        req.range = 'bytes=0-100'
        req.remove_conditional_headers()
        self.assertEqual(req.range, None)

    def test_is_body_readable_POST(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'POST'})
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_GET(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'GET'})
        self.assertFalse(req.is_body_readable)

    def test_is_body_readable_unknown_method_and_content_length(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'WTF'})
        req.content_length = 10
        self.assertTrue(req.is_body_readable)

    def test_is_body_readable_special_flag(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD':'WTF',
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        self.assertTrue('HTTP_CACHE_CONTROL' not in req.environ)

    def test_cache_control_set_dict(self):
        environ = {}
        req = self._makeOne(environ)
        req.cache_control = {'max-age': 5}
        result = req.cache_control
        self.assertEqual(result.max_age, 5)

    def test_cache_control_set_object(self):
        from webob.cachecontrol import CacheControl
        environ = {}
        req = self._makeOne(environ)
        req.cache_control = CacheControl({'max-age': 5}, type='request')
        result = req.cache_control
        self.assertEqual(result.max_age, 5)

    def test_cache_control_gets_cached(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertTrue(req.cache_control is req.cache_control)

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
        req = self._makeOne(environ)
        def application(environ, start_response):
            start_response('200 OK', [('content-type', 'text/plain')])
            return ['...\n']
        status, headers, output = req.call_application(application)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')

    def test_call_application_provides_write(self):
        environ = {}
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                exc_info = sys.exc_info()
            start_response('200 OK', [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        self.assertRaises(RuntimeError, req.call_application, application)

    def test_call_application_returns_exc_info(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                exc_info = sys.exc_info()
            start_response('200 OK', [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        status, headers, output, exc_info = req.call_application(
            application, True)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers, [('content-type', 'text/plain')])
        self.assertEqual(''.join(output), '...\n')
        self.assertEqual(exc_info[0], RuntimeError)

    #get_response
    def test_blank__method_subtitution(self):
        request = self._blankOne('/', environ={'REQUEST_METHOD': 'PUT'})
        self.assertEqual(request.method, 'PUT')

        request = self._blankOne(
            '/', environ={'REQUEST_METHOD': 'PUT'}, POST={})
        self.assertEqual(request.method, 'PUT')

        request = self._blankOne(
            '/', environ={'REQUEST_METHOD': 'HEAD'}, POST={})
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_in_env(self):
        request = self._blankOne(
            '/', environ={'CONTENT_TYPE': 'application/json'})
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = self._blankOne(
            '/', environ={'CONTENT_TYPE': 'application/json'}, POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_in_headers(self):
        request = self._blankOne(
            '/', headers={'Content-type': 'application/json'})
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = self._blankOne(
            '/', headers={'Content-Type': 'application/json'}, POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__ctype_as_kw(self):
        request = self._blankOne('/', content_type='application/json')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'GET')

        request = self._blankOne('/', content_type='application/json',
                                         POST='')
        self.assertEqual(request.content_type, 'application/json')
        self.assertEqual(request.method, 'POST')

    def test_blank__str_post_data_for_unsupported_ctype(self):
        self.assertRaises(ValueError,
                          self._blankOne,
                          '/', content_type='application/json', POST={})

    def test_blank__post_urlencoded(self):
        request = self._blankOne('/', POST={'first':1, 'second':2})
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content_type,
                         'application/x-www-form-urlencoded')
        self.assertEqual(request.body, b'first=1&second=2')
        self.assertEqual(request.content_length, 16)

    def test_blank__post_multipart(self):
        request = self._blankOne(
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
        request = self._blankOne('/', POST=POST)
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
            ValueError, self._blankOne, '/', POST={'first':('filename1', '1')},
            content_type='application/x-www-form-urlencoded')

    #from_bytes
    def test_from_bytes_extra_data(self):
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type')
        cls = self._getTargetClass()
        self.assertRaises(ValueError, cls.from_bytes,
                _test_req_copy+b'EXTRA!')

    #as_bytes
    def test_as_bytes_skip_body(self):
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        body = req.as_bytes(skip_body=True)
        self.assertEqual(body.count(b'\r\n\r\n'), 0)
        self.assertEqual(req.as_bytes(skip_body=337), req.as_bytes())
        body = req.as_bytes(337-1).split(b'\r\n\r\n', 1)[1]
        self.assertEqual(body, b'<body skipped (len=337)>')

    def test_as_string_skip_body(self):
        with warnings.catch_warnings(record=True):
            cls = self._getTargetClass()
            req = cls.from_string(_test_req)
            body = req.as_string(skip_body=True)
            self.assertEqual(body.count(b'\r\n\r\n'), 0)
            self.assertEqual(req.as_string(skip_body=337), req.as_string())
            body = req.as_string(337-1).split(b'\r\n\r\n', 1)[1]
            self.assertEqual(body, b'<body skipped (len=337)>')
    
class TestBaseRequest(unittest.TestCase):
    # tests of methods of a base request which are encoding-specific
    def _getTargetClass(self):
        from webob.request import BaseRequest
        return BaseRequest
        
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
        result = req.method
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'OPTIONS')

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        result = req.http_version
        self.assertEqual(result, '1.1')

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.script_name, '/script')

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_info, '/path/info')

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
        self.assertEqual(req.remote_user, 'phred')

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_addr, '1.2.3.4')

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.query_string, 'foo=bar&baz=bam')

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_name, 'somehost.tld')

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
        self.assertEqual(req.uscript_name, '/script')

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertTrue(isinstance(req.upath_info, text_type))
        self.assertEqual(req.upath_info, '/path/info')

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        req.upath_info = text_('/another')
        self.assertTrue(isinstance(req.upath_info, text_type))
        self.assertEqual(req.upath_info, '/another')

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        self.assertEqual(req.content_type, 'text/xml')
        self.assertEqual(environ['CONTENT_TYPE'], 'text/xml;charset="utf8"')

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        self.assertEqual(headers,
                        {'Content-Type': CONTENT_TYPE,
                         'Content-Length': '123'})

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        self.assertEqual(req.headers,
                        {'Qux': 'Spam'})
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
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.2')

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, None)

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '4333')

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com:8888')

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.application_url
        self.assertEqual(app_url.__class__, str)
        self.assertEqual(app_url, 'http://localhost/%C3%AB')

    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.path_url
        self.assertEqual(app_url.__class__, str)
        self.assertEqual(app_url, 'http://localhost/%C3%AB/%C3%AB')

    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.path
        self.assertEqual(app_url.__class__, str)
        self.assertEqual(app_url, '/%C3%AB/%C3%AB')

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info')

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info?foo=bar&baz=bam')

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url, 'http://example.com/script/path/info')

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
                         'http://example.com/script/path/info?foo=bar&baz=bam')

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
                         'http://example.com/script/other/page')

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
                         'http://example.com/other/page')

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
                         'http://example.com/other/page')

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
                         'http://example.com/script/path/other/page')

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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, 'path')
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
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, 'example.com:8888')

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
        self.assertEqual(inst.encget('a', encattr='url_encoding'),
                         text_(b'\xc3\xab', 'utf-8'))

    def test_encget_with_encattr_latin_1(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        inst.my_encoding = 'latin-1'
        self.assertEqual(inst.encget('a', encattr='my_encoding'),
                         text_(b'\xc3\xab', 'latin-1'))

    def test_encget_no_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a'), val)

    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'http://localhost/%C3%AB/a')

    def test_header_getter(self):
        if PY3:
            val = b'abc'.decode('latin-1')
        else:
            val = b'abc'
        inst = self._makeOne({'HTTP_FLUB':val})
        result = inst.headers['Flub']
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'abc')

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        self.assertEqual(inst.json_body, {'a':'1'})

    def test_host_get(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'example.com')

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        self.assertEqual(result.__class__, str)
        self.assertEqual(result, 'example.com:80')

class TestLegacyRequest(unittest.TestCase):
    # tests of methods of a bytesrequest which deal with http environment vars
    def _getTargetClass(self):
        from webob.request import LegacyRequest
        return LegacyRequest
        
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
        self.assertEqual(req.method, 'OPTIONS')

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.http_version, '1.1')

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.script_name, '/script')

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_info, '/path/info')

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
        self.assertEqual(req.remote_user, 'phred')

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.remote_addr, '1.2.3.4')

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.query_string, 'foo=bar&baz=bam')

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.server_name, 'somehost.tld')

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
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.content_type, 'application/xml+foobar')

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        self.assertEqual(req.content_type, 'text/xml')
        self.assertEqual(environ['CONTENT_TYPE'], 'text/xml;charset="utf8"')

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        self.assertEqual(req.content_type, '')
        self.assertTrue('CONTENT_TYPE' not in environ)

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        self.assertEqual(headers,
                        {'Content-Type':CONTENT_TYPE,
                         'Content-Length': '123'})

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        self.assertEqual(req.headers,
                        {'Qux': 'Spam'})
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
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.1')

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, '192.168.1.2')

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        self.assertEqual(req.client_addr, None)

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '80')

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '443')

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '8888')

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_port, '4333')

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com')

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'http://example.com:8888')

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com')

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.host_url, 'https://example.com:4333')

    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.application_url
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(app_url, 'http://localhost/%C3%83%C2%AB')
        else:
            self.assertEqual(app_url, 'http://localhost/%C3%AB')

    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path_url
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(result,
                             'http://localhost/%C3%83%C2%AB/%C3%83%C2%AB')
        else:
            self.assertEqual(result, 'http://localhost/%C3%AB/%C3%AB')

    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(result, '/%C3%83%C2%AB/%C3%83%C2%AB')
        else:
            self.assertEqual(result, '/%C3%AB/%C3%AB')

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info')

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.path_qs, '/script/path/info?foo=bar&baz=bam')

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        self.assertEqual(req.url, 'http://example.com/script/path/info')

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
                         'http://example.com/script/path/info?foo=bar&baz=bam')

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
                         'http://example.com/script/other/page')

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
                         'http://example.com/other/page')

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
                         'http://example.com/other/page')

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
                         'http://example.com/script/path/other/page')

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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
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
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        self.assertEqual(peeked, 'path')
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
        self.assertEqual(req.host, 'example.com:8888')

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        self.assertEqual(req.host, 'example.com:8888')

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
        self.assertEqual(inst.encget('a', encattr='url_encoding'),
                         native_(b'\xc3\xab', 'latin-1'))

    def test_encget_no_encattr(self):
        if PY3:
            val = b'\xc3\xab'.decode('latin-1')
        else:
            val = b'\xc3\xab'
        inst = self._makeOne({'a':val})
        self.assertEqual(inst.encget('a'), native_(b'\xc3\xab', 'latin-1'))

    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        if PY3: # pragma: no cover
            # this result is why you should not use legacyrequest under py 3
            self.assertEqual(result, 'http://localhost/%C3%83%C2%AB/a')
        else:
            self.assertEqual(result, 'http://localhost/%C3%AB/a')

    def test_header_getter(self):
        if PY3:
            val = b'abc'.decode('latin-1')
        else:
            val = b'abc'
        inst = self._makeOne({'HTTP_FLUB':val})
        result = inst.headers['Flub']
        self.assertEqual(result, 'abc')

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        self.assertEqual(inst.json_body, {'a':'1'})

    def test_host_get_w_http_host(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        self.assertEqual(result, 'example.com')

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        self.assertEqual(result, 'example.com:80')

class TestRequestConstructorWarnings(unittest.TestCase):
    def _getTargetClass(self):
        from webob.request import Request
        return Request
        
    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def test_ctor_w_unicode_errors(self):
        with warnings.catch_warnings(record=True) as w:
            # still emit if warning was printed previously
            warnings.simplefilter('always')
            self._makeOne({}, unicode_errors=True)
        self.assertEqual(len(w), 1)

    def test_ctor_w_decode_param_names(self):
        with warnings.catch_warnings(record=True) as w:
            # still emit if warning was printed previously
            warnings.simplefilter('always')
            self._makeOne({}, decode_param_names=True)
        self.assertEqual(len(w), 1)

class TestRequestWithAdhocAttr(unittest.TestCase):
    def _blankOne(self, *arg, **kw):
        from webob.request import Request
        return Request.blank(*arg, **kw)

    def test_adhoc_attrs_set(self):
        req = self._blankOne('/')
        req.foo = 1
        self.assertEqual(req.environ['webob.adhoc_attrs'], {'foo': 1})

    def test_adhoc_attrs_set_nonadhoc(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs':{}})
        req.request_body_tempfile_limit = 1
        self.assertEqual(req.environ['webob.adhoc_attrs'], {})

    def test_adhoc_attrs_get(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        self.assertEqual(req.foo, 1)

    def test_adhoc_attrs_get_missing(self):
        req = self._blankOne('/')
        self.assertRaises(AttributeError, getattr, req, 'some_attr')

    def test_adhoc_attrs_del(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        del req.foo
        self.assertEqual(req.environ['webob.adhoc_attrs'], {})

    def test_adhoc_attrs_del_missing(self):
        req = self._blankOne('/')
        self.assertRaises(AttributeError, delattr, req, 'some_attr')

class TestRequest_functional(unittest.TestCase):
    # functional tests of request
    def _getTargetClass(self):
        from webob.request import Request
        return Request
    
    def _makeOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls(*arg, **kw)

    def _blankOne(self, *arg, **kw):
        cls = self._getTargetClass()
        return cls.blank(*arg, **kw)

    def test_gets(self):
        request = self._blankOne('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        self.assertEqual(status, '200 OK')
        res = b''.join(app_iter)
        self.assertTrue(b'Hello' in res)
        self.assertTrue(b"MultiDict([])" in res)
        self.assertTrue(b"post is <NoVars: Not a form request>" in res)

    def test_gets_with_query_string(self):
        request = self._blankOne('/?name=george')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"MultiDict" in res)
        self.assertTrue(b"'name'" in res)
        self.assertTrue(b"'george'" in res)
        self.assertTrue(b"Val is " in res)

    def test_language_parsing1(self):
        request = self._blankOne('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"The languages are: []" in res)

    def test_language_parsing2(self):
        request = self._blankOne(
            '/', headers={'Accept-Language': 'da, en-gb;q=0.8'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"languages are: ['da', 'en-gb']" in res)

    def test_language_parsing3(self):
        request = self._blankOne(
            '/',
            headers={'Accept-Language': 'en-gb;q=0.8, da'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"languages are: ['da', 'en-gb']" in res)

    def test_mime_parsing1(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'text/html'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"accepttypes is: text/html" in res)

    def test_mime_parsing2(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'application/xml'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"accepttypes is: application/xml" in res)

    def test_mime_parsing3(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'application/xml,*/*'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        self.assertTrue(b"accepttypes is: application/xml" in res)

    def test_accept_best_match(self):
        accept = self._blankOne('/').accept
        self.assertTrue(not accept)
        self.assertTrue(not self._blankOne('/', headers={'Accept': ''}).accept)
        req = self._blankOne('/', headers={'Accept':'text/plain'})
        self.assertTrue(req.accept)
        self.assertRaises(ValueError, req.accept.best_match, ['*/*'])
        req = self._blankOne('/', accept=['*/*','text/*'])
        self.assertEqual(
            req.accept.best_match(['application/x-foo', 'text/plain']),
            'text/plain')
        self.assertEqual(
            req.accept.best_match(['text/plain', 'application/x-foo']),
            'text/plain')
        req = self._blankOne('/', accept=['text/plain', 'message/*'])
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
            req = self._blankOne('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/xbel+xml', 'text/xml']
        tests = [('text/*;q=0.5,*/*; q=0.1', 'text/xml'),
                ('text/html,application/atom+xml; q=0.9', None)]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        supported = ['application/json', 'text/html']
        tests = [
            ('application/json, text/javascript, */*', 'application/json'),
            ('application/json, text/html;q=0.9', 'application/json'),
        ]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            self.assertEqual(req.accept.best_match(supported), get)

        offered = ['image/png', 'application/xml']
        tests = [
            ('image/png', 'image/png'),
            ('image/*', 'image/png'),
            ('image/*, application/xml', 'application/xml'),
        ]

        for accept, get in tests:
            req = self._blankOne('/', accept=accept)
            self.assertEqual(req.accept.best_match(offered), get)

    def test_headers(self):
        headers = {
            'If-Modified-Since': 'Sat, 29 Oct 1994 19:43:31 GMT',
            'Cookie': 'var1=value1',
            'User-Agent': 'Mozilla 4.0 (compatible; MSIE)',
            'If-None-Match': '"etag001", "etag002"',
            'X-Requested-With': 'XMLHttpRequest',
            }
        request = self._blankOne('/?foo=bar&baz', headers=headers)
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
            self.assertTrue(bytes_(thing) in res)

    def test_bad_cookie(self):
        req = self._blankOne('/')
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
        req = self._blankOne('/')
        req.headers['Cookie'] = 'foo="?foo"; Path=/'
        self.assertEqual(req.cookies, {'foo': '?foo'})

    def test_path_quoting(self):
        path = '/:@&+$,/bar'
        req = self._blankOne(path)
        self.assertEqual(req.path, path)
        self.assertTrue(req.url.endswith(path))

    def test_params(self):
        req = self._blankOne('/?a=1&b=2')
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
        req = self._blankOne('/?%E1%80%80=x')
        val = text_type(b'\u1000', 'unicode_escape')
        self.assertTrue(val in list(req.GET.keys()))
        self.assertEqual(req.GET[val], 'x')

    def test_copy_body(self):
        req = self._blankOne('/', method='POST', body=b'some text',
                            request_body_tempfile_limit=1)
        old_body_file = req.body_file_raw
        req.copy_body()
        self.assertTrue(req.body_file_raw is not old_body_file)
        req = self._blankOne('/', method='POST',
                body_file=UnseekableInput(b'0123456789'), content_length=10)
        self.assertTrue(not hasattr(req.body_file_raw, 'seek'))
        old_body_file = req.body_file_raw
        req.make_body_seekable()
        self.assertTrue(req.body_file_raw is not old_body_file)
        self.assertEqual(req.body, b'0123456789')
        old_body_file = req.body_file
        req.make_body_seekable()
        self.assertTrue(req.body_file_raw is old_body_file)
        self.assertTrue(req.body_file is old_body_file)

    def test_broken_seek(self):
        # copy() should work even when the input has a broken seek method
        req = self._blankOne('/', method='POST',
                body_file=UnseekableInputWithSeek(b'0123456789'),
                content_length=10)
        self.assertTrue(hasattr(req.body_file_raw, 'seek'))
        self.assertRaises(IOError, req.body_file_raw.seek, 0)
        old_body_file = req.body_file
        req2 = req.copy()
        self.assertTrue(req2.body_file_raw is req2.body_file is not
                        old_body_file)
        self.assertEqual(req2.body, b'0123456789')

    def test_set_body(self):
        req = self._blankOne('/', method='PUT', body=b'foo')
        self.assertTrue(req.is_body_seekable)
        self.assertEqual(req.body, b'foo')
        self.assertEqual(req.content_length, 3)
        del req.body
        self.assertEqual(req.body, b'')
        self.assertEqual(req.content_length, 0)

    def test_broken_clen_header(self):
        # if the UA sends "content_length: ..' header (the name is wrong)
        # it should not break the req.headers.items()
        req = self._blankOne('/')
        req.environ['HTTP_CONTENT_LENGTH'] = '0'
        req.headers.items()

    def test_nonstr_keys(self):
        # non-string env keys shouldn't break req.headers
        req = self._blankOne('/')
        req.environ[1] = 1
        req.headers.items()

    def test_authorization(self):
        req = self._blankOne('/')
        req.authorization = 'Digest uri="/?a=b"'
        self.assertEqual(req.authorization, ('Digest', {'uri': '/?a=b'}))

    def test_as_bytes(self):
        req = self._blankOne('http://example.com:8000/test.html?params')
        inp = BytesIO(req.as_bytes())
        self.equal_req(req, inp)

        req = self._blankOne('http://example.com/test2')
        req.method = 'POST'
        req.body = b'test=example'
        inp = BytesIO(req.as_bytes())
        self.equal_req(req, inp)

    def test_as_text(self):
        req = self._blankOne('http://example.com:8000/test.html?params')
        inp = StringIO(req.as_text())
        self.equal_req(req, inp)

        req = self._blankOne('http://example.com/test2')
        req.method = 'POST'
        req.body = b'test=example'
        inp = StringIO(req.as_text())
        self.equal_req(req, inp)

    def test_req_kw_none_val(self):
        request = self._makeOne({}, content_length=None)
        self.assertTrue('content-length' not in request.headers)
        self.assertTrue('content-type' not in request.headers)

    def test_env_keys(self):
        req = self._blankOne('/')
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
        self.assertRaises(TypeError, self._makeOne, environ=None)

    def test_unexpected_kw(self):
        # Passed an attr in kw that does not exist in the class, should
        # raise an error
        # Passed an attr in kw that does exist in the class, should be ok
        self.assertRaises(TypeError,
                          self._makeOne, {'a':1}, this_does_not_exist=1)
        r = self._makeOne({'a':1}, server_name='127.0.0.1')
        self.assertEqual(getattr(r, 'server_name', None), '127.0.0.1')

    def test_conttype_set_del(self):
        # Deleting content_type attr from a request should update the
        # environ dict
        # Assigning content_type should replace first option of the environ
        # dict
        r = self._makeOne({'a':1}, **{'content_type':'text/html'})
        self.assertTrue('CONTENT_TYPE' in r.environ)
        self.assertTrue(hasattr(r, 'content_type'))
        del r.content_type
        self.assertTrue('CONTENT_TYPE' not in r.environ)
        a = self._makeOne({'a':1},
                content_type='charset=utf-8;application/atom+xml;type=entry')
        self.assertTrue(a.environ['CONTENT_TYPE']==
                'charset=utf-8;application/atom+xml;type=entry')
        a.content_type = 'charset=utf-8'
        self.assertTrue(a.environ['CONTENT_TYPE']==
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
        r = self._makeOne({'a':1}, headers=headers)
        for i in headers.keys():
            self.assertTrue(i in r.headers and
                'HTTP_'+i.upper().replace('-', '_') in r.environ)
        r.headers = {'Server':'Apache'}
        self.assertEqual(list(r.environ.keys()), ['a',  'HTTP_SERVER'])

    def test_host_url(self):
        # Request has a read only property host_url that combines several
        # keys to create a host_url
        a = self._makeOne(
            {'wsgi.url_scheme':'http'}, **{'host':'www.example.com'})
        self.assertEqual(a.host_url, 'http://www.example.com')
        a = self._makeOne(
            {'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                                'server_port':5000})
        self.assertEqual(a.host_url, 'http://localhost:5000')
        a = self._makeOne(
            {'wsgi.url_scheme':'https'}, **{'server_name':'localhost',
                                            'server_port':443})
        self.assertEqual(a.host_url, 'https://localhost')

    def test_path_info_p(self):
        # Peek path_info to see what's coming
        # Pop path_info until there's nothing remaining
        a = self._makeOne({'a':1}, **{'path_info':'/foo/bar','script_name':''})
        self.assertEqual(a.path_info_peek(), 'foo')
        self.assertEqual(a.path_info_pop(), 'foo')
        self.assertEqual(a.path_info_peek(), 'bar')
        self.assertEqual(a.path_info_pop(), 'bar')
        self.assertEqual(a.path_info_peek(), None)
        self.assertEqual(a.path_info_pop(), None)

    def test_urlvars_property(self):
        # Testing urlvars setter/getter/deleter
        a = self._makeOne({'wsgiorg.routing_args':((),{'x':'y'}),
                           'paste.urlvars':{'test':'value'}})
        a.urlvars = {'hello':'world'}
        self.assertTrue('paste.urlvars' not in a.environ)
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ((), {'hello':'world'}))
        del a.urlvars
        self.assertTrue('wsgiorg.routing_args' not in a.environ)
        a = self._makeOne({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlvars, {'test':'value'})
        a.urlvars = {'hello':'world'}
        self.assertEqual(a.environ['paste.urlvars'], {'hello':'world'})
        del a.urlvars
        self.assertTrue('paste.urlvars' not in a.environ)

    def test_urlargs_property(self):
        # Testing urlargs setter/getter/deleter
        a = self._makeOne({'paste.urlvars':{'test':'value'}})
        self.assertEqual(a.urlargs, ())
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {'test':'value'}))
        a = self._makeOne({'a':1})
        a.urlargs = {'hello':'world'}
        self.assertEqual(a.environ['wsgiorg.routing_args'],
                         ({'hello':'world'}, {}))
        del a.urlargs
        self.assertTrue('wsgiorg.routing_args' not in a.environ)

    def test_host_property(self):
        # Testing host setter/getter/deleter
        a = self._makeOne({'wsgi.url_scheme':'http'}, server_name='localhost',
                          server_port=5000)
        self.assertEqual(a.host, "localhost:5000")
        a.host = "localhost:5000"
        self.assertTrue('HTTP_HOST' in a.environ)
        del a.host
        self.assertTrue('HTTP_HOST' not in a.environ)

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
        cls = self._getTargetClass()
        limit = cls.request_body_tempfile_limit
        len_strl = limit // len(string.ascii_letters) + 1
        r = self._makeOne(
            {'a':1, 'REQUEST_METHOD': 'POST'},
            body_file=DummyIO(bytes_(string.ascii_letters) * len_strl))
        self.assertEqual(len(r.body), len(string.ascii_letters*len_strl)-1)
        self.assertRaises(TypeError,
                          setattr, r, 'body', text_('hello world'))
        r.body = None
        self.assertEqual(r.body, b'')
        r = self._makeOne({'a':1}, method='PUT', body_file=DummyIO(
            bytes_(string.ascii_letters)))
        self.assertTrue(not hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assertTrue(hasattr(r.body_file_raw, 'seek'))
        r = self._makeOne({'a':1}, method='PUT',
                          body_file=BytesIO(bytes_(string.ascii_letters)))
        self.assertTrue(hasattr(r.body_file_raw, 'seek'))
        r.make_body_seekable()
        self.assertTrue(hasattr(r.body_file_raw, 'seek'))

    def test_repr_invalid(self):
        # If we have an invalid WSGI environ, the repr should tell us.
        req = self._makeOne({'CONTENT_LENGTH':'0', 'body':''})
        self.assertTrue(repr(req).endswith('(invalid WSGI environ)>'))

    def test_from_garbage_file(self):
        # If we pass a file with garbage to from_file method it should
        # raise an error plus missing bits in from_file method
        io = BytesIO(b'hello world')

        cls = self._getTargetClass()
        self.assertRaises(ValueError, cls.from_file, io)
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
        req = cls.from_file(val_file)
        self.assertTrue(isinstance(req, cls))
        self.assertTrue(not repr(req).endswith('(invalid WSGI environ)>'))
        val_file = BytesIO(
            b"GET /webob/ HTTP/1.1\n"
            b"Host pythonpaste.org\n"
        )
        self.assertRaises(ValueError, cls.from_file, val_file)

    def test_from_bytes(self):
        # A valid request without a Content-Length header should still read
        # the full body.
        # Also test parity between as_string and from_bytes / from_file.
        import cgi
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        self.assertTrue(isinstance(req, cls))
        self.assertTrue(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assertTrue('\n' not in req.http_version or '\r' in
                        req.http_version)
        self.assertTrue(',' not in req.host)
        self.assertTrue(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assertTrue(b'foo' in req.body)
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        self.assertTrue(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assertTrue(isinstance(bar, cgi.FieldStorage))
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

        req2 = cls.from_bytes(_test_req2)
        self.assertTrue('host' not in req2.headers)
        self.assertEqual(req2.as_bytes(), _test_req2.rstrip())
        self.assertRaises(ValueError, cls.from_bytes, _test_req2 + b'xx')

    def test_from_text(self):
        import cgi
        cls = self._getTargetClass()
        req = cls.from_text(text_(_test_req, 'utf-8'))
        self.assertTrue(isinstance(req, cls))
        self.assertTrue(not repr(req).endswith('(invalid WSGI environ)>'))
        self.assertTrue('\n' not in req.http_version or '\r' in
                        req.http_version)
        self.assertTrue(',' not in req.host)
        self.assertTrue(req.content_length is not None)
        self.assertEqual(req.content_length, 337)
        self.assertTrue(b'foo' in req.body)
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        self.assertTrue(bar_contents in req.body)
        self.assertEqual(req.params['foo'], 'foo')
        bar = req.params['bar']
        self.assertTrue(isinstance(bar, cgi.FieldStorage))
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

        req2 = cls.from_bytes(_test_req2)
        self.assertTrue('host' not in req2.headers)
        self.assertEqual(req2.as_bytes(), _test_req2.rstrip())
        self.assertRaises(ValueError, cls.from_bytes, _test_req2 + b'xx')

    def test_blank(self):
        # BaseRequest.blank class method
        self.assertRaises(ValueError, self._blankOne,
                    'www.example.com/foo?hello=world', None,
                    'www.example.com/foo?hello=world')
        self.assertRaises(ValueError, self._blankOne,
                    'gopher.example.com/foo?hello=world', None,
                    'gopher://gopher.example.com')
        req = self._blankOne('www.example.com/foo?hello=world', None,
                             'http://www.example.com')
        self.assertEqual(req.environ.get('HTTP_HOST', None),
                         'www.example.com:80')
        self.assertEqual(req.environ.get('PATH_INFO', None),
                         'www.example.com/foo')
        self.assertEqual(req.environ.get('QUERY_STRING', None),
                         'hello=world')
        self.assertEqual(req.environ.get('REQUEST_METHOD', None), 'GET')
        req = self._blankOne('www.example.com/secure?hello=world', None,
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


    def test_post_does_not_reparse(self):
        # test that there's no repetitive parsing is happening on every
        # req.POST access
        req = self._blankOne('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        f0 = req.body_file_raw
        post1 = req.POST
        f1 = req.body_file_raw
        self.assertTrue(f1 is not f0)
        post2 = req.POST
        f2 = req.body_file_raw
        self.assertTrue(post1 is post2)
        self.assertTrue(f1 is f2)


    def test_middleware_body(self):
        def app(env, sr):
            sr('200 OK', [])
            return [env['wsgi.input'].read()]

        def mw(env, sr):
            req = self._makeOne(env)
            data = req.body_file.read()
            resp = req.get_response(app)
            resp.headers['x-data'] = data
            return resp(env, sr)

        req = self._blankOne('/', method='PUT', body=b'abc')
        resp = req.get_response(mw)
        self.assertEqual(resp.body, b'abc')
        self.assertEqual(resp.headers['x-data'], b'abc')

    def test_body_file_noseek(self):
        req = self._blankOne('/', method='PUT', body=b'abc')
        lst = [req.body_file.read(1) for i in range(3)]
        self.assertEqual(lst, [b'a', b'b', b'c'])

    def test_cgi_escaping_fix(self):
        req = self._blankOne('/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        self.assertEqual(list(req.POST.keys()), ['%20%22"'])
        req.body_file.read()
        self.assertEqual(list(req.POST.keys()), ['%20%22"'])

    def test_content_type_none(self):
        r = self._blankOne('/', content_type='text/html')
        self.assertEqual(r.content_type, 'text/html')
        r.content_type = None

    def test_body_file_seekable(self):
        r = self._blankOne('/', method='POST')
        r.body_file = BytesIO(b'body')
        self.assertEqual(r.body_file_seekable.read(), b'body')

    def test_request_init(self):
        # port from doctest (docs/reference.txt)
        req = self._blankOne('/article?id=1')
        self.assertEqual(req.environ['HTTP_HOST'], 'localhost:80')
        self.assertEqual(req.environ['PATH_INFO'], '/article')
        self.assertEqual(req.environ['QUERY_STRING'], 'id=1')
        self.assertEqual(req.environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(req.environ['SCRIPT_NAME'], '')
        self.assertEqual(req.environ['SERVER_NAME'], 'localhost')
        self.assertEqual(req.environ['SERVER_PORT'], '80')
        self.assertEqual(req.environ['SERVER_PROTOCOL'], 'HTTP/1.0')
        self.assertTrue(hasattr(req.environ['wsgi.errors'], 'write') and
                     hasattr(req.environ['wsgi.errors'], 'flush'))
        self.assertTrue(hasattr(req.environ['wsgi.input'], 'next') or
                     hasattr(req.environ['wsgi.input'], '__next__'))
        self.assertEqual(req.environ['wsgi.multiprocess'], False)
        self.assertEqual(req.environ['wsgi.multithread'], False)
        self.assertEqual(req.environ['wsgi.run_once'], False)
        self.assertEqual(req.environ['wsgi.url_scheme'], 'http')
        self.assertEqual(req.environ['wsgi.version'], (1, 0))

        # Test body
        self.assertTrue(hasattr(req.body_file, 'read'))
        self.assertEqual(req.body, b'')
        req.method = 'PUT'
        req.body = b'test'
        self.assertTrue(hasattr(req.body_file, 'read'))
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
        self.assertTrue(req.remote_user is None)
        self.assertTrue(req.remote_addr is None)
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
        req = self._blankOne('/test?check=a&check=b&name=Bob')
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        self.assertEqual(req.GET, GET)
        self.assertEqual(req.GET['check'], 'b')
        self.assertEqual(req.GET.getall('check'), ['a', 'b'])
        self.assertEqual(list(req.GET.items()),
                         [('check', 'a'), ('check', 'b'), ('name', 'Bob')])

        self.assertTrue(isinstance(req.POST, NoVars))
        # NoVars can be read like a dict, but not written
        self.assertEqual(list(req.POST.items()), [])
        req.method = 'POST'
        req.body = b'name=Joe&email=joe@example.com'
        self.assertEqual(req.POST,
                         MultiDict([('name', 'Joe'),
                                    ('email', 'joe@example.com')]))
        self.assertEqual(req.POST['name'], 'Joe')

        self.assertTrue(isinstance(req.params, NestedMultiDict))
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
        req = self._blankOne('/test?check=a&check=b&name=Bob')
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
        self.assertTrue(isinstance(req.cookies, collections.MutableMapping))
        self.assertEqual(list(req.cookies.items()), [('test', 'value')])
        req.charset = None
        self.assertEqual(req.cookies, {'test': 'value'})

        # Accept-* headers
        self.assertTrue('text/html' in req.accept)
        req.accept = 'text/html;q=0.5, application/xhtml+xml;q=1'
        self.assertTrue(isinstance(req.accept, MIMEAccept))
        self.assertTrue('text/html' in req.accept)

        self.assertRaises(DeprecationWarning,
                          req.accept.first_match, ['text/html'])
        self.assertEqual(req.accept.best_match(['text/html',
                                                'application/xhtml+xml']),
                         'application/xhtml+xml')

        req.accept_language = 'es, pt-BR'
        self.assertEqual(req.accept_language.best_match(['es']), 'es')

        # Conditional Requests
        server_token = 'opaque-token'
        # shouldn't return 304
        self.assertTrue(not server_token in req.if_none_match)
        req.if_none_match = server_token
        self.assertTrue(isinstance(req.if_none_match, ETagMatcher))
        # You *should* return 304
        self.assertTrue(server_token in req.if_none_match)
        # if_none_match should use weak matching
        weak_token = 'W/"%s"' % server_token
        req.if_none_match = weak_token
        assert req.headers['if-none-match'] == weak_token
        self.assertTrue(server_token in req.if_none_match)


        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        self.assertEqual(req.headers['If-Modified-Since'],
                         'Sun, 01 Jan 2006 12:00:00 GMT')
        server_modified = datetime(2005, 1, 1, 12, 0, tzinfo=UTC)
        self.assertTrue(req.if_modified_since)
        self.assertTrue(req.if_modified_since >= server_modified)

        self.assertTrue(not req.if_range)
        self.assertTrue(Response(etag='some-etag',
                              last_modified=datetime(2005, 1, 1, 12, 0))
            in req.if_range)
        req.if_range = 'opaque-etag'
        self.assertTrue(Response(etag='other-etag') not in req.if_range)
        self.assertTrue(Response(etag='opaque-etag') in req.if_range)

        res = Response(etag='opaque-etag')
        self.assertTrue(res in req.if_range)

        req.range = 'bytes=0-100'
        self.assertTrue(isinstance(req.range, Range))
        self.assertEqual(tuple(req.range), (0, 101))
        cr = req.range.content_range(length=1000)
        self.assertEqual(tuple(cr), (0, 101, 1000))

        self.assertTrue(server_token in req.if_match)
        # No If-Match means everything is ok
        req.if_match = server_token
        self.assertTrue(server_token in req.if_match)
        # Still OK
        req.if_match = 'other-token'
        # Not OK, should return 412 Precondition Failed:
        self.assertTrue(not server_token in req.if_match)

    def test_call_WSGI_app(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'Hi!']
        self.assertEqual(req.call_application(wsgi_app),
                         ('200 OK', [('Content-type', 'text/plain')],
                          [b'Hi!']))

        res = req.get_response(wsgi_app)
        from webob.response import Response
        self.assertTrue(isinstance(res, Response))
        self.assertEqual(res.status, '200 OK')
        from webob.headers import ResponseHeaders
        self.assertTrue(isinstance(res.headers, ResponseHeaders))
        self.assertEqual(list(res.headers.items()),
                         [('Content-type', 'text/plain')])
        self.assertEqual(res.body, b'Hi!')

    def test_get_response_catch_exc_info_true(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return [b'Hi!']
        res = req.get_response(wsgi_app, catch_exc_info=True)
        from webob.response import Response
        self.assertTrue(isinstance(res, Response))
        self.assertEqual(res.status, '200 OK')
        from webob.headers import ResponseHeaders
        self.assertTrue(isinstance(res.headers, ResponseHeaders))
        self.assertEqual(list(res.headers.items()),
                         [('Content-type', 'text/plain')])
        self.assertEqual(res.body, b'Hi!')

    def equal_req(self, req, inp):
        cls = self._getTargetClass()
        req2 = cls.from_file(inp)
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


class Test_environ_from_url(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from webob.request import environ_from_url
        return environ_from_url(*arg, **kw)

    def test_environ_from_url(self):
        # Generating an environ just from an url plus testing environ_add_POST
        self.assertRaises(TypeError, self._callFUT,
                    'http://www.example.com/foo?bar=baz#qux')
        self.assertRaises(TypeError, self._callFUT,
                    'gopher://gopher.example.com')
        req = self._callFUT('http://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:80')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '80')
        req = self._callFUT('https://www.example.com/foo?bar=baz')
        self.assertEqual(req.get('HTTP_HOST', None), 'www.example.com:443')
        self.assertEqual(req.get('PATH_INFO', None), '/foo')
        self.assertEqual(req.get('QUERY_STRING', None), 'bar=baz')
        self.assertEqual(req.get('REQUEST_METHOD', None), 'GET')
        self.assertEqual(req.get('SCRIPT_NAME', None), '')
        self.assertEqual(req.get('SERVER_NAME', None), 'www.example.com')
        self.assertEqual(req.get('SERVER_PORT', None), '443')


        from webob.request import environ_add_POST

        environ_add_POST(req, None)
        self.assertTrue('CONTENT_TYPE' not in req)
        self.assertTrue('CONTENT_LENGTH' not in req)
        environ_add_POST(req, {'hello':'world'})
        self.assertTrue(req.get('HTTP_HOST', None), 'www.example.com:443')
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
        from webob.request import Request
        env = self._callFUT('/%E6%B5%81')
        self.assertEqual(env['PATH_INFO'], '/\xe6\xb5\x81')
        request = Request(env)
        expected = text_(b'/\xe6\xb5\x81', 'utf-8') # u'/\u6d41'
        self.assertEqual(request.path_info, expected)
        self.assertEqual(request.upath_info, expected)

def simpleapp(environ, start_response):
    from webob.request import Request
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

