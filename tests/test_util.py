import unittest
from webob.response import Response

class Test_warn_deprecation(unittest.TestCase):
    def setUp(self):
        import warnings
        self.oldwarn = warnings.warn
        warnings.warn = self._warn
        self.warnings = []

    def tearDown(self):
        import warnings
        warnings.warn = self.oldwarn
        del self.warnings

    def _callFUT(self, text, version, stacklevel):
        from webob.util import warn_deprecation
        return warn_deprecation(text, version, stacklevel)

    def _warn(self, text, type, stacklevel=1):
        self.warnings.append(locals())

    def test_multidict_update_warning(self):
        # test warning when duplicate keys are passed
        r = Response()
        r.headers.update([
            ('Set-Cookie', 'a=b'),
            ('Set-Cookie', 'x=y'),
        ])
        self.assertEqual(len(self.warnings), 1)
        deprecation_warning = self.warnings[0]
        self.assertEqual(deprecation_warning['type'], UserWarning)
        assert 'Consider using .extend()' in deprecation_warning['text']

    def test_multidict_update_warning_unnecessary(self):
        # no warning on normal operation
        r = Response()
        r.headers.update([('Set-Cookie', 'a=b')])
        self.assertEqual(len(self.warnings), 0)

    def test_warn_deprecation(self):
        v = '1.3.0'
        from webob.util import warn_deprecation
        self.assertRaises(DeprecationWarning, warn_deprecation, 'foo', v[:3], 1)

    def test_warn_deprecation_future_version(self):
        v = '9.9.9'
        from webob.util import warn_deprecation
        warn_deprecation('foo', v[:3], 1)
        self.assertEqual(len(self.warnings), 1)

class Test_strings_differ(unittest.TestCase):
    def _callFUT(self, *args, **kw):
        from webob.util import strings_differ
        return strings_differ(*args, **kw)

    def test_it(self):
        self.assertFalse(self._callFUT(b'foo', b'foo'))
        self.assertTrue(self._callFUT(b'123', b'345'))
        self.assertTrue(self._callFUT(b'1234', b'123'))
        self.assertTrue(self._callFUT(b'123', b'1234'))

    def test_it_with_internal_comparator(self):
        result = self._callFUT(b'foo', b'foo', compare_digest=None)
        self.assertFalse(result)

        result = self._callFUT(b'123', b'abc', compare_digest=None)
        self.assertTrue(result)

    def test_it_with_external_comparator(self):
        class DummyComparator(object):
            called = False
            def __init__(self, ret_val):
                self.ret_val = ret_val

            def __call__(self, a, b):
                self.called = True
                return self.ret_val

        dummy_compare = DummyComparator(True)
        result = self._callFUT(b'foo', b'foo', compare_digest=dummy_compare)
        self.assertTrue(dummy_compare.called)
        self.assertFalse(result)

        dummy_compare = DummyComparator(False)
        result = self._callFUT(b'123', b'345', compare_digest=dummy_compare)
        self.assertTrue(dummy_compare.called)
        self.assertTrue(result)

        dummy_compare = DummyComparator(False)
        result = self._callFUT(b'abc', b'abc', compare_digest=dummy_compare)
        self.assertTrue(dummy_compare.called)
        self.assertTrue(result)

