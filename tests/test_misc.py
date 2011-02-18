from webob import html_escape
from nose.tools import eq_


def test_html_escape():
    for v, s in [
        (None, ''),
        (' ', ' '),
        ('&egrave;', '&amp;egrave;'),
        (u'\xe9', '&#233;'),
        (t_esc_HTML(), '<div>hello</div>'),
        (t_esc_Unicode(), '&#233;'),
        (t_esc_UnsafeAttrs(), '&lt;UnsafeAttrs&gt;'),
    ]:
        eq_(html_escape(v), s)


class t_esc_HTML(object):
    def __html__(self):
        return '<div>hello</div>'


class t_esc_Unicode(object):
    def __unicode__(self):
        return u'\xe9'

class t_esc_UnsafeAttrs(object):
    attr = 'value'
    def __getattr__(self):
        return self.attr
    def __repr__(self):
        return '<UnsafeAttrs>'


