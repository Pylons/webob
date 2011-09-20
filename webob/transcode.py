"""
Middleware that transcodes requests from non-UTF-8 charsets
"""
__all__ = ['transcode_mw']

import io, urllib, urlparse, cgi
from webob.request import detect_charset, LimitedLengthFile, _encode_multipart, _is_utf8
from webob.descriptors import parse_int_safe

def transcode_mw(app, unicode_errors='strict'):
    def transcode_mw_inner(env, sr):
        if (env['REQUEST_METHOD'] in ('POST', 'PUT')
            and env.get('CONTENT_TYPE')
        ):
            charset = detect_charset(env['CONTENT_TYPE'])
            if not _is_utf8(charset):
                env = _transcode_env(env, charset, unicode_errors)
        return app(env, sr)
    return transcode_mw_inner

def _transcode_env(env, charset, errors='strict'):
    content_type = env['CONTENT_TYPE'].split(';')[0]
    if content_type == 'multipart/form-data':
        multipart = True
    elif content_type == 'application/x-www-form-urlencoded':
        multipart = False
    else:
        return env

    trans = lambda b: b.decode(charset, errors).encode('utf8')
    f = env['wsgi.input']
    clen = parse_int_safe(env.get('CONTENT_LENGTH'))
    seekable = env.get('webob.is_body_seekable')
    if not seekable and clen is not None:
        f = LimitedLengthFile(f, clen)
        f = io.BufferedReader(f)

    if multipart:
        decode = lambda b: b.decode(charset, errors)
        fs_environ = env.copy()
        fs_environ.setdefault('CONTENT_LENGTH', '0')
        fs_environ['QUERY_STRING'] = ''
        fs = cgi.FieldStorage(fp=f,
                              environ=fs_environ,
                              keep_blank_values=True)

        data = []
        for field in fs.list or ():
            field.name = decode(field.name)
            if field.filename:
                field.filename = decode(field.filename)
                data.append((field.name, field))
            else:
                data.append((field.name, decode(field.value)))

        content_type, fout = _encode_multipart(
            data,
            content_type,
            fout=io.BytesIO()
        )
        content_length = fout.tell()
        fout.seek(0)
    else:
        data = urlparse.parse_qsl(f.read())
        data = [(trans(k), trans(v)) for k,v in data]
        data = urllib.urlencode(data)
        fout = io.BytesIO(data)
        content_length = len(data)

    # cookies and path are always utf-8
    r = env.copy()
    r['CONTENT_TYPE'] = content_type + '; charset="UTF-8"'
    r['CONTENT_LENGTH'] = content_length
    r['wsgi.input'] = fout
    r['webob.is_body_seekable'] = True
    return r
