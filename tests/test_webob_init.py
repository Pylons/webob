# 32, 37

from webob import html_escape
from nose.tools import ok_

class Dummy1(object):

    def __init__(self, text):
        self.text = text

    def __html__(self):
        return "<html><head></head><body>%s</body></html>" % (self.text)

class Dummy2(object):

    def __init__(self, text):
        self.text = text

    def __unicode__(self):
        return u"<html><head></head><body>%s</body></html>" % (self.text)

def test_html_escape():
    """Testing webob.html_escape method
    Testing scenarios:
        * s is None, return ''
        * Object with __html__ attr, should return it
    """
    ok_(html_escape(None)=='', "Passed None, should return ''")
    html_p = Dummy1('Hello World')
    ok_(html_escape(html_p)==\
        "<html><head></head><body>Hello World</body></html>", "Return "
        "html method from Dummy1 Object")
    html_p = Dummy2('Hello World')
    ok_(html_escape(html_p)==\
        '&lt;html&gt;&lt;head&gt;&lt;/head&gt;&lt;body&gt;Hello World&lt;/body&gt;&lt;/html&gt;' , "Return unicode method from Dummy2 Object")

