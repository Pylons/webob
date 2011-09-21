import unittest
from webob import Response
from webob.etag import ETagMatcher, IfRange

class etag_propertyTests(unittest.TestCase):
    def _getTargetClass(self):
        from webob.etag import etag_property
        return etag_property

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def _makeDummyRequest(self, **kw):
        """
        Return a DummyRequest object with attrs from kwargs.
        Use like:     dr = _makeDummyRequest(environment={'userid': 'johngalt'})
        Then you can: uid = dr.environment.get('userid', 'SomeDefault')
        """
        class Dummy(object):
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)
        d = Dummy(**kw)
        return d

    def test_fget_missing_key(self):
        ep = self._makeOne("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={})
        self.assertEquals(ep.fget(req), "DEFAULT")

    def test_fget_found_key(self):
        ep = self._makeOne("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'VALUE'})
        res = ep.fget(req)
        self.assertEquals(res.etags, ['VALUE'])
        self.assertEquals(res.weak_etags, [])

    def test_fget_star_key(self):
        ep = self._makeOne("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'*'})
        res = ep.fget(req)
        import webob.etag
        self.assertEquals(type(res), webob.etag._AnyETag)
        self.assertEquals(res.__dict__, {})

    def test_fset_None(self):
        ep = self._makeOne("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'*'})
        res = ep.fset(req, None)
        self.assertEquals(res, None)

    def test_fset_not_None(self):
        ep = self._makeOne("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'OLDVAL'})
        res = ep.fset(req, "NEWVAL")
        self.assertEquals(res, None)
        self.assertEquals(req.environ['KEY'], 'NEWVAL')

    def test_fedl(self):
        ep = self._makeOne("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY':'VAL', 'QUAY':'VALYOU'})
        res = ep.fdel(req)
        self.assertEquals(res, None)
        self.assertFalse('KEY' in req.environ)
        self.assertEquals(req.environ['QUAY'], 'VALYOU')

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

    def test___contains__something(self):
        etag = self._makeOne()
        self.assertEqual('anything' in etag, True)

    def test_weak_match_something(self):
        etag = self._makeOne()
        self.assertRaises(DeprecationWarning, etag.weak_match, 'anything')

    def test___str__(self):
        etag = self._makeOne()
        self.assertEqual(str(etag), '*')

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

    def test___contains__something(self):
        etag = self._makeOne()
        assert 'anything' not in etag

    def test_weak_match(self):
        etag = self._makeOne()
        self.assertRaises(DeprecationWarning, etag.weak_match, None)

    def test___str__(self):
        etag = self._makeOne()
        self.assertEqual(str(etag), '')

class ETagMatcherTests(unittest.TestCase):
    def _getTargetClass(self):
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
        self.assertRaises(DeprecationWarning, matcher.weak_match, "etag")

    def test___repr__one(self):
        matcher = self._makeOne(("ETAGS",), ("WEAK",))
        self.assertEqual(matcher.__repr__(), '<ETag ETAGS>')

    def test___repr__multi(self):
        matcher = self._makeOne(("ETAG1","ETAG2"), ("WEAK",))
        self.assertEqual(matcher.__repr__(), '<ETag ETAG1 or ETAG2>')

    def test___str__etag(self):
        matcher = self._makeOne(("ETAG",))
        self.assertEqual(str(matcher), '"ETAG"')

    def test___str__etag_w_weak(self):
        matcher = self._makeOne(("ETAG",), ("WEAK",))
        self.assertEqual(str(matcher), '"ETAG", W/"WEAK"')



class ParseTests(unittest.TestCase):
    def test_parse_None(self):
        et = ETagMatcher.parse(None)
        self.assertEqual(et.etags, [])
        self.assertEqual(et.weak_etags, [])

    def test_parse_anyetag(self):
        # these tests smell bad, are they useful?
        et = ETagMatcher.parse('*')
        self.assertEqual(et.__dict__, {})
        self.assertEqual(et.__repr__(), '<ETag *>')

    def test_parse_one(self):
        et = ETagMatcher.parse('ONE')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, [])

    def test_parse_commasep(self):
        et = ETagMatcher.parse('ONE, TWO')
        self.assertEqual(et.etags, ['ONE', 'TWO'])
        self.assertEqual(et.weak_etags, [])

    def test_parse_commasep_w_weak(self):
        et = ETagMatcher.parse('ONE, w/TWO')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, ['TWO'])

    def test_parse_quoted(self):
        et = ETagMatcher.parse('"ONE"')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, [])

    def test_parse_quoted_two(self):
        et = ETagMatcher.parse('"ONE", "TWO"')
        self.assertEqual(et.etags, ['ONE', 'TWO'])
        self.assertEqual(et.weak_etags, [])

    def test_parse_quoted_two_weak(self):
        et = ETagMatcher.parse('"ONE", W/"TWO"')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, ['TWO'])

    def test_parse_wo_close_quote(self):
        # Unsure if this is testing likely input
        et = ETagMatcher.parse('"ONE')
        self.assertEqual(et.etags, ['ONE'])
        self.assertEqual(et.weak_etags, [])

class IfRangeTests(unittest.TestCase):
    def test___repr__(self):
        self.assertEqual(repr(IfRange(None)), 'IfRange(None)')

    def test___repr__etag(self):
        self.assertEqual(repr(IfRange('ETAG')), "IfRange('ETAG')")

    def test___repr__date(self):
        ir = IfRange.parse('Fri, 09 Nov 2001 01:08:47 GMT')
        self.assertEqual(
            repr(ir),
            'IfRangeDate(datetime.datetime(2001, 11, 9, 1, 8, 47, tzinfo=UTC))'
        )

