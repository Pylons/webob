from datetime import date, datetime
from os.path import getmtime
import tempfile
from time import gmtime
import os
import shutil
import string
import sys
import tarfile
import unittest
import zipfile

from nose.tools import eq_

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


def test_dataapp():
    def exec_app(app, *args, **kw):
        req = Request(environ_from_url('/'), *args, **kw)
        resp = req.get_response(app)
        if req.method == 'HEAD':
            resp._app_iter = ()
        return resp

    def _check_foo(r, status, body):
        eq_(r.status_int, status)
        eq_(r.accept_ranges, 'bytes')
        eq_(r.content_type, 'application/octet-stream')
        eq_(r.content_length, 3)
        eq_(r.body, bytes_(body))

    app = static.DataApp(b'foo')
    _check_foo(exec_app(app), 200, 'foo')
    _check_foo(exec_app(app, method='HEAD'), 200, '')
    eq_(exec_app(app, method='POST').status_int, 405)


def test_dataapp_last_modified():
    app = static.DataApp(b'data', last_modified=date(2005,1,1))

    req1 = Request(environ_from_url('/'), if_modified_since=date(2000,1,1))
    resp1 = req1.get_response(app)
    eq_(resp1.status_int, 200)
    eq_(resp1.content_length, 4)

    req2 = Request(environ_from_url('/'), if_modified_since=date(2010,1,1))
    resp2 = req2.get_response(app)
    eq_(resp2.status_int, 304)
    eq_(resp2.content_length, None)
    eq_(resp2.body, b'')

    app.body = b'update'

    resp3 = req1.get_response(app)
    eq_(resp3.status_int, 200)
    eq_(resp3.content_length, 6)
    eq_(resp3.body, b'update')

    resp4 = req2.get_response(app)
    eq_(resp4.status_int, 200)
    eq_(resp4.content_length, 6)
    eq_(resp4.body, b'update')


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
        eq_(resp1.content_type, 'text/x-python')
        eq_(resp1.charset, 'UTF-8')
        eq_(resp1.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        app.update(force=True)
        resp2 = get_response(app)
        eq_(resp2.content_type, 'text/x-python')
        eq_(resp2.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        resp3 = get_response(app, range=(7, 11))
        eq_(resp3.status_int, 206)
        eq_(tuple(resp3.content_range)[:2], (7, 11))
        eq_(resp3.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))
        eq_(resp3.body, b'this')

    def test_unexisting_file(self):
        app = static.FileApp('/tmp/this/doesnt/exist')
        self.assertEqual(404, get_response(app).status_int)

    def test_allowed_methods(self):
        app = static.FileApp(self.tempfile)

        # Alias
        resp = lambda method: get_response(app, method=method)

        self.assertEqual(200, resp(method='GET').status_int)
        self.assertEqual(200, resp(method='HEAD').status_int)
        self.assertEqual(405, resp(method='POST').status_int)
        # Actually any other method is not allowed
        self.assertEqual(405, resp(method='xxx').status_int)

    def test_exception_while_opening_file(self):
        # Mock the built-in ``open()`` function to allow finner control about
        # what we are testing.
        def open_ioerror(*args, **kwargs):
            raise IOError()

        def open_oserror(*args, **kwargs):
            raise OSError()

        app = static.FileApp(self.tempfile)
        old_open = __builtins__['open']

        try:
            __builtins__['open'] = open_ioerror
            self.assertEqual(403, get_response(app).status_int)

            __builtins__['open'] = open_oserror
            self.assertEqual(403, get_response(app).status_int)
        finally:
            __builtins__['open'] = old_open


class TestFileIter(unittest.TestCase):
    def test_empty_file(self):
        fp = tempfile.NamedTemporaryFile()
        fi = static.FileIter(fp)
        self.assertRaises(StopIteration, next, iter(fi))


class TestDirectoryApp(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_empty_directory(self):
        app = static.DirectoryApp(self.test_dir)
        self.assertEqual(404, get_response(app).status_int)
        self.assertEqual(404, get_response(app, '/foo').status_int)

    def test_serve_file(self):
        app = static.DirectoryApp(self.test_dir)
        create_file('abcde', self.test_dir, 'bar')
        self.assertEqual(404, get_response(app).status_int)
        self.assertEqual(404, get_response(app, '/foo').status_int)

        resp = get_response(app, '/bar')
        self.assertEqual(200, resp.status_int)
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
        self.assertEqual(403, get_response(app, '/../bar').status_int)

    def test_file_app_arguments(self):
        app = static.DirectoryApp(self.test_dir, content_type='xxx/yyy')
        create_file('abcde', self.test_dir, 'bar')

        resp = get_response(app, '/bar')
        self.assertEqual(200, resp.status_int)
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
        self.assertRaises(AssertionError, static.DirectoryApp, serve_path)


class TestArchivedFilesApp(unittest.TestCase):
    def setUp(self):
        fp = tempfile.NamedTemporaryFile(delete=False)
        self.archive_name = fp.name
        fp.close()

        # /DIR_ARCHIVE/
        # /DIR_ARCHIVE/foo      <- abcde
        # /DIR_ARCHIVE/bar/
        # /DIR_ARCHIVE/bar/baz  <- fgh
        self.dir_archive = tempfile.mkdtemp()
        create_file('abcde', self.dir_archive, 'foo')

        os.mkdir(os.path.join(self.dir_archive, 'bar'))
        create_file('fgh', self.dir_archive, 'bar', 'baz')

    def tearDown(self):
        os.unlink(self.archive_name)
        shutil.rmtree(self.dir_archive)

    def _create_archive(self, kind):
        # We change the current working directory to add files so that they are
        # not prefixed by the full temporary directory name.
        old_cwd = os.getcwd()
        if kind == 'zip':
            os.chdir(self.dir_archive)
            with zipfile.ZipFile(self.archive_name, 'w') as fp:
                fp.write('foo')
                fp.write('bar')
                fp.write(os.path.join('bar', 'baz'))
        elif kind == 'tar':
            os.chdir(self.dir_archive)
            with tarfile.open(self.archive_name, 'w') as fp:
                # We don't use fp.add('.') because it creates the archive with
                # paths inside, equal to './', './foo', which causes problem  to
                # extract the files after.
                fp.add('foo')
                fp.add('bar') # Add directory recursively
        else:
            assert False, "unsupported archive type %r" % kind

        os.chdir(old_cwd)

    def _test_read_archive_content(self, kind):
        self._create_archive(kind)
        app = static.ArchivedFilesApp(self.archive_name)

        resp1 = get_response(app, '/foo')
        self.assertEqual(200, resp1.status_int)
        self.assertEqual(bytes_('abcde'), resp1.body)

        # Unknow file
        resp2 = get_response(app, '/unknown')
        self.assertEqual(200, resp2.status_int)
        self.assertEqual(bytes_(''), resp2.body)

        # Directory
        resp3 = get_response(app, '/bar')
        self.assertEqual(200, resp3.status_int)
        self.assertEqual(bytes_(''), resp3.body)

        # File in subdirectory
        resp4 = get_response(app, '/bar/baz')
        self.assertEqual(200, resp4.status_int)
        self.assertEqual(bytes_('fgh'), resp4.body)

    def test_zip_archive(self):
        self._test_read_archive_content("zip")

    def test_tar_archive(self):
        self._test_read_archive_content("tar")

    def test_unknown_archive(self):
        self.assertRaises(AssertionError,
                          static.ArchivedFilesApp, self.archive_name)


class TestPkgResourcesApp(unittest.TestCase):

    test_mod = 'webob_static_testmod'

    def setUp(self):
        self.dir_archive = tempfile.mkdtemp()
        mod_dir = os.path.join(self.dir_archive, self.test_mod)
        os.mkdir(mod_dir)
        os.mkdir(os.path.join(mod_dir, 'plop'))

        create_file("", mod_dir, '__init__.py')
        create_file("jpeg file", mod_dir, 'foo.jpg', )
        create_file("text file", mod_dir, 'plop', 'bar.txt')

        sys.path.insert(0, self.dir_archive)

    def tearDown(self):
        sys.path.remove(self.dir_archive)
        # pkg_resources access sys.modules to import the module. Since we change
        # the directory for each test, we need to clear the cached reference or
        # it will always try to load the module from the first directory used.
        sys.modules.pop(self.test_mod)
        shutil.rmtree(self.dir_archive)

    def test_serve_files_from_module(self):
        app = static.PkgResourcesApp(self.test_mod)

        rep = get_response(app, '/foo.jpg')
        self.assertEqual(200, rep.status_int)
        self.assertEqual(bytes_('jpeg file'), rep.body)

        rep = get_response(app, '/plop/bar.txt')
        self.assertEqual(200, rep.status_int)
        self.assertEqual(bytes_('text file'), rep.body)

    def test_serve_missing_file(self):
        app = static.PkgResourcesApp(self.test_mod)
        rep = get_response(app, '/non-existent-file')
        # XXX: this seems wrong, it should return 404
        self.assertEqual(200, rep.status_int)
        self.assertEqual(bytes_(''), rep.body)

    def test_serve_directory(self):
        app = static.PkgResourcesApp(self.test_mod)
        rep = get_response(app, '/plop/')
        # XXX: this seems wrong, it should return 404 or 405
        self.assertEqual(200, rep.status_int)
        self.assertEqual(bytes_(''), rep.body)

    def test_serve_with_prefix(self):
        app = static.PkgResourcesApp(self.test_mod, 'plop')

        rep = get_response(app, '/foo.jpg')
        # XXX: this seems wrong, it should return 404
        self.assertEqual(200, rep.status_int)
        self.assertEqual(bytes_(''), rep.body)

        rep = get_response(app, '/bar.txt')
        self.assertEqual(200, rep.status_int)
        self.assertEqual(bytes_('text file'), rep.body)
