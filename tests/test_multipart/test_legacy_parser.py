# -*- coding: utf-8 -*-
from .utils import BaseParserTest

import unittest
import base64
import os.path, tempfile

from io import BytesIO

from webob import multipart
from webob.multipart import to_bytes

#TODO: bufsize=10, line=1234567890--boundary\n
#TODO: bufsize < len(boundary) (should not be possible)
#TODO: bufsize = len(boundary)+5 (edge case)
#TODO: At least one test per possible exception (100% coverage)


class TestMultipartParser(BaseParserTest):

    def test_copyfile(self):
        source = BytesIO(to_bytes('abc'))
        target = BytesIO()
        self.assertEqual(multipart.copy_file(source, target), 3)
        target.seek(0)
        self.assertEqual(target.read(), to_bytes('abc'))

    def test_big_file(self):
        ''' If the size of an uploaded part exceeds memfile_limit,
            it is written to disk. '''
        test_file = 'abc'*1024
        parser = self.parser(
            '--foo\r\n',
        'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', test_file, '\r\n--foo\r\n',
        'Content-Disposition: form-data; name="file2"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', test_file + 'a', '\r\n--foo\r\n',
        'Content-Disposition: form-data; name="file3"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', test_file*2, '\r\n--foo--',
         memfile_limit=len(test_file))

        self.assertEqual(parser.get('file1').file.read(), to_bytes(test_file))
        self.assertTrue(parser.get('file1').is_buffered())
        self.assertEqual(parser.get('file2').file.read(), to_bytes(test_file + 'a'))
        self.assertFalse(parser.get('file2').is_buffered())
        self.assertEqual(parser.get('file3').file.read(), to_bytes(test_file*2))
        self.assertFalse(parser.get('file3').is_buffered())

    def test_get_all(self):
        ''' Test the get() and get_all() methods. '''
        p = self.parser('--foo\r\n',
        'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', 'abc'*1024, '\r\n--foo\r\n',
        'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', 'def'*1024, '\r\n--foo--')
        self.assertEqual(p.get('file1').file.read(), to_bytes('abc'*1024))
        self.assertEqual(p.get('file2'), None)
        self.assertEqual(len(p.get_all('file1')), 2)
        self.assertEqual(p.get_all('file1')[1].file.read(), to_bytes('def'*1024))
        self.assertEqual(p.get_all('file1'), p.parts())

    def test_file_seek(self):
        ''' The file object should be readable withoud a seek(0). '''
        test_file = 'abc'*1024
        p = self.parser(
            '--foo\r\n',
            'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
            'Content-Type: image/png\r\n',
            '\r\n',
             test_file,
             '\r\n--foo--')
        self.assertEqual(p.get('file1').file.read(), to_bytes(test_file))
        self.assertEqual(p.get('file1').value, test_file)

    def test_unicode_value(self):
        ''' The .value property always returns unicode '''
        test_file = 'abc'*1024
        p = self.parser('--foo\r\n',
        'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', test_file, '\r\n--foo--')
        self.assertEqual(p.get('file1').file.read(), to_bytes(test_file))
        self.assertEqual(p.get('file1').value, test_file)
        self.assertTrue(hasattr(p.get('file1').value, 'encode'))

    def test_save_as(self):
        ''' save_as stores data in a file keeping the file position. '''
        def tmp_file_name():
            # create a temporary file name (on Python 2.6+ NamedTemporaryFile
            # with delete=False could be used)
            fd, fname = tempfile.mkstemp()
            f = os.fdopen(fd)
            f.close()
            return fname
        test_file = 'abc'*1024
        p = self.parser('--foo\r\n',
        'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', test_file, '\r\n--foo--')
        self.assertEqual(p.get('file1').file.read(1024), to_bytes(test_file)[:1024])
        tfn = tmp_file_name()
        p.get('file1').save_as(tfn)
        tf = open(tfn, 'rb')
        self.assertEqual(tf.read(), to_bytes(test_file))
        tf.close()
        self.assertEqual(p.get('file1').file.read(), to_bytes(test_file)[1024:])

    def test_part_header(self):
        ''' HTTP allows headers to be multiline. '''
        p = self.parser('--foo\r\n',
        'Content-Disposition: form-data; name="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', "xxx", '\r\n--foo--')
        part = p.get("file1")
        self.assertEqual(part.file.read(), b"xxx")
        self.assertEqual(part.size, 3)
        self.assertEqual(part.name, "file1")
        self.assertEqual(part.filename, "random.png")
        self.assertEqual(part.charset, "utf8")
        self.assertEqual(part.headerlist, [
            ('Content-Disposition','form-data; name="file1"; filename="random.png"'),
            ('Content-Type','image/png')
        ])
        self.assertEqual(part.headers["CoNtEnT-TyPe"], "image/png")
        self.assertEqual(part.disposition, 'form-data; name="file1"; filename="random.png"')
        self.assertEqual(part.content_type, "image/png")

    def test_multiline_header(self):
        ''' HTTP allows headers to be multiline. '''
        test_file = to_bytes('abc'*1024)
        test_text = u'Test text\n with\r\n ümläuts!'
        p = self.parser('--foo\r\n',
        'Content-Disposition: form-data;\r\n',
        '\tname="file1"; filename="random.png"\r\n',
        'Content-Type: image/png\r\n', '\r\n', test_file, '\r\n--foo\r\n',
        'Content-Disposition: form-data;\r\n',
        ' name="text"\r\n', '\r\n', test_text,
         '\r\n--foo--')
        self.assertEqual(p.get('file1').file.read(), test_file)
        self.assertEqual(p.get('file1').filename, 'random.png')
        self.assertEqual(p.get('text').value, test_text)

    def test_disk_limit(self):
        with self.assertRaises(multipart.MultipartError):
            self.write_field("file1", 'x'*1025, filename="foo.bin")
            self.write_end()
            self.parser(spool_limit=10, disk_limit=1024)

    def test_spool_limit(self):
        self.write_field("file1", 'x'*1024, filename="foo.bin")
        self.write_field("file2", 'x'*1025, filename="foo.bin")
        self.write_end()
        p = self.parser(spool_limit=1024)
        self.assertTrue(p.get("file1").is_buffered())
        self.assertFalse(p.get("file2").is_buffered())

    def test_spool_limit_nocheck_write_func(self):
        self.write_field("file1", 'x'*10240, filename="foo.bin")
        self.write_end()
        p = self.parser(spool_limit=1024, buffer_size=1024)
        # A large upload should trigger the fast _write_nocheck path
        self.assertEqual(p.get("file1")._write, p.get("file1")._write_nocheck)

    def test_memory_limit(self):
        self.write_field("file1", 'x'*1024, filename="foo.bin")
        self.write_end()
        p = self.parser(memory_limit=1024)
        self.assertTrue(p.get("file1").is_buffered())

        self.reset()
        self.write_field("file1", 'x'*1024, filename="foo.bin")
        self.write_field("file2", 'x', filename="foo.bin")
        self.write_end()
        with self.assertMultipartError("Memory limit reached"):
            p = self.parser(memory_limit=1024)

    def test_content_length(self):
        self.write_field("file1", 'x'*1024, filename="foo.bin")
        self.write_end()
        clen = len(self.get_buffer_copy().getvalue())

        # Correct content length
        list(self.parser(content_length=clen))

        # Short content length
        with self.assertMultipartError("Unexpected end of multipart stream"):
            list(self.parser(content_length=clen-1))

        # Large content length (we don't care)
        list(self.parser(content_length=clen+1))
