"""
Middleware that transcodes requests from non-UTF-8 charsets
"""
__all__ = ['transcode_mw']

import io, urllib, urlparse, cgi
from webob.request import _encode_multipart, BaseRequest, CHARSET_RE
from webob.descriptors import parse_int_safe

def transcode_mw(app, unicode_errors='strict'):
    def transcode_mw_inner(env, sr):
        req = BaseRequest(env)
        req = _transcode_req(req, req.charset, unicode_errors)
        return app(req.environ, sr)
    return transcode_mw_inner

def _transcode_req(req, charset, errors='strict'):
    if charset == 'UTF-8':
        return req

    # cookies and path are always utf-8
    t = Transcoder(charset, errors)

    new_content_type = CHARSET_RE.sub('; charset="UTF-8"', req._content_type_raw)
    content_type = req.content_type
    r = BaseRequest(
        req.environ.copy(),
        query_string = t.transcode_query(req.query_string),
        content_type=new_content_type,
    )

    if content_type == 'application/x-www-form-urlencoded':
        r.body = t.transcode_query(r.body)
        return r
    elif content_type != 'multipart/form-data':
        return r

    fs_environ = req.environ.copy()
    fs_environ.setdefault('CONTENT_LENGTH', '0')
    fs_environ['QUERY_STRING'] = ''
    fs = cgi.FieldStorage(fp=req.body_file,
                          environ=fs_environ,
                          keep_blank_values=True)

    fout = t.transcode_fs(fs, r._content_type_raw)

    r.content_length = fout.tell()
    fout.seek(0)
    r.body_file = fout
    return r


class Transcoder(object):
    def __init__(self, charset, errors='strict'):
        self.charset = charset # source charset
        self.errors = errors # unicode errors
        self._trans = lambda b: b.decode(charset, errors).encode('utf8')

    def transcode_query(self, q):
        t = self._trans
        if '='.encode(self.charset) not in q:
            # this doesn't look like a form submission
            return q
        q = urlparse.parse_qsl(q,
            keep_blank_values=True,
            strict_parsing=False
        )
        q = [(t(k), t(v)) for k,v in q]
        return urllib.urlencode(q)

    def transcode_fs(self, fs, content_type):
        # transcode FieldStorage
        decode = lambda b: b.decode(self.charset, self.errors)
        data = []
        for field in fs.list or ():
            field.name = decode(field.name)
            if field.filename:
                field.filename = decode(field.filename)
                data.append((field.name, field))
            else:
                data.append((field.name, decode(field.value)))

        # TODO: transcode big requests to temp file
        content_type, fout = _encode_multipart(
            data,
            content_type,
            fout=io.BytesIO()
        )
        return fout
