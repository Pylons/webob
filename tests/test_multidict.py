import sys

import pytest

from webob import multidict
from webob.util import text_

requires_cgi = pytest.mark.skipif(
    sys.version_info >= (3, 13), reason="requires `cgi` module"
)


class BaseDictTests:
    def setup_method(self, method):
        self._list = [("a", text_("\xe9")), ("a", "e"), ("a", "f"), ("b", "1")]
        self.data = multidict.MultiDict(self._list)
        self.d = self._get_instance()

    def _get_instance(self, **kwargs):
        if kwargs:
            data = multidict.MultiDict(kwargs)
        else:
            data = self.data.copy()
        return self.klass(data)

    def test_len(self):
        assert len(self.d) == 4

    def test_getone(self):
        assert self.d.getone("b") == "1"

    def test_getone_missing(self):
        pytest.raises(KeyError, self.d.getone, "z")

    def test_getone_multiple_raises(self):
        pytest.raises(KeyError, self.d.getone, "a")

    def test_getall(self):
        assert list(self.d.getall("b")) == ["1"]

    def test_dict_of_lists(self):
        assert self.d.dict_of_lists() == {"a": [text_("\xe9"), "e", "f"], "b": ["1"]}

    def test_dict_api(self):
        assert "a" in self.d.mixed()
        assert "a" in self.d.keys()
        assert ("b", "1") in self.d.items()
        assert "1" in self.d.values()
        assert len(self.d) == 4

    def test_set_del_item(self):
        d = self._get_instance()
        assert "a" in d
        del d["a"]
        assert "a" not in d

    def test_pop(self):
        d = self._get_instance()
        d["a"] = "1"
        assert d.pop("a") == "1"
        assert d.pop("x", "1") == "1"

    def test_pop_wrong_args(self):
        d = self._get_instance()
        pytest.raises(TypeError, d.pop, "a", "1", "1")

    def test_pop_missing(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.pop, "z")

    def test_popitem(self):
        d = self._get_instance()
        assert d.popitem() == ("b", "1")

    def test_update(self):
        d = self._get_instance()
        d.update(e="1")
        assert "e" in d
        d.update(dict(x="1"))
        assert "x" in d
        d.update([("y", "1")])
        assert "y" in d

    def test_setdefault(self):
        d = self._get_instance()
        d.setdefault("a", "1")
        assert d["a"] != "1"
        d.setdefault("e", "1")
        assert "e" in d

    def test_add(self):
        d = multidict.MultiDict({"a": "1"})
        d.add("a", "2")
        assert list(d.getall("a")) == ["1", "2"]
        d = self._get_instance()
        d.add("b", "3")
        assert list(d.getall("b")) == ["1", "3"]

    def test_copy(self):
        assert self.d.copy() is not self.d
        if hasattr(self.d, "multi"):
            assert not self.d.copy().multi is self.d.multi
            assert not self.d.copy() is self.d.multi

    def test_clear(self):
        d = self._get_instance()
        d.clear()
        assert len(d) == 0

    def test_bool(self):
        d = self._get_instance()
        assert d
        d.clear()
        assert not d

    def test_repr(self):
        assert repr(self._get_instance())

    def test_too_many_args(self):
        from webob.multidict import MultiDict

        pytest.raises(TypeError, MultiDict, "1", 2)

    def test_no_args(self):
        from webob.multidict import MultiDict

        md = MultiDict()
        assert md._items == []

    def test_kwargs(self):
        from webob.multidict import MultiDict

        md = MultiDict(kw1="val1")
        assert md._items == [("kw1", "val1")]

    def test_view_list_not_list(self):
        from webob.multidict import MultiDict

        d = MultiDict()
        pytest.raises(TypeError, d.view_list, 42)

    def test_view_list(self):
        from webob.multidict import MultiDict

        d = MultiDict()
        assert d.view_list([1, 2])._items == [1, 2]

    @requires_cgi
    def test_from_fieldstorage_with_filename(self):
        from webob.multidict import MultiDict

        d = MultiDict()
        fs = DummyFieldStorage("a", "1", "file")
        assert d.from_fieldstorage(fs) == MultiDict({"a": fs.list[0]})

    @requires_cgi
    def test_from_fieldstorage_without_filename(self):
        from webob.multidict import MultiDict

        d = MultiDict()
        fs = DummyFieldStorage("a", "1")
        assert d.from_fieldstorage(fs) == MultiDict({"a": "1"})

    @requires_cgi
    def test_from_fieldstorage_with_charset(self):
        from cgi import FieldStorage

        from webob.multidict import MultiDict
        from webob.request import BaseRequest

        multipart_type = "multipart/form-data; boundary=foobar"
        from io import BytesIO

        body = (
            b"--foobar\r\n"
            b'Content-Disposition: form-data; name="title"\r\n'
            b'Content-type: text/plain; charset="ISO-2022-JP"\r\n'
            b"\r\n"
            b"\x1b$B$3$s$K$A$O\x1b(B"
            b"\r\n"
            b"--foobar--"
        )
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank("/").environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD="POST")
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        assert vars["title"].encode("utf8") == text_("こんにちは", "utf8").encode(
            "utf8"
        )

    @requires_cgi
    def test_from_fieldstorage_with_base64_encoding(self):
        from cgi import FieldStorage

        from webob.multidict import MultiDict
        from webob.request import BaseRequest

        multipart_type = "multipart/form-data; boundary=foobar"
        from io import BytesIO

        body = (
            b"--foobar\r\n"
            b'Content-Disposition: form-data; name="title"\r\n'
            b'Content-type: text/plain; charset="ISO-2022-JP"\r\n'
            b"Content-Transfer-Encoding: base64\r\n"
            b"\r\n"
            b"GyRCJDMkcyRLJEEkTxsoQg=="
            b"\r\n"
            b"--foobar--"
        )
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank("/").environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD="POST")
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        assert vars["title"].encode("utf8") == text_("こんにちは", "utf8").encode(
            "utf8"
        )

    @requires_cgi
    def test_from_fieldstorage_with_quoted_printable_encoding(self):
        from cgi import FieldStorage

        from webob.multidict import MultiDict
        from webob.request import BaseRequest

        multipart_type = "multipart/form-data; boundary=foobar"
        from io import BytesIO

        body = (
            b"--foobar\r\n"
            b'Content-Disposition: form-data; name="title"\r\n'
            b'Content-type: text/plain; charset="ISO-2022-JP"\r\n'
            b"Content-Transfer-Encoding: quoted-printable\r\n"
            b"\r\n"
            b"=1B$B$3$s$K$A$O=1B(B"
            b"\r\n"
            b"--foobar--"
        )
        multipart_body = BytesIO(body)
        environ = BaseRequest.blank("/").environ
        environ.update(CONTENT_TYPE=multipart_type)
        environ.update(REQUEST_METHOD="POST")
        environ.update(CONTENT_LENGTH=len(body))
        fs = FieldStorage(multipart_body, environ=environ)
        vars = MultiDict.from_fieldstorage(fs)
        assert vars["title"].encode("utf8") == text_("こんにちは", "utf8").encode(
            "utf8"
        )


class TestMultiDict(BaseDictTests):
    klass = multidict.MultiDict

    def test_update_behavior_warning(self):
        import warnings

        class Foo(dict):
            def __len__(self):
                return 0

        foo = Foo()
        foo["a"] = 1
        d = self._get_instance()
        with warnings.catch_warnings(record=True) as w:
            d.update(foo)
        assert len(w) == 1

    def test_repr_with_password(self):
        d = self._get_instance(password="pwd")
        assert repr(d) == "MultiDict([('password', '******')])"

    def test_from_multipart(self):
        from io import BytesIO

        from multipart import MultipartParser

        data = (
            b"--foobar\r\n"
            b'Content-Disposition: form-data; name="foo"\r\n'
            b"\r\n"
            b"bar\r\n"
            b"--foobar\r\n"
            b'Content-Disposition: form-data; name="fizz"; filename="fizz.txt"\r\n'
            b"Content-type: application/octet-stream\r\n"
            b"\r\n"
            b"buzz\r\n"
            b"\r\n"
            b"--foobar--\r\n"
        )
        body = BytesIO(data)
        body.seek(0)
        mp = MultipartParser(body, b"foobar")
        inst = self.klass.from_multipart(mp)
        assert inst["foo"] == "bar"
        fizz = inst["fizz"]
        assert isinstance(fizz, multidict.MultiDictFile)
        assert fizz.filename == "fizz.txt"
        assert fizz.value == b"buzz\r\n"


class TestNestedMultiDict(BaseDictTests):
    klass = multidict.NestedMultiDict

    def test_getitem(self):
        d = self.klass({"a": 1})
        assert d["a"] == 1

    def test_getitem_raises(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.__getitem__, "z")

    def test_contains(self):
        d = self._get_instance()
        assert "a" in d
        assert "z" not in d

    def test_add(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.add, "b", 3)

    def test_set_del_item(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.__delitem__, "a")
        pytest.raises(KeyError, d.__setitem__, "a", 1)

    def test_update(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.update, e=1)
        pytest.raises(KeyError, d.update, dict(x=1))
        pytest.raises(KeyError, d.update, [("y", 1)])

    def test_setdefault(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.setdefault, "a", 1)

    def test_pop(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.pop, "a")
        pytest.raises(KeyError, d.pop, "a", 1)

    def test_popitem(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.popitem, "a")

    def test_pop_wrong_args(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.pop, "a", 1, 1)

    def test_clear(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.clear)

    def test_bool(self):
        d = self._get_instance()
        assert d.__bool__() == True
        d.dicts = [{}]
        assert d.__bool__() == False
        assert not d


class TestGetDict(BaseDictTests):
    klass = multidict.GetDict

    def _get_instance(self, environ=None, **kwargs):
        if environ is None:
            environ = {}
        if kwargs:
            data = multidict.MultiDict(kwargs)
        else:
            data = self.data.copy()
        return self.klass(data, environ)

    def test_inititems(self):
        # The first argument passed into the __init__ method
        class Arg:
            def items(self):
                return [("a", text_("\xe9")), ("a", "e"), ("a", "f"), ("b", 1)]

        d = self._get_instance()
        d._items = None
        d.__init__(Arg(), lambda: None)
        assert self.d._items == self._list

    def test_nullextend(self):
        d = self._get_instance()
        assert d.extend() == None
        d.extend(test="a")
        assert d["test"] == "a"

    def test_extend_from_items(self):
        values = {"a": "1", "b": "2", "c": "3"}

        class MappingWithItems:
            def items(self):
                return values.items()

        d = self._get_instance()
        d.extend(MappingWithItems())
        assert set(values.items()).issubset(d._items)

    def test_extend_from_keys(self):
        values = {"a": "1", "b": "2", "c": "3"}

        class MappingWithoutItems:
            def __getitem__(self, item):
                return values[item]

            def keys(self):
                return values.keys()

        d = self._get_instance()
        d.extend(MappingWithoutItems())
        assert set(values.items()).issubset(d._items)

    def test_extend_from_iterable(self):
        items = [("a", "1")]
        d = self._get_instance()

        d.extend(iter(items))
        assert set(items).issubset(d._items)

    def test_repr_with_password(self):
        d = self._get_instance(password="pwd")
        assert repr(d) == "GET([('password', '******')])"

    def test_setitem_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d["a"] = "2"
        assert env["QUERY_STRING"] == "b=1&a=2"

    def test_add_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.add("a", "2")
        assert env["QUERY_STRING"] == "a=%C3%A9&a=e&a=f&b=1&a=2"

    def test_delitem_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        del d["a"]
        assert env["QUERY_STRING"] == "b=1"

    def test_clear_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.clear()
        assert env["QUERY_STRING"] == ""

    def test_setdefault_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.setdefault("c", "2")
        assert env["QUERY_STRING"] == "a=%C3%A9&a=e&a=f&b=1&c=2"

    def test_pop_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.pop("a")
        assert env["QUERY_STRING"] == "a=e&a=f&b=1"

    def test_popitem_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.popitem()
        assert env["QUERY_STRING"] == "a=%C3%A9&a=e&a=f"

    def test_update_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.update([("a", "2")])
        assert env["QUERY_STRING"] == "b=1&a=2"

    def test_extend_updates_QUERY_STRING(self):
        env = {}
        d = self._get_instance(environ=env)
        d.extend([("a", "2")])
        assert env["QUERY_STRING"] == "a=%C3%A9&a=e&a=f&b=1&a=2"


class TestNoVars:
    klass = multidict.NoVars

    def _get_instance(self):
        return self.klass()

    def test_getitem(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.__getitem__, "a")

    def test_setitem(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.__setitem__, "a")

    def test_delitem(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.__delitem__, "a")

    def test_get(self):
        d = self._get_instance()
        assert d.get("a", default="b") == "b"

    def test_getall(self):
        d = self._get_instance()
        assert d.getall("a") == []

    def test_getone(self):
        d = self._get_instance()
        pytest.raises(KeyError, d.getone, "a")

    def test_mixed(self):
        d = self._get_instance()
        assert d.mixed() == {}

    def test_contains(self):
        d = self._get_instance()
        assert "a" not in d

    def test_copy(self):
        d = self._get_instance()
        assert d.copy() == d

    def test_len(self):
        d = self._get_instance()
        assert len(d) == 0

    def test_repr(self):
        d = self._get_instance()
        assert repr(d) == "<NoVars: N/A>"

    def test_keys(self):
        d = self._get_instance()
        assert list(d.keys()) == []


class DummyField:
    def __init__(self, name, value, filename=None):
        self.name = name
        self.value = value
        self.filename = filename
        self.type_options = {}
        self.headers = {}


class DummyFieldStorage:
    def __init__(self, name, value, filename=None):
        self.list = [DummyField(name, value, filename)]
