import os
import shutil
import tempfile
import unittest
from io import BytesIO
from os.path import getmtime
from time import gmtime

from webob import static
from webob.request import Request, environ_from_url
from webob.response import Response
from webob.util import bytes_


def get_response(app, path="/", **req_kw):
    """Convenient function to query an application"""
    req = Request(environ_from_url(path), **req_kw)

    return req.get_response(app)


def create_file(content, *paths):
    """Convenient function to create a new file with some content"""
    path = os.path.join(*paths)
    with open(path, "wb") as fp:
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
        assert resp1.content_type in ("text/x-python", "text/plain")
        assert resp1.charset == "UTF-8"
        assert resp1.last_modified.timetuple() == gmtime(getmtime(self.tempfile))
        assert resp1.body == b"import this\n"

        resp2 = get_response(app)
        assert resp2.content_type in ("text/x-python", "text/plain")
        assert resp2.last_modified.timetuple() == gmtime(getmtime(self.tempfile))
        assert resp2.body == b"import this\n"

        resp3 = get_response(app, range=(7, 11))
        assert resp3.status_code == 206
        assert tuple(resp3.content_range)[:2] == (7, 11)
        assert resp3.last_modified.timetuple() == gmtime(getmtime(self.tempfile))
        assert resp3.body == bytes_("this")

    def test_unexisting_file(self):
        app = static.FileApp("/tmp/this/doesnt/exist")
        assert get_response(app).status_code == 404

    def test_allowed_methods(self):
        app = static.FileApp(self.tempfile)

        # Alias
        def resp(method):
            return get_response(app, method=method)

        assert resp(method="GET").status_code == 200
        assert resp(method="HEAD").status_code == 200
        assert resp(method="POST").status_code == 405
        # Actually any other method is not allowed
        assert resp(method="xxx").status_code == 405

    def test_exception_while_opening_file(self):
        # Mock the built-in ``open()`` function to allow finner control about
        # what we are testing.
        def open_ioerror(*args, **kwargs):
            raise OSError

        def open_oserror(*args, **kwargs):
            raise OSError

        app = static.FileApp(self.tempfile)

        app._open = open_ioerror
        assert get_response(app).status_code == 403

        app._open = open_oserror
        assert get_response(app).status_code == 403

    def test_use_wsgi_filewrapper(self):
        class TestWrapper:
            __slots__ = ("file", "block_size")

            def __init__(self, file, block_size):
                self.file = file
                self.block_size = block_size

        environ = environ_from_url("/")
        environ["wsgi.file_wrapper"] = TestWrapper
        app = static.FileApp(self.tempfile)
        app_iter = Request(environ).get_response(app).app_iter

        assert isinstance(app_iter, TestWrapper)
        assert bytes_("import this\n") == app_iter.file.read()
        assert app_iter.block_size == static.BLOCK_SIZE


class TestFileIter(unittest.TestCase):
    def test_empty_file(self):
        fp = BytesIO()
        fi = static.FileIter(fp)
        self.assertRaises(StopIteration, next, iter(fi))

    def test_seek(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(seek=4)

        assert bytes_("456789") == next(i)
        self.assertRaises(StopIteration, next, i)

    def test_limit(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=4)

        assert bytes_("0123") == next(i)
        self.assertRaises(StopIteration, next, i)

    def test_limit_and_seek(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=4, seek=1)

        assert bytes_("123") == next(i)
        self.assertRaises(StopIteration, next, i)

    def test_multiple_reads(self):
        fp = BytesIO(bytes_("012"))
        i = static.FileIter(fp).app_iter_range(block_size=1)

        assert bytes_("0") == next(i)
        assert bytes_("1") == next(i)
        assert bytes_("2") == next(i)
        self.assertRaises(StopIteration, next, i)

    def test_seek_bigger_than_limit(self):
        fp = BytesIO(bytes_("0123456789"))
        i = static.FileIter(fp).app_iter_range(limit=1, seek=2)

        # XXX: this should not return anything actually, since we are starting
        # to read after the place we wanted to stop.
        assert bytes_("23456789") == next(i)
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
        assert get_response(app).status_code == 404
        assert get_response(app, "/foo").status_code == 404

    def test_serve_file(self):
        app = static.DirectoryApp(self.test_dir)
        create_file("abcde", self.test_dir, "bar")
        assert get_response(app).status_code == 404
        assert get_response(app, "/foo").status_code == 404

        resp = get_response(app, "/bar")
        assert resp.status_code == 200
        assert bytes_("abcde") == resp.body

    def test_dont_serve_file_in_parent_directory(self):
        # We'll have:
        #   /TEST_DIR/
        #   /TEST_DIR/bar
        #   /TEST_DIR/foo/   <- serve this directory
        create_file("abcde", self.test_dir, "bar")
        serve_path = os.path.join(self.test_dir, "foo")
        os.mkdir(serve_path)
        app = static.DirectoryApp(serve_path)

        # The file exists, but is outside the served dir.
        assert get_response(app, "/../bar").status_code == 403

    def test_dont_leak_parent_directory_file_existance(self):
        # We'll have:
        #   /TEST_DIR/
        #   /TEST_DIR/foo/   <- serve this directory
        serve_path = os.path.join(self.test_dir, "foo")
        os.mkdir(serve_path)
        app = static.DirectoryApp(serve_path)

        # The file exists, but is outside the served dir.
        assert get_response(app, "/../bar2").status_code == 403

    def test_file_app_arguments(self):
        app = static.DirectoryApp(self.test_dir, content_type="xxx/yyy")
        create_file("abcde", self.test_dir, "bar")

        resp = get_response(app, "/bar")
        assert resp.status_code == 200
        assert resp.content_type == "xxx/yyy"

    def test_file_app_factory(self):
        def make_fileapp(*args, **kwargs):
            make_fileapp.called = True

            return Response()

        make_fileapp.called = False

        app = static.DirectoryApp(self.test_dir)
        app.make_fileapp = make_fileapp
        create_file("abcde", self.test_dir, "bar")

        get_response(app, "/bar")
        assert make_fileapp.called

    def test_must_serve_directory(self):
        serve_path = create_file("abcde", self.test_dir, "bar")
        self.assertRaises(IOError, static.DirectoryApp, serve_path)

    def test_index_page(self):
        os.mkdir(os.path.join(self.test_dir, "index-test"))
        create_file(bytes_("index"), self.test_dir, "index-test", "index.html")
        app = static.DirectoryApp(self.test_dir)
        resp = get_response(app, "/index-test")
        assert resp.status_code == 301
        assert resp.location.endswith("/index-test/")
        resp = get_response(app, "/index-test?test")
        assert resp.location.endswith("/index-test/?test")
        resp = get_response(app, "/index-test/")
        assert resp.status_code == 200
        assert resp.body == bytes_("index")
        assert resp.content_type == "text/html"
        resp = get_response(app, "/index-test/index.html")
        assert resp.status_code == 200
        assert resp.body == bytes_("index")
        redir_app = static.DirectoryApp(self.test_dir, hide_index_with_redirect=True)
        resp = get_response(redir_app, "/index-test/index.html")
        assert resp.status_code == 301
        assert resp.location.endswith("/index-test/")
        resp = get_response(redir_app, "/index-test/index.html?test")
        assert resp.location.endswith("/index-test/?test")
        page_app = static.DirectoryApp(self.test_dir, index_page="something-else.html")
        assert get_response(page_app, "/index-test/").status_code == 404
