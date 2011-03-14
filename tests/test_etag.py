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

    def test_weak_match_etags(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertTrue(matcher.weak_match("W/ETAGS"))

    def test_weak_match_weak_etags(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertTrue(matcher.weak_match("W/WEAK"))

    def test_weak_match_weak_not(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertFalse(matcher.weak_match("W/BEER"))

    def test_weak_match_weak_wo_wslash(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertTrue(matcher.weak_match("ETAGS"))

    def test_weak_match_weak_wo_wslash_not(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertFalse(matcher.weak_match("BEER"))

    def test___repr__one(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertEqual(matcher.__repr__(), '<ETag ETAGS>')

    def test___repr__multi(self):
        matcher = self._makeOne(("ETAG1","ETAG2"), ("WEAK",))
        self.assertEqual(matcher.__repr__(), '<ETag ETAG1 or ETAG2>')

    def test_parse_None(self):
        matcher = self._makeOne(("ETAG1",), ("WEAK",))
        et = matcher.parse(None)
        self.assertEqual(et.etags, [])
        self.assertEqual(et.weak_etags, [])

    def test_parse_anyetag(self):
        # these tests smell bad, are they useful?
        matcher = self._makeOne(("ETAG1",), ("WEAK",))
        et = matcher.parse('*')
        self.assertEqual(et.__dict__, {})
        self.assertEqual(et.__repr__(), '<ETag *>')


    def test_parse_one(self):
        matcher = self._makeOne(("ETAG1",), ("WEAK",))
        et = matcher.parse('ONE')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, [])

    def test_parse_commasep(self):
        matcher = self._makeOne(("ETAG1",), ("WEAK",))
        import pdb; pdb.set_trace()
        et = matcher.parse('ONE, TWO')
        self.assertEqual(et.etags, ['ONE', 'TWO'])
        self.assertEqual(et.weak_etags, [])

    def test_parse_commasep_w_weak(self):
        matcher = self._makeOne(("ETAG1",), ("WEAK",))
        et = matcher.parse('ONE, w/TWO')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, ['TWO'])

    # def test_parse_quoted(self):
    #     matcher = self._makeOne(("ETAG1",), ("WEAK",))
    #     import pdb; pdb.set_trace()
    #     et = matcher.parse('"ONE, TWO"')
    #     self.assertEqual(et.etags, ['ONE', 'TWO'])
    #     self.assertEqual(et.weak_etags, [])

