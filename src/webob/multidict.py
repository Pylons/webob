# (c) 2005 Ian Bicking and contributors; written for Paste
# (http://pythonpaste.org) Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Gives a multi-value dictionary object (MultiDict) plus several wrappers
"""
from __future__ import annotations

import binascii
from collections.abc import Collection, Iterable, Iterator, MutableMapping
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeVar, overload
from urllib.parse import urlencode as url_encode
import warnings

if TYPE_CHECKING:
    from _typeshed import SupportsKeysAndGetItem
    from _typeshed.wsgi import WSGIEnvironment
    from typing_extensions import Self

    from webob.compat import cgi_FieldStorage
    from webob.types import _FieldStorageWithFile

    _KT_co = TypeVar("_KT_co", covariant=True)
    _VT_co = TypeVar("_VT_co", covariant=True)

    class _SupportsItemsWithIterableResult(Protocol[_KT_co, _VT_co]):
        def items(self) -> Iterable[tuple[_KT_co, _VT_co]]: ...


_T = TypeVar("_T")
_KT = TypeVar("_KT")
_VT = TypeVar("_VT")

__all__ = ["MultiDict", "NestedMultiDict", "NoVars", "GetDict"]


class MultiDict(MutableMapping[_KT, _VT]):
    """
    An ordered dictionary that can have multiple values for each key.
    Adds the methods getall, getone, mixed and extend and add to the normal
    dictionary interface.
    """

    @overload
    def __init__(self) -> None: ...

    @overload
    def __init__(self: MultiDict[str, _VT], **kwargs: _VT) -> None: ...

    @overload
    def __init__(self, m: _SupportsItemsWithIterableResult[_KT, _VT], /) -> None: ...

    @overload
    def __init__(
        self: MultiDict[str, _VT],
        m: _SupportsItemsWithIterableResult[str, _VT],
        /,
        **kwargs: _VT,
    ) -> None: ...

    @overload
    def __init__(self, m: Iterable[tuple[_KT, _VT]], /) -> None: ...

    @overload
    def __init__(
        self: MultiDict[str, _VT], m: Iterable[tuple[str, _VT]], /, **kwargs: _VT
    ) -> None: ...

    def __init__(self, *args: Any, **kw: _VT) -> None:  # type: ignore[misc]
        if len(args) > 1:
            raise TypeError(
                "MultiDict can only be called with one positional " "argument"
            )

        if args:
            if hasattr(args[0], "items"):
                items = list(args[0].items())
            else:
                items = list(args[0])
            self._items: list[tuple[_KT, _VT]] = items
        else:
            self._items = []

        if kw:
            self._items.extend(kw.items())  # type: ignore[arg-type]

    @classmethod
    def view_list(cls, lst: list[tuple[_KT, _VT]]) -> Self:
        """
        Create a multidict that is a view on the given list
        """

        if not isinstance(lst, list):
            raise TypeError(
                "%s.view_list(obj) takes only actual list objects, not %r"
                % (cls.__name__, lst)
            )
        obj: Self = cls()
        obj._items = lst

        return obj

    @classmethod
    def from_fieldstorage(
        cls, fs: cgi_FieldStorage
    ) -> MultiDict[str, str | _FieldStorageWithFile]:
        """
        Create a multidict from a cgi.FieldStorage instance
        """
        obj: MultiDict[str, str | _FieldStorageWithFile] = cls()
        # fs.list can be None when there's nothing to parse

        for field in fs.list or ():
            charset = field.type_options.get("charset", "utf8")
            transfer_encoding = field.headers.get("Content-Transfer-Encoding", None)
            supported_transfer_encoding: dict[str, Any] = {
                "base64": binascii.a2b_base64,
                "quoted-printable": binascii.a2b_qp,
            }

            if charset == "utf8":

                def decode(b: str) -> str:
                    return b

            else:

                def decode(b: str) -> str:
                    return b.encode("utf8").decode(charset)

            if field.filename:
                field.filename = decode(field.filename)
                obj.add(field.name, field)
            else:
                value = field.value

                if transfer_encoding in supported_transfer_encoding:
                    # binascii accepts bytes
                    value = value.encode("utf8")
                    value = supported_transfer_encoding[transfer_encoding](value)

                    # binascii returns bytes
                    value = value.decode("utf8")
                obj.add(field.name, decode(value))

        return obj

    def __getitem__(self, key: _KT) -> _VT:
        for k, v in reversed(self._items):
            if k == key:
                return v
        raise KeyError(key)

    def __setitem__(self, key: _KT, value: _VT) -> None:
        try:
            del self[key]
        except KeyError:
            pass
        self._items.append((key, value))

    def add(self, key: _KT, value: _VT) -> None:
        """
        Add the key and value, not overwriting any previous value.
        """
        self._items.append((key, value))

    def getall(self, key: _KT) -> list[_VT]:
        """
        Return a list of all values matching the key (may be an empty list)
        """

        return [v for k, v in self._items if k == key]

    def getone(self, key: _KT) -> _VT:
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        v = self.getall(key)

        if not v:
            raise KeyError("Key not found: %r" % key)

        if len(v) > 1:
            raise KeyError(f"Multiple values match {key!r}: {v!r}")

        return v[0]

    def mixed(self) -> dict[_KT, _VT | list[_VT]]:
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        result: dict[_KT, _VT | list[_VT]] = {}
        multi: dict[_KT, None] = {}

        for key, value in self.items():
            if key in result:
                # We do this to not clobber any lists that are
                # *actual* values in this dictionary:

                if key in multi:
                    result[key].append(value)  # type: ignore[union-attr]
                else:
                    result[key] = [result[key], value]  # type: ignore[list-item]
                    multi[key] = None
            else:
                result[key] = value

        return result

    def dict_of_lists(self) -> dict[_KT, list[_VT]]:
        """
        Returns a dictionary where each key is associated with a list of values.
        """
        r: dict[_KT, list[_VT]] = {}

        for key, val in self.items():
            r.setdefault(key, []).append(val)

        return r

    def __delitem__(self, key: _KT) -> None:
        items = self._items
        found = False

        for i in range(len(items) - 1, -1, -1):
            if items[i][0] == key:
                del items[i]
                found = True

        if not found:
            raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        for k, _ in self._items:
            if k == key:
                return True

        return False

    has_key = __contains__

    def clear(self) -> None:
        del self._items[:]

    def copy(self) -> Self:
        return self.__class__(self)

    @overload
    def setdefault(
        self: MultiDict[_KT, _VT | None], key: _KT, default: None = None
    ) -> _VT | None: ...

    @overload
    def setdefault(self, key: _KT, default: _VT) -> _VT: ...

    def setdefault(self, key: _KT, default: _VT | None = None) -> _VT | None:
        for k, v in self._items:
            if key == k:
                return v
        self._items.append((key, default))  # type: ignore[arg-type]

        return default

    @overload
    def pop(self, key: _KT) -> _VT: ...

    @overload
    def pop(self, key: _KT, default: _T, /) -> _VT | _T: ...

    def pop(self, key: _KT, *args: _T) -> _VT | _T:
        if len(args) > 1:
            raise TypeError(
                "pop expected at most 2 arguments, got %s" % repr(1 + len(args))
            )

        for i, (k, v) in enumerate(self._items):
            if k == key:
                del self._items[i]

                return v

        if args:
            return args[0]
        raise KeyError(key)

    def popitem(self) -> tuple[_KT, _VT]:
        return self._items.pop()

    @overload  # type: ignore[override]
    def update(self: MultiDict[str, _VT], **kwargs: _VT) -> None: ...

    @overload
    def update(self, m: Collection[tuple[_KT, _VT]], /) -> None: ...

    @overload
    def update(
        self: MultiDict[str, _VT], m: Collection[tuple[str, _VT]], /, **kwargs: _VT
    ) -> None: ...

    def update(self, *args: Collection[tuple[_KT, _VT]], **kw: _VT) -> None:  # type: ignore[misc]
        if args:
            lst = args[0]

            if len(lst) != len(dict(lst)):
                # this does not catch the cases where we overwrite existing
                # keys, but those would produce too many warning
                msg = (
                    "Behavior of MultiDict.update() has changed "
                    "and overwrites duplicate keys. Consider using .extend()"
                )
                warnings.warn(msg, UserWarning, stacklevel=2)
        MutableMapping.update(self, *args, **kw)

    @overload
    def extend(self, other: _SupportsItemsWithIterableResult[_KT, _VT]) -> None: ...

    @overload
    def extend(
        self: MultiDict[str, _VT],
        other: _SupportsItemsWithIterableResult[str, _VT],
        **kwargs: _VT,
    ) -> None: ...

    @overload
    def extend(self, other: Iterable[tuple[_KT, _VT]]) -> None: ...

    @overload
    def extend(
        self: MultiDict[str, _VT], other: Iterable[tuple[str, _VT]], **kwargs: _VT
    ) -> None: ...

    @overload
    def extend(self, other: SupportsKeysAndGetItem[_KT, _VT]) -> None: ...

    @overload
    def extend(
        self: MultiDict[str, _VT],
        other: SupportsKeysAndGetItem[str, _VT],
        **kwargs: _VT,
    ) -> None: ...

    @overload
    def extend(
        self: MultiDict[str, _VT], other: None = None, **kwargs: _VT
    ) -> None: ...

    def extend(self, other: Any | None = None, **kwargs: _VT) -> None:
        if other is None:
            pass
        elif hasattr(other, "items"):
            self._items.extend(other.items())
        elif hasattr(other, "keys"):
            for k in other.keys():
                self._items.append((k, other[k]))
        else:
            for k, v in other:
                self._items.append((k, v))

        if kwargs:
            self.update(kwargs)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        items = map("(%r, %r)".__mod__, _hide_passwd(self.items()))

        return "{}([{}])".format(self.__class__.__name__, ", ".join(items))

    def __len__(self) -> int:
        return len(self._items)

    #
    # All the iteration:
    #

    def keys(self) -> Iterator[_KT]:  # type: ignore[override]
        for k, _ in self._items:
            yield k

    __iter__ = keys

    def items(self) -> Iterator[tuple[_KT, _VT]]:  # type: ignore[override]
        return iter(self._items)

    def values(self) -> Iterator[_VT]:  # type: ignore[override]
        for _, v in self._items:
            yield v

    if TYPE_CHECKING:
        # more permissive get
        @overload
        def get(self, key: _KT, /) -> _VT | None: ...

        @overload
        def get(self, key: _KT, /, default: _T) -> _VT | _T: ...

        def get(self, key: _KT, /, default: Any = None) -> Any: ...


_dummy = object()


class GetDict(MultiDict[str, str]):
    #     def __init__(self, data, tracker, encoding, errors):
    #         d = lambda b: b.decode(encoding, errors)
    #         data = [(d(k), d(v)) for k,v in data]
    @overload
    def __init__(
        self, data: _SupportsItemsWithIterableResult[str, str], env: WSGIEnvironment
    ) -> None: ...

    @overload
    def __init__(
        self, data: Iterable[tuple[str, str]], env: WSGIEnvironment
    ) -> None: ...

    def __init__(self, data: Any, env: WSGIEnvironment) -> None:
        self.env = env
        MultiDict.__init__(self, data)

    def on_change(self) -> None:
        def e(t: str) -> bytes:
            return t.encode("utf8")

        data = [(e(k), e(v)) for k, v in self.items()]
        qs = url_encode(data)
        self.env["QUERY_STRING"] = qs
        self.env["webob._parsed_query_vars"] = (self, qs)

    def __setitem__(self, key: str, value: str) -> None:
        MultiDict.__setitem__(self, key, value)
        self.on_change()

    def add(self, key: str, value: str) -> None:
        MultiDict.add(self, key, value)
        self.on_change()

    def __delitem__(self, key: str) -> None:
        MultiDict.__delitem__(self, key)
        self.on_change()

    def clear(self) -> None:
        MultiDict.clear(self)
        self.on_change()

    def setdefault(self, key: str, default: str) -> str:
        result = MultiDict.setdefault(self, key, default)
        self.on_change()

        return result

    @overload
    def pop(self, key: str) -> str: ...

    @overload
    def pop(self, key: str, default: _T, /) -> str | _T: ...

    def pop(self, key: str, *args: _T) -> str | _T:
        result = MultiDict.pop(self, key, *args)
        self.on_change()

        return result

    def popitem(self) -> tuple[str, str]:
        result = MultiDict.popitem(self)
        self.on_change()

        return result

    @overload  # type: ignore[override]
    def update(self, **kwargs: str) -> None: ...

    @overload
    def update(self, m: Collection[tuple[str, str]], /, **kwargs: str) -> None: ...

    def update(self, *args: Any, **kwargs: str) -> None:  # type: ignore[misc]
        MultiDict.update(self, *args, **kwargs)
        self.on_change()

    @overload
    def extend(
        self, other: _SupportsItemsWithIterableResult[str, str], **kwargs: str
    ) -> None: ...

    @overload
    def extend(self, other: Iterable[tuple[str, str]], **kwargs: str) -> None: ...

    @overload
    def extend(
        self, other: SupportsKeysAndGetItem[str, str], **kwargs: str
    ) -> None: ...

    @overload
    def extend(self, other: None = None, **kwargs: str) -> None: ...

    def extend(self, *args: Any, **kwargs: str) -> None:  # type: ignore[misc]
        MultiDict.extend(self, *args, **kwargs)  # type: ignore[arg-type]
        self.on_change()

    def __repr__(self) -> str:
        items = map("(%r, %r)".__mod__, _hide_passwd(self.items()))
        # TODO: GET -> GetDict

        return "GET([%s])" % (", ".join(items))

    def copy(self) -> MultiDict[str, str]:  # type: ignore[override]
        # Copies shouldn't be tracked

        return MultiDict(self)


class NestedMultiDict(MultiDict[_KT, _VT]):
    """
    Wraps several MultiDict objects, treating it as one large MultiDict
    """

    # FIXME: the annotation here is too strict currently, because we need to
    #        allow violating the variance of _VT for MultiDict, we should replace
    #        this with a MultiMapping Protocol with the correct variance
    def __init__(self, *dicts: MultiDict[_KT, _VT]) -> None:
        self.dicts = dicts

    def __getitem__(self, key: _KT) -> _VT:
        for d in self.dicts:
            value = d.get(key, _dummy)

            if value is not _dummy:
                return value  # type: ignore[return-value]
        raise KeyError(key)

    if TYPE_CHECKING:
        # NOTE: This gives us a slightly better type checker error
        _readonly = None
    else:

        def _readonly(self, *args, **kw):
            raise KeyError("NestedMultiDict objects are read-only")

    __setitem__ = _readonly  # type: ignore[assignment]
    add = _readonly  # type: ignore[assignment]
    __delitem__ = _readonly  # type: ignore[assignment]
    clear = _readonly  # type: ignore[assignment]
    setdefault = _readonly  # type: ignore[assignment]
    pop = _readonly  # type: ignore[assignment]
    popitem = _readonly  # type: ignore[assignment]
    update = _readonly  # type: ignore[assignment]

    def getall(self, key: _KT) -> list[_VT]:
        result = []

        for d in self.dicts:
            result.extend(d.getall(key))

        return result

    # Inherited:
    # getone
    # mixed
    # dict_of_lists

    def copy(self) -> MultiDict[_KT, _VT]:  # type: ignore[override]
        return MultiDict(self)

    def __contains__(self, key: object) -> bool:
        for d in self.dicts:
            if key in d:
                return True

        return False

    has_key = __contains__

    def __len__(self) -> int:
        v = 0

        for d in self.dicts:
            v += len(d)

        return v

    def __bool__(self) -> bool:
        for d in self.dicts:
            if d:
                return True

        return False

    def items(self) -> Iterator[tuple[_KT, _VT]]:  # type: ignore[override]
        for d in self.dicts:
            yield from d.items()

    def values(self) -> Iterator[_VT]:  # type: ignore[override]
        for d in self.dicts:
            yield from d.values()

    def keys(self) -> Iterator[_KT]:  # type: ignore[override]
        for d in self.dicts:
            yield from d

    __iter__ = keys


class NoVars:
    """
    Represents no variables; used when no variables
    are applicable.

    This is read-only
    """

    def __init__(self, reason: str | None = None) -> None:
        self.reason = reason or "N/A"

    if not TYPE_CHECKING:
        # NOTE: It's better to pretend the methods don't exist for NoVars
        #       so we get better type errors

        def __getitem__(self, key):
            raise KeyError(f"No key {key!r}: {self.reason}")

        def __setitem__(self, *args, **kw):
            raise KeyError("Cannot add variables: %s" % self.reason)

        add = __setitem__
        setdefault = __setitem__
        update = __setitem__

        def __delitem__(self, *args, **kw):
            raise KeyError("No keys to delete: %s" % self.reason)

        clear = __delitem__
        pop = __delitem__
        popitem = __delitem__

        getone = __getitem__

    @overload
    def get(self, key: str, default: None = None) -> None: ...

    @overload
    def get(self, key: str, default: _T) -> _T: ...

    def get(self, key: str, default: _T | None = None) -> _T | None:
        return default

    def getall(self, key: str) -> list[str]:
        return []

    def mixed(self) -> dict[str, str | list[str]]:
        return {}

    def dict_of_lists(self) -> dict[str, list[str]]:
        return {}  # pragma: no cover

    def __contains__(self, key: object) -> Literal[False]:
        return False

    has_key = __contains__

    def copy(self) -> Self:
        return self

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.reason}>"

    def __len__(self) -> Literal[0]:
        return 0

    def keys(self) -> Iterator[str]:
        return iter([])

    def items(self) -> Iterator[tuple[str, str]]:
        return iter([])

    values = keys
    __iter__ = keys


def _hide_passwd(
    items: Iterable[tuple[object, object]],
) -> Iterator[tuple[object, object]]:
    for k, v in items:
        if isinstance(k, str) and ("password" in k or "passwd" in k or "pwd" in k):
            yield k, "******"
        else:
            yield k, v
