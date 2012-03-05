from datetime import date, datetime
from os.path import getmtime
import tempfile
from time import gmtime
import os
import shutil
import string
import tarfile
import unittest
import zipfile

from nose.tools import eq_

from webob import static
from webob.compat import bytes_
from webob.request import Request, environ_from_url
from webob.response import Response


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

    def _get_response(self, app, **kw):
        return Request(environ_from_url('/'), **kw).\
                get_response(app)

    def test_fileapp(self):
        app = static.FileApp(self.tempfile)
        resp1 = self._get_response(app)
        eq_(resp1.content_type, 'text/x-python')
        eq_(resp1.charset, 'UTF-8')
        eq_(resp1.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        app.update(force=True)
        resp2 = self._get_response(app)
        eq_(resp2.content_type, 'text/x-python')
        eq_(resp2.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))

        resp3 = self._get_response(app, range=(7, 11))
        eq_(resp3.status_int, 206)
        eq_(tuple(resp3.content_range)[:2], (7, 11))
        eq_(resp3.last_modified.timetuple(), gmtime(getmtime(self.tempfile)))
        eq_(resp3.body, b'this')
    def test_unexisting_file(self):
        app = static.FileApp('/tmp/this/doesnt/exist')
        self.assertEqual(404, self._get_response(app).status_int)

    def test_allowed_methods(self):
        app = static.FileApp(self.tempfile)

        # Alias
        resp = lambda method: self._get_response(app, method=method)

        self.assertEqual(200, resp(method='GET').status_int)
        self.assertEqual(200, resp(method='HEAD').status_int)
        self.assertEqual(405, resp(method='POST').status_int)
        # Actually any other method is not allowed
        self.assertEqual(405, resp(method='xxx').status_int)


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

    def _get_response(self, app, path='/', **kw):
        return Request(environ_from_url(path), **kw).\
                get_response(app)

    def _create_file(self, content, *paths):
        path = os.path.join(self.test_dir, *paths)
        with open(path, 'wb') as fp:
            fp.write(content)
        return path

    def test_empty_directory(self):
        app = static.DirectoryApp(self.test_dir)
        self.assertEqual(404, self._get_response(app).status_int)
        self.assertEqual(404, self._get_response(app, '/foo').status_int)

    def test_serve_file(self):
        app = static.DirectoryApp(self.test_dir)
        self._create_file(bytes_('abcde'), 'bar')
        self.assertEqual(404, self._get_response(app).status_int)
        self.assertEqual(404, self._get_response(app, '/foo').status_int)

        resp = self._get_response(app, '/bar')
        self.assertEqual(200, resp.status_int)
        self.assertEqual(bytes_('abcde'), resp.body)

    def test_dont_serve_file_in_parent_directory(self):
        # We'll have:
        #   /TEST_DIR/
        #   /TEST_DIR/bar
        #   /TEST_DIR/foo/   <- serve this directory
        self._create_file(bytes_('abcde'), 'bar')
        serve_path = os.path.join(self.test_dir, 'foo')
        os.mkdir(serve_path)
        app = static.DirectoryApp(serve_path)

        # The file exists, but is outside the served dir.
        self.assertEqual(403, self._get_response(app, '/../bar').status_int)

    def test_file_app_arguments(self):
        app = static.DirectoryApp(self.test_dir, content_type='xxx/yyy')
        self._create_file(bytes_('abcde'), 'bar')

        resp = self._get_response(app, '/bar')
        self.assertEqual(200, resp.status_int)
        self.assertEqual('xxx/yyy', resp.content_type)

    def test_file_app_factory(self):
        def make_fileapp(*args, **kwargs):
            make_fileapp.called = True
            return Response()
        make_fileapp.called = False

        app = static.DirectoryApp(self.test_dir)
        app.make_fileapp = make_fileapp
        self._create_file(bytes_('abcde'), 'bar')

        self._get_response(app, '/bar')
        self.assertTrue(make_fileapp.called)

    def test_must_serve_directory(self):
        serve_path = self._create_file(bytes_('abcde'), self.test_dir, 'bar')
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
        with open(os.path.join(self.dir_archive, 'foo'), 'w') as fp:
            fp.write('abcde')
        os.mkdir(os.path.join(self.dir_archive, 'bar'))
        with open(os.path.join(self.dir_archive, 'bar', 'baz'), 'w') as fp:
            fp.write('fgh')

    def tearDown(self):
        os.unlink(self.archive_name)
        shutil.rmtree(self.dir_archive)

    def _get_response(self, app, path='/', **kw):
        return Request(environ_from_url(path), **kw).\
                get_response(app)

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

        resp1 = self._get_response(app, '/foo')
        self.assertEqual(200, resp1.status_int)
        self.assertEqual(bytes_('abcde'), resp1.body)

        # Unknow file
        resp2 = self._get_response(app, '/unknown')
        self.assertEqual(200, resp2.status_int)
        self.assertEqual(bytes_(''), resp2.body)

        # Directory
        resp3 = self._get_response(app, '/bar')
        self.assertEqual(200, resp3.status_int)
        self.assertEqual(bytes_(''), resp3.body)

        # File in subdirectory
        resp4 = self._get_response(app, '/bar/baz')
        self.assertEqual(200, resp4.status_int)
        self.assertEqual(bytes_('fgh'), resp4.body)

    def test_zip_archive(self):
        self._test_read_archive_content("zip")

    def test_tar_archive(self):
        self._test_read_archive_content("tar")

    def test_unknown_archive(self):
        self.assertRaises(AssertionError,
                          static.ArchivedFilesApp, self.archive_name)
