import unittest
###############################################################################

# TODO:
# - test etag_property

class AnyETagTests(unittest.TestCase):
    def _getTargetClass(self):
        from webob.etag import _AnyETag
        return _AnyETag

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___repr__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__repr__(), '<ETag *>')

    def test___nonzero__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__nonzero__(), False)

    def test___contains__None(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__(None), True)

    def test___contains__empty_list(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__([]), True)

    def test___contains__empty_string(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__(''), True)

    def test___contains__something(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__('something'), True)

    def test_weak_match_None(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match(None), True)

    def test_weak_match_empty_list(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match([]), True)

    def test_weak_match_empty_string(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match(''), True)

    def test_weak_match_something(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match('something'), True)

    def test___str__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__str__(), '*')

class NoETagTests(unittest.TestCase):
    def _getTargetClass(self):
        from webob.etag import _NoETag
        return _NoETag

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___repr__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__repr__(), '<No ETag>')

    def test___nonzero__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__nonzero__(), False)

    def test___contains__None(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__(None), False)

    def test___contains__empty_list(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__([]), False)

    def test___contains__empty_string(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__(''), False)

    def test___contains__something(self):
        etag = self._makeOne()
        self.assertEqual(etag.__contains__('something'), False)

    def test_weak_match_None(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match(None), False)

    def test_weak_match_empty_list(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match([]), False)

    def test_weak_match_empty_string(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match(''), False)

    def test_weak_match_something(self):
        etag = self._makeOne()
        self.assertEqual(etag.weak_match('something'), False)

    def test___str__(self):
        etag = self._makeOne()
        self.assertEqual(etag.__str__(), '')

class ETagMatcherTests(unittest.TestCase):
    def _getTargetClass(self):
        from webob.etag import ETagMatcher
        return ETagMatcher

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___init__wo_weak_etags(self):
        matcher = self._makeOne(("ETAGS",))
        self.assertEqual(matcher.etags, ("ETAGS",))
        self.assertEqual(matcher.weak_etags, ())

    def test___init__w_weak_etags(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertEqual(matcher.etags, ("ETAGS",))
        self.assertEqual(matcher.weak_etags, ("WEAK",))

    def test___contains__tags(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertTrue("ETAGS" in matcher)

    def test___contains__weak_tags(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertTrue("WEAK" in matcher)

    def test___contains__not(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertFalse("BEER" in matcher)

    def test___contains__None(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertFalse(None in matcher)



