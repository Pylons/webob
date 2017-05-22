import unittest
from io import BytesIO

import pytest
import sys

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

class Test_cgi_FieldStorage_Py3_tests(object):

    def test_fieldstorage_not_multipart(self):
        from webob.compat import cgi_FieldStorage

        POSTDATA = b'{"name": "Bert"}'

        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'text/plain',
            'CONTENT_LENGTH': str(len(POSTDATA))
        }
        fp = BytesIO(POSTDATA)
        fs = cgi_FieldStorage(fp, environ=env)
        assert fs.list is None
        assert fs.value == b'{"name": "Bert"}'

    @pytest.mark.skipif(
        sys.version_info < (3, 0),
        reason="FieldStorage on Python 2.7 is broken, see "
               "https://github.com/Pylons/webob/issues/293"
    )
    def test_fieldstorage_part_content_length(self):
        from webob.compat import cgi_FieldStorage
        BOUNDARY = "JfISa01"
        POSTDATA = """--JfISa01
Content-Disposition: form-data; name="submit-name"
Content-Length: 5

Larry
--JfISa01"""
        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'multipart/form-data; boundary={}'.format(BOUNDARY),
            'CONTENT_LENGTH': str(len(POSTDATA))}
        fp = BytesIO(POSTDATA.encode('latin-1'))
        fs = cgi_FieldStorage(fp, environ=env)
        assert len(fs.list) == 1
        assert fs.list[0].name == 'submit-name'
        assert fs.list[0].value == 'Larry'
    
    def test_my_fieldstorage_part_content_length(self):
        from webob.compat import cgi_FieldStorage
        BOUNDARY = "4ddfd368-cb07-4b9e-b003-876010298a6c"
        POSTDATA = """--4ddfd368-cb07-4b9e-b003-876010298a6c
Content-Disposition: form-data; name="object"; filename="file.txt"
Content-Type: text/plain
Content-Length: 5
Content-Transfer-Encoding: 7bit

ADMIN
--4ddfd368-cb07-4b9e-b003-876010298a6c
Content-Disposition: form-data; name="sign_date"
Content-Type: application/json; charset=UTF-8
Content-Length: 22
Content-Transfer-Encoding: 7bit

"2016-11-23T12:22:41Z"
--4ddfd368-cb07-4b9e-b003-876010298a6c
Content-Disposition: form-data; name="staffId"
Content-Type: text/plain; charset=UTF-8
Content-Length: 5
Content-Transfer-Encoding: 7bit

ADMIN
--4ddfd368-cb07-4b9e-b003-876010298a6c--"""
        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'multipart/form-data; boundary={}'.format(BOUNDARY),
            'CONTENT_LENGTH': str(len(POSTDATA))}
        fp = BytesIO(POSTDATA.encode('latin-1'))
        fs = cgi_FieldStorage(fp, environ=env)
        assert len(fs.list) == 3
        expect = [{'name':'object', 'filename':'file.txt', 'value':b'ADMIN'},
                  {'name':'sign_date', 'filename':None, 'value':'"2016-11-23T12:22:41Z"'},
                  {'name':'staffId', 'filename':None, 'value':'ADMIN'}]
        for x in range(len(fs.list)):
            for k, exp in expect[x].items():
                got = getattr(fs.list[x], k)
                assert got == exp

    def test_fieldstorage_multipart_leading_whitespace(self):
        from webob.compat import cgi_FieldStorage

        BOUNDARY = "---------------------------721837373350705526688164684"
        POSTDATA = """-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="id"

1234
-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="title"


-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="file"; filename="test.txt"
Content-Type: text/plain

Testing 123.

-----------------------------721837373350705526688164684
Content-Disposition: form-data; name="submit"

 Add\x20
-----------------------------721837373350705526688164684--
"""

        env = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'multipart/form-data; boundary={}'.format(BOUNDARY),
            'CONTENT_LENGTH': '560'}
        # Add some leading whitespace to our post data that will cause the
        # first line to not be the innerboundary.
        fp = BytesIO(b"\r\n" + POSTDATA.encode('latin-1'))
        fs = cgi_FieldStorage(fp, environ=env)
        assert len(fs.list) == 4
        expect = [{'name':'id', 'filename':None, 'value':'1234'},
                  {'name':'title', 'filename':None, 'value':''},
                  {'name':'file', 'filename':'test.txt', 'value':b'Testing 123.\n'},
                  {'name':'submit', 'filename':None, 'value':' Add '}]
        for x in range(len(fs.list)):
            for k, exp in expect[x].items():
                got = getattr(fs.list[x], k)
                assert got == exp
