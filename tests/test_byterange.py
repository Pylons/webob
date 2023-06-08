from collections.abc import Iterable

import pytest
from webob.byterange import ContentRange, Range, _is_content_range_valid

# Range class


def test_not_satisfiable():
    range = Range.parse("bytes=-100")
    assert range.range_for_length(50) is None
    range = Range.parse("bytes=100-")
    assert range.range_for_length(50) is None


def test_range_parse():
    assert isinstance(Range.parse("bytes=0-99"), Range)
    assert isinstance(Range.parse("BYTES=0-99"), Range)
    assert isinstance(Range.parse("bytes = 0-99"), Range)
    assert isinstance(Range.parse("bytes=0 - 102"), Range)
    assert Range.parse("bytes=10-5") is None
    assert Range.parse("bytes 5-10") is None
    assert Range.parse("words=10-5") is None


def test_range_content_range_length_none():
    range = Range(0, 100)
    assert range.content_range(None) is None
    assert isinstance(range.content_range(1), ContentRange)
    assert tuple(range.content_range(1)) == (0, 1, 1)
    assert tuple(range.content_range(200)) == (0, 100, 200)


def test_range_for_length_end_is_none():
    # End is None
    range = Range(0, None)
    assert range.range_for_length(100) == (0, 100)


def test_range_for_length_end_is_none_negative_start():
    # End is None and start is negative
    range = Range(-5, None)
    assert range.range_for_length(100) == (95, 100)


def test_range_start_none():
    # Start is None
    range = Range(None, 99)
    assert range.range_for_length(100) is None


def test_range_str_end_none():
    range = Range(0, None)
    assert str(range) == "bytes=0-"


def test_range_str_end_none_negative_start():
    range = Range(-5, None)
    assert str(range) == "bytes=-5"


def test_range_str_1():
    range = Range(0, 100)
    assert str(range) == "bytes=0-99"


def test_range_repr():
    range = Range(0, 99)
    assert repr(range) == "<Range bytes 0-99>"


# ContentRange class


def test_contentrange_bad_input():
    with pytest.raises(ValueError):
        ContentRange(None, 99, None)


def test_contentrange_repr():
    contentrange = ContentRange(0, 99, 100)
    assert repr(contentrange) == "<ContentRange bytes 0-98/100>"


def test_contentrange_str():
    contentrange = ContentRange(0, 99, None)
    assert str(contentrange) == "bytes 0-98/*"
    contentrange = ContentRange(None, None, 100)
    assert str(contentrange) == "bytes */100"


def test_contentrange_iter():
    contentrange = ContentRange(0, 99, 100)
    assert isinstance(contentrange, Iterable)
    assert ContentRange.parse("bytes 0-99/100").__class__ == ContentRange
    assert ContentRange.parse(None) is None
    assert ContentRange.parse("0-99 100") is None
    assert ContentRange.parse("bytes 0-99 100") is None
    assert ContentRange.parse("bytes 0-99/xxx") is None
    assert ContentRange.parse("bytes 0 99/100") is None
    assert ContentRange.parse("bytes */100").__class__ == ContentRange
    assert ContentRange.parse("bytes A-99/100") is None
    assert ContentRange.parse("bytes 0-B/100") is None
    assert ContentRange.parse("bytes 99-0/100") is None
    assert ContentRange.parse("bytes 0 99/*") is None


# _is_content_range_valid function


def test_is_content_range_valid():
    assert not _is_content_range_valid(None, 99, 90)
    assert not _is_content_range_valid(99, None, 90)
    assert _is_content_range_valid(None, None, 90)
    assert not _is_content_range_valid(None, 99, 90)
    assert _is_content_range_valid(0, 99, None)
    assert not _is_content_range_valid(0, 99, 90, response=True)
    assert _is_content_range_valid(0, 99, 90)
