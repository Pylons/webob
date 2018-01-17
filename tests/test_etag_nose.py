import pytest

from webob.etag import IfRange, ETagMatcher
from webob import Response

def test_if_range_None():
    ir = IfRange.parse(None)
    assert str(ir) == ''
    assert not ir
    assert Response() in ir
    assert Response(etag='foo') in ir
    assert Response(etag='foo GMT') in ir

def test_if_range_match_date():
    date = 'Fri, 09 Nov 2001 01:08:47 GMT'
    ir = IfRange.parse(date)
    assert str(ir) == date
    assert Response() not in ir
    assert Response(etag='etag') not in ir
    assert Response(etag=date) not in ir
    assert Response(last_modified='Fri, 09 Nov 2001 01:00:00 GMT') in ir
    assert Response(last_modified='Fri, 10 Nov 2001 01:00:00 GMT') not in ir

def test_if_range_match_etag():
    ir = IfRange.parse('ETAG')
    assert str(ir) == '"ETAG"'
    assert Response() not in ir
    assert Response(etag='other') not in ir
    assert Response(etag='ETAG') in ir
    assert Response(etag='W/"ETAG"') not in ir

def test_if_range_match_etag_weak():
    ir = IfRange.parse('W/"ETAG"')
    assert str(ir) == ''
    assert Response(etag='ETAG') not in ir
    assert Response(etag='W/"ETAG"') not in ir

def test_if_range_repr():
    assert repr(IfRange.parse(None)) == 'IfRange(<ETag *>)'
    assert str(IfRange.parse(None)) == ''

def test_resp_etag():
    def t(tag, res, raw, strong):
        assert Response(etag=tag).etag == res
        assert Response(etag=tag).headers.get('etag') == raw
        assert Response(etag=tag).etag_strong == strong
    t('foo', 'foo', '"foo"', 'foo')
    t('"foo"', 'foo', '"foo"', 'foo')
    t('a"b', 'a"b', '"a\\"b"', 'a"b')
    t('W/"foo"', 'foo', 'W/"foo"', None)
    t('W/"a\\"b"', 'a"b', 'W/"a\\"b"', None)
    t(('foo', True), 'foo', '"foo"', 'foo')
    t(('foo', False), 'foo', 'W/"foo"', None)
    t(('"foo"', True), '"foo"', r'"\"foo\""', '"foo"')
    t(('W/"foo"', True), 'W/"foo"', r'"W/\"foo\""', 'W/"foo"')
    t(('W/"foo"', False), 'W/"foo"', r'W/"W/\"foo\""', None)

def test_matcher():
    matcher = ETagMatcher(['ETAGS'])
    matcher = ETagMatcher(['ETAGS'])
    assert matcher.etags == ['ETAGS']
    assert "ETAGS" in matcher
    assert "WEAK" not in matcher
    assert "BEER" not in matcher
    assert None not in matcher
    assert repr(matcher) == '<ETag ETAGS>'
    assert str(matcher) == '"ETAGS"'

    matcher2 = ETagMatcher(("ETAG1","ETAG2"))
    assert repr(matcher2) == '<ETag ETAG1 or ETAG2>'
