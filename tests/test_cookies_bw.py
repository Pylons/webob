# -*- coding: utf-8 -*-
from datetime import timedelta
from webob import cookies
from webob.compat import text_
from nose.tools import (eq_, assert_raises)
import unittest
from webob.compat import native_
from webob.compat import PY3

import warnings

def test_invalid_cookie_space():
    cookies._should_raise = False

    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Trigger a warning.
        
        cookies._value_quote(b'hello world')

        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert "ValueError" in str(w[-1].message)

    cookies._should_raise = True
