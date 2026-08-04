from __future__ import annotations

from html import escape
import re
from typing import TYPE_CHECKING, overload
import warnings

from webob.headers import _trans_key

if TYPE_CHECKING:
    from collections.abc import Iterator


def unquote(string: bytes) -> bytes:
    if not string:
        return b""
    res = string.split(b"%")

    if len(res) != 1:
        string = res[0]

        for item in res[1:]:
            string += bytes([int(item[:2], 16)]) + item[2:]

    return string


def url_unquote(s: str) -> str:
    return unquote(s.encode("ascii")).decode("latin-1")


def parse_qsl_text(qs: str, encoding: str = "utf-8") -> Iterator[tuple[str, str]]:
    qsb = qs.encode("latin-1")
    qsb = qsb.replace(b"+", b" ")
    pairs = [s2 for s1 in qsb.split(b"&") for s2 in s1.split(b";") if s2]

    for name_value in pairs:
        nv = name_value.split(b"=", 1)

        if len(nv) != 2:
            nv.append(b"")
        name = unquote(nv[0])
        value = unquote(nv[1])
        yield (name.decode(encoding), value.decode(encoding))


@overload
def text_(s: str | bytes, encoding: str = "latin-1", errors: str = "strict") -> str: ...


@overload
def text_(s: None, encoding: str = "latin-1", errors: str = "strict") -> None: ...


def text_(
    s: str | bytes | None, encoding: str = "latin-1", errors: str = "strict"
) -> str | None:
    if isinstance(s, bytes):
        return str(s, encoding, errors)

    return s


@overload
def bytes_(
    s: str | bytes, encoding: str = "latin-1", errors: str = "strict"
) -> bytes: ...


@overload
def bytes_(s: None, encoding: str = "latin-1", errors: str = "strict") -> None: ...


def bytes_(
    s: str | bytes | None, encoding: str = "latin-1", errors: str = "strict"
) -> bytes | None:
    if isinstance(s, str):
        return s.encode(encoding, errors)

    return s


def html_escape(s: object) -> str:
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
        return __html__()  # type: ignore[no-any-return]

    if not isinstance(s, str):
        s = str(s)
    s = escape(s, True)

    if isinstance(s, str):
        s = s.encode("ascii", "xmlcharrefreplace")

    return text_(s)


# RFC 3986 section 3.1: scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+\-.]*$")


def _split_uri_reference(
    uri: str,
) -> tuple[str | None, str | None, str, str | None, str | None]:
    """Split a URI reference into its five components.

    Returns a ``(scheme, authority, path, query, fragment)`` tuple,
    following the grammar from RFC 3986 (see appendix B). Components that
    are not present in the reference are ``None``. The path is always
    present, but may be the empty string.

    Unlike ``urllib.parse.urlsplit()``, no characters are ever removed
    from the reference: ASCII tab/CR/LF and leading or trailing C0
    control and space characters are treated like any other character.
    """
    scheme = authority = query = fragment = None

    rest, sep, token = uri.partition("#")

    if sep:
        fragment = token

    rest, sep, token = rest.partition("?")

    if sep:
        query = token

    token, sep, candidate = rest.partition(":")

    if sep and _URI_SCHEME_RE.match(token):
        scheme = token
        rest = candidate

    if rest.startswith("//"):
        end = rest.find("/", 2)

        if end == -1:
            authority, rest = rest[2:], ""
        else:
            authority, rest = rest[2:end], rest[end:]

    return scheme, authority, rest, query, fragment


def _remove_dot_segments(path: str) -> str:
    """Remove ``.`` and ``..`` segments from a path (RFC 3986 5.2.4)."""
    output: list[str] = []

    while path:
        if path.startswith("../"):
            path = path[3:]
        elif path.startswith("./"):
            path = path[2:]
        elif path.startswith("/./"):
            path = "/" + path[3:]
        elif path == "/.":
            path = "/"
        elif path.startswith("/../"):
            path = "/" + path[4:]

            if output:
                output.pop()
        elif path == "/..":
            path = "/"

            if output:
                output.pop()
        elif path in (".", ".."):
            path = ""
        else:
            end = path.find("/", 1) if path.startswith("/") else path.find("/")

            if end == -1:
                output.append(path)
                path = ""
            else:
                output.append(path[:end])
                path = path[end:]

    return "".join(output)


def _merge_paths(base_authority: str | None, base_path: str, path: str) -> str:
    """Merge a relative-path reference with the base path (RFC 3986 5.2.3)."""

    if base_authority is not None and base_path == "":
        return "/" + path

    if "/" in base_path:
        return base_path[: base_path.rfind("/") + 1] + path

    return path


def urljoin(base: str | None, url: str) -> str:
    """Resolve a URI reference relative to a base URI (RFC 3986 section 5).

    A replacement for ``urllib.parse.urljoin()``. The standard library
    implementation follows the WHATWG URL living standard (on Python
    3.10+) by removing ASCII tab, CR, and LF anywhere in the URL and
    stripping leading and trailing C0 control and space characters
    before parsing. Those transformations can silently turn an otherwise
    harmless relative reference such as ``" //evil.example"`` into a
    protocol-relative or absolute URL, which has repeatedly led to open
    redirect issues when normalizing the ``Location`` header (see
    CVE-2024-42353/GHSA-mg3v-6m49-jhp3, GHSA-fh3h-vg37-cc95, and
    GHSA-6hx8-3wjj-gr8g).

    This implementation resolves the reference exactly as given,
    character for character, with no whitespace removal whatsoever.
    """

    # Mirror urllib.parse.urljoin()'s short-circuits for degenerate input
    # (such as a reference of None or the empty string), which callers of
    # Request.relative_url() may rely on.

    if not base:
        return url

    if not url:
        return base

    b_scheme, b_authority, b_path, b_query, b_fragment = _split_uri_reference(base)
    r_scheme, r_authority, r_path, r_query, r_fragment = _split_uri_reference(url)

    # Like urllib.parse.urljoin(), use the non-strict variant of the
    # resolution algorithm (RFC 3986 5.2.2): a reference whose scheme
    # matches the base scheme is treated as a relative reference.

    if (
        r_scheme is not None
        and b_scheme is not None
        and r_scheme.lower() == b_scheme.lower()
    ):
        r_scheme = None

    if r_scheme is not None:
        scheme: str | None = r_scheme
        authority = r_authority
        path = _remove_dot_segments(r_path)
        query = r_query
    elif r_authority is not None:
        scheme = b_scheme
        authority = r_authority
        path = _remove_dot_segments(r_path)
        query = r_query
    elif r_path == "":
        scheme = b_scheme
        authority = b_authority
        path = b_path
        query = r_query if r_query is not None else b_query
    else:
        scheme = b_scheme
        authority = b_authority

        if r_path.startswith("/"):
            path = _remove_dot_segments(r_path)
        else:
            path = _remove_dot_segments(_merge_paths(b_authority, b_path, r_path))
        query = r_query
    fragment = r_fragment

    # Recompose the components (RFC 3986 5.3)
    result = []

    if scheme is not None:
        result.append(scheme + ":")

    if authority is not None:
        result.append("//" + authority)
    result.append(path)

    if query is not None:
        result.append("?" + query)

    if fragment is not None:
        result.append("#" + fragment)

    return "".join(result)


def header_docstring(header: str, rfc_section: str) -> str:
    if header.isupper():
        # FIXME: What should we do when this returns `None`?
        header = _trans_key(header)  # type: ignore[assignment]
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


def warn_deprecation(text: str, version: str, stacklevel: int) -> None:
    # version specifies when to start raising exceptions instead of warnings

    if version in ("1.2", "1.3", "1.4", "1.5", "1.6", "1.7"):
        raise DeprecationWarning(text)
    else:
        cls = DeprecationWarning
    warnings.warn(text, cls, stacklevel=stacklevel + 1)


status_reasons: dict[int, str] = {
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
status_generic_reasons: dict[int, str] = {
    1: "Continue",
    2: "Success",
    3: "Multiple Choices",
    4: "Unknown Client Error",
    5: "Unknown Server Error",
}
