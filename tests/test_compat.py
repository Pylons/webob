import unittest

from webob.compat import text_type

class text_Tests(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from webob.compat import text_
        return text_(*arg, **kw)

    def test_binary(self):
        result = self._callFUT(b'123')
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, text_type(b'123', 'ascii'))

    def test_binary_alternate_decoding(self):
        result = self._callFUT(b'La Pe\xc3\xb1a', 'utf-8')
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, text_type(b'La Pe\xc3\xb1a', 'utf-8'))

    def test_binary_decoding_error(self):
        self.assertRaises(UnicodeDecodeError, self._callFUT, b'\xff', 'utf-8')

    def test_text(self):
        result = self._callFUT(text_type(b'123', 'ascii'))
        self.assertTrue(isinstance(result, text_type))
        self.assertEqual(result, text_type(b'123', 'ascii'))

class bytes_Tests(unittest.TestCase):
    def _callFUT(self, *arg, **kw):
        from webob.compat import bytes_
        return bytes_(*arg, **kw)

    def test_binary(self):
        result = self._callFUT(b'123')
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, b'123')

    def test_text(self):
        val = text_type(b'123', 'ascii')
        result = self._callFUT(val)
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, b'123')

    def test_text_alternate_encoding(self):
        val = text_type(b'La Pe\xc3\xb1a', 'utf-8')
        result = self._callFUT(val, 'utf-8')
        self.assertTrue(isinstance(result, bytes))
        self.assertEqual(result, b'La Pe\xc3\xb1a')

