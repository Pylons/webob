from nose.tools import eq_

from webob.cachecontrol import CacheControl

def test_cache_control_object_max_age_None():
    cc = CacheControl({}, 'a')
    cc.properties['max-age'] = None
    eq_(cc.max_age, -1)

