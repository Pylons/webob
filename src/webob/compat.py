# flake8: noqa

import cgi
from cgi import FieldStorage as _cgi_FieldStorage, parse_header
from html import escape
from queue import Empty, Queue
import sys
import tempfile
import types


# Various different FieldStorage work-arounds required on Python 3.x
class cgi_FieldStorage(_cgi_FieldStorage):  # pragma: no cover
    def __repr__(self):
        """monkey patch for FieldStorage.__repr__

        Unbelievably, the default __repr__ on FieldStorage reads
        the entire file content instead of being sane about it.
        This is a simple replacement that doesn't do that
        """

        if self.file:
            return "FieldStorage(%r, %r)" % (self.name, self.filename)

        return "FieldStorage(%r, %r, %r)" % (self.name, self.filename, self.value)

    # Work around https://bugs.python.org/issue27777
    def make_file(self):
        if self._binary_file or self.length >= 0:
            return tempfile.TemporaryFile("wb+")
        else:
            return tempfile.TemporaryFile("w+", encoding=self.encoding, newline="\n")

    # Work around http://bugs.python.org/issue23801
    # This is taken exactly from Python 3.5's cgi.py module
    def read_multi(self, environ, keep_blank_values, strict_parsing):
        """Internal: read a part that is itself multipart."""
        ib = self.innerboundary

        if not cgi.valid_boundary(ib):
            raise ValueError("Invalid boundary in multipart form: %r" % (ib,))
        self.list = []

        if self.qs_on_post:
            query = cgi.urllib.parse.parse_qsl(
                self.qs_on_post,
                self.keep_blank_values,
                self.strict_parsing,
                encoding=self.encoding,
                errors=self.errors,
            )

            for key, value in query:
                self.list.append(cgi.MiniFieldStorage(key, value))

        klass = self.FieldStorageClass or self.__class__
        first_line = self.fp.readline()  # bytes

        if not isinstance(first_line, bytes):
            raise ValueError(
                "%s should return bytes, got %s" % (self.fp, type(first_line).__name__)
            )
        self.bytes_read += len(first_line)

        # Ensure that we consume the file until we've hit our innerboundary

        while first_line.strip() != (b"--" + self.innerboundary) and first_line:
            first_line = self.fp.readline()
            self.bytes_read += len(first_line)

        while True:
            parser = cgi.FeedParser()
            hdr_text = b""

            while True:
                data = self.fp.readline()
                hdr_text += data

                if not data.strip():
                    break

            if not hdr_text:
                break
            # parser takes strings, not bytes
            self.bytes_read += len(hdr_text)
            parser.feed(hdr_text.decode(self.encoding, self.errors))
            headers = parser.close()
            # Some clients add Content-Length for part headers, ignore them

            if "content-length" in headers:
                filename = None

                if "content-disposition" in self.headers:
                    cdisp, pdict = parse_header(self.headers["content-disposition"])

                    if "filename" in pdict:
                        filename = pdict["filename"]

                if filename is None:
                    del headers["content-length"]
            part = klass(
                self.fp,
                headers,
                ib,
                environ,
                keep_blank_values,
                strict_parsing,
                self.limit - self.bytes_read,
                self.encoding,
                self.errors,
            )
            self.bytes_read += part.bytes_read
            self.list.append(part)

            if part.done or self.bytes_read >= self.length > 0:
                break
        self.skip_lines()
