# -*- coding: utf-8 -*-
from datetime import timedelta
from webob import cookies
from nose.tools import eq_

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
    c['foo'] = b'bar'
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
    eq_(cookies.serialize_cookie_date('Tue, 04-Jan-2011 13:43:50 GMT'),
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
    eq_(result, '7464960000')

def test_serialize_max_age_int():
    val = 86400
    result = cookies.serialize_max_age(val)
    eq_(result, '86400')

def test_serialize_max_age_str():
    val = '86400'
    result = cookies.serialize_max_age(val)
    eq_(result, '86400')

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

