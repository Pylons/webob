import pytest

from webob.util import html_escape, text_


class t_esc_HTML:
    def __html__(self):
        return "<div>hello</div>"


class t_esc_Unicode:
    def __str__(self):
        return "\xe9"


class t_esc_UnsafeAttrs:
    attr = "value"

    def __getattr__(self, k):
        return self.attr

    def __repr__(self):
        return "<UnsafeAttrs>"


class t_esc_SuperMoose:
    def __str__(self):
        return "m\xf8ose"


@pytest.mark.parametrize(
    "input,expected",
    [
        ('these chars: < > & "', "these chars: &lt; &gt; &amp; &quot;"),
        (" ", " "),
        ("&egrave;", "&amp;egrave;"),
        # The apostrophe is *not* escaped, which some might consider to be
        # a serious bug (see, e.g. http://www.cvedetails.com/cve/CVE-2010-2480/)
        pytest.param("'", "&#x27;"),
        ("the majestic m\xf8ose", "the majestic m&#248;ose"),
        # 8-bit strings are passed through
        ("\xe9", "&#233;"),
        # ``None`` is treated specially, and returns the empty string.
        (None, ""),
        # Objects that define a ``__html__`` method handle their own escaping
        (t_esc_HTML(), "<div>hello</div>"),
        # Things that are not strings are converted to strings and then escaped
        (42, "42"),
        (t_esc_SuperMoose(), "m&#248;ose"),
        (t_esc_Unicode(), "&#233;"),
        (t_esc_UnsafeAttrs(), "&lt;UnsafeAttrs&gt;"),
        pytest.param(Exception("expected a '<'."), "expected a &#x27;&lt;&#x27;."),
    ],
)
def test_html_escape(input, expected):
    assert expected == html_escape(input)
