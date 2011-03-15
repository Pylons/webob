from nose.tools import eq_
from nose.tools import raises
import unittest


def test_cache_control_object_max_age_None():
    from webob.cachecontrol import CacheControl
    cc = CacheControl({}, 'a')
    cc.properties['max-age'] = None
    eq_(cc.max_age, -1)


class TestUpdateDict(unittest.TestCase):

    def setUp(self):
        self.call_queue = []
        def callback(args):
            self.call_queue.append("Called with: %s" % repr(args))
        self.callback = callback

    def make_one(self, callback):
        from webob.cachecontrol import UpdateDict
        ud = UpdateDict()
        ud.updated = callback
        return ud
    
    def test_set_delete(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        assert len(self.call_queue) == 1
        assert self.call_queue[-1] == "Called with: {'first': 1}"        

        del newone['first'] 
        assert len(self.call_queue) == 2
        assert self.call_queue[-1] == 'Called with: {}'                

    def test_setdefault(self):
        newone = self.make_one(self.callback)
        assert newone.setdefault('haters', 'gonna-hate') == 'gonna-hate'
        assert len(self.call_queue) == 1
        assert self.call_queue[-1] == "Called with: {'haters': 'gonna-hate'}", self.call_queue[-1]

        # no effect if failobj is not set
        assert newone.setdefault('haters', 'gonna-love') == 'gonna-hate'
        assert len(self.call_queue) == 1

    def test_pop(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        newone.pop('first')
        assert len(self.call_queue) == 2
        assert self.call_queue[-1] == 'Called with: {}', self.call_queue[-1]                

    def test_popitem(self):
        newone = self.make_one(self.callback)
        newone['first'] = 1
        assert newone.popitem() == ('first', 1)
        assert len(self.call_queue) == 2
        assert self.call_queue[-1] == 'Called with: {}', self.call_queue[-1]                

    def test_callback_args(self):
        assert True
        #assert False


class TestExistProp(unittest.TestCase):
    """
    Test webob.cachecontrol.exists_property
    """
    
    def setUp(self):
        pass

    def make_one(self):
        from webob.cachecontrol import exists_property

        class Dummy(object):
            properties = dict(prop=1)
            type = 'dummy'
            prop = exists_property('prop', 'dummy')
            badprop = exists_property('badprop', 'big_dummy')
            
        return Dummy

    def test_get_on_class(self):
        from webob.cachecontrol import exists_property
        Dummy = self.make_one()
        assert isinstance(Dummy.prop, exists_property), Dummy.prop

    def test_get_on_instance(self):
        obj = self.make_one()()
        assert obj.prop is True

    @raises(AttributeError)
    def test_type_mismatch_raise(self):
        obj = self.make_one()()
        obj.badprop = True

    def test_set_w_value(self):
        obj = self.make_one()()
        obj.prop = True
        assert obj.prop is True
        assert obj.properties['prop'] is None
