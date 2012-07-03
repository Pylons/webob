from io import BytesIO
from os.path import getmtime
import tempfile
from time import gmtime
import os
import shutil
import unittest

from webob import static
from webob.compat import bytes_
from webob.request import Request, environ_from_url
from webob.response import Response


def get_response(app, path='/', **req_kw):
    """Convenient function to query an application"""
    req = Request(environ_from_url(path), **req_kw)
    return req.get_response(app)


def create_file(content, *paths):
    """Convenient function to create a new file with some content"""
    path = os.path.join(*paths)
    with open(path, 'wb') as fp:
        fp.write(bytes_(content))
    return path


class TestFileApp(unittest.TestCase):
    def setUp(self):
        fp = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
        self.tempfile = fp.name
        fp.write(b"import this\n")
        fp.close()

    def tearDown(self):
        os.unlink(self.tempfile)

    def test_fileapp(self):
        app = static.FileApp(self.tempfile)
        resp1 = get_response(app)
        self.assertEqual(resp1.content_type, 'text/x-python')
        self.assertEqual(resp1.charset, 'UTF-8')
        self.assertEqual(resp1.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        resp2 = get_response(app)
        self.assertEqual(resp2.content_type, 'text/x-python')
        self.assertEqual(resp2.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        resp3 = get_response(app, range=(7, 11))
        self.assertEqual(resp3.status_code, 206)
        self.assertEqual(tuple(resp3.content_range)[:2], (7, 11))
        self.assertEqual(resp3.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))
        self.assertEqual(resp3.body, bytes_('this'))

    def test_unexisting_file(self):
        app = static.FileApp('/tmp/this/doesnt/exist')
        self.assertEqual(404, get_response(app).status_code)

    def test_allowed_methods(self):
        app = static.FileApp(self.tempfile)

        # Alias
        resp = lambda method: get_response(app, method=method)

        self.assertEqual(200, resp(method='GET').status_code)
        self.assertEqual(200, resp(method='HEAD').status_code)
        self.assertEqual(405, resp(method='POST').status_code)
        # Actually any other method is not allowed
        self.assertEqual(405, resp(method='xxx').status_code)

    def test_exception_while_opening_file(self):
        # Mock the built-in ``open()`` function to allow finner control about
        # what we are testing.
        def open_ioerror(*args, **kwargs):
            raise IOError()

        def open_oserror(*args, **kwargs):
            raise OSError()

        app = static.FileApp(self.tempfile)

        app._open = open_ioerror
        self.assertEqual(403, get_response(app).status_code)

        app._open = open_oserror
        self.assertEqual(403, get_response(app).status_code)

    def test_use_wsgi_filewrapper(self):
        class TestWrapper(object):
            def __init__(self, file, block_size):
                self.file = file
                self.block_size = block_size

        environ = environ_from_url('/')
        environ['wsgi.file_wrapper'] = TestWrapper
        app = static.FileApp(self.tempfile)
        app_iter = Request(environ).get_response(app).app_iter

        self.assertTrue(isinstance(app_iter, TestWrapper))
        self.assertEqual(bytes_('import this\n'), app_iter.file.read())
        self.assertEqual(static.BLOCK_SIZE, app_iter.block_size)


class TestFileIter(unittest.TestCase):
    def test_empty_file(self):
        fp = BytesIO()
        fi = static.FileIter(fp)
        self.assertRaises(StopIteration, next, iter(fi))

    def test_seek(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(seek=4)

        self.assertEqual(bytes_("456789"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_limit(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=4)

        self.assertEqual(bytes_("0123"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_limit_and_seek(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=4, seek=1)

        self.assertEqual(bytes_("123"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_multiple_reads(self):
        fp = BytesIO(bytes_("012"))
        i = static.FileIter(fp).app_iter_range(block_size=1)

        self.assertEqual(bytes_("0"), next(i))
        self.assertEqual(bytes_("1"), next(i))
        self.assertEqual(bytes_("2"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_seek_bigger_than_limit(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=1, seek=2)

        # XXX: this should not return anything actually, since we are starting
        # to read after the place we wanted to stop.
        self.assertEqual(bytes_("23456789"), next(i))
        self.assertRaises(StopIteration, next, i)

    def test_limit_is_zero(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=0)

        self.assertRaises(StopIteration, next, i)



class TestDirectoryApp(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_empty_directory(self):
        app = static.DirectoryApp(self.test_dir)
        self.assertEqual(404, get_response(app).status_code)
        self.assertEqual(404, get_response(app, '/foo').status_code)

    def test_serve_file(self):
        app = static.DirectoryApp(self.test_dir)
        create_file('abcde', self.test_dir, 'bar')
        self.assertEqual(404, get_response(app).status_code)
        self.assertEqual(404, get_response(app, '/foo').status_code)

        resp = get_response(app, '/bar')
        self.assertEqual(200, resp.status_code)
        self.assertEqual(bytes_('abcde'), resp.body)

    def test_dont_serve_file_in_parent_directory(self):
        # We'll have:
        #   /TEST_DIR/
        #   /TEST_DIR/bar
        #   /TEST_DIR/foo/   <- serve this directory
        create_file('abcde', self.test_dir, 'bar')
        serve_path = os.path.join(self.test_dir, 'foo')
        os.mkdir(serve_path)
        app = static.DirectoryApp(serve_path)

        # The file exists, but is outside the served dir.
        self.assertEqual(403, get_response(app, '/../bar').status_code)

    def test_file_app_arguments(self):
        app = static.DirectoryApp(self.test_dir, content_type='xxx/yyy')
        create_file('abcde', self.test_dir, 'bar')

        resp = get_response(app, '/bar')
        self.assertEqual(200, resp.status_code)
        self.assertEqual('xxx/yyy', resp.content_type)

    def test_file_app_factory(self):
        def make_fileapp(*args, **kwargs):
            make_fileapp.called = True
            return Response()
        make_fileapp.called = False

        app = static.DirectoryApp(self.test_dir)
        app.make_fileapp = make_fileapp
        create_file('abcde', self.test_dir, 'bar')

        get_response(app, '/bar')
        self.assertTrue(make_fileapp.called)

    def test_must_serve_directory(self):
        serve_path = create_file('abcde', self.test_dir, 'bar')
        self.assertRaises(IOError, static.DirectoryApp, serve_path)

    def test_index_page(self):
        os.mkdir(os.path.join(self.test_dir, 'index-test'))
        create_file(bytes_('index'), self.test_dir, 'index-test', 'index.html')
        app = static.DirectoryApp(self.test_dir)
        resp = get_response(app, '/index-test')
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.location.endswith('/index-test/'))
        resp = get_response(app, '/index-test?test')
        self.assertTrue(resp.location.endswith('/index-test/?test'))
        resp = get_response(app, '/index-test/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, bytes_('index'))
        self.assertEqual(resp.content_type, 'text/html')
        resp = get_response(app, '/index-test/index.html')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.body, bytes_('index'))
        redir_app = static.DirectoryApp(self.test_dir, hide_index_with_redirect=True)
        resp = get_response(redir_app, '/index-test/index.html')
        self.assertEqual(resp.status_code, 301)
        self.assertTrue(resp.location.endswith('/index-test/'))
        resp = get_response(redir_app, '/index-test/index.html?test')
        self.assertTrue(resp.location.endswith('/index-test/?test'))
        page_app = static.DirectoryApp(self.test_dir, index_page='something-else.html')
        self.assertEqual(get_response(page_app, '/index-test/').status_code, 404)
