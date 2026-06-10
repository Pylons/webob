from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar, overload

from webob.byterange import ContentRange, Range
from webob.datetime_utils import parse_date, serialize_date
from webob.util import header_docstring, warn_deprecation

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from time import _TimeTuple, struct_time

    from typing_extensions import TypeAlias

    from webob.etag import IfRange, IfRangeDate
    from webob.request import BaseRequest
    from webob.response import Response
    from webob.types import (
        AsymmetricPropertyWithDelete,
        SymmetricProperty,
        SymmetricPropertyWithDelete,
    )

    _T = TypeVar("_T")
    _DefaultT = TypeVar("_DefaultT")
    _GetterReturnType = TypeVar("_GetterReturnType")
    _SetterValueType = TypeVar("_SetterValueType")
    _ConvertedGetterReturnType = TypeVar("_ConvertedGetterReturnType")
    _ConvertedSetterValueType = TypeVar("_ConvertedSetterValueType")
    _DescriptorT = TypeVar("_DescriptorT", bound=AsymmetricPropertyWithDelete[Any, Any])

    _StringProperty: TypeAlias = SymmetricPropertyWithDelete["str | None"]
    _ListProperty: TypeAlias = AsymmetricPropertyWithDelete[
        "tuple[str, ...] | None", "Iterable[str] | str | None"
    ]
    _DateProperty: TypeAlias = AsymmetricPropertyWithDelete[
        "datetime | None",
        "date | datetime | timedelta | _TimeTuple | struct_time | float | str | None",
    ]
    _ContentRangeParams: TypeAlias = """(
        ContentRange
        | list[int]
        | list[None]
        | list[int | None]
        | tuple[int, int]
        | tuple[None, None]
        | tuple[int, int, int | None]
        | tuple[None, None, int | None]
        | str
        | None
    )"""


CHARSET_RE = re.compile(r";\s*charset=([^;]*)", re.I)
SCHEME_RE = re.compile(r"^[a-z]+:", re.I)


_not_given = object()


@overload
def environ_getter(
    key: str, *, rfc_section: str | None = None
) -> SymmetricProperty[Any]: ...


@overload
def environ_getter(
    key: str, default: None, rfc_section: str | None = None
) -> SymmetricPropertyWithDelete[Any | None]: ...


@overload
def environ_getter(
    key: str, default: _DefaultT, rfc_section: str | None = None
) -> AsymmetricPropertyWithDelete[Any | _DefaultT, Any | _DefaultT | None]: ...


def environ_getter(
    key: str, default: Any = _not_given, rfc_section: str | None = None
) -> AsymmetricPropertyWithDelete[Any, Any] | SymmetricProperty[Any]:
    if rfc_section:
        doc = header_docstring(key, rfc_section)
    else:
        doc = "Gets and sets the ``%s`` key in the environment." % key
    if default is _not_given:

        def fget(req: BaseRequest) -> Any:
            return req.environ[key]

        def fset(req: BaseRequest, val: Any) -> None:
            req.environ[key] = val

        fdel = None
    else:

        def fget(req: BaseRequest) -> Any | _DefaultT:
            return req.environ.get(key, default)

        def fset(req: BaseRequest, val: Any) -> None:
            if val is None:
                if key in req.environ:
                    del req.environ[key]
            else:
                req.environ[key] = val

        def fdel(req: BaseRequest) -> None:
            del req.environ[key]

    return property(fget, fset, fdel, doc=doc)


@overload
def environ_decoder(
    key: str, *, rfc_section: str | None = None, encattr: str | None = None
) -> SymmetricProperty[str]: ...


@overload
def environ_decoder(
    key: str, default: str, rfc_section: str | None = None, encattr: str | None = None
) -> AsymmetricPropertyWithDelete[str, str | None]: ...


@overload
def environ_decoder(
    key: str, default: None, rfc_section: str | None = None, encattr: str | None = None
) -> SymmetricPropertyWithDelete[str | None]: ...


def environ_decoder(
    key: str,
    default: Any = _not_given,
    rfc_section: str | None = None,
    encattr: str | None = None,
) -> SymmetricPropertyWithDelete[str | None] | SymmetricProperty[str]:

    if rfc_section:
        doc = header_docstring(key, rfc_section)
    else:
        doc = "Gets and sets the ``%s`` key in the environment." % key
    if default is _not_given:

        def fget(req: BaseRequest) -> str:
            return req.encget(key, encattr=encattr)

        def fset(req: BaseRequest, val: str) -> None:
            return req.encset(key, val, encattr=encattr)

        fdel = None
    else:

        def fget(req: BaseRequest) -> str | _DefaultT:
            return req.encget(key, default, encattr=encattr)

        def fset(req: BaseRequest, val: str | None) -> None:  # type: ignore[misc]
            if val is None:
                if key in req.environ:
                    del req.environ[key]
            else:
                return req.encset(key, val, encattr=encattr)

        def fdel(req: BaseRequest) -> None:
            del req.environ[key]

    return property(fget, fset, fdel, doc=doc)


def upath_property(key: str) -> SymmetricProperty[str]:
    def fget(req: BaseRequest) -> str:
        encoding = req.url_encoding
        return req.environ.get(key, "").encode("latin-1").decode(encoding)  # type: ignore[no-any-return]

    def fset(req: BaseRequest, val: str) -> None:
        encoding = req.url_encoding
        req.environ[key] = val.encode(encoding).decode("latin-1")

    return property(fget, fset, doc="upath_property(%r)" % key)


def deprecated_property(
    attr: _DescriptorT, name: str, text: str, version: str
) -> _DescriptorT:  # pragma: no cover
    """
    Wraps a descriptor, with a deprecation warning or error
    """

    def warn() -> None:
        warn_deprecation(f"The attribute {name} is deprecated: {text}", version, 3)

    def fget(self: object) -> Any:
        warn()
        return attr.__get__(self, type(self))

    def fset(self: object, val: Any) -> None:
        warn()
        attr.__set__(self, val)

    def fdel(self: object) -> None:
        warn()
        attr.__delete__(self)

    return property(fget, fset, fdel, "<Deprecated attribute %s>" % name)  # type: ignore[return-value]


def header_getter(header: str, rfc_section: str) -> _StringProperty:
    doc = header_docstring(header, rfc_section)
    key = header.lower()

    def fget(r: Response) -> str | None:
        for k, v in r._headerlist:
            if k.lower() == key:
                return v
        return None

    def fset(r: Response, value: str | None) -> None:
        fdel(r)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError("Value must be text_type")
            if "\n" in value or "\r" in value:
                raise ValueError("Header value may not contain control characters")

            r._headerlist.append((header, value))

    def fdel(r: Response) -> None:
        r._headerlist[:] = [(k, v) for (k, v) in r._headerlist if k.lower() != key]

    return property(fget, fset, fdel, doc)


def converter(
    prop: AsymmetricPropertyWithDelete[_GetterReturnType, _SetterValueType],
    parse: Callable[[_GetterReturnType], _ConvertedGetterReturnType],
    serialize: Callable[[_ConvertedSetterValueType], _SetterValueType],
    convert_name: str | None = None,
) -> AsymmetricPropertyWithDelete[
    _ConvertedGetterReturnType, _ConvertedSetterValueType | None
]:

    assert isinstance(prop, property)
    convert_name = convert_name or "``{}`` and ``{}``".format(
        parse.__name__,
        serialize.__name__,
    )
    doc = prop.__doc__ or ""
    doc += "  Converts it using %s." % convert_name
    hget, hset = prop.fget, prop.fset

    def fget(r: object) -> _ConvertedGetterReturnType:
        assert hget is not None
        return parse(hget(r))

    def fset(r: object, val: _ConvertedSetterValueType) -> None:
        assert hset is not None
        if val is not None:
            sval = serialize(val)
        else:
            sval = None
        hset(r, sval)

    return property(fget, fset, prop.fdel, doc)


def list_header(header: str, rfc_section: str) -> _ListProperty:
    prop = header_getter(header, rfc_section)
    return converter(prop, parse_list, serialize_list, "list")


def parse_list(value: str | None) -> tuple[str, ...] | None:
    if not value:
        return None
    return tuple(filter(None, [v.strip() for v in value.split(",")]))


def serialize_list(value: Iterable[str] | str) -> str:
    if isinstance(value, (str, bytes)):
        return str(value)
    else:
        return ", ".join(map(str, value))


def converter_date(prop: _StringProperty) -> _DateProperty:
    return converter(prop, parse_date, serialize_date, "HTTP date")


def date_header(header: str, rfc_section: str) -> _DateProperty:
    return converter_date(header_getter(header, rfc_section))


#######################
# Converter functions
#######################


_rx_etag = re.compile(r'(?:^|\s)(W/)?"((?:\\"|.)*?)"')


def parse_etag_response(value: str | None, strong: bool = False) -> str | None:
    """
    Parse a response ETag.
    See:
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.19
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.11
    """
    if not value:
        return None
    m = _rx_etag.match(value)
    if not m:
        # this etag is invalid, but we'll just return it anyway
        return value
    elif strong and m.group(1):
        # this is a weak etag and we want only strong ones
        return None
    else:
        return m.group(2).replace('\\"', '"')


def serialize_etag_response(
    value: tuple[str, bool] | str,
) -> str:  # return '"%s"' % value.replace('"', '\\"')
    strong = True
    if isinstance(value, tuple):
        value, strong = value
    elif _rx_etag.match(value):
        # this is a valid etag already
        return value
    # let's quote the value
    r = '"%s"' % value.replace('"', '\\"')
    if not strong:
        r = "W/" + r
    return r


def serialize_if_range(
    value: IfRange | IfRangeDate | datetime | date | str,
) -> str | None:
    if isinstance(value, (datetime, date)):
        return serialize_date(value)
    value = str(value)
    return value or None


def parse_range(value: str | None) -> Range | None:
    if not value:
        return None
    # Might return None too:
    return Range.parse(value)


def serialize_range(
    value: tuple[int, int | None] | list[int | None] | list[int] | str | None,
) -> str | None:
    if not value:
        return None
    elif isinstance(value, (list, tuple)):
        return str(Range(*value))
    else:
        assert isinstance(value, str)
        return value


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def parse_int_safe(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


serialize_int: Callable[[int], str] = str


def parse_content_range(value: str | None) -> ContentRange | None:
    if not value or not value.strip():
        return None
    # May still return None
    return ContentRange.parse(value)


def serialize_content_range(value: _ContentRangeParams) -> str | None:
    if isinstance(value, (tuple, list)):
        if len(value) not in (2, 3):
            raise ValueError(
                "When setting content_range to a list/tuple, it must "
                f"be length 2 or 3 (not {value!r})"
            )
        if len(value) == 2:
            begin, end = value
            length = None
        else:
            begin, end, length = value
        value = ContentRange(begin, end, length)  # type: ignore[arg-type]
    value = str(value).strip()
    if not value:
        return None
    return value


_rx_auth_param = re.compile(r'([a-z]+)[ \t]*=[ \t]*(".*?"|[^,]*?)[ \t]*(?:\Z|, *)')


def parse_auth_params(params: str) -> dict[str, str]:
    r = {}
    for k, v in _rx_auth_param.findall(params):
        r[k] = v.strip('"')
    return r


# see http://lists.w3.org/Archives/Public/ietf-http-wg/2009OctDec/0297.html
known_auth_schemes = dict.fromkeys(
    [
        "Basic",
        "Digest",
        "WSSE",
        "HMACDigest",
        "GoogleLogin",
        "Cookie",
        "OpenID",
    ],
    None,
)


class Authorization(NamedTuple):
    authtype: str
    params: dict[str, str] | str


_authorization = Authorization
del Authorization


def parse_auth(val: str | None) -> _authorization | None:
    if val is not None:
        params: dict[str, str] | str
        authtype, sep, params = val.partition(" ")
        if authtype in known_auth_schemes:
            if authtype == "Basic" and '"' not in params:
                # this is the "Authentication: Basic XXXXX==" case
                pass
            else:
                params = parse_auth_params(params)
        return _authorization(authtype, params)
    return val


def serialize_auth(
    val: tuple[str, dict[str, str] | str] | list[Any] | str | None,
) -> str | None:
    if isinstance(val, (tuple, list)):
        authtype, params = val
        if isinstance(params, dict):
            params = ", ".join(map('%s="%s"'.__mod__, params.items()))
        assert isinstance(params, str)
        return f"{authtype} {params}"
    return val
