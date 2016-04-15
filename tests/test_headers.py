import pytest

from webob import headers

def test_ResponseHeaders_delitem_notpresent():
    """Deleting a missing key from ResponseHeaders should raise a KeyError"""
    d = headers.ResponseHeaders()
    with pytest.raises(KeyError):
        d.__delitem__('b')

def test_ResponseHeaders_delitem_present():
    """
    Deleting a present key should not raise an error at all
    """
    d = headers.ResponseHeaders(a=1)
    del d['a']
    assert 'a' not in d

def test_ResponseHeaders_setdefault():
    """Testing set_default for ResponseHeaders"""
    d = headers.ResponseHeaders(a=1)
    res = d.setdefault('b', 1)
    assert res == d['b'] == 1
    res = d.setdefault('b', 10)
    assert res == d['b'] == 1
    res = d.setdefault('B', 10)
    assert res == d['b'] == d['B'] == 1

def test_ResponseHeader_pop():
    """Testing if pop return TypeError when more than len(*args)>1 plus other
    assorted tests"""
    d = headers.ResponseHeaders(a=1, b=2, c=3, d=4)
    with pytest.raises(TypeError):
        d.pop('a', 'z', 'y')
    assert d.pop('a') == 1
    assert 'a' not in d
    assert d.pop('B') == 2
    assert 'b' not in d
    assert d.pop('c', 'u') == 3
    assert 'c' not in d
    assert d.pop('e', 'u') == 'u'
    assert 'e' not in d
    with pytest.raises(KeyError):
        d.pop('z')

def test_ResponseHeaders_getitem_miss():
    d = headers.ResponseHeaders()
    with pytest.raises(KeyError):
        d.__getitem__('a')

def test_ResponseHeaders_getall():
    d = headers.ResponseHeaders()
    d.add('a', 1)
    d.add('a', 2)
    result = d.getall('a')
    assert result == [1,2]

def test_ResponseHeaders_mixed():
    d = headers.ResponseHeaders()
    d.add('a', 1)
    d.add('a', 2)
    d['b'] = 1
    result = d.mixed()
    assert result == {'a':[1,2], 'b':1}

def test_ResponseHeaders_setitem_scalar_replaces_seq():
    d = headers.ResponseHeaders()
    d.add('a', 2)
    d['a'] = 1
    result = d.getall('a')
    assert result == [1]

def test_ResponseHeaders_contains():
    d = headers.ResponseHeaders()
    d['a'] = 1
    assert 'a' in d
    assert not 'b' in d

def test_EnvironHeaders_delitem():
    d = headers.EnvironHeaders({'CONTENT_LENGTH': '10'})
    del d['CONTENT-LENGTH']
    assert not d
    with pytest.raises(KeyError):
        d.__delitem__('CONTENT-LENGTH')

def test_EnvironHeaders_getitem():
    d = headers.EnvironHeaders({'CONTENT_LENGTH': '10'})
    assert d['CONTENT-LENGTH'] == '10'

def test_EnvironHeaders_setitem():
    d = headers.EnvironHeaders({})
    d['abc'] = '10'
    assert d['abc'] == '10'

def test_EnvironHeaders_contains():
    d = headers.EnvironHeaders({})
    d['a'] = '10'
    assert 'a' in d
    assert 'b' not in d

def test__trans_key_not_basestring():
    result = headers._trans_key(None)
    assert result == None

def test__trans_key_not_a_header():
    result = headers._trans_key('')
    assert result == None

def test__trans_key_key2header():
    result = headers._trans_key('CONTENT_TYPE')
    assert result == 'Content-Type'

def test__trans_key_httpheader():
    result = headers._trans_key('HTTP_FOO_BAR')
    assert result == 'Foo-Bar'
