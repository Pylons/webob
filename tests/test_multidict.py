# -*- coding: utf-8 -*-

import unittest
from nose.tools import raises
from webob import multidict

class MultiDictTestCase(unittest.TestCase):
    klass = multidict.MultiDict
    _list = [('a', u'\xe9'), ('a', 'e'), ('a', 'f'), ('b', 1)]
    data = multidict.MultiDict(_list)
    
    def setUp(self):
        self.d = self._get_instance()

    def _get_instance(self):
        return self.klass(self.data.copy()) 

    def test_len(self):
        assert len(self.d) == 4 

    def test_getone(self):
        assert self.d.getone('b') == 1
        self.assertRaises(KeyError, self.d.getone, 'a')

    def test_getall(self):
        assert self.d.getall('b') == [1]

    def test_dict_of_lists(self):
        assert self.d.dict_of_lists() == {'a': [u'\xe9', u'e', u'f'], 'b': [1]}, self.d.dict_of_lists()

    def test_dict_api(self):
        assert 'a' in self.d.mixed()
        assert 'a' in self.d.keys()
        assert 'a' in self.d.iterkeys()
        assert ('b', 1) in self.d.items()
        assert ('b', 1) in self.d.iteritems()
        assert 1 in self.d.values()
        assert 1 in self.d.itervalues()
        assert len(self.d) == 4 

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
    
    def test_decode_key(self):
        d = self._get_instance()
        d.decode_keys = True
        
        class Key(object):  
            pass

        key = Key()
        self.assertEquals(key, d._decode_key(key))

    def test_decode_value(self):
        import cgi

        d = self._get_instance()
        d.decode_keys = True
        
        fs = cgi.FieldStorage()
        fs.name = 'a'
        self.assertEqual(d._decode_value(fs).name, 'a')

    def test_encode_key(self):
        d = self._get_instance()
        value = unicode('a')
        self.assertEquals(d._encode_value(value),'a')
        
class NestedMultiDictTestCase(MultiDictTestCase):
    klass = multidict.NestedMultiDict

    def test_getitem(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__getitem__, 'z')
    
    def test_contains(self):
        d = self._get_instance()
        self.assertEquals(d.__contains__('a'), True)
        self.assertEquals(d.__contains__('z'), False)

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
        self.assertEqual(d.__nonzero__(), True)
        d.dicts = [{}]
        self.assertEqual(d.__nonzero__(), False)
        assert not d

class TrackableMultiDict(MultiDictTestCase):
    klass = multidict.TrackableMultiDict

    def _get_instance(self):
        def tracker(*args, **kwargs): pass
        return self.klass(self.data.copy(), __tracker=tracker, __name='tracker')

    def test_inititems(self):
        #The first argument passed into the __init__ method
        class Arg:
            def items(self):
                return [('a', u'\xe9'), ('a', 'e'), ('a', 'f'), ('b', 1)] 
         
        d = self._get_instance()
        d._items = None
        d.__init__(Arg())
        self.assertEquals(self.d._items, self._list)

    def test_nullextend(self):
        d = self._get_instance()
        assert d.extend() == None
        d.extend(test = 'a')
        assert d['test'] == 'a'

    def test_listextend(self):
        class Other:
            def items(self):
                return [u'\xe9', u'e', r'f', 1]
        
        other = Other()
        d = self._get_instance()
        d.extend(other)
        
        _list = [u'\xe9', u'e', r'f', 1]
        for v in _list:
            assert v in d._items
         
    def test_dictextend(self):
        class Other:
            def __getitem__(self, item):
                if item is 'a':
                    return 1
                elif item is 'b':
                    return 2
                elif item is 'c':
                    return 3            
    
            def keys(self):
                return ['a', 'b', 'c']
        
        other = Other()
        d = self._get_instance()
        d.extend(other)
        
        _list = [('a', 1), ('b', 2), ('c', 3)]
        for v in _list:
            assert v in d._items

class NoVarsTestCase(unittest.TestCase):
    klass = multidict.NoVars

    def _get_instance(self):
        return self.klass()

    def test_getitem(self):
        d = self._get_instance()
        self.assertRaises(KeyError, d.__getitem__, 'a')
