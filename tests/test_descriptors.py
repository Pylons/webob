# -*- coding: utf-8 -*-

from nose.tools import eq_
from nose.tools import ok_
from nose.tools import assert_raises
from nose.tools import assert_false

from webob import Request


def test_environ_getter_only_key():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey')
    eq_(desc.__doc__, "Gets and sets the 'akey' key in the environment.")
    assert_raises(KeyError, desc.fget, req)
    desc.fset(req, 'bar')
    eq_(req.environ['akey'], 'bar')
    eq_(desc.fdel, None)

def test_environ_getter_default():
    from webob.descriptors import environ_getter
    req = Request.blank('/')
    desc = environ_getter('akey', default='the_default')
    eq_(desc.__doc__, "Gets and sets the 'akey' key in the environment.")
    eq_(desc.fget(req), 'the_default')
    desc.fset(req, 'bar')
    eq_(req.environ['akey'], 'bar')
    desc.fset(req, None)
    ok_('akey' not in req.environ)
    desc.fset(req, 'baz')
    eq_(req.environ['akey'], 'baz')
    desc.fdel(req)
    ok_('akey' not in req.environ)

def test_environ_getter_rfc_section():
    from webob.descriptors import environ_getter
    desc = environ_getter('akey', rfc_section='14.3')
    eq_(desc.__doc__, "Gets and sets the 'akey' key in the environment. For "
        "more information on akey see `section 14.3 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_.")

def test_upath_property():
    from webob.descriptors import upath_property
    req = Request.blank('/')
    desc = upath_property('akey')
    eq_(desc.fget(req), '')
    desc.fset(req, 'avalue')
    eq_(desc.fget(req), 'avalue')

def test_header_getter():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    eq_(desc.__doc__, "Gets and sets and deletes the AHEADER header. For "
        "more information on AHEADER see `section 14.3 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_.")
    eq_(desc.fget(resp), None)
    desc.fset(resp, 'avalue')
    eq_(desc.fget(resp), 'avalue')
    desc.fset(resp, None)
    eq_(desc.fget(resp), None)
    desc.fset(resp, 'avalue2')
    eq_(desc.fget(resp), 'avalue2')
    desc.fdel(resp)
    eq_(desc.fget(resp), None)

def test_header_getter_unicode():
    from webob.descriptors import header_getter
    from webob import Response
    resp = Response('aresp')
    desc = header_getter('AHEADER', '14.3')
    eq_(desc.__doc__, "Gets and sets and deletes the AHEADER header. For "
        "more information on AHEADER see `section 14.3 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.3>`_.")
    eq_(desc.fget(resp), None)
    desc.fset(resp, u'avalue')
    eq_(desc.fget(resp), u'avalue')
    desc.fset(resp, None)
    eq_(desc.fget(resp), None)
    desc.fset(resp, u'avalue2')
    eq_(desc.fget(resp), u'avalue2')
    desc.fdel(resp)
    eq_(desc.fget(resp), None)


def test_converter_not_prop():
    from webob.descriptors import converter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    assert_raises(AssertionError,converter,
        ('CONTENT_LENGTH', None, '14.13'),
        parse_int_safe, serialize_int, 'int')

def test_converter_with_name():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    eq_(desc.__doc__, "Gets and sets the 'CONTENT_LENGTH' key in the "
        "environment. For more information on CONTENT_LENGTH see `section 14.13 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13>`_.  "
        "Converts it using int.")
    eq_(desc.fget(req), 666)
    desc.fset(req, '999')
    eq_(desc.fget(req), 999)

def test_converter_without_name():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int)
    eq_(desc.fget(req), 666)
    desc.fset(req, '999')
    eq_(desc.fget(req), 999)

def test_converter_none_for_wrong_type():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        ## XXX: Should this fail  if the type is wrong?
        environ_getter('CONTENT_LENGTH', 'sixsixsix', '14.13'),
        parse_int_safe, serialize_int, 'int')
    eq_(desc.__doc__, "Gets and sets the 'CONTENT_LENGTH' key in the "
        "environment. For more information on CONTENT_LENGTH see `section 14.13 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13>`_.  "
        "Converts it using int.")
    eq_(desc.fget(req), None)
    desc.fset(req, '999')
    eq_(desc.fget(req), 999)

def test_converter_delete():
    from webob.descriptors import converter
    from webob.descriptors import environ_getter
    from webob.descriptors import parse_int_safe
    from webob.descriptors import serialize_int
    req = Request.blank('/')
    desc = converter(
        ## XXX: Should this fail  if the type is wrong?
        environ_getter('CONTENT_LENGTH', '666', '14.13'),
        parse_int_safe, serialize_int, 'int')
    eq_(desc.__doc__, "Gets and sets the 'CONTENT_LENGTH' key in the "
        "environment. For more information on CONTENT_LENGTH see `section 14.13 "
        "<http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.13>`_.  "
        "Converts it using int.")
    eq_(desc.fget(req), 666)
    assert_raises(KeyError, desc.fdel, req)

def test_list_header():
    from webob.descriptors import list_header
    desc = list_header('CONTENT_LENGTH', '14.13')
    eq_(type(desc), property)

def test_parse_list():
    from webob.descriptors import parse_list
    result = parse_list('avalue')
    eq_(result, ('avalue',))
    result = parse_list('avalue,avalue2')
    eq_(result, ('avalue', 'avalue2'))

def test_parse_list_unicode():
    from webob.descriptors import parse_list
    result = parse_list(u'avalue')
    eq_(result, ('avalue',))
    result = parse_list(u'avalue,avalue2')
    eq_(result, ('avalue', 'avalue2'))

def test_serilize_list():
    from webob.descriptors import serialize_list
    result = serialize_list(('avalue', 'avalue2'))
    eq_(result, 'avalue, avalue2')

def test_serilize_list_unicode():
    from webob.descriptors import serialize_list
    result = serialize_list((u'avalue', u'avalue2'))
    eq_(result, 'avalue, avalue2')
