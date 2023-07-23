import warnings

import pytest

from webob.response import Response
from webob.util import warn_deprecation


class Test_warn_deprecation:
    def setup_method(self, method):

        self.oldwarn = warnings.warn
        warnings.warn = self._warn
        self.warnings = []

    def tearDown(self):

        warnings.warn = self.oldwarn
        del self.warnings

    def _callFUT(self, text, version, stacklevel):

        return warn_deprecation(text, version, stacklevel)

    def _warn(self, text, type, stacklevel=1):
        self.warnings.append(locals())

    def test_multidict_update_warning(self):
        # test warning when duplicate keys are passed
        r = Response()
        r.headers.update([("Set-Cookie", "a=b"), ("Set-Cookie", "x=y")])
        assert len(self.warnings) == 1
        deprecation_warning = self.warnings[0]
        assert deprecation_warning["type"] == UserWarning
        assert "Consider using .extend()" in deprecation_warning["text"]

    def test_multidict_update_warning_unnecessary(self):
        # no warning on normal operation
        r = Response()
        r.headers.update([("Set-Cookie", "a=b")])
        assert len(self.warnings) == 0

    def test_warn_deprecation(self):
        v = "1.3.0"

        pytest.raises(DeprecationWarning, warn_deprecation, "foo", v[:3], 1)

    def test_warn_deprecation_future_version(self):
        v = "9.9.9"

        warn_deprecation("foo", v[:3], 1)
        assert len(self.warnings) == 1
