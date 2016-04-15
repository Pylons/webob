import pytest

from webob.util import html_escape
from webob.multidict import MultiDict
from webob.compat import (
    text_,
    PY3
    )

def test_html_escape():
    if PY3:
        EXPECTED_LT = 'expected a &#x27;&lt;&#x27;.'
    else:
        EXPECTED_LT = "expected a '&lt;'."
    for v, s in [
        # unsafe chars
        ('these chars: < > & "', 'these chars: &lt; &gt; &amp; &quot;'),
        (' ', ' '),
        ('&egrave;', '&amp;egrave;'),
        # The apostrophe is *not* escaped, which some might consider to be
        # a serious bug (see, e.g. http://www.cvedetails.com/cve/CVE-2010-2480/)
        (text_('the majestic m\xf8ose'), 'the majestic m&#248;ose'),
        # ("'", "&#39;")

        # 8-bit strings are passed through
        (text_('\xe9'), '&#233;'),
        # (text_(b'the majestic m\xf8ose').encode('utf-8'),
        #  'the majestic m\xc3\xb8ose'),

        # ``None`` is treated specially, and returns the empty string.
        (None, ''),

        # Objects that define a ``__html__`` method handle their own escaping
        (t_esc_HTML(), '<div>hello</div>'),

        # Things that are not strings are converted to strings and then escaped
        (42, '42'),
        (Exception("expected a '<'."), EXPECTED_LT),

        # If an object implements both ``__str__`` and ``__unicode__``, the latter
        # is preferred
        (t_esc_SuperMoose(), 'm&#248;ose'),
        (t_esc_Unicode(), '&#233;'),
        (t_esc_UnsafeAttrs(), '&lt;UnsafeAttrs&gt;'),
    ]:
        assert html_escape(v) == s

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

def test_multidict():
    d = MultiDict(a=1, b=2)
    assert d['a'] == 1
    assert d.getall('c') == []

    d.add('a', 2)
    assert d['a'] == 2
    assert d.getall('a') == [1, 2]

    d['b'] = 4
    assert d.getall('b') == [4]
    assert list(d.keys()) == ['a', 'a', 'b']
    assert list(d.items()) == [('a', 1), ('a', 2), ('b', 4)]
    assert d.mixed() == {'a': [1, 2], 'b': 4}

    # test getone

    # KeyError: "Multiple values match 'a': [1, 2]"
    with pytest.raises(KeyError):
        d.getone('a')

    assert d.getone('b') == 4
    # KeyError: "Key not found: 'g'"
    with pytest.raises(KeyError):
        d.getone('g')

    assert d.dict_of_lists() == {'a': [1, 2], 'b': [4]}
    assert 'b' in d
    assert 'e' not in d
    d.clear()
    assert 'b' not in d
    d['a'] = 4
    d.add('a', 5)
    e = d.copy()
    assert 'a' in e
    e.clear()
    e['f'] = 42
    d.update(e)
    assert d == MultiDict([('a', 4), ('a', 5), ('f', 42)])
    f = d.pop('a')
    assert f == 4
    assert d['a'] == 5

    assert d.pop('g', 42) == 42
    with pytest.raises(KeyError):
        d.pop('n')
    # TypeError: pop expected at most 2 arguments, got 3
    with pytest.raises(TypeError):
        d.pop(4, 2, 3)
    d.setdefault('g', []).append(4)
    assert d == MultiDict([('a', 5), ('f', 42), ('g', [4])])

def test_multidict_init():
    d = MultiDict([('a', 'b')], c=2)
    assert repr(d) == "MultiDict([('a', 'b'), ('c', 2)])"
    assert d == MultiDict([('a', 'b')], c=2)

    # TypeError: MultiDict can only be called with one positional argument
    with pytest.raises(TypeError):
        MultiDict(1, 2, 3)

    # TypeError: MultiDict.view_list(obj) takes only actual list objects, not None
    with pytest.raises(TypeError):
        MultiDict.view_list(None)
