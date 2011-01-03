# -*- coding: UTF-8 -*-
# 57, 59, 112, 151-154
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
    c = cookies.Cookie('$=a; dismiss-top=6; CP=null*; $=42'\
                       'PHPSESSID=0a539d42abc001cdc762809248d4beed; a=42')
    ok_('$' not in c, 'Key $ should have been ignored')



