# -*- coding: utf-8 -*-
from .utils import BaseParserTest

from webob import multipart

class TestFormParser(BaseParserTest):

    def test_multipart(self):
       self.write_field("file1", "abc", filename="random.png", content_type="image/png")
       self.write_field("text1", "abc",)
       self.write_end()
       forms, files = self.parse_form_data()

       self.assertEqual(forms['text1'], 'abc')
       self.assertEqual(files['file1'].file.read(), b'abc')
       self.assertEqual(files['file1'].filename, 'random.png')
       self.assertEqual(files['file1'].name, 'file1')
       self.assertEqual(files['file1'].content_type, 'image/png')

    def test_empty(self):
        self.write_end()
        forms, files = self.parse_form_data()
        self.assertEqual(0, len(forms))
        self.assertEqual(0, len(files))

    def test_urlencoded(self):
        for ctype in ('application/x-www-form-urlencoded', 'application/x-url-encoded'):
            self.reset().write('a=b&c=d')
            self.environ['CONTENT_TYPE'] = ctype
            forms, files = self.parse_form_data()
            self.assertEqual(forms['a'], 'b')
            self.assertEqual(forms['c'], 'd')

    def test_urlencoded_latin1(self):
        for ctype in ('application/x-www-form-urlencoded', 'application/x-url-encoded'):
            self.reset().write(b'a=\xe0\xe1&e=%E8%E9')
            self.environ['CONTENT_TYPE'] = ctype
            forms, files = self.parse_form_data(charset='iso-8859-1')
            self.assertEqual(forms['a'], 'àá')
            self.assertEqual(forms['e'], 'èé')

    def test_urlencoded_utf8(self):
        for ctype in ('application/x-www-form-urlencoded', 'application/x-url-encoded'):
            self.reset().write(b'a=\xc6\x80\xe2\x99\xad&e=%E1%B8%9F%E2%99%AE')
            self.environ['CONTENT_TYPE'] = ctype
            forms, files = self.parse_form_data()
            self.assertEqual(forms['a'], 'ƀ♭')
            self.assertEqual(forms['e'], 'ḟ♮')

    def test_empty(self):
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)

    def test_wrong_method(self):
        self.environ['REQUEST_METHOD'] = 'GET'
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)

    def test_missing_content_type(self):
        self.environ['CONTENT_TYPE'] = None
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)

    def test_unsupported_content_type(self):
        self.environ['CONTENT_TYPE'] = 'multipart/fantasy'
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)

    def test_missing_boundary(self):
        self.environ['CONTENT_TYPE'] = 'multipart/form-data'
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)

    def test_invalid_content_length(self):
        self.environ['CONTENT_LENGTH'] = ''
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)
        self.environ['CONTENT_LENGTH'] = 'notanumber'
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)
    
    def test_invalid_environ(self):
        self.environ['wsgi.input'] = None
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(strict=True)

    def test_big_urlencoded_detect_early(self):
        self.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        self.environ['CONTENT_LENGTH'] = 1024+1
        self.write('a=b')
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(mem_limit=1024, strict=True)

    def test_big_urlencoded_detect_late(self):
        self.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        self.write('a='+'b'*1024)
        with self.assertRaises(multipart.MultipartError):
            self.parse_form_data(mem_limit=1024, strict=True)

    def test_content_length(self):
        self.write('a=b&c=ddd')
        self.environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        self.environ['CONTENT_LENGTH'] = '7'

        # Obey Content-Length, do not overread
        forms, files = self.parse_form_data()
        self.assertEqual(forms["c"], "d")

        # Detect short inputs
        with self.assertMultipartError("Unexpected end of data stream"):
            self.environ['CONTENT_LENGTH'] = '10'
            self.parse_form_data(strict=True)

    def test_close_on_error(self):
        self.write_field("file1", 'x'*1024, filename="foo.bin")
        self.write_field("file2", 'x'*1025, filename="foo.bin")
        # self.write_end() <-- bad multipart
        # In case of an error, all parts parsed up until then should be closed
        # Can't really be tested here, but will show up in coverace
        with self.assertMultipartError("Unexpected end of multipart stream"):
            self.parse_form_data(strict=True)
