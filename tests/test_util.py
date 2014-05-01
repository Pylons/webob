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

    def test_warn_deprecation_next_version(self):
        # Bump this at the same time you bump warn_deprecation in util.py
        v = '1.4.0'
        from webob.util import warn_deprecation
        warn_deprecation('foo', v[:3], 1)
        self.assertEqual(len(self.warnings), 1)

    def test_warn_deprecation_future_version(self):
        v = '9.9.9'
        from webob.util import warn_deprecation
        warn_deprecation('foo', v[:3], 1)
        self.assertEqual(len(self.warnings), 2)
