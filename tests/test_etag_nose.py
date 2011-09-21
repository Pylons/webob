from webob.etag import IfRange
from webob import Response
from nose.tools import eq_

def test_if_range_None():
    ir = IfRange.parse(None)
    eq_(str(ir), '')
    assert not ir
    assert Response() in ir
    assert Response(etag='foo') in ir
    assert Response(etag='foo GMT') in ir

def test_match_date():
    date = 'Fri, 09 Nov 2001 01:08:47 GMT'
    ir = IfRange.parse(date)
    eq_(str(ir), date)
    assert Response() not in ir
    assert Response(etag='etag') not in ir
    assert Response(etag=date) not in ir
    assert Response(last_modified='Fri, 09 Nov 2001 01:00:00 GMT') in ir
    assert Response(last_modified='Fri, 10 Nov 2001 01:00:00 GMT') not in ir

def test_match_etag():
    ir = IfRange.parse('ETAG')
    eq_(str(ir), '"ETAG"')
    assert Response() not in ir
    assert Response(etag='other') not in ir
    assert Response(etag='ETAG') in ir
    assert Response(etag='W/"ETAG"') not in ir

def test_match_etag_weak():
    ir = IfRange.parse('W/"ETAG"')
    eq_(str(ir), '')
    assert Response(etag='ETAG') not in ir
    assert Response(etag='W/"ETAG"') not in ir


def test___repr__():
    eq_(repr(IfRange.parse(None)), 'IfRange(<ETag *>)')

def test___str__():
    eq_(str(IfRange.parse(None)), '')

def test_resp_etag():
    def t(tag, res, raw, strong):
        eq_(Response(etag=tag).etag, res)
        eq_(Response(etag=tag).headers.get('etag'), raw)
        eq_(Response(etag=tag).etag_strong, strong)
    t('foo', 'foo', '"foo"', 'foo')
    t('"foo"', 'foo', '"foo"', 'foo')
    t('a"b', 'a"b', '"a\\"b"', 'a"b')
    t('W/"foo"', 'foo', 'W/"foo"', None)
    t('W/"a\\"b"', 'a"b', 'W/"a\\"b"', None)
