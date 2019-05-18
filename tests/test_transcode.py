from webob.request import Request, Transcoder
from webob.response import Response
from webob.util import text_

t1 = (
    b'--BOUNDARY\r\nContent-Disposition: form-data; name="a"\r\n\r\n\xea\xf3...'
    b"\r\n--BOUNDARY--"
)
t2 = (
    b'--BOUNDARY\r\nContent-Disposition: form-data; name="a"; filename="file"\r\n'
    b"\r\n\xea\xf3...\r\n--BOUNDARY--"
)
t3 = (
    b'--BOUNDARY\r\nContent-Disposition: form-data; name="a"; filename="\xea\xf3...'
    b'"\r\n\r\nfoo\r\n--BOUNDARY--'
)


def test_transcode():
    def tapp(env, sr):
        req = Request(env)
        req = req.decode()

        v = req.POST[req.query_string]

        if hasattr(v, "filename"):
            r = Response(text_("%s\n%r" % (v.filename, v.value)))
        else:
            r = Response(v)

        return r(env, sr)

    text = b"\xea\xf3...".decode("cp1251")

    def test(post):
        req = Request.blank("/?a", POST=post)
        req.environ[
            "CONTENT_TYPE"
        ] = "multipart/form-data; charset=windows-1251; boundary=BOUNDARY"

        return req.get_response(tapp)

    r = test(t1)
    assert r.text == text
    r = test(t2)
    assert r.text == "file\n%r" % text.encode("cp1251")
    r = test(t3)
    assert r.text, "%s\n%r" % (text == b"foo")


def test_transcode_query():
    req = Request.blank("/?%EF%F0%E8=%E2%E5%F2")
    req2 = req.decode("cp1251")
    assert req2.query_string == "%D0%BF%D1%80%D0%B8=%D0%B2%D0%B5%D1%82"


def test_transcode_non_multipart():
    req = Request.blank("/?a", POST="%EF%F0%E8=%E2%E5%F2")
    req._content_type_raw = "application/x-www-form-urlencoded"
    req2 = req.decode("cp1251")
    assert text_(req2.body) == "%D0%BF%D1%80%D0%B8=%D0%B2%D0%B5%D1%82"


def test_transcode_non_form():
    req = Request.blank("/?a", POST="%EF%F0%E8=%E2%E5%F2")
    req._content_type_raw = "application/x-foo"
    req2 = req.decode("cp1251")
    assert text_(req2.body) == "%EF%F0%E8=%E2%E5%F2"


def test_transcode_noop():
    req = Request.blank("/")
    assert req.decode() is req


def test_transcode_query_ascii():
    t = Transcoder("ascii")
    assert t.transcode_query("a") == "a"
