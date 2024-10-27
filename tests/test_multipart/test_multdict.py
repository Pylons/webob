# -*- coding: utf-8 -*-
import unittest
from webob import multipart


class TestMultiDict(unittest.TestCase):

    def test_init(self):
        md = multipart.MultiDict([("a", "1")], {"a": "2"}, a="3")
        self.assertEqual(md.dict, {"a": ["1", "2", "3"]})

    def test_append(self):
        md = multipart.MultiDict()
        md["a"] = "1"
        md["a"] = "2"
        md.append("a", "3")
        md.update(a="4")
        self.assertEqual(md.dict, {"a": ["1", "2", "3", "4"]})

    def test_behaves_like_dict(self):
        md = multipart.MultiDict([("a", "1"), ("a", "2")])
        self.assertTrue("a" in md)
        self.assertFalse("b" in md)
        self.assertTrue("a" in md.keys())
        self.assertEqual(list(md), ["a"])
        del md["a"]
        self.assertTrue("a" not in md)

    def test_access_last(self):
        md = multipart.MultiDict([("a", "1"), ("a", "2")])
        self.assertEqual(md["a"], "2")
        self.assertEqual(md.get("a"), "2")
        self.assertEqual(md.get("b"), None)

    def test_replace(self):
        md = multipart.MultiDict([("a", "1"), ("a", "2")])
        md.replace("a", "3")
        self.assertEqual(md.dict, {"a": ["3"]})

    def test_str_repr(self):
        md = multipart.MultiDict([("a", "1"), ("a", "2")])
        self.assertEqual(str(md), str(md.dict))
        self.assertEqual(repr(md), repr(md.dict))

    def test_access_index(self):
        md = multipart.MultiDict([("a", "1"), ("a", "2")])
        self.assertEqual(md.get("a", index=0), "1")

    def test_access_all(self):
        md = multipart.MultiDict([("a", "1"), ("a", "2")])
        self.assertEqual(md.getall("a"), ["1", "2"])
        self.assertEqual(list(md.iterallitems()), [("a", "1"), ("a", "2")])
