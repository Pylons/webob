import pytest

from webob.util import html_escape
from webob.compat import (
    text_,
    PY3
    )

py2only = pytest.mark.skipif("sys.version_info >= (3, 0)")
py3only = pytest.mark.skipif("sys.version_info < (3, 0)")

class t_esc_HTML(object):
    def __html__(self):
        return '<div>hello</div>'


class t_esc_Unicode(object):
    def __unicode__(self):
        return text_(b'\xe9')

class t_esc_UnsafeAttrs(object):
    attr = 'value'
    def __getattr__(self, k):
        return self.attr
    def __repr__(self):
        return '<UnsafeAttrs>'

class t_esc_SuperMoose(object):
    def __str__(self):
        return text_(b'm\xf8ose').encode('utf-8')
    def __unicode__(self):
        return text_(b'm\xf8ose')


@pytest.mark.parametrize("input,expected", [
    ('these chars: < > & "', 'these chars: &lt; &gt; &amp; &quot;'),
    (' ', ' '),
    ('&egrave;', '&amp;egrave;'),

    # The apostrophe is *not* escaped, which some might consider to be
    # a serious bug (see, e.g. http://www.cvedetails.com/cve/CVE-2010-2480/)
    pytest.param("'", "'", marks=py2only),
    pytest.param("'", "&#x27;", marks=py3only),

    (text_('the majestic m\xf8ose'), 'the majestic m&#248;ose'),

    # 8-bit strings are passed through
    (text_('\xe9'), '&#233;'),

    # ``None`` is treated specially, and returns the empty string.
    (None, ''),

    # Objects that define a ``__html__`` method handle their own escaping
    (t_esc_HTML(), '<div>hello</div>'),

    # Things that are not strings are converted to strings and then escaped
    (42, '42'),

    # If an object implements both ``__str__`` and ``__unicode__``, the latter
    # is preferred
    (t_esc_SuperMoose(), 'm&#248;ose'),
    (t_esc_Unicode(), '&#233;'),
    (t_esc_UnsafeAttrs(), '&lt;UnsafeAttrs&gt;'),

    pytest.param(Exception("expected a '<'."), "expected a '&lt;'.", marks=py2only),
    pytest.param(
        Exception("expected a '<'."),
        "expected a &#x27;&lt;&#x27;.",
        marks=py3only
    ),
])
def test_html_escape(input, expected):
    assert expected == html_escape(input)
