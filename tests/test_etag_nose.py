from webob.etag import IfRange
from webob import Response
from nose.tools import eq_

def test_if_range_is_None():
    assert not IfRange.parse(None)
    assert IfRange.parse(None).match('foo')
    assert IfRange.parse(None).match('foo GMT')
    assert IfRange.parse(None).match()
    assert IfRange.parse(None).match_response(Response())

def test___repr__():
    eq_(repr(IfRange.parse(None)), 'IfRange(<ETag *>)')

def test___str__():
    eq_(str(IfRange.parse(None)), '')
