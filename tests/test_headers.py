# -*- coding: UTF-8 -*-
from webob import headers
from nose.tools import ok_, assert_raises, eq_ as eq

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
    assert res == d['b'] == 1
    res = d.setdefault('b', 10)
    assert res == d['b'] == 1
    res = d.setdefault('B', 10)
    assert res == d['b'] == d['B'] == 1

def test_pop():
    """Testing if pop return TypeError when more than len(*args)>1 plus other
    assorted tests"""
    d = headers.ResponseHeaders(a=1, b=2, c=3, d=4)
    assert_raises(TypeError, d.pop, 'a', 'z', 'y')
    assert d.pop('a') == 1
    assert 'a' not in d
    assert d.pop('B') == 2
    assert 'b' not in d
    assert d.pop('c', 'u') == 3
    assert 'c' not in d
    assert d.pop('e', 'u') =='u'
    assert 'e' not in d
    assert_raises(KeyError, d.pop, 'z')

def test_delitem_environheaders():
    d = headers.EnvironHeaders({'CONTENT_LENGTH': '10'})
    del d['CONTENT-LENGTH']
    assert not d
    assert_raises(KeyError, d.__delitem__, 'CONTENT-LENGTH')
