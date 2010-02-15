# -*- coding: utf-8 -*-

import unittest
from webob import multidict

class MultiDictTestCase(unittest.TestCase):
    klass = multidict.MultiDict
    data = multidict.MultiDict([('a', u'\xe9'), ('a', 'e'), ('b', 1)])

    def setUp(self):
        self.d =  self._get_instance()

    def _get_instance(self):
        return self.klass(self.data.copy())

    def test_len(self):
        assert len(self.d) == 3

    def test_getone(self):
        assert self.d.getone('b') == 1
        self.assertRaises(KeyError, self.d.getone, 'a')

    def test_getall(self):
        assert self.d.getall('b') == [1]

    def test_dict_of_lists(self):
        assert self.d.dict_of_lists() == {'a': [u'\xe9', u'e'], 'b': [1]}, self.d.dict_of_lists()

    def test_dict_api(self):
        assert 'a' in self.d.mixed()
        assert 'a' in self.d.keys()
        assert 'a' in self.d.iterkeys()
        assert ('b', 1) in self.d.items()
        assert ('b', 1) in self.d.iteritems()
        assert 1 in self.d.values()
        assert 1 in self.d.itervalues()
        assert len(self.d) == 3

    def test_set_del_item(self):
        d = self._get_instance()
        assert 'a' in d
        del d['a']
        assert 'a' not in d
        d['a'] = 1

    def test_pop(self):
        d = self._get_instance()
        d['a'] = 1
        assert d.pop('a') == 1
        assert d.pop('x', 1) == 1
        assert d.popitem() == ('b', 1)

    def test_update(self):
        d = self._get_instance()
        d.update(e=1)
        assert 'e' in d
        d.update(dict(x=1))
        assert 'x' in d
        d.update([('y', 1)])
        assert 'y' in d

    def test_setdefault(self):
        d = self._get_instance()
        d.setdefault('a', 1)
        assert d['a'] != 1
        d.setdefault('e', 1)
        assert 'e' in d

    def test_add(self):
        d = self._get_instance()
        d.add('b', 3)
        assert d.getall('b') == [1, 3]

    def test_copy(self):
        assert self.d.copy() is not self.d
        if hasattr(self.d, 'multi'):
            assert self.d.copy().multi is not self.d.multi
            assert self.d.copy() is not self.d.multi

    def test_clear(self):
        d = self._get_instance()
        d.clear()
        assert len(d) == 0

    def test_nonzero(self):
        d = self._get_instance()
        assert d
        d.clear()
        assert not d


class UnicodeMultiDictTestCase(MultiDictTestCase):
    klass = multidict.UnicodeMultiDict

class NestedMultiDictTestCase(MultiDictTestCase):
    klass = multidict.NestedMultiDict

    def test_add(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.add, 'b', 3)

    def test_set_del_item(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__delitem__, 'a')
        self.assertRaises(KeyError, d.__setitem__, 'a', 1)

    def test_update(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.update, e=1)
        self.assertRaises(KeyError, d.update, dict(x=1))
        self.assertRaises(KeyError, d.update, [('y', 1)])

    def test_setdefault(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.setdefault, 'a', 1)

    def test_pop(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.pop, 'a')
        self.assertRaises(KeyError, d.pop, 'a', 1)

    def test_clear(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.clear)

    def test_nonzero(self):
        d = self._get_instance()
        assert d

class TrackableMultiDict(MultiDictTestCase):
    klass = multidict.TrackableMultiDict

    def _get_instance(self):
        def tracker(*args, **kwargs): pass
        return self.klass(self.data.copy(), __tracker=tracker, __name='tracker')
