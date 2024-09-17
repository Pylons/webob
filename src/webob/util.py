import warnings

from html import escape
from webob.headers import _trans_key


def unquote(string):
    if not string:
        return b""
    res = string.split(b"%")

    if len(res) != 1:
        string = res[0]

        for item in res[1:]:
            string += bytes([int(item[:2], 16)]) + item[2:]

    return string


def url_unquote(s):
    return unquote(s.encode("ascii")).decode("latin-1")


def parse_qsl_text(qs, encoding="utf-8"):
    qs = qs.encode("latin-1")
    qs = qs.replace(b"+", b" ")
    pairs = [s2 for s1 in qs.split(b"&") for s2 in s1.split(b";") if s2]

    for name_value in pairs:
        nv = name_value.split(b"=", 1)

        if len(nv) != 2:
            nv.append("")
        name = unquote(nv[0])
        value = unquote(nv[1])
        yield (name.decode(encoding), value.decode(encoding))


def text_(s, encoding="latin-1", errors="strict"):
    if isinstance(s, bytes):
        return str(s, encoding, errors)

    return s


def bytes_(s, encoding="latin-1", errors="strict"):
    if isinstance(s, str):
        return s.encode(encoding, errors)

    return s


def html_escape(s):
    """HTML-escape a string or object

    This converts any non-string objects passed into it to strings
    (actually, using ``unicode()``).  All values returned are
    non-unicode strings (using ``&#num;`` entities for all non-ASCII
    characters).

    None is treated specially, and returns the empty string.
    """

    if s is None:
        return ""
    __html__ = getattr(s, "__html__", None)

    if __html__ is not None and callable(__html__):
        return s.__html__()

    if not isinstance(s, str):
        s = str(s)
    s = escape(s, True)

    if isinstance(s, str):
        s = s.encode("ascii", "xmlcharrefreplace")

    return text_(s)


def header_docstring(header, rfc_section):
    if header.isupper():
        header = _trans_key(header)
    major_section = rfc_section.split(".")[0]
    link = "http://www.w3.org/Protocols/rfc2616/rfc2616-sec{}.html#sec{}".format(
        major_section,
        rfc_section,
    )

    return "Gets and sets the ``{}`` header (`HTTP spec section {} <{}>`_).".format(
        header,
        rfc_section,
        link,
    )


def warn_deprecation(text, version, stacklevel):
    # version specifies when to start raising exceptions instead of warnings

    if version in ("1.2", "1.3", "1.4", "1.5", "1.6", "1.7"):
        raise DeprecationWarning(text)
    else:
        cls = DeprecationWarning
    warnings.warn(text, cls, stacklevel=stacklevel + 1)


status_reasons = {
    # Status Codes
    # Informational
    100: "Continue",
    101: "Switching Protocols",
    102: "Processing",
    # Successful
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    207: "Multi Status",
    226: "IM Used",
    # Redirection
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",
    # Client Error
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request URI Too Long",
    415: "Unsupported Media Type",
    416: "Requested Range Not Satisfiable",
    417: "Expectation Failed",
    418: "I'm a teapot",
    422: "Unprocessable Entity",
    423: "Locked",
    424: "Failed Dependency",
    426: "Upgrade Required",
    428: "Precondition Required",
    429: "Too Many Requests",
    451: "Unavailable for Legal Reasons",
    431: "Request Header Fields Too Large",
    # Server Error
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout",
    505: "HTTP Version Not Supported",
    507: "Insufficient Storage",
    510: "Not Extended",
    511: "Network Authentication Required",
}

# generic class responses as per RFC2616
status_generic_reasons = {
    1: "Continue",
    2: "Success",
    3: "Multiple Choices",
    4: "Unknown Client Error",
    5: "Unknown Server Error",
}
