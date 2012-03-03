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

    def __lshift__(self, req):
        return NotImplemented

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
    _max_cache_size = (1<<12) # 4Kb

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
            self.cached_response = exc.HTTPNotFound(comment=self.filename)
            return
        if stat.st_mtime != self.last_modified or force:
            self.last_modified = stat.st_mtime
            if stat.st_size < self._max_cache_size:
                data = open(self.filename, 'rb').read()
                self.cached_response = DataApp(data, last_modified=stat.st_mtime, **self.kw)
            else:
                self.cached_response = None
                self.content_length = stat.st_size

    @wsgify
    def __call__(self, req):
        if req.method not in ('GET', 'HEAD'):
            return exc.HTTPMethodNotAllowed("You cannot %s a file" %
                                            req.method)
        force = (req.cache_control.max_age == 0)
        self.update(force) # RFC 2616 13.2.6
        r = self.cached_response # access just once to avoid the need for locking
        if r:
            return r
        elif not os.path.exists(self.filename):
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
        FileApp instances are cached. This app double-checks not to serve any files that are not in a subdirectory.
        To customize FileApp instances creation override `make_fileapp` method.
    """

    def __init__(self, path, **kw):
        self.path = os.path.abspath(path)
        if not self.path.endswith(os.path.sep):
            self.path += os.path.sep
        assert os.path.isdir(self.path)
        self.cached_apps = {}
        self.fileapp_kw = kw

    def make_fileapp(self, path):
        return FileApp(path, **self.fileapp_kw)

    @wsgify
    def __call__(self, req):
        path_info = req.path_info.lstrip('/')
        try:
            return self.cached_apps[path_info]
        except KeyError:
            path = os.path.abspath(os.path.join(self.path, path_info))
            if not os.path.isfile(path):
                return exc.HTTPNotFound(comment=path)
            elif not path.startswith(self.path):
                return exc.HTTPForbidden()
            else:
                return self.cached_apps.setdefault(path_info, self.make_fileapp(path))


class ArchivedFilesApp(object):
    """
        An application that serves files from a zip or tar archive via DataApps.
    """
    def __init__(self, filepath, expires=None):
        if zipfile.is_zipfile(filepath):
            self.archive = zipfile.ZipFile(filepath, 'r')
        elif tarfile.is_tarfile(filepath):
            self.archive = tarfile.TarFileCompat(filepath, 'r')
        else:
            raise AssertionError("filepath '%s' is not a zip or tar " % filepath)
        self.expires = expires
        self.cached_apps = {}

    @wsgify
    def __call__(self, req):
        path = req.path_info.lstrip('/')
        try:
            return self.cached_apps[path_info]
        except KeyError:
            try:
                info = self.archive.getinfo(path)
            except KeyError:
                app = None
            else:
                if info.filename.endswith('/'):
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
            return self.cached_apps.setdefault(path, app)


class PkgResourcesApp(object):
    """
        An application to serve package resources as static files.
    """
    def __init__(self, module, prefix=''):
        self.module = module
        if prefix and not prefix.endswith('/'):
            prefix += '/'
        self.prefix = prefix
        self.cached_apps = {}

    @wsgify
    def __call__(self, req):
        path_info = req.path_info.lstrip('/')
        try:
            return self.cached_apps[path_info]
        except KeyError:
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
            return self.cached_apps.setdefault(path_info, app)

