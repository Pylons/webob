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
