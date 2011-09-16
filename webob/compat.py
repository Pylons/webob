# code stolen from "six"

import sys
import types
import cgi
import os

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

if PY3: # pragma: no cover
    from urllib import parse
    urlparse = parse
    long = int
else:
    import urlparse

if PY3: # pragma: no cover
    from collections import MutableMapping as DictMixin
else:
    from UserDict import DictMixin
    
if PY3: # pragma: no cover
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote
    from urllib.parse import urlencode as url_encode
    from urllib.request import urlopen as url_open
else:
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote
    from urllib import urlencode as url_encode
    from urllib2 import urlopen as url_open
    


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc

if PY3: # pragma: no cover
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")

if PY3:
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else:
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

if PY3: # pragma: no cover
    def iteritems_(d):
        return d.items()
    def itervalues_(d):
        return d.values()
else:
    def iteritems_(d):
        return d.iteritems()
    def itervalues_(d):
        return d.itervalues()

if PY3: # pragma: no cover
    enc, esc = sys.getfilesystemencoding(), 'surrogateescape'
    def unicode_to_wsgi(u):
        # On Python 3, convert an environment variable to a WSGI
        # "bytes-as-unicode" string
        return u.encode(enc, esc).decode('iso-8859-1')
    def wsgi_to_unicode(u):
        # Convert a "bytes-as-unicode" string to Unicode
        return u.encode('iso-8859-1', esc).decode(enc)
else:
    def unicode_to_wsgi(u):
        return u.encode('iso-8859-1')
    def wsgi_to_unicode(s):
        return s.decode('iso-8859-1')

try: # pragma: no cover
    from hashlib import md5
except ImportError: # pragma: no cover
    from md5 import md5

try:
    next = next
except NameError:
    def next(v):
        return v.next()
    
if PY3: # pragma: no cover
    def parse_qsl_text(qs, keep_blank_values=False, strict_parsing=False,
                       encoding='utf-8', errors='replace'):
        source = wsgi_to_unicode(qs)
        decoded = urlparse.parse_qsl(
            source,
            keep_blank_values=keep_blank_values,
            strict_parsing=strict_parsing,
            encoding=encoding,
            errors=errors,
            )
        return decoded
else:
    def parse_qsl_text(qs, keep_blank_values=False, strict_parsing=False,
                       encoding='utf-8', errors='replace'):
        decoded = [
            (x.decode(encoding, errors), y.decode(encoding, errors))
             for (x, y) in urlparse.parse_qsl(
                 qs,
                 keep_blank_values=keep_blank_values,
                 strict_parsing=strict_parsing)
            ]
        return decoded
                
if PY3: # pragma: no cover
    def multidict_from_bodyfile(fp=None, environ=os.environ,
                                keep_blank_values=False, encoding='utf-8',
                                errors='replace'):
        fs = cgi.FieldStorage(
            fp=fp,
            environ=environ,
            keep_blank_values=keep_blank_values,
            encoding=encoding,
            errors=errors)
        from webob.multidict import MultiDict
        obj = MultiDict()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                obj.add(field.name, field)
            else:
                obj.add(field.name, field.value)
        return obj
else:
    def multidict_from_bodyfile(fp=None, environ=os.environ,
                                keep_blank_values=False, encoding='utf-8',
                                errors='replace'):
        fs = cgi.FieldStorage(
            fp=fp,
            environ=environ,
            keep_blank_values=keep_blank_values
            )
        from webob.multidict import MultiDict
        obj = MultiDict()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                obj.add(field.name.decode(encoding, errors), field)
            else:
                obj.add(field.name.decode(encoding, errors),
                        field.value.decode(encoding, errors))
        return obj
        
