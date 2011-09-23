# code stolen from "six"

import cgi
import os
import sys
import types

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes
    long = int
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

def text_(s, encoding='latin-1', errors='strict'):
    if isinstance(s, binary_type):
        return s.decode(encoding, errors)
    return s

def bytes_(s, encoding='latin-1', errors='strict'):
    if isinstance(s, text_type):
        return s.encode(encoding, errors)
    return s

if PY3: # pragma: no cover
    def native_(s, encoding='latin-1', errors='strict'):
        if isinstance(s, text_type):
            return s
        return str(s, encoding, errors)
else:
    def native_(s, encoding='latin-1', errors='strict'):
        if isinstance(s, text_type):
            return s.encode(encoding, errors)
        return str(s)

if PY3: # pragma: no cover
    def text_to_wsgi(u):
        return u.encode('ascii').decode('latin-1')
else:
    def text_to_wsgi(u):
        return u.encode('latin-1', 'surrogateescape')

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

try: # pragma: no cover
    from urllib import parse
    urlparse = parse
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote
    from urllib.parse import urlencode as url_encode
    from urllib.request import urlopen as url_open
except ImportError:
    import urlparse
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote
    from urllib import urlencode as url_encode
    from urllib2 import urlopen as url_open

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value


    print_ = getattr(builtins, "print")
    del builtins

else: # pragma: no cover
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


if PY3:
    #from urllib.parse import unquote

    def unquote(string):
        if not string:
            return b''
        res = string.split(b'%')
        if len(res) != 1:
            string = res[0]
            for item in res[1:]:
                try:
                    string += bytes([int(item[:2], 16)]) + item[2:]
                except ValueError:
                    string += b'%' + item
        return string

    def parse_qsl_text(qs, encoding='utf-8', errors='replace'):
        qs = qs.encode('latin-1')
        qs = qs.replace(b'+', b' ')
        pairs = [s2 for s1 in qs.split(b'&') for s2 in s1.split(b';') if s3]
        for name_value in pairs:
            nv = name_value.split(b'=', 1)
            if len(nv) != 2:
                nv.append('')
            name = unquote(nv[0])
            value = unquote(nv[1])
            yield (name.decode(encoding, errors), value.decode(encoding, errors))

else:
    from urlparse import parse_qsl

    def parse_qsl_text(qs, encoding='utf-8', errors='replace'):
        qsl = parse_qsl(
            qs,
            keep_blank_values=True,
            strict_parsing=False
        )
        for (x, y) in qsl:
            yield (x.decode(encoding, errors), y.decode(encoding, errors))


if PY3: # pragma: no cover
    from webob.multidict import MultiDict
    def multidict_from_bodyfile(fp=None, environ=os.environ,
                                keep_blank_values=False, encoding='utf-8',
                                errors='replace'):
        fs = cgi.FieldStorage(
            fp=fp,
            environ=environ,
            keep_blank_values=keep_blank_values,
            encoding=encoding,
            errors=errors)
        obj = MultiDict()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                # decode filename and name from str to unicode
                field.filename = text_(field.filename, encoding, errors)
                field.name = text_(field.name, encoding, errors)
                obj.add(field.name, field)
            else:
                obj.add(field.name, field.value)
        return obj
else:
    from webob.multidict import MultiDict
    def multidict_from_bodyfile(fp=None, environ=os.environ,
                                keep_blank_values=False, encoding='utf-8',
                                errors='replace'):
        fs = cgi.FieldStorage(
            fp=fp,
            environ=environ,
            keep_blank_values=keep_blank_values
            )
        obj = MultiDict()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                # decode filename and name from str to unicode
                field.filename = text_(field.filename, encoding, errors)
                field.name = text_(field.name, encoding, errors)
                obj.add(field.name, field)
            else:
                obj.add(field.name.decode(encoding, errors),
                        field.value.decode(encoding, errors))
        return obj

