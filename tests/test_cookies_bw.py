# -*- coding: utf-8 -*-
from datetime import timedelta
from webob import cookies
from webob.compat import text_
from nose.tools import (eq_, assert_raises)
import unittest
from webob.compat import native_
from webob.compat import PY3

import warnings

def setup_module(module):
    cookies._should_raise = False

def teardown_module(module):
    cookies._should_raise = False

def test_invalid_cookie_space():
    with warnings.catch_warnings(record=True) as w:
        # Cause all warnings to always be triggered.
        warnings.simplefilter("always")
        # Trigger a warning.
        
        cookies._value_quote(b'hello world')

        eq_(len(w), 1)
        eq_(issubclass(w[-1].category, RuntimeWarning), True)
        eq_("ValueError" in str(w[-1].message), True)
