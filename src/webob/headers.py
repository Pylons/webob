from __future__ import annotations

from collections.abc import Iterator, MutableMapping
from typing import TYPE_CHECKING, TypeVar, overload

from webob.multidict import MultiDict

if TYPE_CHECKING:
    from _typeshed.wsgi import WSGIEnvironment

    _T = TypeVar("_T")

__all__ = ["ResponseHeaders", "EnvironHeaders"]


class ResponseHeaders(MultiDict[str, str]):
    """
    Dictionary view on the response headerlist.
    Keys are normalized for case and whitespace.
    """

    def __getitem__(self, key: str) -> str:
        key = key.lower()

        for k, v in reversed(self._items):
            if k.lower() == key:
                return v
        raise KeyError(key)

    def getall(self, key: str) -> list[str]:
        key = key.lower()

        return [v for (k, v) in self._items if k.lower() == key]

    def mixed(self) -> dict[str, str | list[str]]:
        r: dict[str, str | list[str]] = self.dict_of_lists()  # type: ignore[assignment]

        for key, val in r.items():
            if len(val) == 1:
                r[key] = val[0]

        return r

    def dict_of_lists(self) -> dict[str, list[str]]:
        r: dict[str, list[str]] = {}

        for key, val in self.items():
            r.setdefault(key.lower(), []).append(val)

        return r

    def __setitem__(self, key: str, value: str) -> None:
        norm_key = key.lower()
        self._items[:] = [(k, v) for (k, v) in self._items if k.lower() != norm_key]
        self._items.append((key, value))

    def __delitem__(self, key: str) -> None:
        key = key.lower()
        items = self._items
        found = False

        for i in range(len(items) - 1, -1, -1):
            if items[i][0].lower() == key:
                del items[i]
                found = True

        if not found:
            raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False

        key = key.lower()

        for k, _ in self._items:
            if k.lower() == key:
                return True

        return False

    has_key = __contains__

    def setdefault(self, key: str, default: str) -> str:
        c_key = key.lower()

        for k, v in self._items:
            if k.lower() == c_key:
                return v
        self._items.append((key, default))

        return default

    @overload
    def pop(self, key: str) -> str: ...

    @overload
    def pop(self, key: str, default: _T, /) -> str | _T: ...

    def pop(self, key: str, *args: _T) -> str | _T:
        if len(args) > 1:
            raise TypeError(
                "pop expected at most 2 arguments, got %s" % repr(1 + len(args))
            )
        key = key.lower()

        for i in range(len(self._items)):
            if self._items[i][0].lower() == key:
                v = self._items[i][1]
                del self._items[i]

                return v

        if args:
            return args[0]
        else:
            raise KeyError(key)


key2header = {
    "CONTENT_TYPE": "Content-Type",
    "CONTENT_LENGTH": "Content-Length",
    "HTTP_CONTENT_TYPE": "Content_Type",
    "HTTP_CONTENT_LENGTH": "Content_Length",
}

header2key = {v.upper(): k for (k, v) in key2header.items()}


def _trans_key(key: object) -> str | None:
    if not isinstance(key, str):
        return None
    elif key in key2header:
        return key2header[key]
    elif key.startswith("HTTP_"):
        return key[5:].replace("_", "-").title()
    else:
        return None


def _trans_name(name: str) -> str:
    name = name.upper()

    if name in header2key:
        return header2key[name]

    return "HTTP_" + name.replace("-", "_")


class EnvironHeaders(MutableMapping[str, str]):
    """An object that represents the headers as present in a
    WSGI environment.

    This object is a wrapper (with no internal state) for a WSGI
    request object, representing the CGI-style HTTP_* keys as a
    dictionary.  Because a CGI environment can only hold one value for
    each key, this dictionary is single-valued (unlike outgoing
    headers).
    """

    def __init__(self, environ: WSGIEnvironment) -> None:
        self.environ = environ

    def __getitem__(self, hname: str) -> str:
        return self.environ[_trans_name(hname)]  # type: ignore[no-any-return]

    def __setitem__(self, hname: str, value: str) -> None:
        self.environ[_trans_name(hname)] = value

    def __delitem__(self, hname: str) -> None:
        del self.environ[_trans_name(hname)]

    def keys(self) -> Iterator[str]:  # type: ignore[override]
        return filter(None, map(_trans_key, self.environ))

    def __contains__(self, hname: object) -> bool:
        if not isinstance(hname, str):
            return False
        return _trans_name(hname) in self.environ

    def __len__(self) -> int:
        return len(list(self.keys()))

    def __iter__(self) -> Iterator[str]:
        yield from self.keys()
