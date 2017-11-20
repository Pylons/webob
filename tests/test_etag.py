import pytest

from webob.etag import ETagMatcher, IfRange, etag_property

class Test_etag_properties(object):
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
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={})
        assert ep.fget(req) == "DEFAULT"

    def test_fget_found_key(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY': '"VALUE"'})
        res = ep.fget(req)
        assert res.etags == ['VALUE']

    def test_fget_star_key(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY': '*'})
        res = ep.fget(req)
        import webob.etag
        assert type(res) == webob.etag._AnyETag
        assert res.__dict__ == {}

    def test_fset_None(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY': '*'})
        res = ep.fset(req, None)
        assert res is None

    def test_fset_not_None(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY': 'OLDVAL'})
        res = ep.fset(req, "NEWVAL")
        assert res is None
        assert req.environ['KEY'] == 'NEWVAL'

    def test_fedl(self):
        ep = etag_property("KEY", "DEFAULT", "RFC_SECTION")
        req = self._makeDummyRequest(environ={'KEY': 'VAL', 'QUAY': 'VALYOU'})
        res = ep.fdel(req)
        assert res is None
        assert 'KEY' not in req.environ
        assert req.environ['QUAY'] == 'VALYOU'

class Test_AnyETag(object):
    def _getTargetClass(self):
        from webob.etag import _AnyETag
        return _AnyETag

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___repr__(self):
        etag = self._makeOne()
        assert etag.__repr__() == '<ETag *>'

    def test___nonzero__(self):
        etag = self._makeOne()
        assert etag.__nonzero__() is False

    def test___contains__something(self):
        etag = self._makeOne()
        assert 'anything' in etag

    def test___str__(self):
        etag = self._makeOne()
        assert str(etag) == '*'

class Test_NoETag(object):
    def _getTargetClass(self):
        from webob.etag import _NoETag
        return _NoETag

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___repr__(self):
        etag = self._makeOne()
        assert etag.__repr__() == '<No ETag>'

    def test___nonzero__(self):
        etag = self._makeOne()
        assert etag.__nonzero__() is False

    def test___contains__something(self):
        etag = self._makeOne()
        assert 'anything' not in etag

    def test___str__(self):
        etag = self._makeOne()
        assert str(etag) == ''


class Test_Parse(object):
    def test_parse_None(self):
        et = ETagMatcher.parse(None)
        assert et.etags == []

    def test_parse_anyetag(self):
        # these tests smell bad, are they useful?
        et = ETagMatcher.parse('*')
        assert et.__dict__ == {}
        assert et.__repr__() == '<ETag *>'

    def test_parse_one(self):
        et = ETagMatcher.parse('"ONE"')
        assert et.etags == ['ONE']

    def test_parse_invalid(self):
        for tag in ['one', 'one, two', '"one two']:
            et = ETagMatcher.parse(tag)
            assert et.etags == [tag]
        et = ETagMatcher.parse('"foo" and w/"weak"', strong=False)
        assert et.etags == ['foo']

    def test_parse_commasep(self):
        et = ETagMatcher.parse('"ONE", "TWO"')
        assert et.etags, ['ONE' == 'TWO']

    def test_parse_commasep_w_weak(self):
        et = ETagMatcher.parse('"ONE", W/"TWO"')
        assert et.etags == ['ONE']
        et = ETagMatcher.parse('"ONE", W/"TWO"', strong=False)
        assert et.etags, ['ONE' == 'TWO']

    def test_parse_quoted(self):
        et = ETagMatcher.parse('"ONE"')
        assert et.etags == ['ONE']

    def test_parse_quoted_two(self):
        et = ETagMatcher.parse('"ONE", "TWO"')
        assert et.etags, ['ONE' == 'TWO']

    def test_parse_quoted_two_weak(self):
        et = ETagMatcher.parse('"ONE", W/"TWO"')
        assert et.etags == ['ONE']
        et = ETagMatcher.parse('"ONE", W/"TWO"', strong=False)
        assert et.etags, ['ONE' == 'TWO']

class Test_IfRange(object):
    def test___repr__(self):
        assert repr(IfRange(None)) == 'IfRange(None)'

    def test___repr__etag(self):
        assert repr(IfRange('ETAG')) == "IfRange('ETAG')"

    def test___repr__date(self):
        ir = IfRange.parse('Fri, 09 Nov 2001 01:08:47 GMT')
        assert repr(ir) == 'IfRangeDate(datetime.datetime(2001, 11, 9, 1, 8, 47, tzinfo=UTC))'
