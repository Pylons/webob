import warnings

from webob import cookies

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

        assert len(w) == 1
        assert issubclass(w[-1].category, RuntimeWarning) is True
        assert "ValueError" in str(w[-1].message)
