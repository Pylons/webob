from unittest import TestCase


class TestAccept(TestCase):
    def test_init_accept_content_type(self):
        from webob.acceptparse import Accept
        name, value = ('Content-Type', 'text/html')
        accept = Accept(name, value)
        assert accept.header_name == name
        assert accept.header_value == value
        assert accept._parsed == [('text/html', 1)]

    def test_init_accept_accept_charset(self):
        from webob.acceptparse import Accept
        name, value = ('Accept-Charset', 'iso-8859-5, unicode-1-1;q=0.8')
        accept = Accept(name, value)
        assert accept.header_name == name
        assert accept.header_value == value
        assert accept._parsed == [('iso-8859-5', 1),
                                  ('unicode-1-1', 0.80000000000000004),
                                  ('iso-8859-1', 1)]

    def test_init_accept_accept_charset_with_iso_8859_1(self):
        from webob.acceptparse import Accept
        name, value = ('Accept-Charset', 'iso-8859-1')
        accept = Accept(name, value)
        assert accept.header_name == name
        assert accept.header_value == value
        assert accept._parsed == [('iso-8859-1', 1)]

    def test_init_accept_accept_charset_wildcard(self):
        from webob.acceptparse import Accept
        name, value = ('Accept-Charset', '*')
        accept = Accept(name, value)
        assert accept.header_name == name
        assert accept.header_value == value
        assert accept._parsed == [('*', 1)]

    def test_init_accept_accept_language(self):
        from webob.acceptparse import Accept
        name, value = ('Accept-Language', 'da, en-gb;q=0.8, en;q=0.7')
        accept = Accept(name, value)
        assert accept.header_name == name
        assert accept.header_value == value
        assert accept._parsed == [('da', 1),
                                  ('en-gb', 0.80000000000000004),
                                  ('en', 0.69999999999999996)]

    def test_init_accept_invalid_value(self):
        from webob.acceptparse import Accept
        name, value = ('Accept-Language', 'da, q, en-gb;q=0.8')
        accept = Accept(name, value)
        # The "q" value should not be there.
        assert accept._parsed == [('da', 1),
                                  ('en-gb', 0.80000000000000004)]

    def test_init_accept_invalid_q_value(self):
        from webob.acceptparse import Accept
        name, value = ('Accept-Language', 'da, en-gb;q=foo')
        accept = Accept(name, value)
        # I can't get to cover line 40-41 (webob.acceptparse) as the regex
        # will prevent from hitting these lines (aconrad)
        assert accept._parsed == [('da', 1), ('en-gb', 1)]
