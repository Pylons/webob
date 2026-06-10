from __future__ import annotations

from datetime import timedelta
from typing import IO, TYPE_CHECKING, Literal, Protocol, TypedDict, TypeVar, overload

if TYPE_CHECKING:
    from typing import type_check_only

    from typing_extensions import TypeAlias

    from webob.compat import cgi_FieldStorage

    # NOTE: the field storage objects we expose always contain a file
    @type_check_only
    class _FieldStorageWithFile(cgi_FieldStorage):
        file: IO[bytes]
        filename: str


T = TypeVar("T")
GetterReturnType_co = TypeVar("GetterReturnType_co", covariant=True)
SetterValueType_contra = TypeVar("SetterValueType_contra", contravariant=True)


class AsymmetricProperty(Protocol[GetterReturnType_co, SetterValueType_contra]):
    @overload
    def __get__(self, obj: None, type: type[object], /) -> property: ...
    @overload
    def __get__(
        self, obj: object, type: type[object] | None = ..., /
    ) -> GetterReturnType_co: ...

    def __set__(self, obj: object, value: SetterValueType_contra, /) -> None:
        pass


class AsymmetricPropertyWithDelete(
    AsymmetricProperty[GetterReturnType_co, SetterValueType_contra],
    Protocol[GetterReturnType_co, SetterValueType_contra],
):
    def __delete__(self, obj: object, /) -> None:
        pass


SymmetricProperty: TypeAlias = AsymmetricProperty[T, T]
SymmetricPropertyWithDelete: TypeAlias = AsymmetricPropertyWithDelete[T, T]

HTTPMethod: TypeAlias = Literal[
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "DELETE",
    "CONNECT",
    "OPTIONS",
    "TRACE",
    "PATCH",
]
ListOrTuple: TypeAlias = "list[T] | tuple[T, ...]"


class RequestCacheControlDict(TypedDict, total=False):
    max_stale: int
    min_stale: int
    only_if_cached: bool
    no_cache: Literal[True] | str
    no_store: bool
    no_transform: bool
    max_age: int


class ResponseCacheControlDict(TypedDict, total=False):
    public: bool
    private: Literal[True] | str
    no_cache: Literal[True] | str
    no_store: bool
    no_transform: bool
    must_revalidate: bool
    proxy_revalidate: bool
    max_age: int
    s_maxage: int
    s_max_age: int
    stale_while_revalidate: int
    stale_if_error: int


class ResponseCacheExpires(Protocol):
    def __call__(
        self,
        seconds: int | timedelta = 0,
        *,
        public: bool = ...,
        private: Literal[True] | str = ...,
        no_cache: Literal[True] | str = ...,
        no_store: bool = ...,
        no_transform: bool = ...,
        must_revalidate: bool = ...,
        proxy_revalidate: bool = ...,
        max_age: int = ...,
        s_maxage: int = ...,
        s_max_age: int = ...,
        stale_while_revalidate: int = ...,
        stale_if_error: int = ...,
    ) -> None: ...
