# -*- coding: utf-8 -*-
from datetime import timedelta
from webob import cookies
from webob.compat import text_
from nose.tools import eq_
import unittest
from webob.compat import native_
from webob.compat import PY3

def test_cookie_empty():
    c = cookies.Cookie() # empty cookie
    eq_(repr(c), '<Cookie: []>')

def test_cookie_one_value():
    c = cookies.Cookie('dismiss-top=6')
    vals = list(c.values())
    eq_(len(vals), 1)
    eq_(vals[0].name, b'dismiss-top')
    eq_(vals[0].value, b'6')

def test_cookie_one_value_with_trailing_semi():
    c = cookies.Cookie('dismiss-top=6;')
    vals = list(c.values())
    eq_(len(vals), 1)
    eq_(vals[0].name, b'dismiss-top')
    eq_(vals[0].value, b'6')
    c = cookies.Cookie('dismiss-top=6;')

def test_cookie_complex():
    c = cookies.Cookie('dismiss-top=6; CP=null*, '\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,"')
    d = lambda v: v.decode('ascii')
    c_dict = dict((d(k),d(v.value)) for k,v in c.items())
    eq_(c_dict, {'a': '42,',
        'CP': 'null*',
        'PHPSESSID': '0a539d42abc001cdc762809248d4beed',
        'dismiss-top': '6'
    })

def test_cookie_complex_serialize():
    c = cookies.Cookie('dismiss-top=6; CP=null*, '\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,"')
    eq_(c.serialize(),
        'CP=null*; PHPSESSID=0a539d42abc001cdc762809248d4beed; a="42\\054"; '
        'dismiss-top=6')

def test_cookie_load_multiple():
    c = cookies.Cookie('a=1; Secure=true')
    vals = list(c.values())
    eq_(len(vals), 1)
    eq_(c[b'a'][b'secure'], b'true')

def test_cookie_secure():
    c = cookies.Cookie()
    c[text_('foo')] = b'bar'
    c[b'foo'].secure = True
    eq_(c.serialize(), 'foo=bar; secure')

def test_cookie_httponly():
    c = cookies.Cookie()
    c['foo'] = b'bar'
    c[b'foo'].httponly = True
    eq_(c.serialize(), 'foo=bar; HttpOnly')

def test_cookie_reserved_keys():
    c = cookies.Cookie('dismiss-top=6; CP=null*; $version=42; a=42')
    assert '$version' not in c
    c = cookies.Cookie('$reserved=42; a=$42')
    eq_(list(c.keys()), [b'a'])

def test_serialize_cookie_date():
    """
        Testing webob.cookies.serialize_cookie_date.
        Missing scenarios:
            * input value is an str, should be returned verbatim
            * input value is an int, should be converted to timedelta and we
              should continue the rest of the process
    """
    eq_(cookies.serialize_cookie_date(b'Tue, 04-Jan-2011 13:43:50 GMT'),
        b'Tue, 04-Jan-2011 13:43:50 GMT')
    eq_(cookies.serialize_cookie_date(text_('Tue, 04-Jan-2011 13:43:50 GMT')),
        b'Tue, 04-Jan-2011 13:43:50 GMT')
    eq_(cookies.serialize_cookie_date(None), None)
    cdate_delta = cookies.serialize_cookie_date(timedelta(seconds=10))
    cdate_int = cookies.serialize_cookie_date(10)
    eq_(cdate_delta, cdate_int)

def test_ch_unquote():
    eq_(cookies._unquote(b'"hello world'), b'"hello world')
    eq_(cookies._unquote(b'hello world'), b'hello world')
    eq_(cookies._unquote(b'"hello world"'), b'hello world')
    eq_(cookies._quote(b'hello world'), b'"hello world"')
    # quotation mark is escaped w/ backslash
    eq_(cookies._unquote(b'"\\""'), b'"')
    eq_(cookies._quote(b'"'), b'"\\""')
    # misc byte escaped as octal
    eq_(cookies._unquote(b'"\\377"'), b'\xff')
    eq_(cookies._quote(b'\xff'), b'"\\377"')
    # combination
    eq_(cookies._unquote(b'"a\\"\\377"'), b'a"\xff')
    eq_(cookies._quote(b'a"\xff'), b'"a\\"\\377"')

def test_cookie_invalid_name():
    c = cookies.Cookie()
    c['La Pe\xc3\xb1a'] = '1'
    eq_(len(c), 0)

def test_morsel_serialize_with_expires():
    morsel = cookies.Morsel(b'bleh', b'blah')
    morsel.expires = b'Tue, 04-Jan-2011 13:43:50 GMT'
    result = morsel.serialize()
    eq_(result, 'bleh=blah; expires=Tue, 04-Jan-2011 13:43:50 GMT')

def test_serialize_max_age_timedelta():
    import datetime
    val = datetime.timedelta(86400)
    result = cookies.serialize_max_age(val)
    eq_(result, b'7464960000')

def test_serialize_max_age_int():
    val = 86400
    result = cookies.serialize_max_age(val)
    eq_(result, b'86400')

def test_serialize_max_age_str():
    val = '86400'
    result = cookies.serialize_max_age(val)
    eq_(result, b'86400')

def test_escape_comma():
    c = cookies.Cookie()
    c['x'] = b'";,"'
    eq_(c.serialize(True), r'x="\"\073\054\""')

def test_parse_qmark_in_val():
    v = r'x="\"\073\054\""; expires=Sun, 12-Jun-2011 23:16:01 GMT'
    c = cookies.Cookie(v)
    eq_(c[b'x'].value, b'";,"')
    eq_(c[b'x'].expires, b'Sun, 12-Jun-2011 23:16:01 GMT')

def test_morsel_repr():
    v = cookies.Morsel(b'a', b'b')
    result = repr(v)
    eq_(result, "<Morsel: a='b'>")

class TestRequestCookies(unittest.TestCase):
    def _makeOne(self, environ):
        from webob.cookies import RequestCookies
        return RequestCookies(environ)

    def test_get_no_cache_key_in_environ_no_http_cookie_header(self):
        environ = {}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), None)
        parsed = environ['webob._parsed_cookies']
        self.assertEqual(parsed, ({}, ''))

    def test_get_no_cache_key_in_environ_has_http_cookie_header(self):
        header ='a=1; b=2'
        environ = {'HTTP_COOKIE':header}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), '1')
        parsed = environ['webob._parsed_cookies'][0]
        self.assertEqual(parsed['a'], '1')
        self.assertEqual(parsed['b'], '2')
        self.assertEqual(environ['HTTP_COOKIE'], header) # no change

    def test_get_cache_key_in_environ_no_http_cookie_header(self):
        environ = {'webob._parsed_cookies':({}, '')}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), None)
        parsed = environ['webob._parsed_cookies']
        self.assertEqual(parsed, ({}, ''))

    def test_get_cache_key_in_environ_has_http_cookie_header(self):
        header ='a=1; b=2'
        environ = {'HTTP_COOKIE':header, 'webob._parsed_cookies':({}, '')}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a'), '1')
        parsed = environ['webob._parsed_cookies'][0]
        self.assertEqual(parsed['a'], '1')
        self.assertEqual(parsed['b'], '2')
        self.assertEqual(environ['HTTP_COOKIE'], header) # no change

    def test_get_missing_with_default(self):
        environ = {}
        inst = self._makeOne(environ)
        self.assertEqual(inst.get('a', ''), '')

    def test___setitem__name_not_string_type(self):
        inst = self._makeOne({})
        self.assertRaises(TypeError, inst.__setitem__, None, 1)
        
    def test___setitem__name_not_encodeable_to_ascii(self):
        name = native_(b'La Pe\xc3\xb1a', 'utf-8')
        inst = self._makeOne({})
        self.assertRaises(TypeError, inst.__setitem__, name, 'abc')
        
    def test___setitem__name_not_rfc2109_valid(self):
        name = '$a'
        inst = self._makeOne({})
        self.assertRaises(TypeError, inst.__setitem__, name, 'abc')
        
    def test___setitem__value_not_string_type(self):
        inst = self._makeOne({})
        self.assertRaises(ValueError, inst.__setitem__, 'a', None)

    def test___setitem__value_not_utf_8_decodeable(self):
        value = text_(b'La Pe\xc3\xb1a', 'utf-8')
        value = value.encode('utf-16')
        inst = self._makeOne({})
        self.assertRaises(ValueError, inst.__setitem__, 'a', value)

    def test__setitem__success_no_existing_headers(self):
        value = native_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {}
        inst = self._makeOne(environ)
        inst['a'] = value
        self.assertEqual(environ['HTTP_COOKIE'], 'a="La Pe\\303\\261a"')
        
    def test__setitem__success_append(self):
        value = native_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE':'a=1; b=2'}
        inst = self._makeOne(environ)
        inst['c'] = value
        self.assertEqual(
            environ['HTTP_COOKIE'], 'a=1; b=2; c="La Pe\\303\\261a"')

    def test__setitem__success_replace(self):
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        inst['b'] = 'abc'
        self.assertEqual(environ['HTTP_COOKIE'], 'a=1; b=abc; c=3')
        inst['c'] = '4'
        self.assertEqual(environ['HTTP_COOKIE'], 'a=1; b=abc; c=4')

    def test__delitem__fail_no_http_cookie(self):
        environ = {}
        inst = self._makeOne(environ)
        self.assertRaises(KeyError, inst.__delitem__, 'a')
        self.assertEqual(environ, {})

    def test__delitem__fail_with_http_cookie(self):
        environ = {'HTTP_COOKIE':''}
        inst = self._makeOne(environ)
        self.assertRaises(KeyError, inst.__delitem__, 'a')
        self.assertEqual(environ, {'HTTP_COOKIE':''})

    def test__delitem__success(self):
        environ = {'HTTP_COOKIE':'a=1'}
        inst = self._makeOne(environ)
        del inst['a']
        self.assertEqual(environ['HTTP_COOKIE'], '')
        self.assertEqual(inst._cache, {})

    def test_keys(self):
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(inst.keys())), ['a', 'b', 'c'])
        
    def test_values(self):
        val = text_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(inst.values())), ['1', '3', val])

    def test_items(self):
        val = text_(b'La Pe\xc3\xb1a', 'utf-8')
        environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(inst.items())),
                         [('a', '1'), ('b', val), ('c', '3')])

    if not PY3:
        def test_iterkeys(self):
            environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            self.assertEqual(sorted(list(inst.iterkeys())), ['a', 'b', 'c'])

        def test_itervalues(self):
            val = text_(b'La Pe\xc3\xb1a', 'utf-8')
            environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            self.assertEqual(sorted(list(inst.itervalues())), ['1', '3', val])

        def test_iteritems(self):
            val = text_(b'La Pe\xc3\xb1a', 'utf-8')
            environ = {'HTTP_COOKIE':'a=1; b="La Pe\\303\\261a"; c=3'}
            inst = self._makeOne(environ)
            self.assertEqual(sorted(list(inst.iteritems())),
                             [('a', '1'), ('b', val), ('c', '3')])

    def test___contains__(self):
        environ = {'HTTP_COOKIE':'a=1'}
        inst = self._makeOne(environ)
        self.assertTrue('a' in inst)
        self.assertFalse('b' in inst)
        
    def test___iter__(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(sorted(list(iter(inst))), ['a', 'b', 'c'])

    def test___len__(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        self.assertEqual(len(inst), 3)
        del inst['a']
        self.assertEqual(len(inst), 2)

    def test_clear(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        inst.clear()
        self.assertEqual(environ['HTTP_COOKIE'], '')
        self.assertEqual(inst.get('a'), None)

    def test___repr__(self):
        environ = {'HTTP_COOKIE':'a=1; b=2; c=3'}
        inst = self._makeOne(environ)
        r = repr(inst)
        self.assertTrue(r.startswith(
            '<RequestCookies (dict-like) with values '))
        self.assertTrue(r.endswith('>'))
        
        
        
        

        
