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

    def test_accept_repr(self):
        from webob.acceptparse import Accept
        name, value = ('Content-Type', 'text/html')
        accept = Accept(name, value)
        assert '%r' % accept == '<%s at 0x%x %s: %s>' % ('Accept',
                                                         abs(id(accept)),
                                                         name,
                                                         str(accept))

    def test_accept_str(self):
        from webob.acceptparse import Accept
        name, value = ('Content-Type', 'text/html')
        accept = Accept(name, value)
        assert str(accept) == value

    def test_accept_str_with_q_not_1(self):
        from webob.acceptparse import Accept
        name, value = ('Content-Type', 'text/html;q=0.5')
        accept = Accept(name, value)
        assert str(accept) == value

    def test_accept_str_with_q_not_1_multiple(self):
        from webob.acceptparse import Accept
        name, value = ('Content-Type', 'text/html;q=0.5, foo/bar')
        accept = Accept(name, value)
        assert str(accept) == value

    def test_accept_add_other_accept(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', 'text/html') + \
                 Accept('Content-Type', 'foo/bar')
        assert str(accept) == 'text/html, foo/bar'
        accept += Accept('Content-Type', 'bar/baz;q=0.5')
        assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

    def test_accept_add_other_list_of_tuples(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', 'text/html')
        accept += [('foo/bar', 1)]
        assert str(accept) == 'text/html, foo/bar'
        accept += [('bar/baz', 0.5)]
        assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'
        accept += ['she/bangs', 'the/house']
        assert str(accept) == ('text/html, foo/bar, bar/baz;q=0.5, '
                               'she/bangs, the/house')

    def test_accept_add_other_dict(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', 'text/html')
        accept += {'foo/bar': 1}
        assert str(accept) == 'text/html, foo/bar'
        accept += {'bar/baz': 0.5}
        assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

    def test_accept_add_other_empty_str(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', 'text/html')
        accept += ''
        assert str(accept) == 'text/html'

    def test_accept_with_no_value_add_other_str(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', '')
        accept += 'text/html'
        assert str(accept) == 'text/html'

    def test_contains(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', 'text/html')
        assert 'text/html' in accept

    def test_contains_not(self):
        from webob.acceptparse import Accept
        accept = Accept('Content-Type', 'text/html')
        assert not 'foo/bar' in accept
