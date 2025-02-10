"""
Does parsing of ETag-related headers: If-None-Matches, If-Matches

Also If-Range parsing
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from webob.datetime_utils import parse_date, serialize_date
from webob.descriptors import _rx_etag
from webob.util import header_docstring

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime

    from typing_extensions import TypeAlias

    from webob.request import BaseRequest
    from webob.response import Response
    from webob.types import AsymmetricPropertyWithDelete

    _ETag: TypeAlias = "_AnyETag | _NoETag | ETagMatcher"
    _ETagProperty: TypeAlias = AsymmetricPropertyWithDelete[_ETag, "_ETag | str | None"]

__all__ = ["AnyETag", "NoETag", "ETagMatcher", "IfRange", "etag_property"]


def etag_property(
    key: str, default: _ETag, rfc_section: str, strong: bool = True
) -> _ETagProperty:

    doc = header_docstring(key, rfc_section)
    doc += "  Converts it as a Etag."

    def fget(req: BaseRequest) -> _ETag:
        value = req.environ.get(key)
        if not value:
            return default
        else:
            return ETagMatcher.parse(value, strong=strong)

    def fset(req: BaseRequest, val: _ETag | str | None) -> None:
        if val is None:
            req.environ[key] = None
        else:
            req.environ[key] = str(val)

    def fdel(req: BaseRequest) -> None:
        del req.environ[key]

    return property(fget, fset, fdel, doc=doc)


class _AnyETag:
    """
    Represents an ETag of *, or a missing ETag when matching is 'safe'
    """

    def __repr__(self) -> str:
        return "<ETag *>"

    def __bool__(self) -> Literal[False]:
        return False

    def __contains__(self, other: str | None) -> Literal[True]:
        return True

    def __str__(self) -> str:
        return "*"


AnyETag: _AnyETag = _AnyETag()


class _NoETag:
    """
    Represents a missing ETag when matching is unsafe
    """

    def __repr__(self) -> str:
        return "<No ETag>"

    def __bool__(self) -> Literal[False]:
        return False

    def __contains__(self, other: str | None) -> Literal[False]:
        return False

    def __str__(self) -> str:
        return ""


NoETag: _NoETag = _NoETag()


# TODO: convert into a simple tuple


class ETagMatcher:
    def __init__(self, etags: Collection[str]) -> None:
        self.etags = etags

    def __contains__(self, other: str | None) -> bool:
        return other in self.etags

    def __repr__(self) -> str:
        return "<ETag %s>" % (" or ".join(self.etags))

    @classmethod
    def parse(cls, value: str, strong: bool = True) -> ETagMatcher | _AnyETag:
        """
        Parse this from a header value
        """
        if value == "*":
            return AnyETag
        if not value:
            return cls([])
        matches = _rx_etag.findall(value)
        if not matches:
            return cls([value])
        elif strong:
            return cls([t for w, t in matches if not w])
        else:
            return cls([t for w, t in matches])

    def __str__(self) -> str:
        return ", ".join(map('"%s"'.__mod__, self.etags))


class IfRange:
    def __init__(self, etag: _ETag) -> None:
        self.etag = etag

    @classmethod
    def parse(cls, value: str | None) -> IfRange | IfRangeDate:
        """
        Parse this from a header value.
        """
        if not value:
            return cls(AnyETag)
        elif value.endswith(" GMT"):
            # Must be a date
            # FIXME: What if the date is not valid?
            return IfRangeDate(parse_date(value))  # type: ignore[arg-type]
        else:
            return cls(ETagMatcher.parse(value))

    def __contains__(self, resp: Response) -> bool:
        """
        Return True if the If-Range header matches the given etag or last_modified
        """
        return resp.etag_strong in self.etag

    def __bool__(self) -> bool:
        return bool(self.etag)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.etag!r})"

    def __str__(self) -> str:
        return str(self.etag) if self.etag else ""


class IfRangeDate:
    def __init__(self, date: datetime) -> None:
        self.date = date

    def __contains__(self, resp: Response) -> bool:
        last_modified = resp.last_modified
        return (last_modified <= self.date) if last_modified else False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.date!r})"

    def __str__(self) -> str:
        return serialize_date(self.date)
