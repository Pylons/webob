# -*- coding: UTF-8 -*-
from webob import headers
from nose.tools import ok_,assert_raises

class TestError(Exception):
    pass

def test_raise_keyerror():
    """Deleting a missing key from ResponseHeaders should raise a KeyError
    Deleting a present key should not raise an error at all
    """
    d = headers.ResponseHeaders()
    assert_raises(KeyError, d.__delitem__, 'b')
    d = headers.ResponseHeaders(a=1)
    del d['a']
    ok_('a' not in d)

def test_set_default():
    """Testing set_default for ResponseHeaders"""
    d = headers.ResponseHeaders(a=1)
    res = d.setdefault('b', 1)
    ok_(res==1 and d['b']==1)
    res = d.setdefault('b', 10)
    ok_(res==1 and d['b']==1)
    res = d.setdefault('B', 10)
    ok_(res==1 and d['b']==1 and 'B' in d and d['B']==1)

def test_pop():
    """Testing if pop return TypeError when more than len(*args)>1 plus other
    assorted tests"""
    d = headers.ResponseHeaders(a=1, b=2, c=3, d=4)
    try:
        d.pop('a', *('z', 'y'))
        raise(TestError('We did not get an error'))
    except TypeError, e:
        ok_(e.args[0]=='pop expected at most 2 arguments, got 3', 'Did not '
            'raise the expected error. We got %r' % e.args[0])
    else:
        raise(TestError('We did not get the expected error. We got %r' % \
                        e.args[0]))
    ok_(d.pop('a')==1 and 'a' not in d)
    ok_(d.pop('B')==2 and 'b' not in d)
    ok_(d.pop('c', *('u',))==3 and 'c' not in d)
    ok_(d.pop('e', *('u',))=='u' and 'e' not in d)
    try:
        d.pop('z')
        raise(TestError('We did not get an error'))
    except KeyError, e:
        ok_(e.args[0]=='z')
    else:
        raise(TestError('We did not get the expected error. We got %r' % \
                        e.args[0]))

def  test_delitem_environheaders():
    """The name of this method pretty much explains it all"""
    d = headers.EnvironHeaders({'CONTENT_LENGTH':10})
    del d['CONTENT-LENGTH']
    ok_('CONTENT-LENGTH' not in d)
    ok_(len(d)==0)
    assert_raises(KeyError, d.__delitem__, 'CONTENT-LENGTH')
