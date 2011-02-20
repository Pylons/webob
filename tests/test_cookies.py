# -*- coding: UTF-8 -*-
from datetime import timedelta
from webob import cookies
from nose.tools import ok_, assert_raises, eq_

def test_cookie():
    """
        Test cookie parsing, serialization and `repr`
    """
    c = cookies.Cookie() # empty cookie
    eq_(repr(c), '<Cookie: []>')
    # a cookie with one value
    c = cookies.Cookie('dismiss-top=6')
    eq_(repr(c), "<Cookie: [<Morsel: dismiss-top='6'>]>")
    c = cookies.Cookie('dismiss-top=6;')
    eq_(repr(c), "<Cookie: [<Morsel: dismiss-top='6'>]>")
    # more complex cookie, (also mixing commas and semicolons)
    c = cookies.Cookie('dismiss-top=6; CP=null*, '\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,"')
    c_dict = dict((k,v.value) for k,v in c.items())
    eq_(c_dict, {'a': '42,',
        'CP': 'null*',
        'PHPSESSID': '0a539d42abc001cdc762809248d4beed',
        'dismiss-top': '6'
    })
    eq_(c.serialize(),
        'CP=null*, PHPSESSID=0a539d42abc001cdc762809248d4beed, a="42,", '
        'dismiss-top=6')
    # reserved keys ($xx)
    c = cookies.Cookie('dismiss-top=6; CP=null*; $version=42; a=42')
    assert '$version' not in c
    c = cookies.Cookie('$reserved=42; a=$42')
    eq_(c.keys(), ['a'])

def test_serialize_cookie_date():
    """
        Testing webob.cookies.serialize_cookie_date.
        Missing scenarios:
            * input value is an str, should be returned verbatim
            * input value is an int, should be converted to timedelta and we should
              continue the rest of the process
    """
    ok_(cookies.serialize_cookie_date('Tue, 04-Jan-2011 13:43:50 GMT')==\
        'Tue, 04-Jan-2011 13:43:50 GMT', 'We passed a string, should get the '
        'same one')
    ok_(cookies.serialize_cookie_date(None) is None, 'We passed None, should '
        'get None')

    cdate_delta = cookies.serialize_cookie_date(timedelta(seconds=10))
    cdate_int = cookies.serialize_cookie_date(10)
    eq_(cdate_delta, cdate_int,
        'Passing a int to method should return the same result as passing a timedelta'
    )

def test_ch_unquote():
    eq_(cookies._unquote(u'"hello world'), u'"hello world')
    eq_(cookies._unquote(u'hello world'), u'hello world')
    for unq, q in [
        ('hello world', '"hello world"'),
        # quotation mark is escaped w/ backslash
        ('"', r'"\""'),
        # misc byte escaped as octal
        ('\xff', r'"\377"'),
        # combination
        ('a"\xff', r'"a\"\377"'),
    ]:
        eq_(cookies._unquote(q), unq)
        eq_(cookies._quote(unq), q)
