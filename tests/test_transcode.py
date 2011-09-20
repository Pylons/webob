# coding: cp1251
from webob.request import Request
from webob.response import Response
from webob.transcode import transcode_mw
from nose.tools import eq_

# def tapp(env, sr):
#     req = Request(env)
#     r = Response(str(req))
#     #r = Response(str(dict(req.POST)))
#     return r(env, sr)

t1 = '--BOUNDARY\r\nContent-Disposition: form-data; name="a"\r\n\r\n\xea\xf3...\r\n--BOUNDARY--'
t2 = '--BOUNDARY\r\nContent-Disposition: form-data; name="a"; filename="file"\r\n\r\n\xea\xf3...\r\n--BOUNDARY--'
t3 = '--BOUNDARY\r\nContent-Disposition: form-data; name="a"; filename="\xea\xf3..."\r\n\r\nfoo\r\n--BOUNDARY--'

def test_transcode():
    def tapp(env, sr):
        req = Request(env)
        v = req.POST[req.query_string]
        if hasattr(v, 'filename'):
            r = Response(u'%s\n%r' % (v.filename, v.value))
        else:
            r = Response(v)
        return r(env, sr)
    text = u'ку...'
    def test(post):
        req = Request.blank('/?a', POST=post)
        req.environ['CONTENT_TYPE'] = 'multipart/form-data; charset=windows-1251; boundary=BOUNDARY'
        return req.get_response(transcode_mw(tapp))

    r = test(t1)
    eq_(r.text, text)
    r = test(t2)
    eq_(r.text, u'file\n%r' % text.encode('cp1251'))
    r = test(t3)
    eq_(r.text, u"%s\n'foo'" % text)

    #req = Request.blank('/?a', POST={'a': ('file', text.encode('cp1251'))},


    # req = Request({}, charset='utf8')
    # req = Request({})
    # print req.charset
    # print req._charset_cache
    # print req.environ.get('CONTENT_TYPE')
    #print '\xd0\xba\xd1\x83...'.decode('utf8').encode('cp1251')
    #print u'\u043a'.encode('cp1251')
