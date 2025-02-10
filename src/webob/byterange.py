from __future__ import annotations

import re
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from collections.abc import Iterator

    from typing_extensions import Self

__all__ = ["Range", "ContentRange"]

_rx_range = re.compile(r"bytes *= *(\d*) *- *(\d*)", flags=re.I)
_rx_content_range = re.compile(r"bytes (?:(\d+)-(\d+)|[*])/(?:(\d+)|[*])")


class Range:
    """
    Represents the Range header.
    """

    @overload
    def __init__(self, start: None, end: None) -> None: ...

    @overload
    def __init__(self, start: int, end: int | None) -> None: ...

    def __init__(self, start: int | None, end: int | None) -> None:
        assert end is None or end >= 0, "Bad range end: %r" % end
        self.start = start
        self.end = end  # non-inclusive

    def range_for_length(self, length: int | None) -> tuple[int, int] | None:
        """
        *If* there is only one range, and *if* it is satisfiable by
        the given length, then return a (start, end) non-inclusive range
        of bytes to serve.  Otherwise return None
        """
        if length is None:
            return None
        start, end = self.start, self.end
        if end is None:
            assert start is not None
            end = length
            if start < 0:
                start += length
        if _is_content_range_valid(start, end, length):
            assert start is not None
            stop = min(end, length)
            return (start, stop)
        else:
            return None

    def content_range(self, length: int | None) -> ContentRange | None:
        """
        Works like range_for_length; returns None or a ContentRange object

        You can use it like::

            response.content_range = req.range.content_range(response.content_length)

        Though it's still up to you to actually serve that content range!
        """
        range = self.range_for_length(length)
        if range is None:
            return None
        return ContentRange(range[0], range[1], length)

    def __str__(self) -> str:
        s, e = self.start, self.end
        if e is None:
            assert s is not None
            r = "bytes=%s" % s
            if s >= 0:
                r += "-"
            return r
        return f"bytes={s}-{e - 1}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} bytes {self.start!r}-{self.end!r}>"

    def __iter__(self) -> Iterator[int | None]:
        return iter((self.start, self.end))

    @classmethod
    def parse(cls, header: str | None) -> Self | None:
        """
        Parse the header; may return None if header is invalid
        """
        m = _rx_range.match(header or "")
        if not m:
            return None
        start, end = m.groups()
        if not start:
            return cls(-int(end), None)
        start = int(start)
        if not end:
            return cls(start, None)
        end = int(end) + 1  # return val is non-inclusive
        if start >= end:
            return None
        return cls(start, end)


class ContentRange:
    """
    Represents the Content-Range header

    This header is ``start-stop/length``, where start-stop and length
    can be ``*`` (represented as None in the attributes).
    """

    @overload
    def __init__(self, start: None, stop: None, length: int | None) -> None: ...

    @overload
    def __init__(self, start: int, stop: int, length: int | None) -> None: ...

    def __init__(self, start: int | None, stop: int | None, length: int | None) -> None:
        if not _is_content_range_valid(start, stop, length):
            raise ValueError(f"Bad start:stop/length: {start!r}-{stop!r}/{length!r}")
        self.start = start
        self.stop = stop  # this is python-style range end (non-inclusive)
        self.length = length

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self}>"

    def __str__(self) -> str:
        if self.length is None:
            length: str | int = "*"
        else:
            length = self.length
        if self.start is None:
            assert self.stop is None
            return "bytes */%s" % length
        assert self.stop is not None
        stop = self.stop - 1  # from non-inclusive to HTTP-style
        return f"bytes {self.start}-{stop}/{length}"

    def __iter__(self) -> Iterator[int | None]:
        """
        Mostly so you can unpack this, like:

            start, stop, length = res.content_range
        """
        return iter([self.start, self.stop, self.length])

    @classmethod
    def parse(cls, value: str | None) -> Self | None:
        """
        Parse the header.  May return None if it cannot parse.
        """
        m = _rx_content_range.match(value or "")
        if not m:
            return None
        s_str, e_str, l_str = m.groups()
        if s_str:
            s = int(s_str)
            e = int(e_str) + 1
        else:
            s = None
            e = None
        l = int(l_str) if l_str else None
        if not _is_content_range_valid(s, e, l, response=True):
            return None
        return cls(s, e, l)  # type: ignore[arg-type]


def _is_content_range_valid(
    start: int | None, stop: int | None, length: int | None, response: bool = False
) -> bool:

    if (start is None) != (stop is None):
        return False

    if start is None:
        return length is None or length >= 0

    assert stop is not None
    if length is None:
        return 0 <= start < stop
    elif start >= stop:
        return False
    elif response and stop > length:
        # "content-range: bytes 0-50/10" is invalid for a response
        # "range: bytes 0-50" is valid for a request to a 10-bytes entity
        return False
    else:
        return 0 <= start < length
