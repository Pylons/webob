from webob import Request
from webob.acceptparse import Accept, MIMEAccept, NilAccept, NoAccept, accept_property, parse_accept
from nose.tools import eq_, assert_raises

def test_parse_accept_badq():
    assert parse_accept("value1; q=0.1.2") == [('value1', 1)]

def test_init_accept_content_type():
    name, value = ('Content-Type', 'text/html')
    accept = Accept(name, value)
    assert accept.header_name == name
    assert accept.header_value == value
    assert accept._parsed == [('text/html', 1)]

def test_init_accept_accept_charset():
    name, value = ('Accept-Charset', 'iso-8859-5, unicode-1-1;q=0.8')
    accept = Accept(name, value)
    assert accept.header_name == name
    assert accept.header_value == value
    assert accept._parsed == [('iso-8859-5', 1),
                              ('unicode-1-1', 0.80000000000000004),
                              ('iso-8859-1', 1)]

def test_init_accept_accept_charset_with_iso_8859_1():
    name, value = ('Accept-Charset', 'iso-8859-1')
    accept = Accept(name, value)
    assert accept.header_name == name
    assert accept.header_value == value
    assert accept._parsed == [('iso-8859-1', 1)]

def test_init_accept_accept_charset_wildcard():
    name, value = ('Accept-Charset', '*')
    accept = Accept(name, value)
    assert accept.header_name == name
    assert accept.header_value == value
    assert accept._parsed == [('*', 1)]

def test_init_accept_accept_language():
    name, value = ('Accept-Language', 'da, en-gb;q=0.8, en;q=0.7')
    accept = Accept(name, value)
    assert accept.header_name == name
    assert accept.header_value == value
    assert accept._parsed == [('da', 1),
                              ('en-gb', 0.80000000000000004),
                              ('en', 0.69999999999999996)]

def test_init_accept_invalid_value():
    name, value = ('Accept-Language', 'da, q, en-gb;q=0.8')
    accept = Accept(name, value)
    # The "q" value should not be there.
    assert accept._parsed == [('da', 1),
                              ('en-gb', 0.80000000000000004)]

def test_init_accept_invalid_q_value():
    name, value = ('Accept-Language', 'da, en-gb;q=foo')
    accept = Accept(name, value)
    # I can't get to cover line 40-41 (webob.acceptparse) as the regex
    # will prevent from hitting these lines (aconrad)
    assert accept._parsed == [('da', 1), ('en-gb', 1)]

def test_accept_repr():
    name, value = ('Content-Type', 'text/html')
    accept = Accept(name, value)
    assert repr(accept) == '<%s at 0x%x %s: %s>' % ('Accept',
                                                    abs(id(accept)),
                                                    name,
                                                    str(accept))

def test_accept_str():
    name, value = ('Content-Type', 'text/html')
    accept = Accept(name, value)
    assert str(accept) == value

def test_zero_quality():
    assert Accept('Accept-Encoding', 'bar, *;q=0').best_match(['foo']) is None
    assert 'foo' not in Accept('Accept-Encoding', '*;q=0')
    assert Accept('Accept-Encoding', 'foo, *;q=0').first_match(['bar', 'foo']) == 'foo'


def test_accept_str_with_q_not_1():
    name, value = ('Content-Type', 'text/html;q=0.5')
    accept = Accept(name, value)
    assert str(accept) == value

def test_accept_str_with_q_not_1_multiple():
    name, value = ('Content-Type', 'text/html;q=0.5, foo/bar')
    accept = Accept(name, value)
    assert str(accept) == value

def test_accept_add_other_accept():
    accept = Accept('Content-Type', 'text/html') + \
             Accept('Content-Type', 'foo/bar')
    assert str(accept) == 'text/html, foo/bar'
    accept += Accept('Content-Type', 'bar/baz;q=0.5')
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

def test_accept_add_other_list_of_tuples():
    accept = Accept('Content-Type', 'text/html')
    accept += [('foo/bar', 1)]
    assert str(accept) == 'text/html, foo/bar'
    accept += [('bar/baz', 0.5)]
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'
    accept += ['she/bangs', 'the/house']
    assert str(accept) == ('text/html, foo/bar, bar/baz;q=0.5, '
                           'she/bangs, the/house')

def test_accept_add_other_dict():
    accept = Accept('Content-Type', 'text/html')
    accept += {'foo/bar': 1}
    assert str(accept) == 'text/html, foo/bar'
    accept += {'bar/baz': 0.5}
    assert str(accept) == 'text/html, foo/bar, bar/baz;q=0.5'

def test_accept_add_other_empty_str():
    accept = Accept('Content-Type', 'text/html')
    accept += ''
    assert str(accept) == 'text/html'

def test_accept_with_no_value_add_other_str():
    accept = Accept('Content-Type', '')
    accept += 'text/html'
    assert str(accept) == 'text/html'

def test_contains():
    accept = Accept('Content-Type', 'text/html')
    assert 'text/html' in accept

def test_contains_not():
    accept = Accept('Content-Type', 'text/html')
    assert not 'foo/bar' in accept

def test_quality():
    accept = Accept('Content-Type', 'text/html')
    assert accept.quality('text/html') == 1
    accept = Accept('Content-Type', 'text/html;q=0.5')
    assert accept.quality('text/html') == 0.5

def test_quality_not_found():
    accept = Accept('Content-Type', 'text/html')
    assert accept.quality('foo/bar') is None

def test_first_match():
    accept = Accept('Content-Type', 'text/html, foo/bar')
    assert accept.first_match(['text/html', 'foo/bar']) == 'text/html'
    assert accept.first_match(['foo/bar', 'text/html']) == 'foo/bar'
    assert accept.first_match(['xxx/xxx', 'text/html']) == 'text/html'
    assert accept.first_match(['xxx/xxx']) == 'xxx/xxx'
    assert accept.first_match([None, 'text/html']) is None
    assert accept.first_match(['text/html', None]) == 'text/html'
    assert accept.first_match(['foo/bar', None]) == 'foo/bar'
    assert_raises(ValueError, accept.first_match, [])

def test_best_match():
    accept = Accept('Content-Type', 'text/html, foo/bar')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    assert accept.best_match(['foo/bar', 'text/html']) == 'foo/bar'
    assert accept.best_match([('foo/bar', 0.5),
                              'text/html']) == 'text/html'
    assert accept.best_match([('foo/bar', 0.5),
                              ('text/html', 0.4)]) == 'foo/bar'
    assert_raises(ValueError, accept.best_match, ['text/*'])

def test_best_match_with_one_lower_q():
    accept = Accept('Content-Type', 'text/html, foo/bar;q=0.5')
    assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
    accept = Accept('Content-Type', 'text/html;q=0.5, foo/bar')
    assert accept.best_match(['text/html', 'foo/bar']) == 'foo/bar'

def test_best_matches():
    accept = Accept('Content-Type', 'text/html, foo/bar')
    assert accept.best_matches() == ['text/html', 'foo/bar']
    accept = Accept('Content-Type', 'text/html, foo/bar;q=0.5')
    assert accept.best_matches() == ['text/html', 'foo/bar']
    accept = Accept('Content-Type', 'text/html;q=0.5, foo/bar')
    assert accept.best_matches() == ['foo/bar', 'text/html']

def test_best_matches_with_fallback():
    accept = Accept('Content-Type', 'text/html, foo/bar')
    assert accept.best_matches('xxx/yyy') == ['text/html',
                                              'foo/bar',
                                              'xxx/yyy']
    accept = Accept('Content-Type', 'text/html;q=0.5, foo/bar')
    assert accept.best_matches('xxx/yyy') == ['foo/bar',
                                              'text/html',
                                              'xxx/yyy']
    assert accept.best_matches('foo/bar') == ['foo/bar']
    assert accept.best_matches('text/html') == ['foo/bar', 'text/html']

def test_accept_match():
    accept = Accept('Content-Type', 'text/html')
    #FIXME: Accept._match should be standalone function _match that is
    # attached as Accept._match during Accept.__init__.
    assert accept._match('*', 'text/html')
    assert accept._match('text/html', 'text/html')
    assert accept._match('TEXT/HTML', 'text/html')
    assert not accept._match('foo/bar', 'text/html')

def test_accept_match_lang():
    accept = Accept('Accept-Language', 'da, en-gb;q=0.8, en;q=0.7')
    #FIXME: Accept._match_lang should be standalone function _match_lang
    # that is attached as Accept._match during Accept.__init__.
    assert accept._match('*', 'da')
    assert accept._match('da', 'DA')
    assert accept._match('en', 'en-gb')
    assert accept._match('en-gb', 'en-gb')
    assert not accept._match('en-gb', 'fr-fr')


# NilAccept tests

def test_nil():
    nilaccept = NilAccept('Connection-Close')
    assert nilaccept.header_name == 'Connection-Close'
    eq_(repr(nilaccept),
        "<NilAccept for Connection-Close: <class 'webob.acceptparse.Accept'>>"
    )
    assert not nilaccept
    assert str(nilaccept) == ''
    assert nilaccept.quality('dummy') == 0
    assert nilaccept.best_matches() == []
    assert nilaccept.best_matches('foo') == ['foo']


def test_nil_add():
    nilaccept = NilAccept('Connection-Close')
    accept = Accept('Content-Type', 'text/html')
    assert nilaccept + accept is accept
    new_accept = nilaccept + nilaccept
    assert isinstance(new_accept, accept.__class__)
    assert new_accept.header_name == 'Connection-Close'
    assert new_accept.header_value == ''
    new_accept = nilaccept + 'foo'
    assert isinstance(new_accept, accept.__class__)
    assert new_accept.header_name == 'Connection-Close'
    assert new_accept.header_value == 'foo'

def test_nil_radd():
    nilaccept = NilAccept('Connection-Close')
    accept = Accept('Content-Type', 'text/html')
    assert isinstance('foo' + nilaccept, accept.__class__)
    assert ('foo' + nilaccept).header_value == 'foo'
    # How to test ``if isinstance(item, self.MasterClass): return item``
    # under NilAccept.__radd__ ??

def test_nil_radd_masterclass():
    # Is this "reaching into" __radd__ legit?
    nilaccept = NilAccept('Connection-Close')
    accept = Accept('Content-Type', 'text/html')
    assert nilaccept.__radd__(accept) is accept

def test_nil_contains():
    nilaccept = NilAccept('Connection-Close')
    # NilAccept.__contains__ always returns True
    assert '' in nilaccept
    assert 'dummy' in nilaccept

def test_nil_first_match():
    nilaccept = NilAccept('Connection-Close')
    # NilAccept.first_match always returns element 0 of the list
    assert nilaccept.first_match(['dummy', '']) == 'dummy'
    assert nilaccept.first_match(['', 'dummy']) == ''

def test_nil_best_match():
    nilaccept = NilAccept('Connection-Close')
    assert nilaccept.best_match(['foo', 'bar']) == 'foo'
    assert nilaccept.best_match([('foo', 1), ('bar', 0.5)]) == 'foo'
    assert nilaccept.best_match([('foo', 0.5), ('bar', 1)]) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar']) == 'bar'
    # default_match has no effect on NilAccept class
    assert nilaccept.best_match([('foo', 0.5), 'bar'],
                                default_match=True) == 'bar'
    assert nilaccept.best_match([('foo', 0.5), 'bar'],
                                default_match=False) == 'bar'


# NoAccept tests
def test_noaccept_contains():
    noaccept = NoAccept('Connection-Close')
    # NoAccept.__contains__ always returns False
    assert 'text/plain' not in noaccept


# MIMEAccept tests

def test_mime_init():
    mimeaccept = MIMEAccept('Content-Type', 'image/jpg')
    assert mimeaccept._parsed == [('image/jpg', 1)]
    mimeaccept = MIMEAccept('Content-Type', 'image/png, image/jpg;q=0.5')
    assert mimeaccept._parsed == [('image/png', 1), ('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('Content-Type', 'image, image/jpg;q=0.5')
    assert mimeaccept._parsed == [('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('Content-Type', '*/*')
    assert mimeaccept._parsed == [('*/*', 1)]
    mimeaccept = MIMEAccept('Content-Type', '*/png')
    assert mimeaccept._parsed == []
    mimeaccept = MIMEAccept('Content-Type', 'image/*')
    assert mimeaccept._parsed == [('image/*', 1)]

def test_accept_html():
    mimeaccept = MIMEAccept('Content-Type', 'image/jpg')
    assert not mimeaccept.accept_html()
    mimeaccept = MIMEAccept('Content-Type', 'image/jpg, text/html')
    assert mimeaccept.accept_html()

def test_match():
    mimeaccept = MIMEAccept('Content-Type', 'image/jpg')
    assert mimeaccept._match('image/jpg', 'image/jpg')
    assert mimeaccept._match('image/*', 'image/jpg')
    assert mimeaccept._match('*/*', 'image/jpg')
    assert not mimeaccept._match('text/html', 'image/jpg')
    assert_raises(ValueError, mimeaccept._match, 'image/jpg', '*/*')


# property tests

def test_accept_property_fget():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'val')
    eq_(desc.fget(req).header_value, 'val')

def test_accept_property_fget_nil():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/')
    eq_(type(desc.fget(req)), NilAccept)

def test_accept_property_fset():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'baz')
    eq_(desc.fget(req).header_value, 'baz')

def test_accept_property_fset_acceptclass():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, ['utf-8', 'latin-11'])
    eq_(desc.fget(req).header_value, 'utf-8, latin-11, iso-8859-1')

def test_accept_property_fdel():
    desc = accept_property('Accept-Charset', '14.2')
    req = Request.blank('/', environ={'envkey': 'envval'})
    desc.fset(req, 'val')
    assert desc.fget(req).header_value == 'val'
    desc.fdel(req)
    eq_(type(desc.fget(req)), NilAccept)
