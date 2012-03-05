from datetime import datetime
import mimetypes
import os
import tarfile
import zipfile

from pkg_resources import resource_string, resource_exists, resource_isdir

from webob import exc
from webob.compat import bytes_
from webob.dec import wsgify
from webob.response import Response

__all__ = [
    'DataApp', 'FileApp', 'DirectoryApp',
    'ArchivedFilesApp', 'PkgResourcesApp'
]

mimetypes._winreg = None # do not load mimetypes from windows registry
mimetypes.add_type('text/javascript', '.js') # stdlib default is application/x-javascript
mimetypes.add_type('image/x-icon', '.ico') # not among defaults

class DataApp(Response):
    allowed_methods = ('GET', 'HEAD')
    def __init__(self, *args, **kw):
        kw.setdefault('last_modified', datetime.now())
        kw.setdefault('accept_ranges', 'bytes')
        kw.setdefault('content_type', 'application/octet-stream')
        super(DataApp, self).__init__(*args, **kw)
        #@@? self.md5_etag(set_content_md5=True)

    def _set_body(self, body):
        Response.body.fset(self, body)
        self.last_modified = datetime.now()
        self.md5_etag(set_content_md5=True)

    body = property(Response.body.fget, _set_body)

    @wsgify
    def __call__(self, req):
        if req.method in self.allowed_methods:
            return self.conditional_response_app
        else:
            return exc.HTTPMethodNotAllowed("You cannot %s a file" %
                                            req.method)


class FileApp(object):
    """
        An application that will send the file at the given filename.
        Adds a mime type based on ``mimetypes.guess_type()``.
    """

    def __init__(self, filename, **kw):
        self.filename = filename
        content_type, content_encoding = mimetypes.guess_type(filename)
        kw.setdefault('content_type', content_type)
        kw.setdefault('content_encoding', content_encoding)
        self.kw = kw
        self.last_modified = None

    def update(self, force=False):
        try:
            stat = os.stat(self.filename)
        except (IOError, OSError):
            return
        if stat.st_mtime != self.last_modified or force:
            self.last_modified = stat.st_mtime
            self.content_length = stat.st_size

    @wsgify
    def __call__(self, req):
        if req.method not in ('GET', 'HEAD'):
            return exc.HTTPMethodNotAllowed("You cannot %s a file" %
                                            req.method)
        force = (req.cache_control.max_age == 0)
        self.update(force) # RFC 2616 13.2.6
        if not os.path.exists(self.filename):
            return exc.HTTPNotFound(comment=self.filename)

        try:
            file = open(self.filename, 'rb')
        except (IOError, OSError) as e:
            msg = "You are not permitted to view this file (%s)" % e
            return exc.HTTPForbidden(msg)
        return DataApp(
            app_iter = FileIter(file),
            content_length = self.content_length,
            last_modified = self.last_modified,
            #@@ etag
            **self.kw
        )


class FileIter(object):
    def __init__(self, file):
        self.file = file

    def app_iter_range(self, seek=None, limit=None, block_size=1<<16):
        if seek:
            self.file.seek(seek)
            if limit:
                limit -= seek
        try:
            while True:
                data = self.file.read(min(block_size, limit) if limit else block_size)
                if not data:
                    return
                yield data
                if limit:
                    limit -= len(data)
                    if not limit:
                        return
        finally:
            self.file.close()

    __iter__ = app_iter_range


class DirectoryApp(object):
    """
        An application that dispatches requests to corresponding FileApps based on PATH_INFO.
        This app double-checks not to serve any files that are not in a subdirectory.
        To customize FileApp instances creation override `make_fileapp` method.
    """

    def __init__(self, path, **kw):
        self.path = os.path.abspath(path)
        if not self.path.endswith(os.path.sep):
            self.path += os.path.sep
        assert os.path.isdir(self.path)
        self.fileapp_kw = kw

    def make_fileapp(self, path):
        return FileApp(path, **self.fileapp_kw)

    @wsgify
    def __call__(self, req):
        path = os.path.abspath(os.path.join(self.path,
                                            req.path_info.lstrip('/')))
        if not os.path.isfile(path):
            return exc.HTTPNotFound(comment=path)
        elif not path.startswith(self.path):
            return exc.HTTPForbidden()
        else:
            return self.make_fileapp(path)


class ZipFile(object):
    """Small wrapper to provide a uniform interface to archive (zip) objects"""

    def __init__(self, filename):
        self.archive = zipfile.ZipFile(filename)

    def get_info(self, path):
        class ZipInfo(object):
            def __init__(self, info):
                self.info = info

            def isdir(self):
                return self.info.filename.endswith('/')

            @property
            def filename(self):
                return self.info.filename

            @property
            def date_time(self):
                return self.info.date_time

        return ZipInfo(self.archive.getinfo(path))

    def read(self, name):
        return self.archive.read(name)


class TarFile(object):
    """Small wrapper to provide a uniform interface to archive (tar) objects"""
    def __init__(self, filename):
        self.archive = tarfile.TarFile(filename)

    def get_info(self, path):
        class TarInfo(object):
            def __init__(self, info):
                self.info = info

            def isdir(self):
                return self.info.isdir()

            @property
            def filename(self):
                return self.info.name

            @property
            def date_time(self):
                return datetime.fromtimestamp(self.info.mtime).timetuple()[:6]
        return TarInfo(self.archive.getmember(path))

    def read(self, name):
        return self.archive.extractfile(name).read()


class ArchivedFilesApp(object):
    """
        An application that serves files from a zip or tar archive via DataApps.
    """
    def __init__(self, filepath, expires=None):
        if zipfile.is_zipfile(filepath):
            self.archive = ZipFile(filepath)
        elif tarfile.is_tarfile(filepath):
            self.archive = TarFile(filepath)
        else:
            raise AssertionError("filepath '%s' is not a zip or tar " % filepath)
        self.expires = expires

    @wsgify
    def __call__(self, req):
        path = req.path_info.lstrip('/')
        try:
            info = self.archive.get_info(path)
        except KeyError:
            app = None
        else:
            if info.isdir():
                app = None
            else:
                content_type, content_encoding = mimetypes.guess_type(info.filename)
                app = DataApp(
                    body = self.archive.read(path),
                    content_type = content_type,
                    content_encoding = content_encoding,
                    last_modified = datetime(*info.date_time),
                    expires = self.expires,
                )
        return app


class PkgResourcesApp(object):
    """
        An application to serve package resources as static files.
    """
    def __init__(self, module, prefix=''):
        self.module = module
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        self.prefix = prefix

    @wsgify
    def __call__(self, req):
        path_info = req.path_info.lstrip('/')
        path = self.prefix + path_info
        if resource_exists(self.module, path) and not resource_isdir(self.module, path):
            data = resource_string(self.module, path)
            content_type, content_encoding = mimetypes.guess_type(path_info)
            app = DataApp(data,
                content_type=content_type,
                content_encoding = content_encoding,
            )
            app.md5_etag(set_content_md5=True)
        else:
            app = None
        return app

