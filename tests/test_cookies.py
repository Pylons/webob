# -*- coding: UTF-8 -*-
from datetime import timedelta
from webob import cookies
from nose.tools import ok_, assert_raises, eq_

def test_cookie():
    """
        Testing several missing features of cookies.Cookie.
            * repr version
            * ignoring a key-value for Cookie when key == $
    """
    c = cookies.Cookie() # empty cookie
    eq_(repr(c), '<Cookie: []>')
    # a cookie with one value
    c = cookies.Cookie('dismiss-top=6')
    eq_(repr(c), "<Cookie: [<Morsel: dismiss-top='6'>]>")
    c = cookies.Cookie('dismiss-top=6;')
    eq_(repr(c), "<Cookie: [<Morsel: dismiss-top='6'>]>")
    # more complex cookie
    new_c = "<Cookie: [<Morsel: a='42'>, <Morsel: CP='null*'>, "\
    "<Morsel: PHPSESSID='0a539d42abc001cdc762809248d4beed'>, "\
    "<Morsel: dismiss-top='6'>]>"
    c = cookies.Cookie("dismiss-top=6; CP=null*; "\
                       "PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42")
    eq_(repr(c), new_c)
    eq_(c.serialize(),
        'CP=null*, PHPSESSID=0a539d42abc001cdc762809248d4beed, a=42, '
        'dismiss-top=6')
    # data with key==$
    c = cookies.Cookie('dismiss-top=6; CP=null*; $=42'\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
    ok_('$' not in c, 'Key $ should have been ignored')
    c = cookies.Cookie('$=a; dismiss-top=6; CP=null*; $=42'\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
    ok_('$' not in c, 'Key $ should have been ignored')

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
    """Inner method _ch_unquote in cookies._unquote is not tested"""
    str_ = u'"'+u'hello world'+u'"'
    v = cookies._unquote(str_)
    ok_(v==u'hello world', 'Wrong output from _unquote. Expected: %r, '
        'Got: %r' % (u'hello world', v))
    str_ = u'hello world'
    v = cookies._unquote(str_)
    ok_(v==u'hello world', 'Wrong output from _unquote. Expected: %r, '
        'Got: %r' % (u'hello world', v))
    str_ = u'"'+u'hello world'
    v = cookies._unquote(str_)
    ok_(v==u'\"hello world', 'Wrong output from _unquote. Expected: %r, '
        'Got: %r' % (u'\"hello world', v))
    # example extracted from webob.cookies
    ok_(cookies._unquote(r'"a\"\377"')=='a"\xff')

