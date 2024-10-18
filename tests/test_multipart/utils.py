from contextlib import contextmanager
import unittest

from io import BytesIO

from webob import multipart
from webob.multipart import to_bytes

class BaseParserTest(unittest.TestCase):
    def setUp(self):
        self.data = BytesIO()
        self.boundary = 'foo'
        self.environ = {
            'REQUEST_METHOD':'POST',
            'CONTENT_TYPE':'multipart/form-data; boundary=%s' % self.boundary
        }
        self.to_close = []

    def tearDown(self):
        for part in self.to_close:
            if hasattr(part, 'close'):
                part.close()

    def reset(self):
        self.data.seek(0)
        self.data.truncate()
        return self

    def write(self, *chunks):
        for chunk in chunks:
            self.data.write(to_bytes(chunk))
        return self
    
    def write_boundary(self):
        if self.data.tell() > 0:
            self.write(b'\r\n')
        self.write(b'--', to_bytes(self.boundary), b'\r\n')

    def write_end(self, force=False):
        end = b'--' + to_bytes(self.boundary) + b'--'
        if not force and self.data.getvalue().endswith(end):
            return
        if self.data.tell() > 0:
            self.write(b'\r\n')
        self.write(end)

    def write_header(self, header, value, **opts):
        line = to_bytes(header) + b': ' + to_bytes(value)
        for opt, val in opts.items():
            if val is not None:
                line += b"; " + to_bytes(opt) + b'=' + to_bytes(multipart.header_quote(val))
        self.write(line + b'\r\n')

    def write_field(self, name, data, filename=None, content_type=None):
        self.write_boundary()
        self.write_header("Content-Disposition", "form-data", name=name, filename=filename)
        if content_type:
            self.write_header("Content-Type", content_type)
        self.write(b"\r\n")
        self.write(data)

    def get_buffer_copy(self):
        return BytesIO(self.data.getvalue())

    def parser(self, *lines, **kwargs):
        if lines:
            self.reset()
            self.write(*lines)
        self.data.seek(0)

        kwargs.setdefault("boundary", self.boundary)
        p = multipart.MultipartParser(self.data, **kwargs)
        for part in p:
            self.to_close.append(part)
        return p

    def parse_form_data(self, *lines, **kwargs):
        if lines:
            self.reset()
            self.write(*lines)

        environ = kwargs.setdefault('environ', self.environ.copy())
        environ.setdefault('wsgi.input', self.get_buffer_copy())
        for key, value in list(environ.items()):
            if value is None:
                del environ[key]

        forms, files = multipart.parse_form_data(**kwargs)
        self.to_close.extend(part for _, part in files.iterallitems())
        return forms, files

    def assertParserFails(self, *a, **ka):
        self.assertRaises(multipart.MultipartError, self.parser, *a, **ka)

    @contextmanager
    def assertMultipartError(self, message: str = None):
        with self.assertRaises(multipart.MultipartError) as ex:
            yield
        if message:
            self.assertIn(message, str(ex.exception))
