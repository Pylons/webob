# -*- coding: UTF-8 -*-
# 151-154
from datetime import timedelta
from webob import cookies
from nose.tools import ok_, assert_raises

def test_cookie():
    """Testing several missing features of cookies.Cookie.
    * repr version
    * ignoring a key-value for Cookie when key == $
    """
    c = cookies.Cookie() # empty cookie
    ok_(c.__repr__()=='<Cookie: []>', 'Wrong repr. Expected: %r, got: %r' %\
    ('<Cookie: []>', c.__repr__()))
    # a cookie with one value
    c = cookies.Cookie('dismiss-top=6') 
    ok_(c.__repr__()=="<Cookie: [<Morsel: dismiss-top='6'>]>", 
        'Wrong repr. Expected: %r, got: %r' %\
        ("<Cookie: [<Morsel: dismiss-top='6'>]>", c.__repr__()))
    c = cookies.Cookie('dismiss-top=6;') 
    ok_(c.__repr__()=="<Cookie: [<Morsel: dismiss-top='6'>]>", 
        'Wrong repr. Expected: %r, got: %r' %\
        ("<Cookie: [<Morsel: dismiss-top='6'>]>", c.__repr__()))
    # more complex cookie
    new_c = "<Cookie: [<Morsel: a='42'>, <Morsel: CP='null*'>, "\
    "<Morsel: PHPSESSID='0a539d42abc001cdc762809248d4beed'>, "\
    "<Morsel: dismiss-top='6'>]>"
    c = cookies.Cookie("dismiss-top=6; CP=null*; "\
                       "PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42")
    ok_(c.__repr__()==new_c, 'Wrong repr. Expected; %r, got: %r' % (new_c, 
                                                                    c.__repr__()
                                                                   ))
    # data with key==$
    c = cookies.Cookie('dismiss-top=6; CP=null*; $=42'\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
    ok_('$' not in c, 'Key $ should have been ignored')
    c = cookies.Cookie('$=a; dismiss-top=6; CP=null*; $=42'\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
    ok_('$' not in c, 'Key $ should have been ignored')

def test_serialize_cookie_date():
    """Testing webob.cookies.serialize_cookie_date.
    Missing scenarios:
        * input value is an str, should be returned verbatim
        * input value is an int, should be converted to timedelta and we should
          continue the rest of the process
    """
    ok_(cookies.serialize_cookie_date('Tue, 04-Jan-2011 13:43:50 GMT')==\
        'Tue, 04-Jan-2011 13:43:50 GMT', 'We passed a string, should get the '
        'same one')
    ok_(cookies.serialize_cookie_date(None)==None, 'We passed None, should '
        'get None')
    ok_(cookies.serialize_cookie_date(timedelta(seconds=10))==\
        cookies.serialize_cookie_date(10), 'Passing a int to method should '
        'return the same result as passing a timedelta')

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

