"""
Represents the Cache-Control header
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Generic, Literal, overload

if TYPE_CHECKING:
    from collections.abc import Callable

    from _typeshed import SupportsItems
    from typing_extensions import Self, TypeAlias, TypeVar

    _T = TypeVar("_T")
    _DefaultT = TypeVar("_DefaultT", default=None)
    _NoneLiteral = TypeVar("_NoneLiteral", default=None)
    _ScopeT = TypeVar(
        "_ScopeT", Literal["request"], Literal["response"], None, default=None
    )
    _ScopeT2 = TypeVar("_ScopeT2", Literal["request"], Literal["response"], None)
else:
    from typing import TypeVar

    _T = TypeVar("_T")
    _DefaultT = TypeVar("_DefaultT")
    _NoneLiteral = TypeVar("_NoneLiteral")
    _ScopeT = TypeVar("_ScopeT")


class UpdateDict(dict[str, Any]):
    """
    Dict that has a callback on all updates
    """

    # these are declared as class attributes so that
    # we don't need to override constructor just to
    # set some defaults
    updated: Callable[..., Any] | None = None
    updated_args: tuple[Any, ...] | None = None

    def _updated(self) -> None:
        """
        Assign to new_dict.updated to track updates
        """
        updated = self.updated
        if updated is not None:
            args = self.updated_args
            if args is None:
                args = (self,)
            updated(*args)

    # NOTE: These wrappers are supposed to be transparent, so let's
    #       not bother copying the type annotations
    if not TYPE_CHECKING:

        def __setitem__(self, key, item):
            dict.__setitem__(self, key, item)
            self._updated()

        def __delitem__(self, key):
            dict.__delitem__(self, key)
            self._updated()

        def clear(self):
            dict.clear(self)
            self._updated()

        def update(self, *args, **kw):
            dict.update(self, *args, **kw)
            self._updated()

        def setdefault(self, key, value=None):
            val = dict.setdefault(self, key, value)
            if val is value:
                self._updated()
            return val

        def pop(self, *args):
            v = dict.pop(self, *args)
            self._updated()
            return v

        def popitem(self):
            v = dict.popitem(self)
            self._updated()
            return v


token_re = re.compile(r'([a-zA-Z][a-zA-Z_-]*)\s*(?:=(?:"([^"]*)"|([^ \t",;]*)))?')
need_quote_re = re.compile(r"[^a-zA-Z0-9._-]")


class exists_property(Generic[_ScopeT]):
    """
    Represents a property that either is listed in the Cache-Control
    header, or is not listed (has no value)
    """

    def __init__(
        self, prop: str, type: _ScopeT = None  # type: ignore[assignment]
    ) -> None:
        self.prop = prop
        self.type: _ScopeT = type

    @overload
    def __get__(
        self, obj: None, type: type[CacheControl[Any]] | None = None
    ) -> Self: ...

    @overload
    def __get__(
        self: exists_property[None],
        obj: CacheControl[Any],
        type: type[CacheControl[Any]] | None = None,
    ) -> bool: ...

    @overload
    def __get__(
        self, obj: CacheControl[_ScopeT], type: type[CacheControl[Any]] | None = None
    ) -> bool: ...

    def __get__(
        self, obj: CacheControl[Any] | None, type: type[CacheControl[Any]] | None = None
    ) -> Self | bool:
        if obj is None:
            return self
        return self.prop in obj.properties

    @overload
    def __set__(
        self: exists_property[None], obj: CacheControl[Any], value: bool | None
    ) -> None: ...

    @overload
    def __set__(
        self, obj: CacheControl[_ScopeT] | CacheControl[None], value: bool | None
    ) -> None: ...

    def __set__(self, obj: CacheControl[Any], value: bool | None) -> None:
        if self.type is not None and self.type != obj.type:
            raise AttributeError(
                "The property %s only applies to %s Cache-Control"
                % (self.prop, self.type)
            )

        if value:
            obj.properties[self.prop] = None
        else:
            if self.prop in obj.properties:
                del obj.properties[self.prop]

    @overload
    def __delete__(self: exists_property[None], obj: CacheControl[Any]) -> None: ...

    @overload
    def __delete__(self, obj: CacheControl[_ScopeT] | CacheControl[None]) -> None: ...

    def __delete__(self, obj: CacheControl[Any]) -> None:
        self.__set__(obj, False)


class value_property(Generic[_T, _DefaultT, _NoneLiteral, _ScopeT]):
    """
    Represents a property that has a value in the Cache-Control header.

    When no value is actually given, the value of self.none is returned.
    """

    def __init__(
        self,
        prop: str,
        default: _DefaultT = None,  # type: ignore[assignment]
        none: _NoneLiteral = None,  # type: ignore[assignment]
        type: _ScopeT = None,  # type: ignore[assignment]
    ) -> None:
        self.prop = prop
        self.default: _DefaultT = default
        self.none: _NoneLiteral = none
        self.type: _ScopeT = type

    @overload
    def __get__(
        self, obj: None, type: type[CacheControl[Any]] | None = None
    ) -> Self: ...

    @overload
    def __get__(
        self: value_property[_T, _DefaultT, _NoneLiteral, None],
        obj: CacheControl[Any],
        type: type[CacheControl[Any]] | None = None,
    ) -> _T | _DefaultT | _NoneLiteral: ...

    @overload
    def __get__(
        self, obj: CacheControl[_ScopeT], type: type[CacheControl[Any]] | None = None
    ) -> _T | _DefaultT | _NoneLiteral: ...

    def __get__(
        self, obj: CacheControl[Any] | None, type: type[CacheControl[Any]] | None = None
    ) -> Self | _T | _DefaultT | _NoneLiteral:

        if obj is None:
            return self
        if self.prop in obj.properties:
            value = obj.properties[self.prop]
            if value is None:
                return self.none
            else:
                return value  # type: ignore[no-any-return]
        else:
            return self.default

    @overload
    def __set__(
        self: value_property[_T, _DefaultT, _NoneLiteral, None],
        obj: CacheControl[Any],
        value: _T | _DefaultT | Literal[True] | None,
    ) -> None: ...

    @overload
    def __set__(
        self, obj: CacheControl[_ScopeT], value: _T | _DefaultT | Literal[True] | None
    ) -> None: ...

    def __set__(
        self, obj: CacheControl[Any], value: _T | _DefaultT | Literal[True] | None
    ) -> None:

        if self.type is not None and self.type != obj.type:
            raise AttributeError(
                "The property %s only applies to %s Cache-Control"
                % (self.prop, self.type)
            )
        if value == self.default:
            if self.prop in obj.properties:
                del obj.properties[self.prop]
        elif value is True:
            obj.properties[self.prop] = None  # Empty value, but present
        else:
            obj.properties[self.prop] = value

    @overload
    def __delete__(
        self: value_property[_T, _DefaultT, _NoneLiteral, None], obj: CacheControl[Any]
    ) -> None: ...

    @overload
    def __delete__(self, obj: CacheControl[_ScopeT] | CacheControl[None]) -> None: ...

    def __delete__(self, obj: CacheControl[Any]) -> None:
        if self.prop in obj.properties:
            del obj.properties[self.prop]


class CacheControl(Generic[_ScopeT]):
    """
    Represents the Cache-Control header.

    By giving a type of ``'request'`` or ``'response'`` you can
    control what attributes are allowed (some Cache-Control values
    only apply to requests or responses).
    """

    # NOTE: This only exists when accessed through Response/BaseRequest
    header_value: str

    update_dict = UpdateDict

    def __init__(self, properties: dict[str, Any], type: _ScopeT) -> None:
        self.properties = properties
        self.type: _ScopeT = type

    @overload
    @classmethod
    def parse(
        cls,
        header: str,
        updates_to: Callable[[dict[str, Any]], Any] | None = None,
        type: None = None,
    ) -> CacheControl[None]: ...

    @overload
    @classmethod
    def parse(
        cls,
        header: str,
        updates_to: Callable[[dict[str, Any]], Any] | None,
        type: _ScopeT2,
    ) -> CacheControl[_ScopeT2]: ...

    @overload
    @classmethod
    def parse(
        cls,
        header: str,
        updates_to: Callable[[dict[str, Any]], Any] | None = None,
        *,
        type: _ScopeT2,
    ) -> CacheControl[_ScopeT2]: ...

    @classmethod
    def parse(
        cls,
        header: str,
        updates_to: Callable[[dict[str, Any]], Any] | None = None,
        type: Any = None,
    ) -> CacheControl[Any]:
        """
        Parse the header, returning a CacheControl object.

        The object is bound to the request or response object
        ``updates_to``, if that is given.
        """
        props: dict[str, Any]
        if updates_to:
            props = cls.update_dict()
            props.updated = updates_to
        else:
            props = {}
        for match in token_re.finditer(header):
            name = match.group(1)
            value = match.group(2) or match.group(3) or None
            if value:
                try:
                    value = int(value)
                except ValueError:
                    pass
            props[name] = value
        obj = cls(props, type=type)
        if updates_to:
            assert isinstance(props, cls.update_dict)
            props.updated_args = (obj,)
        return obj

    def __repr__(self) -> str:
        return "<CacheControl %r>" % str(self)

    # Request values:
    # no-cache shared (below)
    # no-store shared (below)
    # max-age shared  (below)
    max_stale: value_property[int, None, Literal["*"], Literal["request"]]
    max_stale = value_property("max-stale", none="*", type="request")
    min_fresh: value_property[int, None, None, Literal["request"]]
    min_fresh = value_property("min-fresh", type="request")
    # no-transform shared (below)
    only_if_cached = exists_property("only-if-cached", type="request")

    # Response values:
    public = exists_property("public", type="response")
    private: value_property[str, None, Literal["*"], Literal["response"]]
    private = value_property("private", none="*", type="response")
    no_cache: value_property[str, None, Literal["*"], None]
    no_cache = value_property("no-cache", none="*")
    no_store = exists_property("no-store")
    no_transform = exists_property("no-transform")
    must_revalidate = exists_property("must-revalidate", type="response")
    proxy_revalidate = exists_property("proxy-revalidate", type="response")
    max_age: value_property[int, None, Literal[-1], None]
    max_age = value_property("max-age", none=-1)
    s_maxage: value_property[int, None, None, Literal["response"]]
    s_maxage = value_property("s-maxage", type="response")
    s_max_age = s_maxage
    stale_while_revalidate: value_property[int, None, None, Literal["response"]]
    stale_while_revalidate = value_property("stale-while-revalidate", type="response")
    stale_if_error: value_property[int, None, None, Literal["response"]]
    stale_if_error = value_property("stale-if-error", type="response")

    def __str__(self) -> str:
        return serialize_cache_control(self.properties)

    def copy(self) -> Self:
        """
        Returns a copy of this object.
        """
        return self.__class__(self.properties.copy(), type=self.type)


def serialize_cache_control(
    properties: SupportsItems[str, Any] | CacheControl[Any],
) -> str:
    if isinstance(properties, CacheControl):
        properties = properties.properties
    parts = []
    for name, value in sorted(properties.items()):
        if value is None:
            parts.append(name)
            continue
        value = str(value)
        if need_quote_re.search(value):
            value = '"%s"' % value
        parts.append(f"{name}={value}")
    return ", ".join(parts)


RequestCacheControl: TypeAlias = CacheControl[Literal["request"]]
ResponseCacheControl: TypeAlias = CacheControl[Literal["response"]]
