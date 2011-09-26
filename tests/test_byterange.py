from webob.byterange import Range
from webob.byterange import ContentRange
from webob.byterange import _is_content_range_valid

from nose.tools import assert_true, assert_false, eq_, assert_raises

# Range class

def test_not_satisfiable():
    range = Range.parse('bytes=-100')
    assert range.range_for_length(50) is None
    range = Range.parse('bytes=100-')
    assert range.range_for_length(50) is None

def test_range_parse():
    assert isinstance(Range.parse('bytes=0-99'), Range)
    assert Range.parse('bytes=10-5') is None
    assert Range.parse('bytes 5-10') is None
    assert Range.parse('words=10-5') is None

def test_range_content_range_length_none():
    range = Range(0, 100)
    eq_(range.content_range(None), None)
    assert isinstance(range.content_range(1), ContentRange)
    eq_(tuple(range.content_range(1)), (0,1,1))
    eq_(tuple(range.content_range(200)), (0,100,200))

def test_range_for_length_end_is_none():
    # End is None
    range = Range(0, None)
    eq_(range.range_for_length(100), (0,100))

def test_range_for_length_end_is_none_negative_start():
    # End is None and start is negative
    range = Range(-5, None)
    eq_(range.range_for_length(100), (95,100))

def test_range_start_none():
    # Start is None
    range = Range(None, 99)
    eq_(range.range_for_length(100), None)

def test_range_str_end_none():
    range = Range(0, None)
    eq_(str(range), 'bytes=0-')

def test_range_str_end_none_negative_start():
    range = Range(-5, None)
    eq_(str(range), 'bytes=-5')

def test_range_str_1():
    range = Range(0, 100)
    eq_(str(range), 'bytes=0-99')

def test_range_repr():
    range = Range(0, 99)
    assert_true(range.__repr__(), '<Range bytes 0-98>')


# ContentRange class

def test_contentrange_bad_input():
    assert_raises(ValueError, ContentRange, None, 99, None)

def test_contentrange_repr():
    contentrange = ContentRange(0, 99, 100)
    assert_true(repr(contentrange), '<ContentRange bytes 0-98/100>')

def test_contentrange_str():
    contentrange = ContentRange(0, 99, None)
    eq_(str(contentrange), 'bytes 0-98/*')
    contentrange = ContentRange(None, None, 100)
    eq_(str(contentrange), 'bytes */100')

def test_contentrange_iter():
    contentrange = ContentRange(0, 99, 100)
    assert_true(type(contentrange.__iter__()), iter)
    assert_true(ContentRange.parse('bytes 0-99/100').__class__, ContentRange)
    eq_(ContentRange.parse(None), None)
    eq_(ContentRange.parse('0-99 100'), None)
    eq_(ContentRange.parse('bytes 0-99 100'), None)
    eq_(ContentRange.parse('bytes 0-99/xxx'), None)
    eq_(ContentRange.parse('bytes 0 99/100'), None)
    eq_(ContentRange.parse('bytes */100').__class__, ContentRange)
    eq_(ContentRange.parse('bytes A-99/100'), None)
    eq_(ContentRange.parse('bytes 0-B/100'), None)
    eq_(ContentRange.parse('bytes 99-0/100'), None)
    eq_(ContentRange.parse('bytes 0 99/*'), None)

# _is_content_range_valid function

def test_is_content_range_valid():
    assert not _is_content_range_valid( None, 99, 90)
    assert not _is_content_range_valid( 99, None, 90)
    assert _is_content_range_valid(None, None, 90)
    assert not _is_content_range_valid(None, 99, 90)
    assert _is_content_range_valid(0, 99, None)
    assert not _is_content_range_valid(0, 99, 90, response=True)
    assert _is_content_range_valid(0, 99, 90)
