# -*- coding: utf-8 -*-

import sys
import warnings

from io import (
    BytesIO,
    StringIO,
    )

import pytest

from webob.acceptparse import (
    AcceptCharsetInvalidHeader,
    AcceptCharsetNoHeader,
    AcceptCharsetValidHeader,
    AcceptEncodingInvalidHeader,
    AcceptEncodingNoHeader,
    AcceptEncodingValidHeader,
    AcceptInvalidHeader,
    AcceptLanguageInvalidHeader,
    AcceptLanguageNoHeader,
    AcceptLanguageValidHeader,
    AcceptNoHeader,
    AcceptValidHeader,
    )
from webob.compat import (
    MutableMapping,
    bytes_,
    native_,
    text_type,
    text_,
    )
from webob.multidict import NoVars


py2only = pytest.mark.skipif("sys.version_info >= (3, 0)")
py3only = pytest.mark.skipif("sys.version_info < (3, 0)")


class TestRequestCommon(object):
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
        with pytest.raises(TypeError):
            self._makeOne({}, environ_getter=object())

    def test_ctor_wo_environ_raises_WTF(self):
        with pytest.raises(TypeError):
            self._makeOne(None)

    def test_ctor_w_environ(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.environ == environ

    def test_ctor_w_non_utf8_charset(self):
        environ = {}
        with pytest.raises(DeprecationWarning):
            self._makeOne(environ, charset='latin-1')

    def test_scheme(self):
        environ = {'wsgi.url_scheme': 'something:'}
        req = self._makeOne(environ)
        assert req.scheme == 'something:'

    def test_body_file_getter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {
            'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        assert req.body_file is not INPUT

    def test_body_file_getter_seekable(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {
            'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
            'webob.is_body_seekable': True,
        }
        req = self._makeOne(environ)
        assert req.body_file is INPUT

    def test_body_file_getter_cache(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {
            'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        assert req.body_file is req.body_file

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
        with pytest.raises(ValueError):
            setattr(req, 'body_file', b'foo')

    def test_body_file_setter_non_bytes(self):
        BEFORE = BytesIO(b'before')
        AFTER = BytesIO(b'after')
        environ = {
            'wsgi.input': BEFORE,
            'CONTENT_LENGTH': len('before'),
            'REQUEST_METHOD': 'POST'
        }
        req = self._makeOne(environ)
        req.body_file = AFTER
        assert req.body_file is AFTER
        assert req.content_length == None

    def test_body_file_deleter(self):
        body = b'input'
        INPUT = BytesIO(body)
        environ = {
            'wsgi.input': INPUT,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        del req.body_file
        assert req.body_file.getvalue() == b''
        assert req.content_length == 0

    def test_body_file_raw(self):
        INPUT = BytesIO(b'input')
        environ = {
            'wsgi.input': INPUT,
            'CONTENT_LENGTH': len('input'),
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        assert req.body_file_raw is INPUT

    def test_body_file_seekable_input_not_seekable(self):
        data = b'input'
        INPUT = BytesIO(data)
        INPUT.seek(1, 0) # consume
        environ = {
            'wsgi.input': INPUT,
            'webob.is_body_seekable': False,
            'CONTENT_LENGTH': len(data) - 1,
            'REQUEST_METHOD': 'POST',
        }
        req = self._makeOne(environ)
        seekable = req.body_file_seekable
        assert seekable is not INPUT
        assert seekable.getvalue() == b'nput'

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
        assert seekable is INPUT

    def test_urlvars_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        assert req.urlvars == {'foo': 'bar'}

    def test_urlvars_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        assert req.urlvars == {'foo': 'bar'}

    def test_urlvars_getter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.urlvars == {}
        assert environ['wsgiorg.routing_args'] == ((), {})

    def test_urlvars_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        assert req.urlvars == {'baz': 'bam'}
        assert environ['paste.urlvars'] == {'baz': 'bam'}
        assert 'wsgiorg.routing_args' not in environ

    def test_urlvars_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        assert req.urlvars == {'baz': 'bam'}
        assert environ['wsgiorg.routing_args'] == ((), {'baz': 'bam'})
        assert 'paste.urlvars' not in environ

    def test_urlvars_setter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        req.urlvars = {'baz': 'bam'}
        assert req.urlvars == {'baz': 'bam'}
        assert environ['wsgiorg.routing_args'] == ((), {'baz': 'bam'})
        assert 'paste.urlvars' not in environ

    def test_urlvars_deleter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        assert req.urlvars == {}
        assert 'paste.urlvars' not in environ
        assert environ['wsgiorg.routing_args'] == ((), {})

    def test_urlvars_deleter_w_wsgiorg_key_non_empty_tuple(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        assert req.urlvars == {}
        assert environ['wsgiorg.routing_args'] == (('a', 'b'), {})
        assert 'paste.urlvars' not in environ

    def test_urlvars_deleter_w_wsgiorg_key_empty_tuple(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                   'paste.urlvars': {'qux': 'spam'},
                  }
        req = self._makeOne(environ)
        del req.urlvars
        assert req.urlvars == {}
        assert environ['wsgiorg.routing_args'] == ((), {})
        assert 'paste.urlvars' not in environ

    def test_urlvars_deleter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        del req.urlvars
        assert req.urlvars == {}
        assert environ['wsgiorg.routing_args'] == ((), {})
        assert 'paste.urlvars' not in environ

    def test_urlargs_getter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        assert req.urlargs == ()

    def test_urlargs_getter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        assert req.urlargs, ('a' == 'b')

    def test_urlargs_getter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.urlargs == ()
        assert 'wsgiorg.routing_args' not in environ

    def test_urlargs_setter_w_paste_key(self):
        environ = {'paste.urlvars': {'foo': 'bar'},
                  }
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        assert req.urlargs == ('a', 'b')
        assert environ['wsgiorg.routing_args'] == (('a', 'b'), {'foo': 'bar'})
        assert 'paste.urlvars' not in environ

    def test_urlargs_setter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': ((), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        assert req.urlargs == ('a', 'b')
        assert environ['wsgiorg.routing_args'] == (('a', 'b'), {'foo': 'bar'})

    def test_urlargs_setter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        req.urlargs = ('a', 'b')
        assert req.urlargs == ('a', 'b')
        assert environ['wsgiorg.routing_args'] == (('a', 'b'), {})
        assert 'paste.urlvars' not in environ

    def test_urlargs_deleter_w_wsgiorg_key(self):
        environ = {'wsgiorg.routing_args': (('a', 'b'), {'foo': 'bar'}),
                  }
        req = self._makeOne(environ)
        del req.urlargs
        assert req.urlargs == ()
        assert environ['wsgiorg.routing_args'] == ((), {'foo': 'bar'})

    def test_urlargs_deleter_w_wsgiorg_key_empty(self):
        environ = {'wsgiorg.routing_args': ((), {}),
                  }
        req = self._makeOne(environ)
        del req.urlargs
        assert req.urlargs == ()
        assert 'paste.urlvars' not in environ
        assert 'wsgiorg.routing_args' not in environ

    def test_urlargs_deleter_wo_keys(self):
        environ = {}
        req = self._makeOne(environ)
        del req.urlargs
        assert req.urlargs == ()
        assert 'paste.urlvars' not in environ
        assert 'wsgiorg.routing_args' not in environ

    def test_cookies_empty_environ(self):
        req = self._makeOne({})
        assert req.cookies == {}

    def test_cookies_is_mutable(self):
        req = self._makeOne({})
        cookies = req.cookies
        cookies['a'] = '1'
        assert req.cookies['a'] == '1'

    def test_cookies_w_webob_parsed_cookies_matching_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b', {'a': 'b'}),
        }
        req = self._makeOne(environ)
        assert req.cookies == {'a': 'b'}

    def test_cookies_w_webob_parsed_cookies_mismatched_source(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
            'webob._parsed_cookies': ('a=b;c=d', {'a': 'b', 'c': 'd'}),
        }
        req = self._makeOne(environ)
        assert req.cookies == {'a': 'b'}

    def test_set_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._makeOne(environ)
        req.cookies = {'a':'1', 'b': '2'}
        assert req.cookies == {'a': '1', 'b':'2'}
        rcookies = [x.strip() for x in environ['HTTP_COOKIE'].split(';')]
        assert sorted(rcookies) == ['a=1', 'b=2']

    # body
    def test_body_getter(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        assert req.body == b'input'
        assert req.content_length == len(b'input')

    def test_body_setter_None(self):
        INPUT = BytesIO(b'input')
        environ = {'wsgi.input': INPUT,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len(b'input'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body = None
        assert req.body == b''
        assert req.content_length == 0
        assert req.is_body_seekable

    def test_body_setter_non_string_raises(self):
        req = self._makeOne({})
        def _test():
            req.body = object()
        with pytest.raises(TypeError):
            _test()

    def test_body_setter_value(self):
        BEFORE = BytesIO(b'before')
        environ = {'wsgi.input': BEFORE,
                   'webob.is_body_seekable': True,
                   'CONTENT_LENGTH': len('before'),
                   'REQUEST_METHOD': 'POST'
                  }
        req = self._makeOne(environ)
        req.body = b'after'
        assert req.body == b'after'
        assert req.content_length == len(b'after')
        assert req.is_body_seekable

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
        assert req.body == b''
        assert req.content_length == 0
        assert req.is_body_seekable

    # JSON

    def test_json_body(self):
        body = b'{"a":1}'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        assert req.json == {"a": 1}
        assert req.json_body == {"a": 1}
        req.json = {"b": 2}
        assert req.body == b'{"b":2}'
        del req.json
        assert req.body == b''

    def test_json_body_array(self):
        body = b'[{"a":1}, {"b":2}]'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        assert req.json, [{"a": 1} == {"b": 2}]
        assert req.json_body == [{"a": 1}, {"b": 2}]
        req.json = [{"b": 2}]
        assert req.body == b'[{"b":2}]'
        del req.json
        assert req.body == b''

    # .text

    def test_text_body(self):
        body = b'test'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        assert req.body == b'test'
        assert req.text == 'test'
        req.text = text_('\u1000')
        assert req.body == '\u1000'.encode(req.charset)
        del req.text
        assert req.body == b''
        def set_bad_text():
            req.text = 1
        with pytest.raises(TypeError):
            set_bad_text()

    def test__text_get_without_charset(self):
        body = b'test'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        req._charset = ''
        with pytest.raises(AttributeError):
            getattr(req, 'text')

    def test__text_set_without_charset(self):
        body = b'test'
        INPUT = BytesIO(body)
        environ = {'wsgi.input': INPUT, 'CONTENT_LENGTH': str(len(body))}
        req = self._makeOne(environ)
        req._charset = ''
        with pytest.raises(AttributeError):
            setattr(req, 'text', 'abc')

    # POST
    def test_POST_not_POST_or_PUT(self):
        environ = {'REQUEST_METHOD': 'GET'}
        req = self._makeOne(environ)
        result = req.POST
        assert isinstance(result, NoVars)
        assert result.reason.startswith('Not an HTML form')

    @pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
    def test_POST_existing_cache_hit(self, method):
        data = b'input'
        wsgi_input = BytesIO(data)
        environ = {
            'wsgi.input': wsgi_input,
            'REQUEST_METHOD': method,
            'webob._parsed_post_vars': ({'foo': 'bar'}, wsgi_input),
        }
        req = self._makeOne(environ)
        result = req.POST
        assert result == {'foo': 'bar'}

    @pytest.mark.parametrize('method', ['PUT', 'PATCH', 'DELETE'])
    def test_POST_not_POST_missing_content_type(self, method):
        data = b'input'
        wsgi_input = BytesIO(data)
        environ = {
            'wsgi.input': wsgi_input,
            'REQUEST_METHOD': method,
        }
        req = self._makeOne(environ)
        result = req.POST
        assert isinstance(result, NoVars)
        assert result.reason.startswith('Not an HTML form submission')

    def test_POST_missing_content_type(self):
        data = b'var1=value1&var2=value2&rep=1&rep=2'
        INPUT = BytesIO(data)
        environ = {'wsgi.input': INPUT,
                   'REQUEST_METHOD': 'POST',
                   'CONTENT_LENGTH': len(data),
                   'webob.is_body_seekable': True,
                  }
        req = self._makeOne(environ)
        result = req.POST
        assert result['var1'] == 'value1'

    @pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
    def test_POST_json_no_content_type(self, method):
        data = b'{"password": "last centurion", "email": "rory@wiggy.net"}'
        wsgi_input = BytesIO(data)
        environ = {
            'wsgi.input': wsgi_input,
            'REQUEST_METHOD': method,
            'CONTENT_LENGTH': len(data),
            'webob.is_body_seekable': True,
        }
        req = self._makeOne(environ)
        r_1 = req.body
        r_2 = req.POST
        r_3 = req.body
        assert r_1 == b'{"password": "last centurion", "email": "rory@wiggy.net"}'
        assert r_3 == b'{"password": "last centurion", "email": "rory@wiggy.net"}'

    @pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
    def test_POST_bad_content_type(self, method):
        data = b'input'
        wsgi_input = BytesIO(data)
        environ = {
            'wsgi.input': wsgi_input,
            'REQUEST_METHOD': method,
            'CONTENT_TYPE': 'text/plain',
        }
        req = self._makeOne(environ)
        result = req.POST
        assert isinstance(result, NoVars)
        assert result.reason.startswith('Not an HTML form submission')

    @pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
    def test_POST_urlencoded(self, method):
        data = b'var1=value1&var2=value2&rep=1&rep=2'
        wsgi_input = BytesIO(data)
        environ = {
            'wsgi.input': wsgi_input,
            'REQUEST_METHOD': method,
            'CONTENT_LENGTH': len(data),
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'webob.is_body_seekable': True,
        }
        req = self._makeOne(environ)
        result = req.POST
        assert result['var1'] == 'value1'

    @pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
    def test_POST_multipart(self, method):
        data = (
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
        wsgi_input = BytesIO(data)
        environ = {
            'wsgi.input': wsgi_input,
            'webob.is_body_seekable': True,
            'REQUEST_METHOD': method,
            'CONTENT_TYPE': 'multipart/form-data; '
                            'boundary=----------------------------deb95b63e42a',
            'CONTENT_LENGTH': len(data),
        }
        req = self._makeOne(environ)
        result = req.POST
        assert result['foo'] == 'foo'
        bar = result['bar']
        assert bar.name == 'bar'
        assert bar.filename == 'bar.txt'
        assert bar.file.read() == b'these are the contents of the file "bar.txt"\n'

    # GET
    def test_GET_reflects_query_string(self):
        environ = {
            'QUERY_STRING': 'foo=123',
        }
        req = self._makeOne(environ)
        result = req.GET
        assert result == {'foo': '123'}
        req.query_string = 'foo=456'
        result = req.GET
        assert result == {'foo': '456'}
        req.query_string = ''
        result = req.GET
        assert result == {}

    def test_GET_updates_query_string(self):
        req = self._makeOne({})
        result = req.query_string
        assert result == ''
        req.GET['foo'] = '123'
        result = req.query_string
        assert result == 'foo=123'
        del req.GET['foo']
        result = req.query_string
        assert result == ''

    # cookies
    def test_cookies_wo_webob_parsed_cookies(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._blankOne('/', environ)
        assert req.cookies == {'a': 'b'}

    # copy
    def test_copy_get(self):
        environ = {
            'HTTP_COOKIE': 'a=b',
        }
        req = self._blankOne('/', environ)
        clone = req.copy_get()
        for k, v in req.environ.items():
            if k in ('CONTENT_LENGTH', 'webob.is_body_seekable'):
                assert k not in clone.environ
            elif k == 'wsgi.input':
                assert clone.environ[k] is not v
            else:
                assert clone.environ[k] == v

    def test_remove_conditional_headers_accept_encoding(self):
        req = self._blankOne('/')
        req.accept_encoding='gzip,deflate'
        req.remove_conditional_headers()
        assert bool(req.accept_encoding) == False

    def test_remove_conditional_headers_if_modified_since(self):
        from webob.datetime_utils import UTC
        from datetime import datetime
        req = self._blankOne('/')
        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        req.remove_conditional_headers()
        assert req.if_modified_since == None

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
        assert bool(req.if_range) == False

    def test_remove_conditional_headers_range(self):
        req = self._blankOne('/')
        req.range = 'bytes=0-100'
        req.remove_conditional_headers()
        assert req.range == None

    def test_is_body_readable_POST(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD': 'POST', 'CONTENT_LENGTH': '100'})
        assert req.is_body_readable

    def test_is_body_readable_PATCH(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD': 'PATCH', 'CONTENT_LENGTH': '100'})
        assert req.is_body_readable

    def test_is_body_readable_GET(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD': 'GET', 'CONTENT_LENGTH': '100'})
        assert req.is_body_readable

    def test_is_body_readable_unknown_method_and_content_length(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD': 'WTF', 'CONTENT_LENGTH': '100'})
        assert req.is_body_readable

    def test_is_body_readable_special_flag(self):
        req = self._blankOne('/', environ={'REQUEST_METHOD': 'WTF',
                                          'webob.is_body_readable': True})
        assert req.is_body_readable


    # is_body_seekable
    # make_body_seekable
    # copy_body
    # make_tempfile
    # remove_conditional_headers
    # accept
    def test_accept_no_header(self):
        req = self._makeOne(environ={})
        header = req.accept
        assert isinstance(header, AcceptNoHeader)
        assert header.header_value is None

    def test_accept_invalid_header(self):
        header_value = 'text/html;param=val;q=1;extparam=\x19'
        req = self._makeOne(environ={'HTTP_ACCEPT': header_value})
        header = req.accept
        assert isinstance(header, AcceptInvalidHeader)
        assert header.header_value == header_value

    def test_accept_valid_header(self):
        header_value = ',,text/html;p1="v1";p2=v2;q=0.9;e1="v1";e2;e3=v3,'
        req = self._makeOne(environ={'HTTP_ACCEPT': header_value})
        header = req.accept
        assert isinstance(header, AcceptValidHeader)
        assert header.header_value == header_value

    # accept_charset
    def test_accept_charset_no_header(self):
        req = self._makeOne(environ={})
        header = req.accept_charset
        assert isinstance(header, AcceptCharsetNoHeader)
        assert header.header_value is None

    @pytest.mark.parametrize('header_value', [
        '', ', utf-7;q=0.2, utf-8;q =0.3'
    ])
    def test_accept_charset_invalid_header(self, header_value):
        req = self._makeOne(environ={'HTTP_ACCEPT_CHARSET': header_value})
        header = req.accept_charset
        assert isinstance(header, AcceptCharsetInvalidHeader)
        assert header.header_value == header_value

    def test_accept_charset_valid_header(self):
        header_value = \
            'iso-8859-5;q=0.372,unicode-1-1;q=0.977,UTF-8, *;q=0.000'
        req = self._makeOne(environ={'HTTP_ACCEPT_CHARSET': header_value})
        header = req.accept_charset
        assert isinstance(header, AcceptCharsetValidHeader)
        assert header.header_value == header_value

    # accept_encoding
    def test_accept_encoding_no_header(self):
        req = self._makeOne(environ={})
        header = req.accept_encoding
        assert isinstance(header, AcceptEncodingNoHeader)
        assert header.header_value is None

    @pytest.mark.parametrize('header_value', [
        ', ', ', gzip;q=0.2, compress;q =0.3',
    ])
    def test_accept_encoding_invalid_header(self, header_value):
        req = self._makeOne(environ={'HTTP_ACCEPT_ENCODING': header_value})
        header = req.accept_encoding
        assert isinstance(header, AcceptEncodingInvalidHeader)
        assert header.header_value == header_value

    def test_accept_encoding_valid_header(self):
        header_value = \
            'compress;q=0.372,gzip;q=0.977,, *;q=0.000'
        req = self._makeOne(environ={'HTTP_ACCEPT_ENCODING': header_value})
        header = req.accept_encoding
        assert isinstance(header, AcceptEncodingValidHeader)
        assert header.header_value == header_value

    # accept_language
    def test_accept_language_no_header(self):
        req = self._makeOne(environ={})
        header = req.accept_language
        assert isinstance(header, AcceptLanguageNoHeader)
        assert header.header_value is None

    @pytest.mark.parametrize('header_value', ['', ', da;q=0.2, en-gb;q =0.3'])
    def test_accept_language_invalid_header(self, header_value):
        req = self._makeOne(environ={'HTTP_ACCEPT_LANGUAGE': header_value})
        header = req.accept_language
        assert isinstance(header, AcceptLanguageInvalidHeader)
        assert header.header_value == header_value

    def test_accept_language_valid_header(self):
        header_value = \
            'zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000'
        req = self._makeOne(environ={'HTTP_ACCEPT_LANGUAGE': header_value})
        header = req.accept_language
        assert isinstance(header, AcceptLanguageValidHeader)
        assert header.header_value == header_value

    # authorization

    # cache_control
    def test_cache_control_reflects_environ(self):
        environ = {
            'HTTP_CACHE_CONTROL': 'max-age=5',
        }
        req = self._makeOne(environ)
        result = req.cache_control
        assert result.properties == {'max-age': 5}
        req.environ.update(HTTP_CACHE_CONTROL='max-age=10')
        result = req.cache_control
        assert result.properties == {'max-age': 10}
        req.environ.update(HTTP_CACHE_CONTROL='')
        result = req.cache_control
        assert result.properties == {}

    def test_cache_control_updates_environ(self):
        environ = {}
        req = self._makeOne(environ)
        req.cache_control.max_age = 5
        result = req.environ['HTTP_CACHE_CONTROL']
        assert result == 'max-age=5'
        req.cache_control.max_age = 10
        result = req.environ['HTTP_CACHE_CONTROL']
        assert result == 'max-age=10'
        req.cache_control = None
        result = req.environ['HTTP_CACHE_CONTROL']
        assert result == ''
        del req.cache_control
        assert 'HTTP_CACHE_CONTROL' not in req.environ

    def test_cache_control_set_dict(self):
        environ = {}
        req = self._makeOne(environ)
        req.cache_control = {'max-age': 5}
        result = req.cache_control
        assert result.max_age == 5

    def test_cache_control_set_object(self):
        from webob.cachecontrol import CacheControl
        environ = {}
        req = self._makeOne(environ)
        req.cache_control = CacheControl({'max-age': 5}, type='request')
        result = req.cache_control
        assert result.max_age == 5

    def test_cache_control_gets_cached(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.cache_control is req.cache_control

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
        assert status == '200 OK'
        assert headers == [('content-type', 'text/plain')]
        assert ''.join(output) == '...\n'

    def test_call_application_provides_write(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            write = start_response('200 OK', [('content-type', 'text/plain')])
            write('...\n')
            return []
        status, headers, output = req.call_application(application)
        assert status == '200 OK'
        assert headers == [('content-type', 'text/plain')]
        assert ''.join(output) == '...\n'

    def test_call_application_closes_iterable_when_mixed_w_write_calls(self):
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
        assert ''.join(output) == '...\n...\n'
        assert environ['test._call_application_called_close'] == True

    def test_call_application_raises_exc_info(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                exc_info = sys.exc_info()
            start_response('200 OK',
                           [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        with pytest.raises(RuntimeError):
            req.call_application(application)

    def test_call_application_returns_exc_info(self):
        environ = {}
        req = self._makeOne(environ)
        def application(environ, start_response):
            try:
                raise RuntimeError('OH NOES')
            except:
                exc_info = sys.exc_info()
            start_response('200 OK',
                           [('content-type', 'text/plain')], exc_info)
            return ['...\n']
        status, headers, output, exc_info = req.call_application(
            application, True)
        assert status == '200 OK'
        assert headers == [('content-type', 'text/plain')]
        assert ''.join(output) == '...\n'
        assert exc_info[0] == RuntimeError

    #get_response
    def test_blank__method_subtitution(self):
        request = self._blankOne('/', environ={'REQUEST_METHOD': 'PUT'})
        assert request.method == 'PUT'

        request = self._blankOne(
            '/', environ={'REQUEST_METHOD': 'PUT'}, POST={})
        assert request.method == 'PUT'

        request = self._blankOne(
            '/', environ={'REQUEST_METHOD': 'HEAD'}, POST={})
        assert request.method == 'POST'

    def test_blank__ctype_in_env(self):
        request = self._blankOne(
            '/', environ={'CONTENT_TYPE': 'application/json'})
        assert request.content_type == 'application/json'
        assert request.method == 'GET'

        request = self._blankOne(
            '/', environ={'CONTENT_TYPE': 'application/json'}, POST='')
        assert request.content_type == 'application/json'
        assert request.method == 'POST'

    def test_blank__ctype_in_headers(self):
        request = self._blankOne(
            '/', headers={'Content-type': 'application/json'})
        assert request.content_type == 'application/json'
        assert request.method == 'GET'

        request = self._blankOne(
            '/', headers={'Content-Type': 'application/json'}, POST='')
        assert request.content_type == 'application/json'
        assert request.method == 'POST'

    def test_blank__ctype_as_kw(self):
        request = self._blankOne('/', content_type='application/json')
        assert request.content_type == 'application/json'
        assert request.method == 'GET'

        request = self._blankOne('/', content_type='application/json',
                                         POST='')
        assert request.content_type == 'application/json'
        assert request.method == 'POST'

    def test_blank__str_post_data_for_unsupported_ctype(self):
        with pytest.raises(ValueError):
            self._blankOne('/', content_type='application/json', POST={})

    def test_blank__post_urlencoded(self):
        from webob.multidict import MultiDict
        POST = MultiDict()
        POST["first"] = 1
        POST["second"] = 2

        request = self._blankOne('/', POST=POST)
        assert request.method == 'POST'
        assert request.content_type == 'application/x-www-form-urlencoded'
        assert request.body == b'first=1&second=2'
        assert request.content_length == 16

    def test_blank__post_multipart(self):
        from webob.multidict import MultiDict
        POST = MultiDict()
        POST["first"] = "1"
        POST["second"] = "2"


        request = self._blankOne('/',
                                 POST=POST,
                                 content_type='multipart/form-data; '
                                              'boundary=boundary')
        assert request.method == 'POST'
        assert request.content_type == 'multipart/form-data'
        expected = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="first"\r\n\r\n'
            b'1\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="second"\r\n\r\n'
            b'2\r\n'
            b'--boundary--')
        assert request.body == expected
        assert request.content_length == 139

    def test_blank__post_files(self):
        import cgi
        from webob.request import _get_multipart_boundary
        from webob.multidict import MultiDict
        POST = MultiDict()
        POST["first"] = ('filename1', BytesIO(b'1'))
        POST["second"] = ('filename2', '2')
        POST["third"] = "3"
        request = self._blankOne('/', POST=POST)
        assert request.method == 'POST'
        assert request.content_type == 'multipart/form-data'
        boundary = bytes_(
            _get_multipart_boundary(request.headers['content-type']))
        body_norm = request.body.replace(boundary, b'boundary')
        expected = (
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="first"; '
                    b'filename="filename1"\r\n\r\n'
            b'1\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="second"; '
                    b'filename="filename2"\r\n\r\n'
            b'2\r\n'
            b'--boundary\r\n'
            b'Content-Disposition: form-data; name="third"\r\n\r\n'
            b'3\r\n'
            b'--boundary--'
            )
        assert body_norm == expected
        assert request.content_length == 294
        assert isinstance(request.POST['first'], cgi.FieldStorage)
        assert isinstance(request.POST['second'], cgi.FieldStorage)
        assert request.POST['first'].value == b'1'
        assert request.POST['second'].value == b'2'
        assert request.POST['third'] == '3'

    def test_blank__post_file_w_wrong_ctype(self):
        with pytest.raises(ValueError):
            self._blankOne(
                '/',
                POST={'first': ('filename1', '1')},
                content_type='application/x-www-form-urlencoded')

    #from_bytes
    def test_from_bytes_extra_data(self):
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type')
        cls = self._getTargetClass()
        with pytest.raises(ValueError):
            cls.from_bytes(_test_req_copy+b'EXTRA!')

    #as_bytes
    def test_as_bytes_skip_body(self):
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        body = req.as_bytes(skip_body=True)
        assert body.count(b'\r\n\r\n') == 0
        assert req.as_bytes(skip_body=337) == req.as_bytes()
        body = req.as_bytes(337-1).split(b'\r\n\r\n', 1)[1]
        assert body == b'<body skipped (len=337)>'

    def test_charset_in_content_type(self):
        Request = self._getTargetClass()
        # should raise no exception
        req = Request({
            'REQUEST_METHOD': 'POST',
            'QUERY_STRING':'a=b',
            'CONTENT_TYPE':'text/html;charset=ascii'
        })
        assert req.charset == 'ascii'
        assert dict(req.GET) == {'a': 'b'}
        assert dict(req.POST) == {}
        req.charset = 'ascii' # no exception
        with pytest.raises(DeprecationWarning):
            setattr(req, 'charset', 'utf-8')

        # again no exception
        req = Request({
            'REQUEST_METHOD': 'POST',
            'QUERY_STRING':'a=b',
            'CONTENT_TYPE':'multipart/form-data;charset=ascii'
        })
        assert req.charset == 'ascii'
        assert dict(req.GET) == {'a': 'b'}
        with pytest.raises(DeprecationWarning):
            getattr(req, 'POST')

    def test_limited_length_file_repr(self):
        from webob.request import Request
        req = Request.blank('/', POST='x')
        req.body_file_raw = 'dummy'
        req.is_body_seekable = False
        assert repr(req.body_file.raw), "<LimitedLengthFile('dummy' == maxlen=1)>"

    @pytest.mark.parametrize("is_seekable", [False, True])
    def test_request_wrong_clen(self, is_seekable):
        from webob.request import Request
        tlen = 1<<20
        req = Request.blank('/', POST='x'*tlen)
        assert req.content_length == tlen
        req.body_file = _Helper_test_request_wrong_clen(req.body_file)
        assert req.content_length == None
        req.content_length = tlen + 100
        req.is_body_seekable = is_seekable
        assert req.content_length == tlen+100
        # this raises AssertionError if the body reading
        # trusts content_length too much
        with pytest.raises(IOError):
            req.copy_body()


class TestBaseRequest(object):
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
        assert result.__class__ == str
        assert result == 'OPTIONS'

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        result = req.http_version
        assert result == '1.1'

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        assert req.script_name == '/script'

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert req.path_info == '/path/info'

    def test_content_length_getter(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        assert req.content_length == 1234

    def test_content_length_setter_w_str(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        req.content_length = '3456'
        assert req.content_length == 3456

    def test_remote_user(self):
        environ = {'REMOTE_USER': 'phred',
                  }
        req = self._makeOne(environ)
        assert req.remote_user == 'phred'

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        assert req.remote_addr == '1.2.3.4'

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        assert req.query_string == 'foo=bar&baz=bam'

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        assert req.server_name == 'somehost.tld'

    def test_server_port_getter(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        assert req.server_port == 6666

    def test_server_port_setter_with_string(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        req.server_port = '6667'
        assert req.server_port == 6667

    def test_uscript_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        assert isinstance(req.uscript_name, text_type)
        assert req.uscript_name == '/script'

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert isinstance(req.upath_info, text_type)
        assert req.upath_info == '/path/info'

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        req.upath_info = text_('/another')
        assert isinstance(req.upath_info, text_type)
        assert req.upath_info == '/another'

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = self._makeOne(environ)
        assert req.content_type == 'application/xml+foobar'

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        assert req.content_type == 'application/xml+foobar'

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        assert req.content_type == ''
        assert 'CONTENT_TYPE' not in environ

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        assert req.content_type == 'text/xml'
        assert environ['CONTENT_TYPE'] == 'text/xml;charset="utf8"'

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        assert req.content_type == ''
        assert 'CONTENT_TYPE' not in environ

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        assert req.content_type == ''
        assert 'CONTENT_TYPE' not in environ

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        assert headers == {'Content-Type': CONTENT_TYPE, 'Content-Length': '123'}

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        assert req.headers == {'Qux': 'Spam'}
        assert environ == {'HTTP_QUX': 'Spam'}

    def test_no_headers_deleter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        def _test():
            del req.headers
        with pytest.raises(AttributeError):
            _test()

    def test_client_addr_xff_singleval(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.1'

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.1'

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.1'

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.2'

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.client_addr == None

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '80'

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '80'

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '8888'

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '443'

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '443'

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '8888'

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '4333'

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'http://example.com'

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'http://example.com'

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'http://example.com:8888'

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com'

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com'

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com:4333'

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com:4333'

    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.application_url
        assert app_url.__class__ == str
        assert app_url == 'http://localhost/%C3%AB'

    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.path_url
        assert app_url.__class__ == str
        assert app_url == 'http://localhost/%C3%AB/%C3%AB'

    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = text_(b'/\xc3\xab', 'utf-8')
        app_url = inst.path
        assert app_url.__class__ == str
        assert app_url == '/%C3%AB/%C3%AB'

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert req.path_qs == '/script/path/info'

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.path_qs == '/script/path/info?foo=bar&baz=bam'

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert req.url == 'http://example.com/script/path/info'

    def test_url_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.url == 'http://example.com/script/path/info?foo=bar&baz=bam'

    def test_relative_url_to_app_true_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.relative_url('other/page', True) == 'http://example.com/script/other/page'

    def test_relative_url_to_app_true_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.relative_url('/other/page', True) == 'http://example.com/other/page'

    def test_relative_url_to_app_false_other_w_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.relative_url('/other/page', False) == 'http://example.com/other/page'

    def test_relative_url_to_app_false_other_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.relative_url('other/page', False) == 'http://example.com/script/path/other/page'

    def test_path_info_pop_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == None
        assert environ['SCRIPT_NAME'] == '/script'

    def test_path_info_pop_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == ''
        assert environ['SCRIPT_NAME'] == '/script/'
        assert environ['PATH_INFO'] == ''

    def test_path_info_pop_non_empty_no_pattern(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == 'path'
        assert environ['SCRIPT_NAME'] == '/script/path'
        assert environ['PATH_INFO'] == '/info'

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
        assert popped == None
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == '/path/info'

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
        assert popped == 'path'
        assert environ['SCRIPT_NAME'] == '/script/path'
        assert environ['PATH_INFO'] == '/info'

    def test_path_info_pop_skips_empty_elements(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '//path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == 'path'
        assert environ['SCRIPT_NAME'] == '/script//path'
        assert environ['PATH_INFO'] == '/info'

    def test_path_info_peek_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        assert peeked == None
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == ''

    def test_path_info_peek_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        assert peeked == ''
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == '/'

    def test_path_info_peek_non_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        assert peeked == 'path'
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == '/path'

    def test_is_xhr_no_header(self):
        req = self._makeOne({})
        assert not req.is_xhr

    def test_is_xhr_header_miss(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'notAnXMLHTTPRequest'}
        req = self._makeOne(environ)
        assert not req.is_xhr

    def test_is_xhr_header_hit(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = self._makeOne(environ)
        assert req.is_xhr

    # host
    def test_host_getter_w_HTTP_HOST(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        assert req.host == 'example.com:8888'

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        assert req.host == 'example.com:8888'

    def test_host_setter(self):
        environ = {}
        req = self._makeOne(environ)
        req.host = 'example.com:8888'
        assert environ['HTTP_HOST'] == 'example.com:8888'

    def test_host_deleter_hit(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        del req.host
        assert 'HTTP_HOST' not in environ

    def test_host_deleter_miss(self):
        environ = {}
        req = self._makeOne(environ)
        del req.host # doesn't raise

    def test_domain_nocolon(self):
        environ = {'HTTP_HOST':'example.com'}
        req = self._makeOne(environ)
        assert req.domain == 'example.com'

    def test_domain_withcolon(self):
        environ = {'HTTP_HOST':'example.com:8888'}
        req = self._makeOne(environ)
        assert req.domain == 'example.com'

    def test_domain_with_ipv6(self):
        environ = {'HTTP_HOST': '[2001:DB8::1]:6453'}
        req = self._makeOne(environ)
        assert req.domain == '[2001:DB8::1]'

    def test_domain_with_ipv6_no_port(self):
        environ = {'HTTP_HOST': '[2001:DB8::1]'}
        req = self._makeOne(environ)
        assert req.domain == '[2001:DB8::1]'

    def test_encget_raises_without_default(self):
        inst = self._makeOne({})
        with pytest.raises(KeyError):
            inst.encget('a')

    def test_encget_doesnt_raises_with_default(self):
        inst = self._makeOne({})
        assert inst.encget('a', None) == None

    def test_encget_with_encattr(self):
        val = native_(b'\xc3\xab', 'latin-1')
        inst = self._makeOne({'a': val})
        assert inst.encget('a', encattr='url_encoding') == text_(b'\xc3\xab', 'utf-8')

    def test_encget_with_encattr_latin_1(self):
        val = native_(b'\xc3\xab', 'latin-1')
        inst = self._makeOne({'a': val})
        inst.my_encoding = 'latin-1'
        assert inst.encget('a', encattr='my_encoding') == text_(b'\xc3\xab', 'latin-1')

    def test_encget_no_encattr(self):
        val = native_(b'\xc3\xab', 'latin-1')
        inst = self._makeOne({'a': val})
        assert inst.encget('a') == val

    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        assert result.__class__ == str
        assert result == 'http://localhost/%C3%AB/a'

    def test_header_getter(self):
        val = native_(b'abc', 'latin-1')
        inst = self._makeOne({'HTTP_FLUB': val})
        result = inst.headers['Flub']
        assert result.__class__ == str
        assert result == 'abc'

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        assert inst.json_body == {'a':'1'}
        inst.json_body = {'a': '2'}
        assert inst.body == b'{"a":"2"}'

    def test_host_get(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        assert result.__class__ == str
        assert result == 'example.com'

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        assert result.__class__ == str
        assert result == 'example.com:80'

class TestLegacyRequest(object):
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
        assert req.method == 'OPTIONS'

    def test_http_version(self):
        environ = {'SERVER_PROTOCOL': '1.1',
                  }
        req = self._makeOne(environ)
        assert req.http_version == '1.1'

    def test_script_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        assert req.script_name == '/script'

    def test_path_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert req.path_info == '/path/info'

    def test_content_length_getter(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        assert req.content_length == 1234

    def test_content_length_setter_w_str(self):
        environ = {'CONTENT_LENGTH': '1234',
                  }
        req = self._makeOne(environ)
        req.content_length = '3456'
        assert req.content_length == 3456

    def test_remote_user(self):
        environ = {'REMOTE_USER': 'phred',
                  }
        req = self._makeOne(environ)
        assert req.remote_user == 'phred'

    def test_remote_addr(self):
        environ = {'REMOTE_ADDR': '1.2.3.4',
                  }
        req = self._makeOne(environ)
        assert req.remote_addr == '1.2.3.4'

    def test_remote_host(self):
        environ = {'REMOTE_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.remote_host == 'example.com'

    def test_remote_host_not_set(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.remote_host is None

    def test_query_string(self):
        environ = {'QUERY_STRING': 'foo=bar&baz=bam',
                  }
        req = self._makeOne(environ)
        assert req.query_string == 'foo=bar&baz=bam'

    def test_server_name(self):
        environ = {'SERVER_NAME': 'somehost.tld',
                  }
        req = self._makeOne(environ)
        assert req.server_name == 'somehost.tld'

    def test_server_port_getter(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        assert req.server_port == 6666

    def test_server_port_setter_with_string(self):
        environ = {'SERVER_PORT': '6666',
                  }
        req = self._makeOne(environ)
        req.server_port = '6667'
        assert req.server_port == 6667

    def test_uscript_name(self):
        environ = {'SCRIPT_NAME': '/script',
                  }
        req = self._makeOne(environ)
        assert isinstance(req.uscript_name, text_type)
        result = req.uscript_name
        assert result.__class__ == text_type
        assert result == '/script'

    def test_upath_info(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        result = req.upath_info
        assert isinstance(result, text_type)
        assert result == '/path/info'

    def test_upath_info_set_unicode(self):
        environ = {'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        req.upath_info = text_('/another')
        result = req.upath_info
        assert isinstance(result, text_type)
        assert result == '/another'

    def test_content_type_getter_no_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar',
                  }
        req = self._makeOne(environ)
        assert req.content_type == 'application/xml+foobar'

    def test_content_type_getter_w_parameters(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        assert req.content_type == 'application/xml+foobar'

    def test_content_type_setter_w_None(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = None
        assert req.content_type == ''
        assert 'CONTENT_TYPE' not in environ

    def test_content_type_setter_existing_paramter_no_new_paramter(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        req.content_type = 'text/xml'
        assert req.content_type == 'text/xml'
        assert environ['CONTENT_TYPE'] == 'text/xml;charset="utf8"'

    def test_content_type_deleter_clears_environ_value(self):
        environ = {'CONTENT_TYPE': 'application/xml+foobar;charset="utf8"',
                  }
        req = self._makeOne(environ)
        del req.content_type
        assert req.content_type == ''
        assert 'CONTENT_TYPE' not in environ

    def test_content_type_deleter_no_environ_value(self):
        environ = {}
        req = self._makeOne(environ)
        del req.content_type
        assert req.content_type == ''
        assert 'CONTENT_TYPE' not in environ

    def test_headers_getter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        headers = req.headers
        assert headers == {'Content-Type':CONTENT_TYPE, 'Content-Length': '123'}

    def test_headers_setter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        req.headers = {'Qux': 'Spam'}
        assert req.headers == {'Qux': 'Spam'}
        assert environ['HTTP_QUX'] == native_('Spam')
        assert environ == {'HTTP_QUX': 'Spam'}

    def test_no_headers_deleter(self):
        CONTENT_TYPE = 'application/xml+foobar;charset="utf8"'
        environ = {'CONTENT_TYPE': CONTENT_TYPE,
                   'CONTENT_LENGTH': '123',
                  }
        req = self._makeOne(environ)
        def _test():
            del req.headers
        with pytest.raises(AttributeError):
            _test()

    def test_client_addr_xff_singleval(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.1'

    def test_client_addr_xff_multival(self):
        environ = {
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1, 192.168.1.2',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.1'

    def test_client_addr_prefers_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                   'HTTP_X_FORWARDED_FOR': '192.168.1.1',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.1'

    def test_client_addr_no_xff(self):
        environ = {'REMOTE_ADDR': '192.168.1.2',
                  }
        req = self._makeOne(environ)
        assert req.client_addr == '192.168.1.2'

    def test_client_addr_no_xff_no_remote_addr(self):
        environ = {}
        req = self._makeOne(environ)
        assert req.client_addr == None

    def test_host_port_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '80'

    def test_host_port_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '80'

    def test_host_port_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '8888'

    def test_host_port_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '443'

    def test_host_port_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '443'

    def test_host_port_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '8888'

    def test_host_port_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        assert req.host_port == '4333'

    def test_host_port_ipv6(self):
        environ = {'HTTP_HOST': '[2001:DB8::1]:6453'}
        req = self._makeOne(environ)
        assert req.host_port == '6453'

    def test_host_port_ipv6(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': '[2001:DB8::1]'
                  }
        req = self._makeOne(environ)
        assert req.host_port == '443'

    def test_host_url_w_http_host_and_no_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'http://example.com'

    def test_host_url_w_http_host_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:80',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'http://example.com'

    def test_host_url_w_http_host_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'http',
                   'HTTP_HOST': 'example.com:8888',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'http://example.com:8888'

    def test_host_url_w_http_host_https_and_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com'

    def test_host_url_w_http_host_https_and_standard_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:443',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com'

    def test_host_url_w_http_host_https_and_oddball_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': 'example.com:4333',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com:4333'

    def test_host_url_wo_http_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '4333',
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://example.com:4333'

    def test_host_url_http_ipv6_host(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': '[2001:DB8::1]:6453'
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://[2001:DB8::1]:6453'

    def test_host_url_http_ipv6_host_no_port(self):
        environ = {'wsgi.url_scheme': 'https',
                   'HTTP_HOST': '[2001:DB8::1]'
                  }
        req = self._makeOne(environ)
        assert req.host_url == 'https://[2001:DB8::1]'

    @py2only
    def test_application_url_py2(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.application_url
        assert app_url == 'http://localhost/%C3%AB'

    @py3only
    def test_application_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        app_url = inst.application_url
        assert app_url == 'http://localhost/%C3%83%C2%AB'

    @py2only
    def test_path_url_py2(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path_url
        assert result == 'http://localhost/%C3%AB/%C3%AB'

    @py3only
    def test_path_url(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path_url
        assert result == 'http://localhost/%C3%83%C2%AB/%C3%83%C2%AB'

    @py2only
    def test_path_py2(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path
        assert result == '/%C3%AB/%C3%AB'

    @py3only
    def test_path(self):
        inst = self._blankOne('/%C3%AB')
        inst.script_name = b'/\xc3\xab'
        result = inst.path
        assert result == '/%C3%83%C2%AB/%C3%83%C2%AB'

    def test_path_qs_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert req.path_qs == '/script/path/info'

    def test_path_qs_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.path_qs == '/script/path/info?foo=bar&baz=bam'

    def test_url_no_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        assert req.url == 'http://example.com/script/path/info'

    def test_url_w_qs(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.url == 'http://example.com/script/path/info?foo=bar&baz=bam'

    def test_relative_url_to_app_true_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.relative_url('other/page' == True,
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
        assert req.relative_url('/other/page' == True,
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
        assert req.relative_url('/other/page', False) == 'http://example.com/other/page'

    def test_relative_url_to_app_false_other_wo_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                   'QUERY_STRING': 'foo=bar&baz=bam'
                  }
        req = self._makeOne(environ)
        assert req.relative_url('other/page', False) == 'http://example.com/script/path/other/page'

    def test_path_info_pop_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == None
        assert environ['SCRIPT_NAME'] == '/script'

    def test_path_info_pop_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == ''
        assert environ['SCRIPT_NAME'] == '/script/'
        assert environ['PATH_INFO'] == ''

    def test_path_info_pop_non_empty_no_pattern(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == 'path'
        assert environ['SCRIPT_NAME'] == '/script/path'
        assert environ['PATH_INFO'] == '/info'

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
        assert popped == None
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == '/path/info'

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
        assert popped == 'path'
        assert environ['SCRIPT_NAME'] == '/script/path'
        assert environ['PATH_INFO'] == '/info'

    def test_path_info_pop_skips_empty_elements(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '//path/info',
                  }
        req = self._makeOne(environ)
        popped = req.path_info_pop()
        assert popped == 'path'
        assert environ['SCRIPT_NAME'] == '/script//path'
        assert environ['PATH_INFO'] == '/info'

    def test_path_info_peek_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        assert peeked == None
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == ''

    def test_path_info_peek_just_leading_slash(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        assert peeked == ''
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == '/'

    def test_path_info_peek_non_empty(self):
        environ = {'wsgi.url_scheme': 'http',
                   'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '80',
                   'SCRIPT_NAME': '/script',
                   'PATH_INFO': '/path',
                  }
        req = self._makeOne(environ)
        peeked = req.path_info_peek()
        assert peeked == 'path'
        assert environ['SCRIPT_NAME'] == '/script'
        assert environ['PATH_INFO'] == '/path'

    def test_is_xhr_no_header(self):
        req = self._makeOne({})
        assert not req.is_xhr

    def test_is_xhr_header_miss(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'notAnXMLHTTPRequest'}
        req = self._makeOne(environ)
        assert not req.is_xhr

    def test_is_xhr_header_hit(self):
        environ = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}
        req = self._makeOne(environ)
        assert req.is_xhr

    # host
    def test_host_getter_w_HTTP_HOST(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        assert req.host == 'example.com:8888'

    def test_host_getter_wo_HTTP_HOST(self):
        environ = {'SERVER_NAME': 'example.com',
                   'SERVER_PORT': '8888'}
        req = self._makeOne(environ)
        assert req.host == 'example.com:8888'

    def test_host_setter(self):
        environ = {}
        req = self._makeOne(environ)
        req.host = 'example.com:8888'
        assert environ['HTTP_HOST'] == 'example.com:8888'

    def test_host_deleter_hit(self):
        environ = {'HTTP_HOST': 'example.com:8888'}
        req = self._makeOne(environ)
        del req.host
        assert 'HTTP_HOST' not in environ

    def test_host_deleter_miss(self):
        environ = {}
        req = self._makeOne(environ)
        del req.host # doesn't raise

    def test_encget_raises_without_default(self):
        inst = self._makeOne({})
        with pytest.raises(KeyError):
            inst.encget('a')

    def test_encget_doesnt_raises_with_default(self):
        inst = self._makeOne({})
        assert inst.encget('a', None) == None

    def test_encget_with_encattr(self):
        val = native_(b'\xc3\xab', 'latin-1')
        inst = self._makeOne({'a':val})
        assert inst.encget('a', encattr='url_encoding') == native_(b'\xc3\xab', 'latin-1')

    def test_encget_no_encattr(self):
        val = native_(b'\xc3\xab', 'latin-1')
        inst = self._makeOne({'a': val})
        assert inst.encget('a'), native_(b'\xc3\xab' == 'latin-1')

    @py2only
    def test_relative_url_py2(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        assert result == 'http://localhost/%C3%AB/a'

    @py3only
    def test_relative_url(self):
        inst = self._blankOne('/%C3%AB/c')
        result = inst.relative_url('a')
        assert result == 'http://localhost/%C3%83%C2%AB/a'

    def test_header_getter(self):
        val = native_(b'abc', 'latin-1')
        inst = self._makeOne({'HTTP_FLUB':val})
        result = inst.headers['Flub']
        assert result == 'abc'

    def test_json_body(self):
        inst = self._makeOne({})
        inst.body = b'{"a":"1"}'
        assert inst.json_body == {'a':'1'}

    def test_host_get_w_http_host(self):
        inst = self._makeOne({'HTTP_HOST':'example.com'})
        result = inst.host
        assert result == 'example.com'

    def test_host_get_w_no_http_host(self):
        inst = self._makeOne({'SERVER_NAME':'example.com', 'SERVER_PORT':'80'})
        result = inst.host
        assert result == 'example.com:80'

class TestRequestConstructorWarnings(object):
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
        assert len(w) == 1

    def test_ctor_w_decode_param_names(self):
        with warnings.catch_warnings(record=True) as w:
            # still emit if warning was printed previously
            warnings.simplefilter('always')
            self._makeOne({}, decode_param_names=True)
        assert len(w) == 1

class TestRequestWithAdhocAttr(object):
    def _blankOne(self, *arg, **kw):
        from webob.request import Request
        return Request.blank(*arg, **kw)

    def test_adhoc_attrs_set(self):
        req = self._blankOne('/')
        req.foo = 1
        assert req.environ['webob.adhoc_attrs'] == {'foo': 1}

    def test_adhoc_attrs_set_nonadhoc(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs':{}})
        req.request_body_tempfile_limit = 1
        assert req.environ['webob.adhoc_attrs'] == {}

    def test_adhoc_attrs_get(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        assert req.foo == 1

    def test_adhoc_attrs_get_missing(self):
        req = self._blankOne('/')
        with pytest.raises(AttributeError):
            getattr(req, 'some_attr')

    def test_adhoc_attrs_del(self):
        req = self._blankOne('/', environ={'webob.adhoc_attrs': {'foo': 1}})
        del req.foo
        assert req.environ['webob.adhoc_attrs'] == {}

    def test_adhoc_attrs_del_missing(self):
        req = self._blankOne('/')
        with pytest.raises(AttributeError):
            delattr(req, 'some_attr')

class TestRequest_functional(object):
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
        assert status == '200 OK'
        res = b''.join(app_iter)
        assert b'Hello' in res
        assert b"MultiDict([])" in res
        assert b"post is <NoVars: Not an HTML form" in res

    def test_gets_with_query_string(self):
        request = self._blankOne('/?name=george')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"MultiDict" in res
        assert b"'name'" in res
        assert b"'george'" in res
        assert b"Val is " in res

    def test_language_parsing1(self):
        request = self._blankOne('/')
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"The languages are: []" in res

    def test_language_parsing2(self):
        request = self._blankOne(
            '/', headers={'Accept-Language': 'da, en-gb;q=0.8'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"languages are: ['da', 'en-gb']" in res

    def test_language_parsing3(self):
        request = self._blankOne(
            '/',
            headers={'Accept-Language': 'en-gb;q=0.8, da'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"languages are: ['da', 'en-gb']" in res

    def test_mime_parsing1(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'text/html'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"accepttypes is: text/html" in res

    def test_mime_parsing2(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'application/xml'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"accepttypes is: application/xml" in res

    def test_mime_parsing3(self):
        request = self._blankOne(
            '/',
            headers={'Accept':'application/xml,*/*'})
        status, headerlist, app_iter = request.call_application(simpleapp)
        res = b''.join(app_iter)
        assert b"accepttypes is: application/xml,text/html" in res

    def test_accept_acceptable_offers(self):
        fut = lambda r, offers: r.accept.acceptable_offers(offers)
        accept = self._blankOne('/').accept
        assert not accept
        assert self._blankOne('/', headers={'Accept': ''}).accept
        req = self._blankOne('/', headers={'Accept': 'text/plain'})
        assert req.accept
        req = self._blankOne('/', accept=['*/*', 'text/*'])
        assert fut(req, ['application/x-foo', 'text/plain']) == [
            ('application/x-foo', 1.0), ('text/plain', 1.0)]
        assert fut(req, ['text/plain', 'application/x-foo']) == [
            ('text/plain', 1.0), ('application/x-foo', 1.0)]
        req = self._blankOne('/', accept=['text/plain', 'message/*'])
        assert fut(req, ['message/x-foo', 'text/plain']) == [
            ('message/x-foo', 1.0), ('text/plain', 1.0)]
        assert fut(req, ['text/plain', 'message/x-foo']) == [
            ('text/plain', 1.0), ('message/x-foo', 1.0)]

    @pytest.mark.filterwarnings('ignore:.*best_match.*')
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
            assert req.accept.best_match(supported) == get

        supported = ['application/xbel+xml', 'text/xml']
        tests = [('text/*;q=0.5,*/*; q=0.1', 'text/xml'),
                ('text/html,application/atom+xml; q=0.9', None)]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            assert req.accept.best_match(supported) == get

        supported = ['application/json', 'text/html']
        tests = [
            ('application/json, text/javascript, */*', 'application/json'),
            ('application/json, text/html;q=0.9', 'application/json'),
        ]

        for accept, get in tests:
            req = self._blankOne('/', headers={'Accept':accept})
            assert req.accept.best_match(supported) == get

        offered = ['image/png', 'application/xml']
        tests = [
            ('image/png', 'image/png'),
            ('image/*', 'image/png'),
            ('image/*, application/xml', 'application/xml'),
        ]

        for accept, get in tests:
            req = self._blankOne('/', accept=accept)
            assert req.accept.best_match(offered) == get

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
            assert bytes_(thing) in res

    def test_bad_cookie(self):
        req = self._blankOne('/')
        req.headers['Cookie'] = '070-it-:><?0'
        assert req.cookies == {}
        req.headers['Cookie'] = 'foo=bar'
        assert req.cookies == {'foo': 'bar'}
        req.headers['Cookie'] = '...'
        assert req.cookies == {}
        req.headers['Cookie'] = '=foo'
        assert req.cookies == {}
        req.headers['Cookie'] = ('dismiss-top=6; CP=null*; '
            'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
        assert req.cookies == {
            'CP':           'null*',
            'PHPSESSID':    '0a539d42abc001cdc762809248d4beed',
            'a':            '42',
            'dismiss-top':  '6'
        }
        req.headers['Cookie'] = 'fo234{=bar blub=Blah'
        assert req.cookies == {'blub': 'Blah'}

    def test_cookie_quoting(self):
        req = self._blankOne('/')
        req.headers['Cookie'] = 'foo="?foo"; Path=/'
        assert req.cookies == {'foo': '?foo'}

    def test_path_quoting(self):
        path = "/_.-~!$&'()*+,;=:@/bar"
        req = self._blankOne(path)
        assert req.path == path
        assert req.url.endswith(path)

    def test_path_quoting_pct_encodes(self):
        path = '/[]/bar'
        req = self._blankOne(path)
        assert req.path == '/%5B%5D/bar'
        assert req.url.endswith('/%5B%5D/bar')

    def test_params(self):
        req = self._blankOne('/?a=1&b=2')
        req.method = 'POST'
        req.body = b'b=3'
        assert list(req.params.items()) == [('a', '1'), ('b', '2'), ('b', '3')]
        new_params = req.params.copy()
        assert list(new_params.items()) == [('a', '1'), ('b', '2'), ('b', '3')]
        new_params['b'] = '4'
        assert list(new_params.items()) == [('a', '1'), ('b', '4')]
        # The key name is \u1000:
        req = self._blankOne('/?%E1%80%80=x')
        val = text_type(b'\\u1000', 'unicode_escape')
        assert val in list(req.GET.keys())
        assert req.GET[val] == 'x'

    def test_copy_body(self):
        req = self._blankOne('/', method='POST', body=b'some text',
                            request_body_tempfile_limit=1)
        old_body_file = req.body_file_raw
        req.copy_body()
        assert req.body_file_raw is not old_body_file
        req = self._blankOne('/', method='POST',
                body_file=UnseekableInput(b'0123456789'), content_length=10)
        assert not hasattr(req.body_file_raw, 'seek')
        old_body_file = req.body_file_raw
        req.make_body_seekable()
        assert req.body_file_raw is not old_body_file
        assert req.body == b'0123456789'
        old_body_file = req.body_file
        req.make_body_seekable()
        assert req.body_file_raw is old_body_file
        assert req.body_file is old_body_file

    def test_already_consumed_stream(self):
        from webob.request import Request
        body = 'something'.encode('latin-1')
        content_type = 'application/x-www-form-urlencoded; charset=latin-1'
        environ = {
            'wsgi.input': BytesIO(body),
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST'
        }
        req = Request(environ)
        req = req.decode('latin-1')
        req2 = Request(environ)
        req2 = req2.decode('latin-1')
        assert body == req2.body

    def test_none_field_name(self):
        from webob.request import Request
        body = b'--FOO\r\nContent-Disposition: form-data\r\n\r\n123\r\n--FOO--'
        content_type = 'multipart/form-data; boundary=FOO'
        environ = {
            'wsgi.input': BytesIO(body),
            'CONTENT_TYPE': content_type,
            'CONTENT_LENGTH': len(body),
            'REQUEST_METHOD': 'POST'
        }
        req = Request(environ)
        req = req.decode('latin-1')
        assert body == req.body

    def test_broken_seek(self):
        # copy() should work even when the input has a broken seek method
        req = self._blankOne('/', method='POST',
                body_file=UnseekableInputWithSeek(b'0123456789'),
                content_length=10)
        assert hasattr(req.body_file_raw, 'seek')
        with pytest.raises(IOError):
            req.body_file_raw.seek(0)
        old_body_file = req.body_file
        req2 = req.copy()
        assert req2.body_file_raw is req2.body_file is not old_body_file
        assert req2.body == b'0123456789'

    def test_set_body(self):
        req = self._blankOne('/', method='PUT', body=b'foo')
        assert req.is_body_seekable
        assert req.body == b'foo'
        assert req.content_length == 3
        del req.body
        assert req.body == b''
        assert req.content_length == 0

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
        assert req.authorization == ('Digest', {'uri': '/?a=b'})

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
        assert 'content-length' not in request.headers
        assert 'content-type' not in request.headers

    def test_env_keys(self):
        req = self._blankOne('/')
        # SCRIPT_NAME can be missing
        del req.environ['SCRIPT_NAME']
        assert req.script_name == ''
        assert req.uscript_name == ''

    def test_repr_nodefault(self):
        from webob.request import NoDefault
        nd = NoDefault
        assert repr(nd) == '(No Default)'

    def test_request_noenviron_param(self):
        # Environ is a a mandatory not null param in Request.
        with pytest.raises(TypeError):
            self._makeOne(environ=None)

    def test_unexpected_kw(self):
        # Passed an attr in kw that does not exist in the class, should
        # raise an error
        # Passed an attr in kw that does exist in the class, should be ok
        with pytest.raises(TypeError):
            self._makeOne({'a': 1}, this_does_not_exist=1)

        r = self._makeOne({'a': 1}, server_name='127.0.0.1')
        assert getattr(r, 'server_name', None) == '127.0.0.1'

    def test_conttype_set_del(self):
        # Deleting content_type attr from a request should update the
        # environ dict
        # Assigning content_type should replace first option of the environ
        # dict
        r = self._makeOne({'a':1}, **{'content_type':'text/html'})
        assert 'CONTENT_TYPE' in r.environ
        assert hasattr(r, 'content_type')
        del r.content_type
        assert 'CONTENT_TYPE' not in r.environ
        a = self._makeOne({'a':1},
                content_type='charset=utf-8;application/atom+xml;type=entry')
        assert a.environ['CONTENT_TYPE']== 'charset=utf-8;application/atom+xml;type=entry'
        a.content_type = 'charset=utf-8'
        assert a.environ['CONTENT_TYPE']== 'charset=utf-8;application/atom+xml;type=entry'

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
            assert i in r.headers and 'HTTP_'+i.upper().replace('-', '_') in r.environ
        r.headers = {'Server':'Apache'}
        assert set(r.environ.keys()) == set(['a',  'HTTP_SERVER'])

    def test_host_url(self):
        # Request has a read only property host_url that combines several
        # keys to create a host_url
        a = self._makeOne(
            {'wsgi.url_scheme':'http'}, **{'host':'www.example.com'})
        assert a.host_url == 'http://www.example.com'
        a = self._makeOne(
            {'wsgi.url_scheme':'http'}, **{'server_name':'localhost',
                                                'server_port':5000})
        assert a.host_url == 'http://localhost:5000'
        a = self._makeOne(
            {'wsgi.url_scheme':'https'}, **{'server_name':'localhost',
                                            'server_port':443})
        assert a.host_url == 'https://localhost'

    def test_path_info_p(self):
        # Peek path_info to see what's coming
        # Pop path_info until there's nothing remaining
        a = self._makeOne({'a':1}, **{'path_info':'/foo/bar','script_name':''})
        assert a.path_info_peek() == 'foo'
        assert a.path_info_pop() == 'foo'
        assert a.path_info_peek() == 'bar'
        assert a.path_info_pop() == 'bar'
        assert a.path_info_peek() == None
        assert a.path_info_pop() == None

    def test_urlvars_property(self):
        # Testing urlvars setter/getter/deleter
        a = self._makeOne({'wsgiorg.routing_args':((),{'x':'y'}),
                           'paste.urlvars':{'test':'value'}})
        a.urlvars = {'hello':'world'}
        assert 'paste.urlvars' not in a.environ
        assert a.environ['wsgiorg.routing_args'] == ((), {'hello':'world'})
        del a.urlvars
        assert 'wsgiorg.routing_args' not in a.environ
        a = self._makeOne({'paste.urlvars':{'test':'value'}})
        assert a.urlvars == {'test':'value'}
        a.urlvars = {'hello':'world'}
        assert a.environ['paste.urlvars'] == {'hello':'world'}
        del a.urlvars
        assert 'paste.urlvars' not in a.environ

    def test_urlargs_property(self):
        # Testing urlargs setter/getter/deleter
        a = self._makeOne({'paste.urlvars':{'test':'value'}})
        assert a.urlargs == ()
        a.urlargs = {'hello':'world'}
        assert a.environ['wsgiorg.routing_args'] == ({'hello':'world'}, {'test':'value'})
        a = self._makeOne({'a':1})
        a.urlargs = {'hello':'world'}
        assert a.environ['wsgiorg.routing_args'] == ({'hello':'world'}, {})
        del a.urlargs
        assert 'wsgiorg.routing_args' not in a.environ

    def test_host_property(self):
        # Testing host setter/getter/deleter
        a = self._makeOne({'wsgi.url_scheme':'http'}, server_name='localhost',
                          server_port=5000)
        assert a.host == "localhost:5000"
        a.host = "localhost:5000"
        assert 'HTTP_HOST' in a.environ
        del a.host
        assert 'HTTP_HOST' not in a.environ

    def test_body_property(self):
        # Testing body setter/getter/deleter plus making sure body has a
        # seek method
        # a = Request({'a':1}, **{'CONTENT_LENGTH':'?'})
        # I cannot think of a case where somebody would put anything else
        # than a # numerical value in CONTENT_LENGTH, Google didn't help
        # either
        # assert a.body == ''
        # I need to implement a not seekable stringio like object.

        import string

        cls = self._getTargetClass()
        limit = cls.request_body_tempfile_limit
        len_strl = limit // len(string.ascii_letters) + 1
        r = self._makeOne(
            {
                'a': 1,
                'REQUEST_METHOD': 'POST',
            },
            body_file=BytesIO(bytes_(string.ascii_letters * len_strl))
        )
        assert isinstance(r.body_file, BytesIO)
        assert r.is_body_readable

        assert len(r.body) == len(string.ascii_letters * len_strl)
        with pytest.raises(TypeError):
            setattr(r, 'body', text_('hello world'))

        r.body = None
        assert r.body == b''

        no_seek = UnseekableInput(bytes_(string.ascii_letters))

        r = self._makeOne({'a': 1}, method='PUT', body_file=no_seek)
        assert not hasattr(r.body_file_raw, 'seek')

        r.make_body_seekable()
        assert hasattr(r.body_file_raw, 'seek')

        r = self._makeOne({'a': 1}, method='PUT',
                          body_file=BytesIO(bytes_(string.ascii_letters)))
        assert hasattr(r.body_file_raw, 'seek')

        r.make_body_seekable()
        assert hasattr(r.body_file_raw, 'seek')

    def test_repr_invalid(self):
        # If we have an invalid WSGI environ, the repr should tell us.
        req = self._makeOne({'CONTENT_LENGTH': '0', 'body': ''})
        assert repr(req).endswith('(invalid WSGI environ)>')

    def test_from_garbage_file(self):
        # If we pass a file with garbage to from_file method it should
        # raise an error plus missing bits in from_file method
        io = BytesIO(b'hello world')

        cls = self._getTargetClass()
        with pytest.raises(ValueError):
            cls.from_file(io)

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
        assert isinstance(req, cls)
        assert not repr(req).endswith('(invalid WSGI environ)>')
        val_file = BytesIO(
            b"GET /webob/ HTTP/1.1\n"
            b"Host pythonpaste.org\n"
        )
        with pytest.raises(ValueError):
            cls.from_file(val_file)

    def test_from_file_patch(self):
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req_patch)
        assert "PATCH" == req.method
        assert len(req.body)
        assert req.body in _test_req_patch
        assert _test_req_patch == req.as_bytes()

    def test_from_bytes(self):
        # A valid request without a Content-Length header should still read
        # the full body.
        # Also test parity between as_string and from_bytes / from_file.
        import cgi
        cls = self._getTargetClass()
        req = cls.from_bytes(_test_req)
        assert isinstance(req, cls)
        assert not repr(req).endswith('(invalid WSGI environ)>')
        assert '\n' not in req.http_version or '\r' in req.http_version
        assert ',' not in req.host
        assert req.content_length is not None
        assert req.content_length == 337
        assert b'foo' in req.body
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        assert bar_contents in req.body
        assert req.params['foo'] == 'foo'
        bar = req.params['bar']
        assert isinstance(bar, cgi.FieldStorage)
        assert bar.type == 'application/octet-stream'
        bar.file.seek(0)
        assert bar.file.read() == bar_contents
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type'
            )
        assert req.as_bytes() == _test_req_copy

        req2 = cls.from_bytes(_test_req2)
        assert 'host' not in req2.headers
        assert req2.as_bytes() == _test_req2.rstrip()
        with pytest.raises(ValueError):
            cls.from_bytes(_test_req2 + b'xx')

    def test_from_text(self):
        import cgi
        cls = self._getTargetClass()
        req = cls.from_text(text_(_test_req, 'utf-8'))
        assert isinstance(req, cls)
        assert not repr(req).endswith('(invalid WSGI environ)>')
        assert '\n' not in req.http_version or '\r' in req.http_version
        assert ',' not in req.host
        assert req.content_length is not None
        assert req.content_length == 337
        assert b'foo' in req.body
        bar_contents = b"these are the contents of the file 'bar.txt'\r\n"
        assert bar_contents in req.body
        assert req.params['foo'] == 'foo'
        bar = req.params['bar']
        assert isinstance(bar, cgi.FieldStorage)
        assert bar.type == 'application/octet-stream'
        bar.file.seek(0)
        assert bar.file.read() == bar_contents
        # out should equal contents, except for the Content-Length header,
        # so insert that.
        _test_req_copy = _test_req.replace(
            b'Content-Type',
            b'Content-Length: 337\r\nContent-Type'
            )
        assert req.as_bytes() == _test_req_copy

        req2 = cls.from_bytes(_test_req2)
        assert 'host' not in req2.headers
        assert req2.as_bytes() == _test_req2.rstrip()
        with pytest.raises(ValueError):
            cls.from_bytes(_test_req2 + b'xx')

    def test_blank(self):
        # BaseRequest.blank class method
        with pytest.raises(ValueError):
            self._blankOne(
                'www.example.com/foo?hello=world',
                None,
                'www.example.com/foo?hello=world')
        with pytest.raises(ValueError):
            self._blankOne(
                'gopher.example.com/foo?hello=world',
                None,
                'gopher://gopher.example.com')
        req = self._blankOne('www.example.com/foo?hello=world', None,
                             'http://www.example.com')
        assert req.environ.get('HTTP_HOST', None) == 'www.example.com:80'
        assert req.environ.get('PATH_INFO', None) == 'www.example.com/foo'
        assert req.environ.get('QUERY_STRING', None) == 'hello=world'
        assert req.environ.get('REQUEST_METHOD', None) == 'GET'
        req = self._blankOne(
            'www.example.com/secure?hello=world',
            None,
            'https://www.example.com/secure')
        assert req.environ.get('HTTP_HOST', None) == 'www.example.com:443'
        assert req.environ.get('PATH_INFO', None) == 'www.example.com/secure'
        assert req.environ.get('QUERY_STRING', None) == 'hello=world'
        assert req.environ.get('REQUEST_METHOD', None) == 'GET'
        assert req.environ.get('SCRIPT_NAME', None) == '/secure'
        assert req.environ.get('SERVER_NAME', None) == 'www.example.com'
        assert req.environ.get('SERVER_PORT', None) == '443'

    def test_post_does_not_reparse(self):
        # test that there's no repetitive parsing is happening on every
        # req.POST access
        req = self._blankOne(
            '/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        post1 = req.POST
        assert 'webob._parsed_post_vars' in req.environ
        post2 = req.POST
        assert post1 is post2

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
        assert resp.body == b'abc'
        assert resp.headers['x-data'] == b'abc'

    def test_body_file_noseek(self):
        req = self._blankOne('/', method='PUT', body=b'abc')
        lst = [req.body_file.read(1) for i in range(3)]
        assert lst == [b'a', b'b', b'c']

    def test_cgi_escaping_fix(self):
        req = self._blankOne(
            '/',
            content_type='multipart/form-data; boundary=boundary',
            POST=_cgi_escaping_body
        )
        assert list(req.POST.keys()) == ['%20%22"']
        req.body_file.read()
        assert list(req.POST.keys()) == ['%20%22"']

    def test_content_type_none(self):
        r = self._blankOne('/', content_type='text/html')
        assert r.content_type == 'text/html'
        r.content_type = None

    def test_body_file_seekable(self):
        r = self._blankOne('/', method='POST')
        r.body_file = BytesIO(b'body')
        assert r.body_file_seekable.read() == b'body'

    def test_request_init(self):
        # port from doctest (docs/reference.txt)
        req = self._blankOne('/article?id=1')
        assert req.environ['HTTP_HOST'] == 'localhost:80'
        assert req.environ['PATH_INFO'] == '/article'
        assert req.environ['QUERY_STRING'] == 'id=1'
        assert req.environ['REQUEST_METHOD'] == 'GET'
        assert req.environ['SCRIPT_NAME'] == ''
        assert req.environ['SERVER_NAME'] == 'localhost'
        assert req.environ['SERVER_PORT'] == '80'
        assert req.environ['SERVER_PROTOCOL'] == 'HTTP/1.0'
        assert (hasattr(req.environ['wsgi.errors'], 'write') and
                hasattr(req.environ['wsgi.errors'], 'flush'))
        assert (hasattr(req.environ['wsgi.input'], 'next') or
                hasattr(req.environ['wsgi.input'], '__next__'))
        assert req.environ['wsgi.multiprocess'] == False
        assert req.environ['wsgi.multithread'] == False
        assert req.environ['wsgi.run_once'] == False
        assert req.environ['wsgi.url_scheme'] == 'http'
        assert req.environ['wsgi.version'], (1 == 0)

        # Test body
        assert hasattr(req.body_file, 'read')
        assert req.body == b''
        req.method = 'PUT'
        req.body = b'test'
        assert hasattr(req.body_file, 'read')
        assert req.body == b'test'

        # Test method & URL
        assert req.method == 'PUT'
        assert req.scheme == 'http'
        assert req.script_name == '' # The base of the URL
        req.script_name = '/blog'  # make it more interesting
        assert req.path_info == '/article'
        # Content-Type of the request body
        assert req.content_type == ''
        # The auth'ed user (there is none set)
        assert req.remote_user is None
        assert req.remote_addr is None
        assert req.host == 'localhost:80'
        assert req.host_url == 'http://localhost'
        assert req.application_url == 'http://localhost/blog'
        assert req.path_url == 'http://localhost/blog/article'
        assert req.url == 'http://localhost/blog/article?id=1'
        assert req.path == '/blog/article'
        assert req.path_qs == '/blog/article?id=1'
        assert req.query_string == 'id=1'
        assert req.relative_url('archive') == 'http://localhost/blog/archive'

        # Doesn't change request
        assert req.path_info_peek() == 'article'
        # Does change request!
        assert req.path_info_pop() == 'article'
        assert req.script_name == '/blog/article'
        assert req.path_info == ''

        # Headers
        req.headers['Content-Type'] = 'application/x-www-urlencoded'
        assert sorted(req.headers.items()) == [
            ('Content-Length', '4'),
            ('Content-Type', 'application/x-www-urlencoded'),
            ('Host', 'localhost:80')
        ]
        assert req.environ['CONTENT_TYPE'] == 'application/x-www-urlencoded'

    def test_request_query_and_POST_vars(self):
        # port from doctest (docs/reference.txt)

        # Query & POST variables
        from webob.multidict import MultiDict
        from webob.multidict import NestedMultiDict
        from webob.multidict import GetDict
        req = self._blankOne('/test?check=a&check=b&name=Bob')
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        assert req.GET == GET
        assert req.GET['check'] == 'b'
        assert req.GET.getall('check'), ['a' == 'b']
        assert list(req.GET.items()) == [('check', 'a'), ('check', 'b'), ('name', 'Bob')]

        assert isinstance(req.POST, NoVars)
        # NoVars can be read like a dict, but not written
        assert list(req.POST.items()) == []
        req.method = 'POST'
        req.body = b'name=Joe&email=joe@example.com'
        assert req.POST == MultiDict(
            [
                ('name', 'Joe'),
                ('email', 'joe@example.com')
            ]
        )
        assert req.POST['name'] == 'Joe'

        assert isinstance(req.params, NestedMultiDict)
        assert list(req.params.items()) == [
            ('check', 'a'),
            ('check', 'b'),
            ('name', 'Bob'),
            ('name', 'Joe'),
            ('email', 'joe@example.com')
        ]
        assert req.params['name'] == 'Bob'
        assert req.params.getall('name'), ['Bob' == 'Joe']

    @pytest.mark.filterwarnings('ignore:.*best_match.*')
    def test_request_put(self):
        from datetime import datetime
        from webob import Response
        from webob import UTC
        from webob.acceptparse import Accept
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
        assert req.GET == GET
        assert req.POST == MultiDict([
            ('var1', 'value1'),
            ('var2', 'value2'),
            ('rep', '1'),
            ('rep', '2')]
        )
        assert list(req.GET.items()) == [('check', 'a'), ('check', 'b'), ('name', 'Bob')]

        # Unicode
        req.charset = 'utf8'
        assert list(req.GET.items()) == [('check', 'a'), ('check', 'b'), ('name', 'Bob')]

        # Cookies
        req.headers['Cookie'] = 'test=value'
        assert isinstance(req.cookies, MutableMapping)
        assert list(req.cookies.items()) == [('test', 'value')]
        req.charset = None
        assert req.cookies == {'test': 'value'}

        # Accept-* headers
        assert 'text/html' in req.accept
        req.accept = 'text/html;q=0.5, application/xhtml+xml;q=1'
        assert isinstance(req.accept, Accept)
        assert 'text/html' in req.accept

        assert req.accept.best_match(['text/html', 'application/xhtml+xml']) == 'application/xhtml+xml'

        req.accept_language = 'es, pt-BR'
        assert req.accept_language.best_match(['es']) == 'es'

        # Conditional Requests
        server_token = 'opaque-token'
        # shouldn't return 304
        assert not server_token in req.if_none_match
        req.if_none_match = server_token
        assert isinstance(req.if_none_match, ETagMatcher)
        # You *should* return 304
        assert server_token in req.if_none_match
        # if_none_match should use weak matching
        weak_token = 'W/"%s"' % server_token
        req.if_none_match = weak_token
        assert req.headers['if-none-match'] == weak_token
        assert server_token in req.if_none_match

        req.if_modified_since = datetime(2006, 1, 1, 12, 0, tzinfo=UTC)
        assert req.headers['If-Modified-Since'] == 'Sun, 01 Jan 2006 12:00:00 GMT'
        server_modified = datetime(2005, 1, 1, 12, 0, tzinfo=UTC)
        assert req.if_modified_since
        assert req.if_modified_since >= server_modified

        assert not req.if_range
        assert Response(etag='some-etag', last_modified=datetime(2005, 1, 1, 12, 0)) in req.if_range
        req.if_range = 'opaque-etag'
        assert Response(etag='other-etag') not in req.if_range
        assert Response(etag='opaque-etag') in req.if_range

        res = Response(etag='opaque-etag')
        assert res in req.if_range

        req.range = 'bytes=0-100'
        assert isinstance(req.range, Range)
        assert tuple(req.range), (0 == 101)
        cr = req.range.content_range(length=1000)
        assert tuple(cr), (0, 101 == 1000)

        assert server_token in req.if_match
        # No If-Match means everything is ok
        req.if_match = server_token
        assert server_token in req.if_match
        # Still OK
        req.if_match = 'other-token'
        # Not OK, should return 412 Precondition Failed:
        assert server_token not in req.if_match

    def test_request_patch(self):
        from webob.multidict import MultiDict
        from webob.multidict import GetDict
        req = self._blankOne('/test?check=a&check=b&name=Bob')
        req.method = 'PATCH'
        req.body = b'var1=value1&var2=value2&rep=1&rep=2'
        req.environ['CONTENT_LENGTH'] = str(len(req.body))
        req.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        GET = GetDict([('check', 'a'),
                      ('check', 'b'),
                      ('name', 'Bob')], {})
        assert req.GET == GET
        assert req.POST == MultiDict([
            ('var1', 'value1'),
            ('var2', 'value2'),
            ('rep', '1'),
            ('rep', '2')]
        )

    def test_call_WSGI_app(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [b'Hi!']
        assert req.call_application(wsgi_app) == ('200 OK', [('Content-Type', 'text/plain')], [b'Hi!'])

        res = req.get_response(wsgi_app)
        from webob.response import Response
        assert isinstance(res, Response)
        assert res.status == '200 OK'
        from webob.headers import ResponseHeaders
        assert isinstance(res.headers, ResponseHeaders)
        assert list(res.headers.items()) == [('Content-Type', 'text/plain')]
        assert res.body == b'Hi!'

    def test_call_WSGI_app_204(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('204 No Content', [])
            return [b'']
        assert req.call_application(wsgi_app) == ('204 No Content', [], [b''])

        res = req.get_response(wsgi_app)
        from webob.response import Response
        assert isinstance(res, Response)
        assert res.status == '204 No Content'
        from webob.headers import ResponseHeaders
        assert isinstance(res.headers, ResponseHeaders)
        assert list(res.headers.items()) == []
        assert res.body == b''

    def test_call_WSGI_app_no_content_type(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [])
            return [b'']
        assert req.call_application(wsgi_app) == ('200 OK', [], [b''])

        res = req.get_response(wsgi_app)
        from webob.response import Response
        assert isinstance(res, Response)
        assert res.status == '200 OK'
        assert res.content_type is None
        from webob.headers import ResponseHeaders
        assert isinstance(res.headers, ResponseHeaders)
        assert list(res.headers.items()) == []
        assert res.body == b''

    def test_get_response_catch_exc_info_true(self):
        req = self._blankOne('/')
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [b'Hi!']
        res = req.get_response(wsgi_app, catch_exc_info=True)
        from webob.response import Response
        assert isinstance(res, Response)
        assert res.status == '200 OK'
        from webob.headers import ResponseHeaders
        assert isinstance(res.headers, ResponseHeaders)
        assert list(res.headers.items()) == [('Content-Type', 'text/plain')]
        assert res.body == b'Hi!'

    def equal_req(self, req, inp):
        cls = self._getTargetClass()
        req2 = cls.from_file(inp)
        assert req.url == req2.url
        headers1 = dict(req.headers)
        headers2 = dict(req2.headers)
        assert int(headers1.get('Content-Length', '0')) == int(headers2.get('Content-Length', '0'))
        if 'Content-Length' in headers1:
            del headers1['Content-Length']
        if 'Content-Length' in headers2:
            del headers2['Content-Length']
        assert headers1 == headers2
        req_body = req.body
        req2_body = req2.body
        assert req_body == req2_body

@pytest.mark.filterwarnings('ignore:FakeCGIBody')
class TestFakeCGIBody(object):
    def test_encode_multipart_value_type_options(self):
        from cgi import FieldStorage
        from webob.request import BaseRequest, FakeCGIBody
        from webob.multidict import MultiDict
        multipart_type = 'multipart/form-data; boundary=foobar'
        from io import BytesIO
        body = (
            b'--foobar\r\n'
            b'Content-Disposition: form-data; name="bananas"; '
            b'filename="bananas.txt"\r\n'
            b'Content-type: text/plain; charset="utf-7"\r\n'
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
        assert vars['bananas'].__class__ == FieldStorage
        fake_body = FakeCGIBody(vars, multipart_type)
        assert fake_body.read() == body

    def test_encode_multipart_no_boundary(self):
        from webob.request import FakeCGIBody
        with pytest.raises(ValueError):
            FakeCGIBody({}, 'multipart/form-data')

    def test_repr(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        body.read(1)
        import re
        assert re.sub(r'\b0x[0-9a-f]+\b', '<whereitsat>', repr(body)) == "<FakeCGIBody at <whereitsat> viewing {'bananas': 'ba...nas'}>"

    def test_fileno(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        assert body.fileno() == None

    def test_iter(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        assert list(body) == [
            b'--foobar\r\n',
            b'Content-Disposition: form-data; name="bananas"\r\n',
            b'\r\n',
            b'bananas\r\n',
            b'--foobar--',
            ]

    def test_readline(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'multipart/form-data; boundary=foobar')
        assert body.readline() == b'--foobar\r\n'
        assert  body.readline() == b'Content-Disposition: form-data; name="bananas"\r\n'
        assert body.readline() == b'\r\n'
        assert body.readline() == b'bananas\r\n'
        assert body.readline() == b'--foobar--'
        # subsequent calls to readline will return ''

    def test_read_bad_content_type(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'}, 'application/jibberjabber')
        with pytest.raises(AssertionError):
            body.read()

    def test_read_urlencoded(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'},
                           'application/x-www-form-urlencoded')
        assert body.read() == b'bananas=bananas'

    def test_readable(self):
        from webob.request import FakeCGIBody
        body = FakeCGIBody({'bananas': 'bananas'}, 'application/something')
        assert body.readable()


class Test_cgi_FieldStorage__repr__patch(object):
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
        assert result, "FieldStorage('name' == 'filename')"

    def test_without_file(self):
        class Fake(object):
            name = 'name'
            file = None
            filename = 'filename'
            value = 'value'
        fake = Fake()
        result = self._callFUT(fake)
        assert result, "FieldStorage('name', 'filename' == 'value')"


class TestLimitedLengthFile(object):
    def _makeOne(self, file, maxlen):
        from webob.request import LimitedLengthFile
        return LimitedLengthFile(file, maxlen)

    def test_fileno(self):
        class DummyFile(object):
            def fileno(self):
                return 1
        dummyfile = DummyFile()
        inst = self._makeOne(dummyfile, 0)
        assert inst.fileno() == 1


class Test_environ_from_url(object):
    def _callFUT(self, *arg, **kw):
        from webob.request import environ_from_url
        return environ_from_url(*arg, **kw)

    def test_environ_from_url(self):
        # Generating an environ just from an url plus testing environ_add_POST
        with pytest.raises(TypeError):
            self._callFUT('http://www.example.com/foo?bar=baz#qux')
        with pytest.raises(TypeError):
            self._callFUT('gopher://gopher.example.com')
        req = self._callFUT('http://www.example.com/foo?bar=baz')
        assert req.get('HTTP_HOST', None) == 'www.example.com:80'
        assert req.get('PATH_INFO', None) == '/foo'
        assert req.get('QUERY_STRING', None) == 'bar=baz'
        assert req.get('REQUEST_METHOD', None) == 'GET'
        assert req.get('SCRIPT_NAME', None) == ''
        assert req.get('SERVER_NAME', None) == 'www.example.com'
        assert req.get('SERVER_PORT', None) == '80'
        req = self._callFUT('https://www.example.com/foo?bar=baz')
        assert req.get('HTTP_HOST', None) == 'www.example.com:443'
        assert req.get('PATH_INFO', None) == '/foo'
        assert req.get('QUERY_STRING', None) == 'bar=baz'
        assert req.get('REQUEST_METHOD', None) == 'GET'
        assert req.get('SCRIPT_NAME', None) == ''
        assert req.get('SERVER_NAME', None) == 'www.example.com'
        assert req.get('SERVER_PORT', None) == '443'

        from webob.request import environ_add_POST

        environ_add_POST(req, None)
        assert 'CONTENT_TYPE' not in req
        assert 'CONTENT_LENGTH' not in req
        environ_add_POST(req, {'hello': 'world'})
        assert req.get('HTTP_HOST', None), 'www.example.com:443'
        assert req.get('PATH_INFO', None) == '/foo'
        assert req.get('QUERY_STRING', None) == 'bar=baz'
        assert req.get('REQUEST_METHOD', None) == 'POST'
        assert req.get('SCRIPT_NAME', None) == ''
        assert req.get('SERVER_NAME', None) == 'www.example.com'
        assert req.get('SERVER_PORT', None) == '443'
        assert req.get('CONTENT_LENGTH', None) == '11'
        assert req.get('CONTENT_TYPE', None) == 'application/x-www-form-urlencoded'
        assert req['wsgi.input'].read() == b'hello=world'

    def test_environ_from_url_highorder_path_info(self):
        from webob.request import Request
        env = self._callFUT('/%E6%B5%81')
        assert env['PATH_INFO'] == '/\xe6\xb5\x81'
        request = Request(env)
        expected = text_(b'/\xe6\xb5\x81', 'utf-8') # u'/\u6d41'
        assert request.path_info == expected
        assert request.upath_info == expected

    def test_fileupload_mime_type_detection(self):
        from webob.request import Request
        # sometimes on win the detected mime type for .jpg will be
        # image/pjpeg for ex. so use a non-standard extesion to avoid that
        import mimetypes
        mimetypes.add_type('application/x-foo', '.foo')
        request = Request.blank("/", POST=dict(file1=("foo.foo", "xxx"),
                                               file2=("bar.mp3", "xxx")))
        assert "audio/mpeg" in request.body.decode('ascii',
                                                   str(request))
        assert 'application/x-foo' in request.body.decode('ascii',
                                                          str(request))

class TestRequestMultipart(object):
    def test_multipart_with_charset(self):
        from webob.request import Request
        req = Request.from_bytes(_test_req_multipart_charset)
        assert req.POST['title'].encode('utf8') == text_('こんにちは', 'utf-8').encode('utf8')

def simpleapp(environ, start_response):
    from webob.request import Request
    status = '200 OK'
    response_headers = [('Content-type', 'text/plain')]
    start_response(status, response_headers)
    request = Request(environ)
    request.remote_user = 'bob'
    return [bytes_(x) for x in [
        'Hello world!\n',
        'The get is %r' % request.GET,
        ' and Val is %s\n' % repr(request.GET.get('name')),
        'The languages are: %s\n' % ([o for o, _ in sorted(
            request.accept_language.parsed or (),
            key=lambda x: x[1],  # sort by quality
            reverse=True,
        )]),
        'The accepttypes is: %s\n' % ','.join([
            o for o, _ in request.accept.acceptable_offers([
                'application/xml', 'text/html',
            ])
        ]),
        'post is %r\n' % request.POST,
        'params is %r\n' % request.params,
        'cookies is %r\n' % request.cookies,
        'body: %r\n' % request.body,
        'method: %s\n' % request.method,
        'remote_user: %r\n' % request.environ['REMOTE_USER'],
        'host_url: %r; application_url: %r; path_url: %r; url: %r\n' % (
            request.host_url,
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

_test_req_patch = b"""
PATCH /webob/ HTTP/1.1
Content-Length: 14
Content-Type: application/json

{"foo": "bar"}
"""

_test_req2 = b"""
POST / HTTP/1.0
Content-Length: 0

"""

_test_req_multipart_charset = b"""
POST /upload/ HTTP/1.1
Host: foo.com
User-Agent: Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2.13) Gecko/20101206 Ubuntu/10.04 (lucid) Firefox/3.6.13
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.8,ja;q=0.6
Accept-Encoding: gzip,deflate
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
Content-Type: multipart/form-data; boundary=000e0ce0b196b4ee6804c6c8af94
Content-Length: 926

--000e0ce0b196b4ee6804c6c8af94
Content-Type: text/plain; charset=ISO-2022-JP
Content-Disposition: form-data; name=title
Content-Transfer-Encoding: 7bit

\x1b$B$3$s$K$A$O\x1b(B
--000e0ce0b196b4ee6804c6c8af94
Content-Type: text/plain; charset=ISO-8859-1
Content-Disposition: form-data; name=submit

Submit
--000e0ce0b196b4ee6804c6c8af94
Content-Type: message/external-body; charset=ISO-8859-1; blob-key=AMIfv94TgpPBtKTL3a0U9Qh1QCX7OWSsmdkIoD2ws45kP9zQAGTOfGNz4U18j7CVXzODk85WtiL5gZUFklTGY3y4G0Jz3KTPtJBOFDvQHQew7YUymRIpgUXgENS_fSEmInAIQdpSc2E78MRBVEZY392uhph3r-In96t8Z58WIRc-Yikx1bnarWo
Content-Disposition: form-data; name=file; filename="photo.jpg"

Content-Type: image/jpeg
Content-Length: 38491
X-AppEngine-Upload-Creation: 2012-08-08 15:32:29.035959
Content-MD5: ZjRmNGRhYmNhZTkyNzcyOWQ5ZGUwNDgzOWFkNDAxN2Y=
Content-Disposition: form-data; name=file; filename="photo.jpg"


--000e0ce0b196b4ee6804c6c8af94--"""


_test_req = _norm_req(_test_req)
_test_req_patch = _norm_req(_test_req_patch)
_test_req2 = _norm_req(_test_req2) + b'\r\n'
_test_req_multipart_charset = _norm_req(_test_req_multipart_charset)

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
            if self.pos + size > len(self.data):
                size = len(self.data) - self.pos
            t = self.data[self.pos:self.pos + size]
            self.pos += size
            return t

class UnseekableInputWithSeek(UnseekableInput):
    def seek(self, pos, rel=0):
        raise IOError("Invalid seek!")


class _Helper_test_request_wrong_clen(object):
    def __init__(self, f):
        self.f = f
        self.file_ended = False

    def read(self, *args):
        r = self.f.read(*args)
        if not r:
            if self.file_ended:
                raise AssertionError("Reading should stop after first empty string")
            self.file_ended = True
        return r

    def seek(self, pos):
        pass
