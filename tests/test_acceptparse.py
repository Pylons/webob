from copy import deepcopy
import re
import warnings

import pytest

from webob.acceptparse import (
    Accept,
    AcceptCharset,
    AcceptEncoding,
    AcceptLanguage,
    AcceptLanguageInvalidHeader,
    AcceptLanguageNoHeader,
    AcceptLanguageValidHeader,
    AcceptOffer,
    HeaderState,
    _item_n_weight_re,
    _list_1_or_more__compiled_re,
    accept_charset_property,
    accept_encoding_property,
    accept_language_property,
    accept_property,
    create_accept_charset_header,
    create_accept_encoding_header,
    create_accept_header,
    create_accept_language_header,
)
from webob.request import Request

IGNORE_BEST_MATCH = "ignore:.*best_match.*"
IGNORE_QUALITY = "ignore:.*quality.*"
IGNORE_CONTAINS = "ignore:.*__contains__.*"
IGNORE_ITER = "ignore:.*__iter__.*"


class StringMe:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


class Test_ItemNWeightRe:
    @pytest.mark.parametrize(
        "header_value",
        [
            "q=",
            "q=1",
            ";q",
            ";q=",
            ";q=1",
            "foo;",
            "foo;q",
            "foo;q1",
            "foo;q=",
            "foo;q=-1",
            "foo;q=2",
            "foo;q=1.001",
            "foo;q=0.0001",
            "foo;q=00",
            "foo;q=01",
            "foo;q=00.1",
            "foo,q=0.1",
            "foo;q =1",
            "foo;q= 1",
        ],
    )
    def test_invalid(self, header_value):
        regex = _item_n_weight_re(item_re="foo")
        assert re.match("^" + regex + "$", header_value, re.VERBOSE) is None

    @pytest.mark.parametrize(
        "header_value, groups",
        [
            ("foo", ("foo", None)),
            ("foo;q=0", ("foo", "0")),
            ("foo;q=0.0", ("foo", "0.0")),
            ("foo;q=0.00", ("foo", "0.00")),
            ("foo;q=0.000", ("foo", "0.000")),
            ("foo;q=1", ("foo", "1")),
            ("foo;q=1.0", ("foo", "1.0")),
            ("foo;q=1.00", ("foo", "1.00")),
            ("foo;q=1.000", ("foo", "1.000")),
            ("foo;q=0.1", ("foo", "0.1")),
            ("foo;q=0.87", ("foo", "0.87")),
            ("foo;q=0.382", ("foo", "0.382")),
            ("foo;Q=0.382", ("foo", "0.382")),
            ("foo ;Q=0.382", ("foo", "0.382")),
            ("foo; Q=0.382", ("foo", "0.382")),
            ("foo  ;  Q=0.382", ("foo", "0.382")),
        ],
    )
    def test_valid(self, header_value, groups):
        regex = _item_n_weight_re(item_re="foo")
        assert re.match("^" + regex + "$", header_value, re.VERBOSE).groups() == groups


class Test_List1OrMoreCompiledRe:
    @pytest.mark.parametrize(
        "header_value",
        [
            # RFC 7230 Section 7
            ",",
            ",   ,",
            # RFC 7230 Errata ID: 4169
            "foo , ,bar,charlie   ",
            # Our tests
            " foo , ,bar,charlie",
            " ,foo , ,bar,charlie",
            ",foo , ,bar,charlie, ",
            "\tfoo , ,bar,charlie",
            "\t,foo , ,bar,charlie",
            ",foo , ,bar,charlie\t",
            ",foo , ,bar,charlie,\t",
        ],
    )
    def test_invalid(self, header_value):
        regex = _list_1_or_more__compiled_re(element_re="([a-z]+)")
        assert regex.match(header_value) is None

    @pytest.mark.parametrize(
        "header_value",
        [
            # RFC 7230 Section 7
            "foo,bar",
            "foo, bar,",
            # RFC 7230 Errata ID: 4169
            "foo , ,bar,charlie",
            # Our tests
            "foo , ,bar,charlie",
            ",foo , ,bar,charlie",
            ",foo , ,bar,charlie,",
            ",\t ,,,  \t \t,   ,\t\t\t,foo \t\t,, bar,  ,\tcharlie \t,,  ,",
        ],
    )
    def test_valid(self, header_value):
        regex = _list_1_or_more__compiled_re(element_re="([a-z]+)")
        assert regex.match(header_value)


class TestAccept__parsing:
    @pytest.mark.parametrize(
        "value",
        [
            ", ",
            ", , ",
            "noslash",
            "/",
            "text/",
            "/html",
            "text/html;",
            "text/html;param",
            "text/html;param=",
            "text/html ;param=val;",
            "text/html; param=val;",
            "text/html;param=val;",
            "text/html;param=\x19",
            "text/html;param=\x22",
            "text/html;param=\x5c",
            "text/html;param=\x7f",
            r'text/html;param="\"',
            r'text/html;param="\\\"',
            r'text/html;param="\\""',
            'text/html;param="\\\x19"',
            'text/html;param="\\\x7f"',
            "text/html;q",
            "text/html;q=",
            "text/html;q=-1",
            "text/html;q=2",
            "text/html;q=1.001",
            "text/html;q=0.0001",
            "text/html;q=00",
            "text/html;q=01",
            "text/html;q=00.1",
            "text/html,q=0.1",
            "text/html;q =1",
            "text/html;q= 1",
            "text/html;q=1;",
            "text/html;param;q=1",
            "text/html;q=1;extparam;",
            "text/html;q=1;extparam=val;",
            'text/html;q=1;extparam="val";',
            'text/html;q=1;extparam="',
            'text/html;q=1;extparam="val',
            'text/html;q=1;extparam=val"',
            "text/html;q=1;extparam=\x19",
            "text/html;q=1;extparam=\x22",
            "text/html;q=1;extparam=\x5c",
            "text/html;q=1;extparam=\x7f",
            r'text/html;q=1;extparam="\"',
            r'text/html;q=1;extparam="\\\"',
            r'text/html;q=1;extparam="\\""',
            'text/html;q=1;extparam="\\\x19"',
            'text/html;q=1;extparam="\\\x7f"',
            "text/html;param=\x19;q=1;extparam",
            "text/html;param=val;q=1;extparam=\x19",
        ],
    )
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            Accept.parse(value=value)

    @pytest.mark.parametrize(
        "value, expected_list",
        [
            # Examples from RFC 7231, Section 5.3.2 "Accept":
            (
                "audio/*; q=0.2, audio/basic",
                [("audio/*", 0.2, (), ()), ("audio/basic", 1.0, (), ())],
            ),
            (
                "text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c",
                [
                    ("text/plain", 0.5, (), ()),
                    ("text/html", 1.0, (), ()),
                    ("text/x-dvi", 0.8, (), ()),
                    ("text/x-c", 1.0, (), ()),
                ],
            ),
            (
                "text/*, text/plain, text/plain;format=flowed, */*",
                [
                    ("text/*", 1.0, (), ()),
                    ("text/plain", 1.0, (), ()),
                    ("text/plain;format=flowed", 1.0, (("format", "flowed"),), ()),
                    ("*/*", 1.0, (), ()),
                ],
            ),
            (
                "text/*;q=0.3, text/html;q=0.7, text/html;level=1, "
                "text/html;level=2;q=0.4, */*;q=0.5",
                [
                    ("text/*", 0.3, (), ()),
                    ("text/html", 0.7, (), ()),
                    ("text/html;level=1", 1.0, (("level", "1"),), ()),
                    ("text/html;level=2", 0.4, (("level", "2"),), ()),
                    ("*/*", 0.5, (), ()),
                ],
            ),
            # Our tests
            ("", []),
            (",", []),
            (", ,", []),
            (
                "*/*, text/*, text/html",
                [
                    ("*/*", 1.0, (), ()),
                    ("text/*", 1.0, (), ()),
                    ("text/html", 1.0, (), ()),
                ],
            ),
            # It does not seem from RFC 7231, section 5.3.2 "Accept" that the '*'
            # in a range like '*/html' was intended to have any special meaning
            # (the section lists '*/*', 'type/*' and 'type/subtype', but not
            # '*/subtype'). However, because type and subtype are tokens (section
            # 3.1.1.1), and a token may contain '*'s, '*/subtype' is valid.
            ("*/html", [("*/html", 1.0, (), ())]),
            (
                'text/html \t;\t param1=val1\t; param2="val2" ' + r'; param3="\"\\\\"',
                [
                    (
                        r'text/html;param1=val1;param2=val2;param3="\"\\\\"',
                        1.0,
                        (("param1", "val1"), ("param2", "val2"), ("param3", r'"\\')),
                        (),
                    )
                ],
            ),
            (
                "text/html;param=!#$%&'*+-.^_`|~09AZaz",
                [
                    (
                        "text/html;param=!#$%&'*+-.^_`|~09AZaz",
                        1.0,
                        (("param", "!#$%&'*+-.^_`|~09AZaz"),),
                        (),
                    )
                ],
            ),
            ('text/html;param=""', [('text/html;param=""', 1.0, (("param", ""),), ())]),
            (
                'text/html;param="\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"',
                [
                    (
                        'text/html;param="\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"',
                        1.0,
                        (("param", "\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"),),
                        (),
                    )
                ],
            ),
            (
                'text/html;param="\x80\x81\xfe\xff\\\x22\\\x5c"',
                [
                    (
                        'text/html;param="\x80\x81\xfe\xff\\\x22\\\x5c"',
                        1.0,
                        (("param", "\x80\x81\xfe\xff\x22\x5c"),),
                        (),
                    )
                ],
            ),
            (
                'text/html;param="\\\t\\ \\\x21\\\x7e\\\x80\\\xff"',
                [
                    (
                        'text/html;param="\t \x21\x7e\x80\xff"',
                        1.0,
                        (("param", "\t \x21\x7e\x80\xff"),),
                        (),
                    )
                ],
            ),
            (
                "text/html;param='val'",
                # This makes it look like the media type parameter value could be
                # surrounded with single quotes instead of double quotes, but the
                # single quotes are actually part of the media type parameter value
                # token
                [("text/html;param='val'", 1.0, (("param", "'val'"),), ())],
            ),
            ("text/html;q=0.9", [("text/html", 0.9, (), ())]),
            ("text/html;q=0", [("text/html", 0.0, (), ())]),
            ("text/html;q=0.0", [("text/html", 0.0, (), ())]),
            ("text/html;q=0.00", [("text/html", 0.0, (), ())]),
            ("text/html;q=0.000", [("text/html", 0.0, (), ())]),
            ("text/html;q=1", [("text/html", 1.0, (), ())]),
            ("text/html;q=1.0", [("text/html", 1.0, (), ())]),
            ("text/html;q=1.00", [("text/html", 1.0, (), ())]),
            ("text/html;q=1.000", [("text/html", 1.0, (), ())]),
            ("text/html;q=0.1", [("text/html", 0.1, (), ())]),
            ("text/html;q=0.87", [("text/html", 0.87, (), ())]),
            ("text/html;q=0.382", [("text/html", 0.382, (), ())]),
            ("text/html;Q=0.382", [("text/html", 0.382, (), ())]),
            ("text/html ;Q=0.382", [("text/html", 0.382, (), ())]),
            ("text/html; Q=0.382", [("text/html", 0.382, (), ())]),
            ("text/html  ;  Q=0.382", [("text/html", 0.382, (), ())]),
            ("text/html;q=0.9;q=0.8", [("text/html", 0.9, (), (("q", "0.8"),))]),
            (
                "text/html;q=1;q=1;q=1",
                [("text/html", 1.0, (), (("q", "1"), ("q", "1")))],
            ),
            (
                'text/html;q=0.9;extparam1;extparam2=val2;extparam3="val3"',
                [
                    (
                        "text/html",
                        0.9,
                        (),
                        ("extparam1", ("extparam2", "val2"), ("extparam3", "val3")),
                    )
                ],
            ),
            (
                "text/html;q=1;extparam=!#$%&'*+-.^_`|~09AZaz",
                [("text/html", 1.0, (), (("extparam", "!#$%&'*+-.^_`|~09AZaz"),))],
            ),
            (
                'text/html;q=1;extparam=""',
                [("text/html", 1.0, (), (("extparam", ""),))],
            ),
            (
                'text/html;q=1;extparam="\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"',
                [
                    (
                        "text/html",
                        1.0,
                        (),
                        (("extparam", "\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"),),
                    )
                ],
            ),
            (
                'text/html;q=1;extparam="\x80\x81\xfe\xff\\\x22\\\x5c"',
                [("text/html", 1.0, (), (("extparam", "\x80\x81\xfe\xff\x22\x5c"),))],
            ),
            (
                'text/html;q=1;extparam="\\\t\\ \\\x21\\\x7e\\\x80\\\xff"',
                [("text/html", 1.0, (), (("extparam", "\t \x21\x7e\x80\xff"),))],
            ),
            (
                "text/html;q=1;extparam='val'",
                # This makes it look like the extension parameter value could be
                # surrounded with single quotes instead of double quotes, but the
                # single quotes are actually part of the extension parameter value
                # token
                [("text/html", 1.0, (), (("extparam", "'val'"),))],
            ),
            (
                'text/html;param1="val1";param2=val2;q=0.9;extparam1="val1"'
                ";extparam2;extparam3=val3",
                [
                    (
                        "text/html;param1=val1;param2=val2",
                        0.9,
                        (("param1", "val1"), ("param2", "val2")),
                        (("extparam1", "val1"), "extparam2", ("extparam3", "val3")),
                    )
                ],
            ),
            (
                ", ,, a/b \t;\t p1=1  ;\t\tp2=2  ;  q=0.6\t \t;\t\t e1\t; e2,  ,",
                [("a/b;p1=1;p2=2", 0.6, (("p1", "1"), ("p2", "2")), ("e1", "e2"))],
            ),
            (
                (
                    ",\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, "
                    + "g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,"
                ),
                [
                    ("a/b", 1.0, (), ("e1", ("e2", "v2"))),
                    ("c/d", 1.0, (), ()),
                    ("e/f;p1=v1", 0.0, (("p1", "v1"),), ("e1",)),
                    ("g/h;p1=v1;p2=v2", 0.5, (("p1", "v1"), ("p2", "v2")), ()),
                ],
            ),
        ],
    )
    def test_parse__valid_header(self, value, expected_list):
        returned = Accept.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list

    @pytest.mark.parametrize(
        "offer, expected_return, expected_str",
        [
            ["text/html", ("text", "html", ()), "text/html"],
            [
                "text/html;charset=utf8",
                ("text", "html", (("charset", "utf8"),)),
                "text/html;charset=utf8",
            ],
            [
                "text/html;charset=utf8;x-version=1",
                ("text", "html", (("charset", "utf8"), ("x-version", "1"))),
                "text/html;charset=utf8;x-version=1",
            ],
            [
                "text/HtMl;cHaRseT=UtF-8;X-Version=1",
                ("text", "html", (("charset", "UtF-8"), ("x-version", "1"))),
                "text/html;charset=UtF-8;x-version=1",
            ],
        ],
    )
    def test_parse_offer__valid(self, offer, expected_return, expected_str):
        result = Accept.parse_offer(offer)
        assert result == expected_return
        assert str(result) == expected_str
        assert result is Accept.parse_offer(result)

    @pytest.mark.parametrize(
        "offer",
        [
            "",
            "foo",
            "foo/bar/baz",
            "*/plain",
            "*/plain;charset=utf8",
            "*/plain;charset=utf8;x-version=1",
            "*/*;charset=utf8",
            "text/*;charset=utf8",
            "text/*",
            "*/*",
        ],
    )
    def test_parse_offer__invalid(self, offer):
        with pytest.raises(ValueError):
            Accept.parse_offer(offer)


class TestAccept__valid:
    def test___init___(self):
        header_value = (
            ",\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, "
            + "g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,"
        )
        instance = Accept(header_value)
        assert instance.header_state == HeaderState.Valid
        assert instance.header_value == header_value
        assert instance.parsed == (
            ("a/b", 1.0, (), ("e1", ("e2", "v2"))),
            ("c/d", 1.0, (), ()),
            ("e/f;p1=v1", 0.0, (("p1", "v1"),), ("e1",)),
            ("g/h;p1=v1;p2=v2", 0.5, (("p1", "v1"), ("p2", "v2")), ()),
        )

    def test___bool__(self):
        instance = Accept("type/subtype")
        returned = bool(instance)
        assert returned is True

    @pytest.mark.parametrize(
        "header_value, expected_returned",
        [
            ("", "<Accept('')>"),
            (
                r',,text/html ; p1="\"\1\"" ; q=0.50; e1=1 ;e2  ,  text/plain ,',
                r"""<Accept('text/html;p1="\\"1\\"";q=0.5;e1=1;e2"""
                + ", text/plain')>",
            ),
            (
                ',\t, a/b ;  p1=1 ; p2=2 ;\t q=0.20 ;\te1="\\"\\1\\""\t; e2 ; '
                + "e3=3, c/d ,,",
                r"""<Accept('a/b;p1=1;p2=2;q=0.2;e1="\\"1\\"";e2""" + ";e3=3, c/d')>",
            ),
        ],
    )
    def test___repr__(self, header_value, expected_returned):
        instance = Accept(header_value)
        assert repr(instance) == expected_returned

    @pytest.mark.parametrize(
        "header_value, expected_returned",
        [
            ("", ""),
            (
                r',,text/html ; p1="\"\1\"" ; q=0.50; e1=1 ;e2  ,  text/plain ,',
                r'text/html;p1="\"1\"";q=0.5;e1=1;e2, text/plain',
            ),
            (
                ',\t, a/b ;  p1=1 ; p2=2 ;\t q=0.20 ;\te1="\\"\\1\\""\t; e2 ; '
                + "e3=3, c/d ,,",
                'a/b;p1=1;p2=2;q=0.2;e1="\\"1\\"";e2;e3=3, c/d',
            ),
        ],
    )
    def test___str__(self, header_value, expected_returned):
        instance = Accept(header_value)
        assert str(instance) == expected_returned

    def test_copy(self):
        instance = Accept("*/plain;charset=utf8;x-version=1")
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    @pytest.mark.parametrize(
        "header_value, returned",
        [
            ("tExt/HtMl", True),
            ("APPlication/XHTML+xml", True),
            ("appliCATION/xMl", True),
            ("TeXt/XmL", True),
            ("image/jpg", False),
            ("TeXt/Plain", False),
            ("image/jpg, text/html", True),
        ],
    )
    def test_accept_html(self, header_value, returned):
        instance = Accept(header_value)
        assert instance.accept_html() is returned

    @pytest.mark.parametrize(
        "header_value, returned",
        [
            ("tExt/HtMl", True),
            ("APPlication/XHTML+xml", True),
            ("appliCATION/xMl", True),
            ("TeXt/XmL", True),
            ("image/jpg", False),
            ("TeXt/Plain", False),
            ("image/jpg, text/html", True),
        ],
    )
    def test_accepts_html(self, header_value, returned):
        instance = Accept(header_value)
        assert instance.accepts_html is returned

    @pytest.mark.parametrize(
        "offers, expected_returned",
        [
            (["text/html;p=1;q=0.5"], []),
            (["text/html;q=0.5"], []),
            (["text/html;q=0.5;e=1"], []),
            (["text/html", "text/plain;p=1;q=0.5;e=1", "foo"], [("text/html", 1.0)]),
        ],
    )
    def test_acceptable_offers__invalid_offers(self, offers, expected_returned):
        assert Accept("text/html").acceptable_offers(offers=offers) == expected_returned

    @pytest.mark.parametrize(
        "header_value, offers, expected_returned",
        [
            # RFC 7231, section 5.3.2
            (
                "audio/*; q=0.2, audio/basic",
                ["audio/mpeg", "audio/basic"],
                [("audio/basic", 1.0), ("audio/mpeg", 0.2)],
            ),
            (
                "text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c",
                ["text/x-dvi", "text/x-c", "text/html", "text/plain"],
                [
                    ("text/x-c", 1.0),
                    ("text/html", 1.0),
                    ("text/x-dvi", 0.8),
                    ("text/plain", 0.5),
                ],
            ),
            (
                "text/*;q=0.3, text/html;q=0.7, text/html;level=1, "
                + "text/html;level=2;q=0.4, */*;q=0.5",
                [
                    "text/html;level=1",
                    "text/html",
                    "text/plain",
                    "image/jpeg",
                    "text/html;level=2",
                    "text/html;level=3",
                ],
                [
                    ("text/html;level=1", 1.0),
                    ("text/html", 0.7),
                    ("text/html;level=3", 0.7),
                    ("image/jpeg", 0.5),
                    ("text/html;level=2", 0.4),
                    ("text/plain", 0.3),
                ],
            ),
            # Our tests
            (
                "teXT/*;Q=0.5, TeXt/hTmL;LeVeL=1",
                ["tExT/HtMl;lEvEl=1", "TExt/PlAiN"],
                [("tExT/HtMl;lEvEl=1", 1.0), ("TExt/PlAiN", 0.5)],
            ),
            (
                "text/html, application/json",
                ["text/html", "application/json"],
                [("text/html", 1.0), ("application/json", 1.0)],
            ),
            (
                "text/html  ;\t level=1",
                ["text/html\t\t ; \tlevel=1"],
                [("text/html\t\t ; \tlevel=1", 1.0)],
            ),
            ("", ["text/html"], []),
            ("text/html, image/jpeg", ["audio/basic", "text/plain"], []),
            (
                r'text/html;p1=1;p2=2;p3="\""',
                [r'text/html;p1=1;p2="2";p3="\""'],
                [(r'text/html;p1=1;p2="2";p3="\""', 1.0)],
            ),
            ("text/html;p1=1", ["text/html;p1=2"], []),
            ("text/html", ["text/html;p1=1"], [("text/html;p1=1", 1.0)]),
            ("text/html;p1=1", ["text/html"], []),
            ("text/html", ["text/html"], [("text/html", 1.0)]),
            ("text/*", ["text/html;p=1"], [("text/html;p=1", 1.0)]),
            ("*/*", ["text/html;p=1"], [("text/html;p=1", 1.0)]),
            ("text/*", ["text/html"], [("text/html", 1.0)]),
            ("*/*", ["text/html"], [("text/html", 1.0)]),
            ("text/html;p1=1;q=0", ["text/html;p1=1"], []),
            ("text/html;q=0", ["text/html;p1=1", "text/html"], []),
            ("text/*;q=0", ["text/html;p1=1", "text/html", "text/plain"], []),
            (
                "*/*;q=0",
                ["text/html;p1=1", "text/html", "text/plain", "image/jpeg"],
                [],
            ),
            (
                "*/*;q=0, audio/mpeg",
                [
                    "text/html;p1=1",
                    "audio/mpeg",
                    "text/html",
                    "text/plain",
                    "image/jpeg",
                ],
                [("audio/mpeg", 1.0)],
            ),
            (
                "text/html;p1=1, text/html;q=0",
                ["text/html;p1=1"],
                [("text/html;p1=1", 1.0)],
            ),
            ("text/html, text/*;q=0", ["text/html"], [("text/html", 1.0)]),
            ("text/*, */*;q=0", ["text/html"], [("text/html", 1.0)]),
            ("text/html;q=0, text/html", ["text/html"], []),
            (
                "text/html",
                ["text/html;level=1", "text/html", "text/html;level=2"],
                [
                    ("text/html;level=1", 1.0),
                    ("text/html", 1.0),
                    ("text/html;level=2", 1.0),
                ],
            ),
            (
                "text/*;q=0.3, text/html;q=0, image/png, text/html;level=1, "
                + "text/html;level=2;q=0.4, image/jpeg;q=0.5",
                [
                    "text/html;level=1",
                    "text/html",
                    "text/plain",
                    "image/jpeg",
                    "text/html;level=2",
                    "text/html;level=3",
                    "audio/basic",
                ],
                [
                    ("text/html;level=1", 1.0),
                    ("image/jpeg", 0.5),
                    ("text/html;level=2", 0.4),
                    ("text/plain", 0.3),
                ],
            ),
            (
                "text/*;q=0.3, text/html;q=0.5, text/html;level=1;q=0.7",
                ["text/*", "*/*", "text/html", "image/*"],
                [("text/html", 0.5)],
            ),
            (
                "text/html;level=1;q=0.7",
                ["text/*", "*/*", "text/html", "text/html;level=1", "image/*"],
                [("text/html;level=1", 0.7)],
            ),
            ("*/*", ["text/*"], []),
            ("", ["text/*", "*/*", "text/html", "text/html;level=1", "image/*"], []),
        ],
    )
    def test_acceptable_offers__valid_offers(
        self, header_value, offers, expected_returned
    ):
        instance = Accept(header_value)
        returned = instance.acceptable_offers(offers=offers)
        assert returned == expected_returned

    def test_acceptable_offers_uses_AcceptOffer_objects(self):
        offer = AcceptOffer("text", "html", (("level", "1"),))
        instance = Accept("text/*;q=0.5")
        result = instance.acceptable_offers([offer])
        assert result == [(offer, 0.5)]

    def test_best_match(self):
        accept = Accept("text/html, foo/bar")
        assert accept.best_match(["text/html", "foo/bar"]) == "text/html"
        assert accept.best_match(["foo/bar", "text/html"]) == "foo/bar"

    def test_best_match_with_one_lower_q(self):
        accept = Accept("text/html, foo/bar;q=0.5")
        assert accept.best_match(["text/html", "foo/bar"]) == "text/html"
        accept = Accept("text/html;q=0.5, foo/bar")
        assert accept.best_match(["text/html", "foo/bar"]) == "foo/bar"

    def test_best_match_with_complex_q(self):
        accept = Accept("text/html, foo/bar;q=0.55, baz/gort;q=0.59")
        assert accept.best_match(["text/html", "foo/bar"]) == "text/html"
        accept = Accept("text/html;q=0.5, foo/bar;q=0.586, baz/gort;q=0.596")
        assert accept.best_match(["text/html", "baz/gort"]) == "baz/gort"

    def test_best_match_json(self):
        accept = Accept("text/html, */*; q=0.2")
        assert accept.best_match(["application/json"]) == "application/json"

    def test_best_match_mixedcase(self):
        accept = Accept("image/jpg; q=0.2, Image/pNg; Q=0.4, image/*; q=0.05")
        assert accept.best_match(["Image/JpG"]) == "Image/JpG"
        assert accept.best_match(["image/Tiff"]) == "image/Tiff"
        assert (
            accept.best_match(["image/Tiff", "image/PnG", "image/jpg"]) == "image/PnG"
        )

    def test_quality(self):
        accept = Accept("text/html")
        assert accept.quality("text/html") == 1
        accept = Accept("text/html;q=0.5")
        assert accept.quality("text/html") == 0.5
        accept = Accept("text/*;q=0.5, text/html")
        assert accept.quality("text/html") == 1
        assert accept.quality("text/bar") == 0.5

    def test_quality_not_found(self):
        accept = Accept("text/html")
        assert accept.quality("foo/bar") is None

    def test___contains__(self):
        accept = Accept("A/a, B/b, C/c, B/x;q=0")
        assert "A/a" in accept
        assert "A/b" not in accept
        assert "B/a" not in accept
        assert "B/x" not in accept
        for mask in ["*/*", "text/html", "TEXT/HTML"]:
            assert "text/html" in Accept(mask)


class TestAccept__missing:
    def test___init__(self):
        instance = Accept(None)
        assert instance.header_value is None
        assert instance.parsed is None
        assert instance.header_state == HeaderState.Missing

    def test___bool__(self):
        instance = Accept(None)
        returned = bool(instance)
        assert returned is False

    def test___repr__(self):
        instance = Accept(None)
        assert repr(instance) == "<Accept: Missing>"

    def test___str__(self):
        instance = Accept(None)
        assert str(instance) == "<no header in request>"

    def test_copy(self):
        instance = Accept(None)
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    def test_accept_html(self):
        instance = Accept(None)
        assert instance.accept_html() is True

    def test_accepts_html(self):
        instance = Accept(None)
        assert instance.accepts_html is True

    @pytest.mark.parametrize(
        "offers, expected_returned",
        [
            (["text/html;p=1;q=0.5"], []),
            (["text/html;q=0.5"], []),
            (["text/html;q=0.5;e=1"], []),
            (["text/html", "text/plain;p=1;q=0.5;e=1", "foo"], [("text/html", 1.0)]),
        ],
    )
    def test_acceptable_offers__invalid_offers(self, offers, expected_returned):
        result = Accept(None).acceptable_offers(offers=offers)
        assert result == expected_returned

    def test_acceptable_offers__valid_offers(self):
        instance = Accept(None)
        returned = instance.acceptable_offers(offers=["a/b", "c/d", "e/f"])
        assert returned == [("a/b", 1.0), ("c/d", 1.0), ("e/f", 1.0)]

    def test_best_match(self):
        accept = Accept(None)
        assert accept.best_match(["text/html", "audio/basic"]) == "text/html"
        assert accept.best_match(["audio/basic", "text/html"]) == "audio/basic"
        assert accept.best_match([], default_match="fallback") == "fallback"

    def test_quality(self):
        accept = Accept(None)
        assert accept.quality("text/subtype") == 1.0

    def test___contains__(self):
        accept = Accept(None)
        assert "text/subtype" in accept


class TestAccept__invalid:
    def test___init__(self):
        header_value = ", "
        instance = Accept(header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance.header_state == HeaderState.Invalid

    def test___bool__(self):
        instance = Accept(", ")
        returned = bool(instance)
        assert returned is False

    def test___repr__(self):
        instance = Accept("\x00")
        assert repr(instance) == "<Accept: Invalid>"

    def test___str__(self):
        instance = Accept(", ")
        assert str(instance) == "<invalid header value>"

    def test_copy(self):
        instance = Accept(", ")
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    def test_accept_html(self):
        instance = Accept(", ")
        assert instance.accept_html() is True

    def test_accepts_html(self):
        instance = Accept(", ")
        assert instance.accepts_html is True

    @pytest.mark.parametrize(
        "offers, expected_returned",
        [
            (["text/html;p=1;q=0.5"], []),
            (["text/html;q=0.5"], []),
            (["text/html;q=0.5;e=1"], []),
            (["text/html", "text/plain;p=1;q=0.5;e=1", "foo"], [("text/html", 1.0)]),
        ],
    )
    def test_acceptable_offers__invalid_offers(self, offers, expected_returned):
        assert Accept(", ").acceptable_offers(offers=offers) == expected_returned

    def test_acceptable_offers__valid_offers(self):
        instance = Accept(", ")
        returned = instance.acceptable_offers(offers=["a/b", "c/d", "e/f"])
        assert returned == [("a/b", 1.0), ("c/d", 1.0), ("e/f", 1.0)]

    def test_best_match(self):
        accept = Accept(", ")
        assert accept.best_match(["text/html", "audio/basic"]) == "text/html"
        assert accept.best_match(["audio/basic", "text/html"]) == "audio/basic"
        assert accept.best_match([], default_match="fallback") == "fallback"

    def test_quality(self):
        accept = Accept(None)
        assert accept.quality("text/subtype") == 1.0

    def test___contains__(self):
        accept = Accept(", ")
        assert "text/subtype" in accept


class TestAccept__add:
    invalid_values = [
        ", ",
        [", "],
        (", ",),
        {", ": 1.0},
        {", ;level=1": (1.0, ";e1=1")},
        "a/b, c/d;q=1;e1;",
        ["a/b", "c/d;q=1;e1;"],
        ("a/b", "c/d;q=1;e1;"),
        {"a/b": 1.0, "cd": 1.0},
        {"a/b": (1.0, ";e1=1"), "c/d": (1.0, ";e2=2;")},
        StringMe(", "),
        StringMe("a/b, c/d;q=1;e1;"),
    ]

    valid_nonempty_values_with_headers = [
        # str
        (
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # object with __str__
        (
            StringMe("a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1"),
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # list of strs
        (
            ["a/b;q=0.5", "c/d;p1=1;q=0", "e/f", "g/h;p1=1;q=1;e1=1"],
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ("a/b", 0.5, ""),
                ("c/d;p1=1", 0.0, ""),
                ("e/f", 1.0, ""),
                ("g/h;p1=1", 1.0, ";e1=1"),
            ],
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # list of 2-item tuples, without extension parameters
        (
            [("a/b", 0.5), ("c/d;p1=1", 0.0), ("e/f", 1.0), ("g/h;p1=1", 1.0)],
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1",
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ("a/b", 0.5),
                ("c/d;p1=1", 0.0, ""),
                "e/f",
                ("g/h;p1=1", 1.0, ";e1=1"),
            ],
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # tuple of strs
        (
            ("a/b;q=0.5", "c/d;p1=1;q=0", "e/f", "g/h;p1=1;q=1;e1=1"),
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ("a/b", 0.5, ""),
                ("c/d;p1=1", 0.0, ""),
                ("e/f", 1.0, ""),
                ("g/h;p1=1", 1.0, ";e1=1"),
            ),
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (("a/b", 0.5), ("c/d;p1=1", 0.0), ("e/f", 1.0), ("g/h;p1=1", 1.0)),
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1",
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ("a/b", 0.5),
                ("c/d;p1=1", 0.0, ""),
                "e/f",
                ("g/h;p1=1", 1.0, ";e1=1"),
            ),
            "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
        ),
        # dict
        (
            {"a/b": (0.5, ";e1=1"), "c/d": 0.0, "e/f;p1=1": (1.0, ";e1=1;e2=2")},
            "e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0",
        ),
    ]

    valid_empty_values = ["", [], (), {}, StringMe("")]

    valid_values_with_headers = valid_nonempty_values_with_headers + [
        [x, ""] for x in valid_empty_values
    ]

    # snapshots help confirm the instance is immutable
    def snapshot_instance(self, inst):
        return deepcopy(
            {
                "header_value": inst.header_value,
                "parsed": inst.parsed,
                "header_state": inst.header_state,
            }
        )

    # we want to test math with primitive python values and Accept instances
    @pytest.fixture(params=["primitive", "instance"])
    def maker(self, request):
        if request.param == "primitive":
            return lambda x: x
        return Accept

    # almost always add and radd are symmetrical so we can test both and
    # expect the same result
    @pytest.fixture(params=["add", "radd"])
    def fn(self, request):
        if request.param == "add":
            return lambda x, y: x + y
        return lambda x, y: y + x

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_values_with_headers,
    )
    def test_valid_add_missing(self, input_value, input_header, maker, fn):
        inst = Accept(input_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == input_header

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header

    def test_invalid_add_missing(self, maker, fn):
        inst = Accept("invalid")
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Invalid
        assert inst.header_value == "invalid"

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    def test_missing_add_missing(self, maker, fn):
        inst = Accept(None)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Missing
        assert inst.header_value is None

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize("valid_value, valid_header", valid_values_with_headers)
    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_valid_add_invalid(
        self, valid_value, valid_header, invalid_value, maker, fn
    ):
        inst = Accept(valid_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == valid_header

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == valid_header

    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_invalid_add_invalid(self, invalid_value, maker, fn):
        inst = Accept("invalid")
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Invalid
        assert inst.header_value == "invalid"

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_missing_add_invalid(self, invalid_value, maker, fn):
        inst = Accept(None)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Missing
        assert inst.header_value is None

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_nonempty_values_with_headers,
    )
    def test_nonempty_valid_add_valid(self, input_value, input_header, maker):
        seed_value = ",\t ,i/j, k/l;q=0.333,"
        inst = Accept(seed_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == seed_value

        result = inst + maker(input_value)
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == seed_value + ", " + input_header

        result = maker(input_value) + inst
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header + ", " + seed_value

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_nonempty_values_with_headers,
    )
    @pytest.mark.parametrize("empty_value", valid_empty_values)
    def test_nonempty_valid_add_empty(
        self, input_value, input_header, empty_value, maker, fn
    ):
        inst = Accept(input_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == input_header

        result = fn(inst, maker(empty_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header

    @pytest.mark.parametrize("empty_value", valid_empty_values)
    def test_empty_valid_add_empty(self, empty_value, maker, fn):
        expected_value = ""
        inst = Accept(empty_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == expected_value

        result = fn(inst, maker(empty_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == expected_value


class TestCreateAccept:
    def test_header_value_is_None(self):
        returned = create_accept_header(None)
        assert returned.header_state == HeaderState.Missing
        assert returned.header_value is None
        returned2 = create_accept_header(returned)
        assert returned2 is returned
        assert returned2.header_value is None

    def test_header_value_is_valid(self):
        header_value = "text/html, text/plain;q=0.9"
        returned = create_accept_header(header_value)
        assert returned.header_state == HeaderState.Valid
        assert returned.header_value == header_value
        returned2 = create_accept_header(returned)
        assert returned2 is returned
        assert returned2.header_value == header_value

    @pytest.mark.parametrize("header_value", [", ", "noslash"])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_header(header_value)
        assert returned.header_state == HeaderState.Invalid
        assert returned.header_value == header_value
        returned2 = create_accept_header(returned)
        assert returned2 is returned
        assert returned2.header_value == header_value


class TestAcceptProperty:
    def test_fget_header_is_valid(self):
        header_value = 'text/html;p1="1";p2=v2;q=0.9;e1="1";e2, audio/basic'
        request = Request.blank("/", environ={"HTTP_ACCEPT": header_value})
        property_ = accept_property()
        returned = property_.fget(request=request)
        assert returned.header_state is HeaderState.Valid
        assert returned.header_value == header_value

    def test_fget_header_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT": None})
        property_ = accept_property()
        returned = property_.fget(request=request)
        assert returned.header_state is HeaderState.Missing

    def test_fget_header_is_invalid(self):
        header_value = "invalid"
        request = Request.blank("/", environ={"HTTP_ACCEPT": header_value})
        property_ = accept_property()
        returned = property_.fget(request=request)
        assert returned.header_state is HeaderState.Invalid
        assert returned.header_value == header_value

    def test_fset_value_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        header_value = 'text/html;p1="1";p2=v2;q=0.9;e1="1";e2, audio/basic'
        property_ = accept_property()
        property_.fset(request=request, value=header_value)
        assert request.environ["HTTP_ACCEPT"] == header_value

    def test_fset_value_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        property_ = accept_property()
        property_.fset(request=request, value=None)
        assert "HTTP_ACCEPT" not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        header_value = "invalid"
        property_ = accept_property()
        property_.fset(request=request, value=header_value)
        assert request.environ["HTTP_ACCEPT"] == header_value

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("", ""),
            ([], ""),
            ((), ""),
            ({}, ""),
            # str
            (
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # list of strs
            (
                ["a/b;q=0.5", "c/d;p1=1;q=0", "e/f", "g/h;p1=1;q=1;e1=1"],
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # list of 3-item tuples, with extension parameters
            (
                [
                    ("a/b", 0.5, ""),
                    ("c/d;p1=1", 0.0, ""),
                    ("e/f", 1.0, ""),
                    ("g/h;p1=1", 1.0, ";e1=1"),
                ],
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # list of 2-item tuples, without extension parameters
            (
                [("a/b", 0.5), ("c/d;p1=1", 0.0), ("e/f", 1.0), ("g/h;p1=1", 1.0)],
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1",
            ),
            # list of a mixture of strs, 3-item tuples and 2-item tuples
            (
                [
                    ("a/b", 0.5),
                    ("c/d;p1=1", 0.0, ""),
                    "e/f",
                    ("g/h;p1=1", 1.0, ";e1=1"),
                ],
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # tuple of strs
            (
                ("a/b;q=0.5", "c/d;p1=1;q=0", "e/f", "g/h;p1=1;q=1;e1=1"),
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # tuple of 3-item tuples, with extension parameters
            (
                (
                    ("a/b", 0.5, ""),
                    ("c/d;p1=1", 0.0, ""),
                    ("e/f", 1.0, ""),
                    ("g/h;p1=1", 1.0, ";e1=1"),
                ),
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # tuple of 2-item tuples, without extension parameters
            (
                (("a/b", 0.5), ("c/d;p1=1", 0.0), ("e/f", 1.0), ("g/h;p1=1", 1.0)),
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1",
            ),
            # tuple of a mixture of strs, 3-item tuples and 2-item tuples
            (
                (
                    ("a/b", 0.5),
                    ("c/d;p1=1", 0.0, ""),
                    "e/f",
                    ("g/h;p1=1", 1.0, ";e1=1"),
                ),
                "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1",
            ),
            # dict
            (
                {"a/b": (0.5, ";e1=1"), "c/d": 0.0, "e/f;p1=1": (1.0, ";e1=1;e2=2")},
                "e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0",
            ),
        ],
    )
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        property_ = accept_property()
        property_.fset(request=request, value=value)
        assert request.environ["HTTP_ACCEPT"] == value_as_header

    @pytest.mark.parametrize(
        "header_value", ["", "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1"]
    )
    def test_fset_other_type_with___str__(self, header_value):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        property_ = accept_property()
        value = StringMe(header_value)
        property_.fset(request=request, value=value)
        assert request.environ["HTTP_ACCEPT"] == str(value)

    def test_fset_valid_Accept(self):
        request = Request.blank("/", environ={})
        header_value = "a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1"
        header = Accept(header_value)
        property_ = accept_property()
        property_.fset(request=request, value=header)
        assert request.environ["HTTP_ACCEPT"] == header.header_value

    def test_fset_missing_Accept(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        property_ = accept_property()
        header = Accept(None)
        property_.fset(request=request, value=header)
        assert "HTTP_ACCEPT" not in request.environ

    def test_fset_invalid_Accept(self):
        request = Request.blank("/", environ={})
        header_value = "invalid"
        header = Accept(header_value)
        property_ = accept_property()
        property_.fset(request=request, value=header)
        assert request.environ["HTTP_ACCEPT"] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT": "text/html"})
        property_ = accept_property()
        property_.fdel(request=request)
        assert "HTTP_ACCEPT" not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank("/")
        property_ = accept_property()
        property_.fdel(request=request)
        assert "HTTP_ACCEPT" not in request.environ


class TestAcceptCharset__parsing:
    @pytest.mark.parametrize(
        "value",
        [
            "",
            '"',
            "(",
            ")",
            "/",
            ":",
            ";",
            "<",
            "=",
            ">",
            "?",
            "@",
            "[",
            "\\",
            "]",
            "{",
            "}",
            "foo, bar, baz;q= 0.001",
            "foo , ,bar,charlie   ",
        ],
    )
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptCharset.parse(value=value)

    @pytest.mark.parametrize(
        "value, expected_list",
        [
            ("*", [("*", 1.0)]),
            ("!#$%&'*+-.^_`|~;q=0.5", [("!#$%&'*+-.^_`|~", 0.5)]),
            ("0123456789", [("0123456789", 1.0)]),
            (
                ",\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tcharlie \t,,  ,",
                [("foo", 0.345), ("bar", 0.456), ("charlie", 1.0)],
            ),
            (
                "iso-8859-5;q=0.372,unicode-1-1;q=0.977,UTF-8, *;q=0.000",
                [
                    ("iso-8859-5", 0.372),
                    ("unicode-1-1", 0.977),
                    ("UTF-8", 1.0),
                    ("*", 0.0),
                ],
            ),
            # RFC 7230 Section 7
            ("foo,bar", [("foo", 1.0), ("bar", 1.0)]),
            ("foo, bar,", [("foo", 1.0), ("bar", 1.0)]),
            # RFC 7230 Errata ID: 4169
            ("foo , ,bar,charlie", [("foo", 1.0), ("bar", 1.0), ("charlie", 1.0)]),
        ],
    )
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptCharset.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptCharset__valid:
    def test_parse__inherited(self):
        returned = AcceptCharset.parse(
            value=",iso-8859-5 ; q=0.333 , ,utf-8,unicode-1-1 ;q=0.90,"
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ("iso-8859-5", 0.333),
            ("utf-8", 1.0),
            ("unicode-1-1", 0.9),
        ]

    def test___init___valid_header(self):
        header_value = "iso-8859-5;q=0.372,unicode-1-1;q=0.977,UTF-8, *;q=0.000"
        instance = AcceptCharset(header_value)
        assert instance.header_state is HeaderState.Valid
        assert instance.header_value == header_value
        assert instance.parsed == (
            ("iso-8859-5", 0.372),
            ("unicode-1-1", 0.977),
            ("UTF-8", 1.0),
            ("*", 0.0),
        )

    def test___bool__(self):
        instance = AcceptCharset("valid-header")
        returned = bool(instance)
        assert returned is True

    def test___repr__(self):
        instance = AcceptCharset(",utf-7;q=0.200,UTF-8;q=0.300")
        assert repr(instance) == "<AcceptCharset('utf-7;q=0.2, UTF-8;q=0.3')>"

    def test___str__(self):
        header_value = (
            ", \t,iso-8859-5;q=0.000 \t, utf-8;q=1.000, UTF-7, "
            "unicode-1-1;q=0.210  ,"
        )
        instance = AcceptCharset(header_value)
        assert str(instance) == "iso-8859-5;q=0, utf-8, UTF-7, unicode-1-1;q=0.21"

    def test_copy(self):
        instance = AcceptCharset(",iso-8859-5 ; q=0.333 , ,utf-8,unicode-1-1 ;q=0.90,")
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    @pytest.mark.parametrize("header", ["*", "utf-8", "UTF-8"])
    def test___contains__match(self, header):
        assert "utf-8" in AcceptCharset(header)

    def test___contains__not(self):
        assert "utf-7" not in AcceptCharset("utf-8")
        assert "utf-7" not in AcceptCharset("utf-7;q=0")

    @pytest.mark.parametrize(
        "header_value, offers, returned",
        [
            ("UTF-7, unicode-1-1", ["UTF-8", "iso-8859-5"], []),
            (
                "utf-8, unicode-1-1, iSo-8859-5",
                ["UTF-8", "iso-8859-5"],
                [("UTF-8", 1.0), ("iso-8859-5", 1.0)],
            ),
            (
                "utF-8;q=0.2, uniCode-1-1;q=0.9, iSo-8859-5;q=0.8",
                ["iso-8859-5", "unicode-1-1", "utf-8"],
                [("unicode-1-1", 0.9), ("iso-8859-5", 0.8), ("utf-8", 0.2)],
            ),
            (
                "utf-8, unicode-1-1;q=0.9, iSo-8859-5;q=0.9",
                ["iso-8859-5", "utf-8", "unicode-1-1"],
                [("utf-8", 1.0), ("iso-8859-5", 0.9), ("unicode-1-1", 0.9)],
            ),
            ("*", ["UTF-8", "iso-8859-5"], [("UTF-8", 1.0), ("iso-8859-5", 1.0)]),
            ("*;q=0.8", ["UTF-8", "iso-8859-5"], [("UTF-8", 0.8), ("iso-8859-5", 0.8)]),
            ("UTF-7, *", ["UTF-8", "UTF-7"], [("UTF-8", 1.0), ("UTF-7", 1.0)]),
            ("UTF-7;q=0.5, *", ["UTF-7", "UTF-8"], [("UTF-8", 1.0), ("UTF-7", 0.5)]),
            ("UTF-8, *;q=0", ["UTF-7"], []),
            ("UTF-8, *;q=0", ["UTF-8"], [("UTF-8", 1.0)]),
            ("UTF-8;q=0, *", ["UTF-8"], []),
            ("UTF-8;q=0, *;q=0", ["UTF-8", "UTF-7"], []),
            ("UTF-8, UTF-8;q=0", ["UTF-8"], [("UTF-8", 1.0)]),
            (
                "UTF-8, UTF-8;q=0, UTF-7",
                ["UTF-8", "UTF-7"],
                [("UTF-8", 1.0), ("UTF-7", 1.0)],
            ),
            (
                "UTF-8;q=0.5, UTF-8;q=0.7, UTF-8;q=0.6, UTF-7",
                ["UTF-8", "UTF-7"],
                [("UTF-7", 1.0), ("UTF-8", 0.5)],
            ),
            (
                "UTF-8;q=0.8, *;q=0.9, *;q=0",
                ["UTF-8", "UTF-7"],
                [("UTF-7", 0.9), ("UTF-8", 0.8)],
            ),
            ("UTF-8;q=0.8, *;q=0, *;q=0.9", ["UTF-8", "UTF-7"], [("UTF-8", 0.8)]),
        ],
    )
    def test_acceptable_offers(self, header_value, offers, returned):
        instance = AcceptCharset(header_value)
        assert instance.acceptable_offers(offers=offers) == returned

    def test_best_match(self):
        accept = AcceptCharset("utf-8, iso-8859-5")
        assert accept.best_match(["utf-8", "iso-8859-5"]) == "utf-8"
        assert accept.best_match(["iso-8859-5", "utf-8"]) == "iso-8859-5"

    def test_best_match_with_one_lower_q(self):
        accept = AcceptCharset("utf-8, iso-8859-5;q=0.5")
        assert accept.best_match(["utf-8", "iso-8859-5"]) == "utf-8"
        accept = AcceptCharset("utf-8;q=0.5, iso-8859-5")
        assert accept.best_match(["utf-8", "iso-8859-5"]) == "iso-8859-5"

    def test_best_match_with_complex_q(self):
        accept = AcceptCharset("utf-8, iso-8859-5;q=0.55, utf-7;q=0.59")
        assert accept.best_match(["utf-8", "iso-8859-5"]) == "utf-8"
        accept = AcceptCharset("utf-8;q=0.5, iso-8859-5;q=0.586, utf-7;q=0.596")
        assert accept.best_match(["utf-8", "utf-7"]) == "utf-7"

    def test_best_match_mixedcase(self):
        accept = AcceptCharset("uTf-8; q=0.2, UtF-7; Q=0.4, *; q=0.05")
        assert accept.best_match(["UtF-8"]) == "UtF-8"
        assert accept.best_match(["IsO-8859-5"]) == "IsO-8859-5"
        assert accept.best_match(["iSo-8859-5", "uTF-7", "UtF-8"]) == "uTF-7"

    def test_best_match_zero_quality(self):
        assert AcceptCharset("utf-7, *;q=0").best_match(["utf-8"]) is None

    def test_quality(self):
        accept = AcceptCharset("utf-8")
        assert accept.quality("utf-8") == 1.0
        accept = AcceptCharset("utf-8;q=0.5")
        assert accept.quality("utf-8") == 0.5

    def test_quality_not_found(self):
        accept = AcceptCharset("utf-8")
        assert accept.quality("iso-8859-5") is None


class TestAcceptCharset__missing:
    def test___init__(self):
        instance = AcceptCharset(None)
        assert instance.header_state is HeaderState.Missing
        assert instance.header_value is None
        assert instance.parsed is None

    def test___bool__(self):
        instance = AcceptCharset(None)
        returned = bool(instance)
        assert returned is False

    def test___repr__(self):
        instance = AcceptCharset(None)
        assert repr(instance) == "<AcceptCharset: Missing>"

    def test___str__(self):
        instance = AcceptCharset(None)
        assert str(instance) == "<no header in request>"

    def test_copy(self):
        instance = AcceptCharset(None)
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    def test___contains__(self):
        assert "char-set" in AcceptCharset(None)

    def test_acceptable_offers(self):
        instance = AcceptCharset(None)
        returned = instance.acceptable_offers(offers=["utf-8", "utf-7", "unicode-1-1"])
        assert returned == [("utf-8", 1.0), ("utf-7", 1.0), ("unicode-1-1", 1.0)]

    def test_best_match(self):
        accept = AcceptCharset(None)
        assert accept.best_match(["utf-8", "iso-8859-5"]) == "utf-8"
        assert accept.best_match(["iso-8859-5", "utf-8"]) == "iso-8859-5"
        assert accept.best_match([], default_match="fallback") == "fallback"

    def test_quality(self):
        instance = AcceptCharset(None)
        returned = instance.quality(offer="char-set")
        assert returned == 1.0


class TestAcceptCharset__invalid:
    def test___init__(self):
        header_value = "invalid header"
        instance = AcceptCharset(header_value)
        assert instance.header_state is HeaderState.Invalid
        assert instance.header_value == header_value
        assert instance.parsed is None

    def test___bool__(self):
        instance = AcceptCharset("")
        returned = bool(instance)
        assert returned is False

    def test___repr__(self):
        instance = AcceptCharset("\x00")
        assert repr(instance) == "<AcceptCharset: Invalid>"

    def test___str__(self):
        instance = AcceptCharset("")
        assert str(instance) == "<invalid header value>"

    def test_copy(self):
        instance = AcceptCharset("")
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    def test___contains__(self):
        assert "char-set" in AcceptCharset(None)

    def test_acceptable_offers(self):
        instance = AcceptCharset("")
        returned = instance.acceptable_offers(offers=["utf-8", "utf-7", "unicode-1-1"])
        assert returned == [("utf-8", 1.0), ("utf-7", 1.0), ("unicode-1-1", 1.0)]

    def test_best_match(self):
        accept = AcceptCharset("")
        assert accept.best_match(["utf-8", "iso-8859-5"]) == "utf-8"
        assert accept.best_match(["iso-8859-5", "utf-8"]) == "iso-8859-5"
        assert accept.best_match([], default_match="fallback") == "fallback"

    def test_quality(self):
        instance = AcceptCharset("")
        returned = instance.quality(offer="char-set")
        assert returned == 1.0


class TestAcceptCharset__add:
    invalid_values = [
        "",
        [],
        (),
        {},
        "UTF/8",
        ["UTF/8"],
        ("UTF/8",),
        {"UTF/8": 1.0},
        StringMe(""),
        StringMe("UTF/8"),
    ]

    valid_values_with_headers = [
        (
            "UTF-7;q=0.5, unicode-1-1;q=0, UTF-8",
            "UTF-7;q=0.5, unicode-1-1;q=0, UTF-8",
        ),
        (
            [("UTF-7", 0.5), ("unicode-1-1", 0.0), "UTF-8"],
            "UTF-7;q=0.5, unicode-1-1;q=0, UTF-8",
        ),
        (
            (("UTF-7", 0.5), ("unicode-1-1", 0.0), "UTF-8"),
            "UTF-7;q=0.5, unicode-1-1;q=0, UTF-8",
        ),
        (
            {"UTF-7": 0.5, "unicode-1-1": 0.0, "UTF-8": 1.0},
            "UTF-8, UTF-7;q=0.5, unicode-1-1;q=0",
        ),
        (
            StringMe("UTF-7;q=0.5, unicode-1-1;q=0, UTF-8"),
            "UTF-7;q=0.5, unicode-1-1;q=0, UTF-8",
        ),
    ]

    # snapshots help confirm the instance is immutable
    def snapshot_instance(self, inst):
        return deepcopy(
            {
                "header_value": inst.header_value,
                "parsed": inst.parsed,
                "header_state": inst.header_state,
            }
        )

    # we want to test math with primitive python values and Accept instances
    @pytest.fixture(params=["primitive", "instance"])
    def maker(self, request):
        if request.param == "primitive":
            return lambda x: x
        return AcceptCharset

    # almost always add and radd are symmetrical so we can test both and
    # expect the same result
    @pytest.fixture(params=["add", "radd"])
    def fn(self, request):
        if request.param == "add":
            return lambda x, y: x + y
        return lambda x, y: y + x

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_values_with_headers,
    )
    def test_valid_add_missing(self, input_value, input_header, maker, fn):
        inst = AcceptCharset(input_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == input_header

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header

    def test_invalid_add_missing(self, maker, fn):
        invalid_value = "UTF/8"
        inst = AcceptCharset(invalid_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Invalid
        assert inst.header_value == invalid_value

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    def test_missing_add_missing(self, maker, fn):
        inst = AcceptCharset(None)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Missing
        assert inst.header_value is None

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize("valid_value, valid_header", valid_values_with_headers)
    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_valid_add_invalid(
        self, valid_value, valid_header, invalid_value, maker, fn
    ):
        inst = AcceptCharset(valid_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == valid_header

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == valid_header

    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_invalid_add_invalid(self, invalid_value, maker, fn):
        inst = AcceptCharset("")
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Invalid
        assert inst.header_value == ""

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_missing_add_invalid(self, invalid_value, maker, fn):
        inst = AcceptCharset(None)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Missing
        assert inst.header_value is None

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_values_with_headers,
    )
    def test_valid_add_valid(self, input_value, input_header, maker):
        seed_value = "iso-8859-5"
        inst = AcceptCharset(seed_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == seed_value

        result = inst + maker(input_value)
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == seed_value + ", " + input_header

        result = maker(input_value) + inst
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header + ", " + seed_value


class TestCreateAcceptCharsetHeader:
    def test_header_value_is_valid(self):
        header_value = "iso-8859-5, unicode-1-1;q=0.8"
        returned = create_accept_charset_header(header_value)
        assert isinstance(returned, AcceptCharset)
        assert returned.header_state is HeaderState.Valid
        assert returned.header_value == header_value
        returned2 = create_accept_charset_header(returned)
        assert returned2._header_value == returned._header_value

    def test_header_value_is_None(self):
        returned = create_accept_charset_header(None)
        assert isinstance(returned, AcceptCharset)
        assert returned.header_state is HeaderState.Missing
        assert returned.header_value is None
        returned2 = create_accept_charset_header(returned)
        assert returned2._header_value is None

    @pytest.mark.parametrize("header_value", ["", "iso-8859-5, unicode/1"])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_charset_header(header_value)
        assert isinstance(returned, AcceptCharset)
        assert returned.header_state is HeaderState.Invalid
        assert returned.header_value == header_value
        returned2 = create_accept_charset_header(returned)
        assert returned2._header_value == returned._header_value


class TestAcceptCharsetProperty:
    def test_fget_header_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": None})
        property_ = accept_charset_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptCharset)
        assert returned.header_state is HeaderState.Missing

    def test_fget_header_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "UTF-8"})
        property_ = accept_charset_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptCharset)
        assert returned.header_state is HeaderState.Valid

    def test_fget_header_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": ""})
        property_ = accept_charset_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptCharset)
        assert returned.header_state is HeaderState.Invalid

    def test_fset_value_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "UTF-8"})
        property_ = accept_charset_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_CHARSET" not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "UTF-8"})
        property_ = accept_charset_property()
        property_.fset(request=request, value="")
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Invalid
        assert request.environ["HTTP_ACCEPT_CHARSET"] == ""

    def test_fset_value_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "UTF-8"})
        property_ = accept_charset_property()
        property_.fset(request=request, value="UTF-7")
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_CHARSET"] == "UTF-7"

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            (
                "utf-8;q=0.5, iso-8859-5;q=0, utf-7",
                "utf-8;q=0.5, iso-8859-5;q=0, utf-7",
            ),
            (
                [("utf-8", 0.5), ("iso-8859-5", 0.0), "utf-7"],
                "utf-8;q=0.5, iso-8859-5;q=0, utf-7",
            ),
            (
                (("utf-8", 0.5), ("iso-8859-5", 0.0), "utf-7"),
                "utf-8;q=0.5, iso-8859-5;q=0, utf-7",
            ),
            (
                {"utf-8": 0.5, "iso-8859-5": 0.0, "utf-7": 1.0},
                "utf-7, utf-8;q=0.5, iso-8859-5;q=0",
            ),
        ],
    )
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": ""})
        property_ = accept_charset_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_CHARSET"] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": ""})
        property_ = accept_charset_property()
        value = StringMe("utf-8;q=0.5, iso-8859-5;q=0, utf-7")
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_CHARSET"] == str(value)

    def test_fset_missing_AcceptCharset(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "utf-8"})
        property_ = accept_charset_property()
        header = AcceptCharset(None)
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_CHARSET" not in request.environ

    def test_fset_valid_AcceptCharset(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "utf-8"})
        property_ = accept_charset_property()
        header = AcceptCharset("utf-7")
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_CHARSET"] == header.header_value

    def test_fset_invalid_AcceptCharset(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "utf-8"})
        property_ = accept_charset_property()
        header = AcceptCharset("")
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Invalid
        assert request.environ["HTTP_ACCEPT_CHARSET"] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_CHARSET": "utf-8"})
        property_ = accept_charset_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_CHARSET" not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank("/")
        property_ = accept_charset_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_charset, AcceptCharset)
        assert request.accept_charset.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_CHARSET" not in request.environ


class TestAcceptEncoding__parsing:
    @pytest.mark.parametrize(
        "value",
        [
            '"',
            "(",
            ")",
            "/",
            ":",
            ";",
            "<",
            "=",
            ">",
            "?",
            "@",
            "[",
            "\\",
            "]",
            "{",
            "}",
            ", ",
            ", , ",
            "gzip;q=1.0, identity; q =0.5, *;q=0",
        ],
    )
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptEncoding.parse(value=value)

    @pytest.mark.parametrize(
        "value, expected_list",
        [
            (",", []),
            (", ,", []),
            ("*", [("*", 1.0)]),
            ("!#$%&'*+-.^_`|~;q=0.5", [("!#$%&'*+-.^_`|~", 0.5)]),
            ("0123456789", [("0123456789", 1.0)]),
            (
                ",,\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tCHARLIE \t,,  ,",
                [("foo", 0.345), ("bar", 0.456), ("CHARLIE", 1.0)],
            ),
            # RFC 7231, section 5.3.4
            ("compress, gzip", [("compress", 1.0), ("gzip", 1.0)]),
            ("", []),
            ("*", [("*", 1.0)]),
            ("compress;q=0.5, gzip;q=1.0", [("compress", 0.5), ("gzip", 1.0)]),
            (
                "gzip;q=1.0, identity; q=0.5, *;q=0",
                [("gzip", 1.0), ("identity", 0.5), ("*", 0.0)],
            ),
        ],
    )
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptEncoding.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptEncoding__valid:
    def test___init___(self):
        header_value = ",,\t gzip;q=1.0, identity; q=0, *;q=0.5 \t ,"
        instance = AcceptEncoding(header_value)
        assert instance.header_state is HeaderState.Valid
        assert instance.header_value == header_value
        assert instance.parsed == (("gzip", 1.0), ("identity", 0.0), ("*", 0.5))

    def test___bool__(self):
        instance = AcceptEncoding("gzip")
        returned = bool(instance)
        assert returned is True

    @pytest.mark.parametrize(
        "header_value, expected_returned",
        [
            ("", "<AcceptEncoding('')>"),
            (
                ",\t, a ;\t q=0.20 , b ,',",
                # single quote is valid character in token
                """<AcceptEncoding("a;q=0.2, b, \'")>""",
            ),
        ],
    )
    def test___repr__(self, header_value, expected_returned):
        instance = AcceptEncoding(header_value)
        assert repr(instance) == expected_returned

    @pytest.mark.parametrize(
        "header_value, expected_returned",
        [("", ""), (",\t, a ;\t q=0.20 , b ,',", "a;q=0.2, b, '")],
    )
    def test___str__(self, header_value, expected_returned):
        instance = AcceptEncoding(header_value)
        assert str(instance) == expected_returned

    def test_copy(self):
        instance = AcceptEncoding("gzip")
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    @pytest.mark.parametrize(
        "header_value, offers, expected_returned",
        [
            ("", [], []),
            ("gzip, compress", [], []),
            ("", ["gzip", "deflate"], []),
            ("", ["gzip", "identity"], [("identity", 1.0)]),
            ("compress, deflate, gzip", ["identity"], [("identity", 1.0)]),
            ("compress, identity;q=0, gzip", ["identity"], []),
            # *;q=0 does not make sense, but is valid
            ("*;q=0", ["identity"], []),
            ("*;q=0, deflate, gzip", ["identity"], []),
            ("*;q=0, deflate, identity;q=0, gzip", ["identity"], []),
            ("*;q=0, deflate, identity;q=0.1, gzip", ["identity"], [("identity", 0.1)]),
            (
                "compress, deflate, gzip",
                ["identity", "gzip"],
                [("identity", 1.0), ("gzip", 1.0)],
            ),
            (
                "compress, deflate, gzip",
                ["gzip", "identity"],
                [("gzip", 1.0), ("identity", 1.0)],
            ),
            (
                "IDentity;q=0.5, deflATE;q=0, gZIP;q=0, COMPress",
                ["GZip", "DEFlate", "IDENTity", "comPRESS"],
                [("comPRESS", 1.0), ("IDENTity", 0.5)],
            ),
            (
                "compress;q=0, identity, *;q=0.5, identity;q=0, *;q=0, compress",
                # does not make sense, but is valid
                ["compress", "identity", "deflate", "gzip"],
                [("identity", 1.0), ("deflate", 0.5), ("gzip", 0.5)],
            ),
        ],
    )
    def test_acceptable_offers(self, header_value, offers, expected_returned):
        instance = AcceptEncoding(header_value)
        returned = instance.acceptable_offers(offers=offers)
        assert returned == expected_returned

    def test_best_match(self):
        accept = AcceptEncoding("gzip, iso-8859-5")
        assert accept.best_match(["gzip", "iso-8859-5"]) == "gzip"
        assert accept.best_match(["iso-8859-5", "gzip"]) == "iso-8859-5"

    def test_best_match_with_one_lower_q(self):
        accept = AcceptEncoding("gzip, compress;q=0.5")
        assert accept.best_match(["gzip", "compress"]) == "gzip"
        accept = AcceptEncoding("gzip;q=0.5, compress")
        assert accept.best_match(["gzip", "compress"]) == "compress"

    def test_best_match_with_complex_q(self):
        accept = AcceptEncoding("gzip, compress;q=0.55, deflate;q=0.59")
        assert accept.best_match(["gzip", "compress"]) == "gzip"
        accept = AcceptEncoding("gzip;q=0.5, compress;q=0.586, deflate;q=0.596")
        assert accept.best_match(["gzip", "deflate"]) == "deflate"

    def test_best_match_mixedcase(self):
        accept = AcceptEncoding("gZiP; q=0.2, COMPress; Q=0.4, *; q=0.05")
        assert accept.best_match(["gzIP"]) == "gzIP"
        assert accept.best_match(["DeFlAte"]) == "DeFlAte"
        assert accept.best_match(["deflaTe", "compRess", "UtF-8"]) == "compRess"

    def test_best_match_zero_quality(self):
        assert AcceptEncoding("deflate, *;q=0").best_match(["gzip"]) is None
        assert "content-coding" not in AcceptEncoding("*;q=0")

    def test_quality(self):
        accept = AcceptEncoding("gzip")
        assert accept.quality("gzip") == 1
        accept = AcceptEncoding("gzip;q=0.5")
        assert accept.quality("gzip") == 0.5

    def test_quality_with_identity(self):
        accept = AcceptEncoding("gzip;q=0.5")
        assert accept.quality("identity") == 1.0
        accept = AcceptEncoding("gzip;q=0.5, identity;q=0")
        assert accept.quality("identity") is None
        accept = AcceptEncoding("gzip;q=0.5, identity;q=0.2, *;q=0")
        assert accept.quality("identity") == 0.2
        assert accept.quality("foo") is None

    def test_quality_not_found(self):
        accept = AcceptEncoding("gzip")
        assert accept.quality("compress") is None

    def test___contains__(self):
        accept = AcceptEncoding("gzip, compress")
        assert "gzip" in accept
        assert "deflate" not in accept
        for mask in ["*", "gzip", "gZIP"]:
            accept = AcceptEncoding(mask)
            assert "gzip" in accept
            assert "identity" in accept


class TestAcceptEncoding__missing:
    def test___init__(self):
        instance = AcceptEncoding(None)
        assert instance.header_state is HeaderState.Missing
        assert instance.header_value is None
        assert instance.parsed is None

    def test___bool__(self):
        instance = AcceptEncoding(None)
        returned = bool(instance)
        assert returned is False

    def test___repr__(self):
        instance = AcceptEncoding(None)
        assert repr(instance) == "<AcceptEncoding: Missing>"

    def test___str__(self):
        instance = AcceptEncoding(None)
        assert str(instance) == "<no header in request>"

    def test_copy(self):
        instance = AcceptEncoding(None)
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    def test_acceptable_offers(self):
        instance = AcceptEncoding(None)
        returned = instance.acceptable_offers(offers=["a", "b", "c"])
        assert returned == [("a", 1.0), ("b", 1.0), ("c", 1.0)]

    def test_best_match(self):
        accept = AcceptEncoding(None)
        assert accept.best_match(["gzip", "compress"]) == "gzip"
        assert accept.best_match(["compress", "gzip"]) == "compress"
        assert accept.best_match(["compress", "gzip", "identity"]) == "compress"
        assert accept.best_match([], default_match="fallback") == "fallback"

    def test_quality(self):
        instance = AcceptEncoding(None)
        assert instance.quality("content-coding") == 1.0
        assert instance.quality("identity") == 1.0

    def test___contains__(self):
        instance = AcceptEncoding(None)
        returned = "content-coding" in instance
        assert returned is True


class TestAcceptEncoding__invalid:
    def test___init__(self):
        header_value = "invalid header"
        instance = AcceptEncoding(header_value)
        assert instance.header_state is HeaderState.Invalid
        assert instance.header_value == header_value
        assert instance.parsed is None

    def test___bool__(self):
        instance = AcceptEncoding(", ")
        returned = bool(instance)
        assert returned is False

    def test___repr__(self):
        instance = AcceptEncoding("\x00")
        assert repr(instance) == "<AcceptEncoding: Invalid>"

    def test___str__(self):
        instance = AcceptEncoding(", ")
        assert str(instance) == "<invalid header value>"

    def test_copy(self):
        instance = AcceptEncoding(", ")
        result = instance.copy()
        assert instance is not result
        assert instance.header_value == result.header_value
        assert instance.header_state == result.header_state
        assert instance.parsed == result.parsed

    def test_acceptable_offers(self):
        instance = AcceptEncoding(", ")
        returned = instance.acceptable_offers(offers=["a", "b", "c"])
        assert returned == [("a", 1.0), ("b", 1.0), ("c", 1.0)]

    def test_best_match(self):
        accept = AcceptEncoding(", ")
        assert accept.best_match(["gzip", "compress"]) == "gzip"
        assert accept.best_match(["compress", "gzip"]) == "compress"
        assert accept.best_match(["compress", "gzip", "identity"]) == "compress"
        assert accept.best_match([], default_match="fallback") == "fallback"

    def test_quality(self):
        instance = AcceptEncoding(", ")
        assert instance.quality("content-coding") == 1.0
        assert instance.quality("identity") == 1.0

    def test___contains__(self):
        instance = AcceptEncoding(", ")
        returned = "content-coding" in instance
        assert returned is True


class TestAcceptEncoding__add:
    invalid_values = [
        ", ",
        [", "],
        (", ",),
        {", ": 1.0},
        StringMe(", "),
    ]

    valid_nonempty_values_with_headers = [
        (
            "compress;q=0.5, deflate;q=0, *",
            "compress;q=0.5, deflate;q=0, *",
        ),
        (
            ["compress;q=0.5", "deflate;q=0", "*"],
            "compress;q=0.5, deflate;q=0, *",
        ),
        (
            [("compress", 0.5), ("deflate", 0.0), ("*", 1.0)],
            "compress;q=0.5, deflate;q=0, *",
        ),
        (
            ("compress;q=0.5", "deflate;q=0", "*"),
            "compress;q=0.5, deflate;q=0, *",
        ),
        (
            (("compress", 0.5), ("deflate", 0.0), ("*", 1.0)),
            "compress;q=0.5, deflate;q=0, *",
        ),
        (
            {"compress": 0.5, "deflate": 0.0, "*": 1.0},
            "*, compress;q=0.5, deflate;q=0",
        ),
    ]

    valid_empty_values = ["", [], (), {}, StringMe("")]

    valid_values_with_headers = valid_nonempty_values_with_headers + [
        [x, ""] for x in valid_empty_values
    ]

    # snapshots help confirm the instance is immutable
    def snapshot_instance(self, inst):
        return deepcopy(
            {
                "header_value": inst.header_value,
                "parsed": inst.parsed,
                "header_state": inst.header_state,
            }
        )

    # we want to test math with primitive python values and Accept instances
    @pytest.fixture(params=["primitive", "instance"])
    def maker(self, request):
        if request.param == "primitive":
            return lambda x: x
        return AcceptEncoding

    # almost always add and radd are symmetrical so we can test both and
    # expect the same result
    @pytest.fixture(params=["add", "radd"])
    def fn(self, request):
        if request.param == "add":
            return lambda x, y: x + y
        return lambda x, y: y + x

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_values_with_headers,
    )
    def test_valid_add_missing(self, input_value, input_header, maker, fn):
        inst = AcceptEncoding(input_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == input_header

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header

    def test_invalid_add_missing(self, maker, fn):
        inst = AcceptEncoding(", ")
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Invalid
        assert inst.header_value == ", "

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    def test_missing_add_missing(self, maker, fn):
        inst = AcceptEncoding(None)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Missing
        assert inst.header_value is None

        result = fn(inst, maker(None))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize("valid_value, valid_header", valid_values_with_headers)
    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_valid_add_invalid(
        self, valid_value, valid_header, invalid_value, maker, fn
    ):
        inst = AcceptEncoding(valid_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == valid_header

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == valid_header

    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_invalid_add_invalid(self, invalid_value, maker, fn):
        inst = AcceptEncoding(", ")
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Invalid
        assert inst.header_value == ", "

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize("invalid_value", invalid_values)
    def test_missing_add_invalid(self, invalid_value, maker, fn):
        inst = AcceptEncoding(None)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Missing
        assert inst.header_value is None

        result = fn(inst, maker(invalid_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Missing
        assert result.header_value is None

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_nonempty_values_with_headers,
    )
    def test_nonempty_valid_add_valid(self, input_value, input_header, maker):
        seed_value = ",\t ,gzip, identity;q=0.333,"
        inst = AcceptEncoding(seed_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == seed_value

        result = inst + maker(input_value)
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == seed_value + ", " + input_header

        result = maker(input_value) + inst
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header + ", " + seed_value

    @pytest.mark.parametrize(
        "input_value, input_header",
        valid_nonempty_values_with_headers,
    )
    @pytest.mark.parametrize("empty_value", valid_empty_values)
    def test_nonempty_valid_add_empty(
        self, input_value, input_header, empty_value, maker, fn
    ):
        inst = AcceptEncoding(input_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == input_header

        result = fn(inst, maker(empty_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == input_header

    @pytest.mark.parametrize("empty_value", valid_empty_values)
    def test_empty_valid_add_empty(self, empty_value, maker, fn):
        expected_value = ""
        inst = AcceptEncoding(empty_value)
        snap = self.snapshot_instance(inst)
        assert inst.header_state == HeaderState.Valid
        assert inst.header_value == expected_value

        result = fn(inst, maker(empty_value))
        assert snap == self.snapshot_instance(inst)
        assert result.header_state == HeaderState.Valid
        assert result.header_value == expected_value


class TestCreateAcceptEncodingHeader:
    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_encoding_header(header_value)
        assert isinstance(returned, AcceptEncoding)
        assert returned.header_state is HeaderState.Missing
        assert returned.header_value == header_value
        returned2 = create_accept_encoding_header(returned)
        assert isinstance(returned2, AcceptEncoding)
        assert returned2.header_state is HeaderState.Missing
        assert returned2._header_value == returned._header_value

    def test_header_value_is_valid(self):
        header_value = "gzip, identity;q=0.9"
        returned = create_accept_encoding_header(header_value)
        assert isinstance(returned, AcceptEncoding)
        assert returned.header_state is HeaderState.Valid
        assert returned.header_value == header_value
        returned2 = create_accept_encoding_header(returned)
        assert isinstance(returned2, AcceptEncoding)
        assert returned2.header_state is HeaderState.Valid
        assert returned2._header_value == returned._header_value

    @pytest.mark.parametrize("header_value", [", ", "gzip;q= 1"])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_encoding_header(header_value)
        assert isinstance(returned, AcceptEncoding)
        assert returned.header_state is HeaderState.Invalid
        assert returned.header_value == header_value
        returned2 = create_accept_encoding_header(returned)
        assert isinstance(returned2, AcceptEncoding)
        assert returned2.header_state is HeaderState.Invalid
        assert returned2._header_value == returned._header_value


class TestAcceptEncodingProperty:
    def test_fget_header_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": None})
        property_ = accept_encoding_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptEncoding)
        assert returned.header_state is HeaderState.Missing

    def test_fget_header_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": "gzip"})
        property_ = accept_encoding_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptEncoding)
        assert returned.header_state is HeaderState.Valid

    def test_fget_header_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": ", "})
        property_ = accept_encoding_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptEncoding)
        assert returned.header_state is HeaderState.Invalid

    def test_fset_value_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": "gzip"})
        property_ = accept_encoding_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_ENCODING" not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": "gzip"})
        property_ = accept_encoding_property()
        property_.fset(request=request, value=", ")
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Invalid
        assert request.environ["HTTP_ACCEPT_ENCODING"] == ", "

    def test_fset_value_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": "gzip"})
        property_ = accept_encoding_property()
        property_.fset(request=request, value="compress")
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_ENCODING"] == "compress"

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("gzip;q=0.5, compress;q=0, deflate", "gzip;q=0.5, compress;q=0, deflate"),
            (
                [("gzip", 0.5), ("compress", 0.0), "deflate"],
                "gzip;q=0.5, compress;q=0, deflate",
            ),
            (
                (("gzip", 0.5), ("compress", 0.0), "deflate"),
                "gzip;q=0.5, compress;q=0, deflate",
            ),
            (
                {"gzip": 0.5, "compress": 0.0, "deflate": 1.0},
                "deflate, gzip;q=0.5, compress;q=0",
            ),
        ],
    )
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": ""})
        property_ = accept_encoding_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_ENCODING"] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": ""})
        property_ = accept_encoding_property()
        value = StringMe("gzip;q=0.5, compress;q=0, deflate")
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_ENCODING"] == str(value)

    def test_fset_missing_AcceptEncoding(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": ""})
        property_ = accept_encoding_property()
        header = AcceptEncoding(None)
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_ENCODING" not in request.environ

    def test_fset_valid_AcceptEncoding(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": ""})
        property_ = accept_encoding_property()
        header = AcceptEncoding("gzip")
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Valid
        assert request.environ["HTTP_ACCEPT_ENCODING"] == header.header_value

    def test_fset_invalid_AcceptEncoding(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": "gzip"})
        property_ = accept_encoding_property()
        header = AcceptEncoding(", ")
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Invalid
        assert request.environ["HTTP_ACCEPT_ENCODING"] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_ENCODING": "gzip"})
        property_ = accept_encoding_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_ENCODING" not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank("/")
        property_ = accept_encoding_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_encoding, AcceptEncoding)
        assert request.accept_encoding.header_state is HeaderState.Missing
        assert "HTTP_ACCEPT_ENCODING" not in request.environ


class TestAcceptLanguage:
    @pytest.mark.parametrize(
        "value",
        [
            "",
            "*s",
            "*-a",
            "a-*",
            "a" * 9,
            "a-" + "a" * 9,
            "a-a-" + "a" * 9,
            "-",
            "a-",
            "-a",
            "---",
            "--a",
            "1-a",
            "1-a-a",
            "en_gb",
            "en/gb",
            "foo, bar, baz;q= 0.001",
            "foo , ,bar,charlie   ",
        ],
    )
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptLanguage.parse(value=value)

    @pytest.mark.parametrize(
        "value, expected_list",
        [
            ("*", [("*", 1.0)]),
            ("fR;q=0.5", [("fR", 0.5)]),
            ("zh-Hant;q=0.500", [("zh-Hant", 0.5)]),
            ("zh-Hans-CN;q=1", [("zh-Hans-CN", 1.0)]),
            ("de-CH-x-phonebk;q=1.0", [("de-CH-x-phonebk", 1.0)]),
            ("az-Arab-x-AZE-derbend;q=1.00", [("az-Arab-x-AZE-derbend", 1.0)]),
            ("zh-CN-a-myExt-x-private;q=1.000", [("zh-CN-a-myExt-x-private", 1.0)]),
            ("aaaaaaaa", [("aaaaaaaa", 1.0)]),
            ("aaaaaaaa-a", [("aaaaaaaa-a", 1.0)]),
            ("aaaaaaaa-aaaaaaaa", [("aaaaaaaa-aaaaaaaa", 1.0)]),
            ("a-aaaaaaaa-aaaaaaaa", [("a-aaaaaaaa-aaaaaaaa", 1.0)]),
            ("aaaaaaaa-a-aaaaaaaa", [("aaaaaaaa-a-aaaaaaaa", 1.0)]),
            (
                "zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000",
                [
                    ("zh-Hant", 0.372),
                    ("zh-CN-a-myExt-x-private", 0.977),
                    ("de", 1.0),
                    ("*", 0.0),
                ],
            ),
            (
                ",\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tcharlie \t,,  ,",
                [("foo", 0.345), ("bar", 0.456), ("charlie", 1.0)],
            ),
            # RFC 7230 Section 7
            ("foo,bar", [("foo", 1.0), ("bar", 1.0)]),
            ("foo, bar,", [("foo", 1.0), ("bar", 1.0)]),
            # RFC 7230 Errata ID: 4169
            ("foo , ,bar,charlie", [("foo", 1.0), ("bar", 1.0), ("charlie", 1.0)]),
        ],
    )
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptLanguage.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptLanguageValidHeader:
    @pytest.mark.parametrize("header_value", ["", ", da;q=0.2, en-gb;q=0.3 "])
    def test___init___invalid_header(self, header_value):
        with pytest.raises(ValueError):
            AcceptLanguageValidHeader(header_value=header_value)

    def test___init___valid_header(self):
        header_value = "zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000"
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed == [
            ("zh-Hant", 0.372),
            ("zh-CN-a-myExt-x-private", 0.977),
            ("de", 1.0),
            ("*", 0.0),
        ]
        assert instance._parsed_nonzero == [
            ("zh-Hant", 0.372),
            ("zh-CN-a-myExt-x-private", 0.977),
            ("de", 1.0),
        ]
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        left_operand = AcceptLanguageValidHeader(header_value="en")
        result = left_operand + None
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize(
        "right_operand",
        [
            "",
            [],
            (),
            {},
            "en_gb",
            ["en_gb"],
            ("en_gb",),
            {"en_gb": 1.0},
            ",",
            [","],
            (",",),
            {",": 1.0},
        ],
    )
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptLanguageValidHeader(header_value="en")
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize("str_", ["", "en_gb", ","])
    def test___add___other_type_with_invalid___str__(self, str_):
        left_operand = AcceptLanguageValidHeader(header_value="en")

        class Other:
            def __str__(self):
                return str_

        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("en-gb;q=0.5, fr;q=0, es", "en-gb;q=0.5, fr;q=0, es"),
            ([("en-gb", 0.5), ("fr", 0.0), "es"], "en-gb;q=0.5, fr;q=0, es"),
            ((("en-gb", 0.5), ("fr", 0.0), "es"), "en-gb;q=0.5, fr;q=0, es"),
            ({"en-gb": 0.5, "fr": 0.0, "es": 1.0}, "es, en-gb;q=0.5, fr;q=0"),
        ],
    )
    def test___add___valid_value(self, value, value_as_header):
        header = ",\t ,de, zh-Hans;q=0.333,"
        result = AcceptLanguageValidHeader(header_value=header) + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header + ", " + value_as_header

    def test___add___other_type_with_valid___str__(self):
        header = ",\t ,de, zh-Hans;q=0.333,"

        class Other:
            def __str__(self):
                return "en-gb;q=0.5, fr;q=0, es"

        right_operand = Other()
        result = AcceptLanguageValidHeader(header_value=header) + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header + ", " + str(right_operand)

    def test___add___AcceptLanguageValidHeader(self):
        header1 = ",\t ,de, zh-Hans;q=0.333,"
        header2 = ", ,fr;q=0, \tes;q=1,"
        result = AcceptLanguageValidHeader(
            header_value=header1
        ) + AcceptLanguageValidHeader(header_value=header2)
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header1 + ", " + header2

    def test___add___AcceptLanguageNoHeader(self):
        valid_header_instance = AcceptLanguageValidHeader(header_value="es")
        result = valid_header_instance + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    @pytest.mark.parametrize("header_value", ["", "en_gb", ","])
    def test___add___AcceptLanguageInvalidHeader(self, header_value):
        valid_header_instance = AcceptLanguageValidHeader(header_value="header")
        result = valid_header_instance + AcceptLanguageInvalidHeader(
            header_value=header_value
        )
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    def test___bool__(self):
        instance = AcceptLanguageValidHeader(header_value="valid-header")
        returned = bool(instance)
        assert returned is True

    @pytest.mark.parametrize(
        "header_value, offer",
        [
            ("*", "da"),
            ("da", "DA"),
            ("en", "en-gb"),
            ("en-gb", "en-gb"),
            ("en-gb", "en"),
            ("en-gb", "en_GB"),
        ],
    )
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains___in(self, header_value, offer):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert offer in instance

    @pytest.mark.parametrize(
        "header_value, offer",
        [("en-gb", "en-us"), ("en-gb", "fr-fr"), ("en-gb", "fr"), ("en", "fr-fr")],
    )
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains___not_in(self, header_value, offer):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert offer not in instance

    @pytest.mark.parametrize(
        "header_value, expected_list",
        [
            ("fr;q=0, jp;q=0", []),
            ("en-gb, da", ["en-gb", "da"]),
            ("en-gb;q=0.5, da;q=0.5", ["en-gb", "da"]),
            (
                "de;q=0.8, de-DE-1996;q=0.5, de-Deva;q=0, de-Latn-DE",
                ["de-Latn-DE", "de", "de-DE-1996"],
            ),
            # __iter__ is currently a simple filter for the ranges in the header
            # with non-0 qvalues, and does not attempt to account for the special
            # meanings of q=0 and *:
            ("en-gb;q=0, *", ["*"]),
            ("de, de;q=0", ["de"]),
        ],
    )
    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self, header_value, expected_list):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert list(instance) == expected_list

    def test___radd___None(self):
        right_operand = AcceptLanguageValidHeader(header_value="en")
        result = None + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize(
        "left_operand",
        [
            "",
            [],
            (),
            {},
            "en_gb",
            ["en_gb"],
            ("en_gb",),
            {"en_gb": 1.0},
            ",",
            [","],
            (",",),
            {",": 1.0},
        ],
    )
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptLanguageValidHeader(header_value="en")
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize("str_", ["", "en_gb", ","])
    def test___radd___other_type_with_invalid___str__(self, str_):
        right_operand = AcceptLanguageValidHeader(header_value="en")

        class Other:
            def __str__(self):
                return str_

        result = Other() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("en-gb;q=0.5, fr;q=0, es", "en-gb;q=0.5, fr;q=0, es"),
            ([("en-gb", 0.5), ("fr", 0.0), "es"], "en-gb;q=0.5, fr;q=0, es"),
            ((("en-gb", 0.5), ("fr", 0.0), "es"), "en-gb;q=0.5, fr;q=0, es"),
            ({"en-gb": 0.5, "fr": 0.0, "es": 1.0}, "es, en-gb;q=0.5, fr;q=0"),
        ],
    )
    def test___radd___valid_value(self, value, value_as_header):
        right_operand = AcceptLanguageValidHeader(
            header_value=",\t ,de, zh-Hans;q=0.333,"
        )
        result = value + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert (
            result.header_value == value_as_header + ", " + right_operand.header_value
        )

    def test___radd___other_type_with_valid___str__(self):
        right_operand = AcceptLanguageValidHeader(
            header_value=",\t ,de, zh-Hans;q=0.333,"
        )

        class Other:
            def __str__(self):
                return "en-gb;q=0.5, fr;q=0, es"

        left_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert (
            result.header_value == str(left_operand) + ", " + right_operand.header_value
        )

    def test___repr__(self):
        instance = AcceptLanguageValidHeader(header_value=",da;q=0.200,en-gb;q=0.300")
        assert repr(instance) == "<AcceptLanguageValidHeader ('da;q=0.2, en-gb;q=0.3')>"

    def test___str__(self):
        header_value = ", \t,de;q=0.000 \t, es;q=1.000, zh, jp;q=0.210  ,"
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert str(instance) == "de;q=0, es, zh, jp;q=0.21"

    @pytest.mark.parametrize(
        "header_value, language_tags, expected_returned",
        [
            # Example from RFC 4647, Section 3.4
            (
                "de-de",
                ["de", "de-DE-1996", "de-Deva", "de-Latn-DE"],
                [("de-DE-1996", 1.0)],
            ),
            # Empty `language_tags`
            ("a", [], []),
            # No matches
            ("a, b", ["c", "d"], []),
            # Several ranges and tags, no matches
            ("a-b;q=0.9, c-d;q=0.5, e-f", ("a", "b", "c", "d", "e", "f"), []),
            # Case-insensitive match
            ("foO, BaR", ["foo", "bar"], [("foo", 1.0), ("bar", 1.0)]),
            # If a tag matches a non-'*' range with q=0, tag is filtered out
            ("b-c, a, b;q=0, d;q=0", ["b-c", "a", "b-c-d", "d-e-f"], [("a", 1.0)]),
            # Match if a range exactly equals a tag
            ("d-e-f", ["a-b-c", "d-e-f"], [("d-e-f", 1.0)]),
            # Match if a range exactly equals a prefix of the tag such that the
            # first character following the prefix is '-'
            (
                "a-b-c-d, a-b-c-d-e, a-b-c-d-f-g-h",
                ["a-b-c-d-f-g"],
                [("a-b-c-d-f-g", 1.0)],
            ),
            # '*', when it is the only range in the header, matches everything
            ("*", ["a", "b"], [("a", 1.0), ("b", 1.0)]),
            # '*' range matches only tags not matched by any other range
            (
                "*;q=0.2, a;q=0.5, b",
                ["a-a", "b-a", "c-a", "d-a"],
                [("b-a", 1.0), ("a-a", 0.5), ("c-a", 0.2), ("d-a", 0.2)],
            ),
            # '*' range without a qvalue gives a matched qvalue of 1.0
            (
                "a;q=0.5, b, *",
                ["a-a", "b-a", "c-a", "d-a"],
                [("b-a", 1.0), ("c-a", 1.0), ("d-a", 1.0), ("a-a", 0.5)],
            ),
            # The qvalue for the '*' range works the same way as qvalues for
            # non-'*' ranges.
            (
                "a;q=0.5, *;q=0.9",
                # (meaning: prefer anything other than 'a', with 'a' as a
                # fallback)
                ["a", "b"],
                [("b", 0.9), ("a", 0.5)],
            ),
            # More than one range matching the same tag: range with the highest
            # qvalue is matched
            ("a-b-c;q=0.7, a;q=0.9, a-b;q=0.8", ["a-b-c"], [("a-b-c", 0.9)]),
            # More than one range with the same qvalue matching the same tag:
            # the range in an earlier position in the header is matched
            (
                "a-b-c;q=0.7, a;q=0.9, b;q=0.9, a-b;q=0.9",
                ["a-b-c", "b"],
                [("a-b-c", 0.9), ("b", 0.9)],
            ),
            # The returned list of tuples is sorted in descending order of qvalue
            (
                "a;q=0.7, b;q=0.3, c, d;q=0.5",
                ["d", "c", "b", "a"],
                [("c", 1.0), ("a", 0.7), ("d", 0.5), ("b", 0.3)],
            ),
            # When qvalues are the same, the tag whose matched range appears
            # earlier in the header comes first
            ("a, c, b", ["b", "a", "c"], [("a", 1.0), ("c", 1.0), ("b", 1.0)]),
            # When many tags match the same range (so same qvalue and same
            # matched range position in header), they are returned in order of
            # their position in the `language_tags` argument
            ("a", ["a-b", "a", "a-b-c"], [("a-b", 1.0), ("a", 1.0), ("a-b-c", 1.0)]),
            # When a non-'*' range appears in the header more than once, we use
            # the first one for matching and ignore the others
            (
                "a;q=0.5, c;q=0.6, b;q=0.7, c;q=0.9",
                ["a", "b", "c"],
                [("b", 0.7), ("c", 0.6), ("a", 0.5)],
            ),
            (
                "a, b, c;q=0.5, c;q=0",
                ["a-a", "b-a", "c-a"],
                [("a-a", 1.0), ("b-a", 1.0), ("c-a", 0.5)],
            ),
            (
                "a;q=0.5, c;q=0.9, b;q=0.9, c;q=0.9",
                ["a", "b", "c"],
                [("c", 0.9), ("b", 0.9), ("a", 0.5)],
            ),
            # When the '*' range appears in the header more than once, we use
            # the first one for matching and ignore the others
            (
                "a;q=0.5, *;q=0.6, b;q=0.7, *;q=0.9",
                ["a", "b", "c"],
                [("b", 0.7), ("c", 0.6), ("a", 0.5)],
            ),
            (
                "a, b, *;q=0.5, *;q=0",
                ["a-a", "b-a", "c-a"],
                [("a-a", 1.0), ("b-a", 1.0), ("c-a", 0.5)],
            ),
            (
                "a;q=0.5, *;q=0.9, b;q=0.9, *;q=0.9",
                ["a", "b", "c"],
                [("c", 0.9), ("b", 0.9), ("a", 0.5)],
            ),
            # Both '*' and non-'*' ranges appearing more than once
            (
                "a-b;q=0.5, c-d, *, a-b, c-d;q=0.3, *;q=0",
                ["a-b-c", "c-d-e", "e-f-g"],
                [("c-d-e", 1.0), ("e-f-g", 1.0), ("a-b-c", 0.5)],
            ),
        ],
    )
    def test_basic_filtering(self, header_value, language_tags, expected_returned):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.basic_filtering(language_tags=language_tags)
        assert returned == expected_returned

    @pytest.mark.parametrize(
        "header_value, offers, default_match, expected_returned",
        [
            ("bar, *;q=0", ["foo"], None, None),
            ("en-gb, sr-Cyrl", ["sr-Cyrl", "en-gb"], None, "sr-Cyrl"),
            ("en-gb, sr-Cyrl", ["en-gb", "sr-Cyrl"], None, "en-gb"),
            ("en-gb, sr-Cyrl", [("sr-Cyrl", 0.5), "en-gb"], None, "en-gb"),
            ("en-gb, sr-Cyrl", [("sr-Cyrl", 0.5), ("en-gb", 0.4)], None, "sr-Cyrl"),
            ("en-gb, sr-Cyrl;q=0.5", ["en-gb", "sr-Cyrl"], None, "en-gb"),
            ("en-gb;q=0.5, sr-Cyrl", ["en-gb", "sr-Cyrl"], None, "sr-Cyrl"),
            ("en-gb, sr-Cyrl;q=0.55, es;q=0.59", ["en-gb", "sr-Cyrl"], None, "en-gb"),
            (
                "en-gb;q=0.5, sr-Cyrl;q=0.586, es-419;q=0.597",
                ["en-gb", "es-419"],
                None,
                "es-419",
            ),
        ],
    )
    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self, header_value, offers, default_match, expected_returned):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.best_match(offers=offers, default_match=default_match)
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageValidHeader(header_value="valid-header")
        with pytest.raises(TypeError):
            instance.lookup(
                language_tags=["tag"],
                default_range="language-range",
                default_tag=None,
                default=None,
            )

    def test_lookup_default_range_cannot_be_asterisk(self):
        instance = AcceptLanguageValidHeader(header_value="valid-header")
        with pytest.raises(ValueError):
            instance.lookup(
                language_tags=["tag"],
                default_range="*",
                default_tag="default-tag",
                default=None,
            )

    @pytest.mark.parametrize(
        (
            "header_value, language_tags, default_range, default_tag, default"
            ", expected"
        ),
        [
            # Each language range in the header is considered in turn, in
            # descending order of qvalue
            (
                "aA;q=0.3, Bb, cC;q=0.7",
                ["Aa", "bB", "Cc"],
                None,
                "default-tag",
                None,
                "bB",
            ),
            # For ranges with the same qvalue, position in header is the
            # tiebreaker.
            (
                "bB-Cc;q=0.8, aA;q=0.9, Bb;q=0.9",
                ["bb", "aa"],
                None,
                "default-tag",
                None,
                "aa",
            ),
            # Each language range represents the most specific tag that is an
            # acceptable match. Examples from RFC 4647, section 3.4, first
            # paragraph:
            (
                "de-ch",
                ["de-CH-1996", "de-CH", "de"],
                None,
                "default-tag",
                None,
                "de-CH",
            ),
            ("de-ch", ["de-CH-1996", "de"], None, "default-tag", None, "de"),
            # The language range is progressively truncated from the end until
            # a matching language tag is located. From the example of a Lookup
            # Fallback Pattern in RFC 4647, section 3.4:
            (
                "zh-Hant-CN-x-private1-private2",
                [
                    "zh-Hant-CN-x-private1-private2",
                    "zh-Hant-CN-x-private1",
                    "zh-Hant-CN-x",
                    "zh-Hant-CN",
                    "zh-Hant",
                    "zh",
                ],
                None,
                "default-tag",
                None,
                "zh-Hant-CN-x-private1-private2",
            ),
            (
                "zh-Hant-CN-x-private1-private2",
                [
                    "zh-Hant-CN-x-private1",
                    "zh-Hant-CN-x",
                    "zh-Hant-CN",
                    "zh-Hant",
                    "zh",
                ],
                None,
                "default-tag",
                None,
                "zh-Hant-CN-x-private1",
            ),
            (
                "zh-Hant-CN-x-private1-private2",
                ["zh-Hant-CN-x", "zh-Hant-CN", "zh-Hant", "zh"],
                None,
                "default-tag",
                None,
                "zh-Hant-CN",
            ),
            (
                "zh-Hant-CN-x-private1-private2",
                ["zh-Hant-CN", "zh-Hant", "zh"],
                None,
                "default-tag",
                None,
                "zh-Hant-CN",
            ),
            (
                "zh-Hant-CN-x-private1-private2",
                ["zh-Hant", "zh"],
                None,
                "default-tag",
                None,
                "zh-Hant",
            ),
            ("zh-Hant-CN-x-private1-private2", ["zh"], None, "default-tag", None, "zh"),
            (
                "zh-Hant-CN-x-private1-private2",
                ["some-other-tag-1", "some-other-tag-2"],
                None,
                "default-tag",
                None,
                "default-tag",
            ),
            # Further tests to check that single-letter or -digit subtags are
            # removed at the same time as their closest trailing subtag:
            ("AA-T-subtag", ["Aa-t", "aA"], None, "default-tag", None, "aA"),
            ("AA-1-subtag", ["aa-1", "aA"], None, "default-tag", None, "aA"),
            (
                "Aa-P-subtag-8-subtag",
                ["Aa-p-subtag-8", "Aa-p", "aA"],
                None,
                "default-tag",
                None,
                "aA",
            ),
            (
                "aA-3-subTag-C-subtag",
                ["aA-3-subtag-c", "aA-3", "aA"],
                None,
                "default-tag",
                None,
                "aA",
            ),
            # Test that single-letter or -digit subtag in first position works
            # as expected
            (
                "T-subtag",
                ["t-SubTag", "another"],
                None,
                "default-tag",
                None,
                "t-SubTag",
            ),
            ("T-subtag", ["another"], None, "default-tag", None, "default-tag"),
            # If the language range "*" is followed by other language ranges,
            # it is skipped.
            ("*, Aa-aA-AA", ["bb", "aA"], None, "default-tag", None, "aA"),
            # If the language range "*" is the only one in the header, lookup
            # proceeds to the default arguments.
            ("*", ["bb", "aa"], None, "default-tag", None, "default-tag"),
            # If no other language range follows the "*" in the header, lookup
            # proceeds to the default arguments.
            ("dd, cc, *", ["bb", "aa"], None, "default-tag", None, "default-tag"),
            # If a non-'*' range has q=0, any tag that matches the range
            # exactly (without subtag truncation) is not acceptable.
            (
                "aa, bB-Cc-DD;q=0, bB-Cc, cc",
                ["bb", "bb-Cc-DD", "bb-cC-dd", "Bb-cc", "bb-cC-dd"],
                None,
                "default-tag",
                None,
                "Bb-cc",
            ),
            # ;q=0 and ;q={not 0} both in header: q=0 takes precedence and
            # makes the exact match not acceptable, but the q={not 0} means
            # that tags can still match after subtag truncation.
            (
                "aa, bB-Cc-DD;q=0.9, cc, Bb-cC-dD;q=0",
                ["bb", "Bb-Cc", "Bb-cC-dD"],
                None,
                "default-tag",
                None,
                "Bb-Cc",
            ),
            # If none of the ranges in the header match any of the language
            # tags, and the `default_range` argument is not None and does not
            # match any q=0 range in the header, we search through it by
            # progressively truncating from the end, as we do with the ranges
            # in the header. Example from RFC 4647, section 3.4.1:
            (
                "fr-FR, zh-Hant",
                ["fr-FR", "fr", "zh-Hant", "zh", "ja-JP", "ja"],
                "ja-JP",
                "default-tag",
                None,
                "fr-FR",
            ),
            (
                "fr-FR, zh-Hant",
                ["fr", "zh-Hant", "zh", "ja-JP", "ja"],
                "ja-JP",
                "default-tag",
                None,
                "fr",
            ),
            (
                "fr-FR, zh-Hant",
                ["zh-Hant", "zh", "ja-JP", "ja"],
                "ja-JP",
                "default-tag",
                None,
                "zh-Hant",
            ),
            (
                "fr-FR, zh-Hant",
                ["zh", "ja-JP", "ja"],
                "ja-JP",
                "default-tag",
                None,
                "zh",
            ),
            ("fr-FR, zh-Hant", ["ja-JP", "ja"], "ja-JP", "default-tag", None, "ja-JP"),
            ("fr-FR, zh-Hant", ["ja"], "ja-JP", "default-tag", None, "ja"),
            (
                "fr-FR, zh-Hant",
                ["some-other-tag-1", "some-other-tag-2"],
                "ja-JP",
                "default-tag",
                None,
                "default-tag",
            ),
            # If none of the ranges in the header match the language tags, the
            # `default_range` argument is not None, and there is a '*;q=0'
            # range in the header, then the `default_range` and its substrings
            # from subtag truncation are not acceptable.
            (
                "aa-bb, cc-dd, *;q=0",
                ["ee-ff", "ee"],
                "ee-ff",
                None,
                "default",
                "default",
            ),
            # If none of the ranges in the header match the language tags, the
            # `default_range` argument is not None, and the argument exactly
            # matches a non-'*' range in the header with q=0 (without fallback
            # subtag truncation), then the `default_range` itself is not
            # acceptable...
            (
                "aa-bb, cc-dd, eE-Ff;q=0",
                ["Ee-fF"],
                "EE-FF",
                "default-tag",
                None,
                "default-tag",
            ),
            # ...but it should still be searched with subtag truncation,
            # because its substrings other than itself are still acceptable:
            (
                "aa-bb, cc-dd, eE-Ff-Gg;q=0",
                ["Ee", "Ee-fF-gG", "Ee-fF"],
                "EE-FF-GG",
                "default-tag",
                None,
                "Ee-fF",
            ),
            (
                "aa-bb, cc-dd, eE-Ff-Gg;q=0",
                ["Ee-fF-gG", "Ee"],
                "EE-FF-GG",
                "default-tag",
                None,
                "Ee",
            ),
            # If `default_range` only has one subtag, then no subtag truncation
            # is possible, and we proceed to `default-tag`:
            ("aa-bb, cc-dd, eE;q=0", ["Ee"], "EE", "default-tag", None, "default-tag"),
            # If the `default_range` argument would only match a non-'*' range
            # in the header with q=0 exactly if the `default_range` had subtags
            # from the end truncated, then it is acceptable, and we attempt to
            # match it with the language tags using subtag truncation. However,
            # the tag equivalent of the range with q=0 would be considered not
            # acceptable and ruled out, if we reach it during the subtag
            # truncation search.
            (
                "aa-bb, cc-dd, eE-Ff;q=0",
                ["Ee-fF", "Ee-fF-33", "ee"],
                "EE-FF-33",
                "default-tag",
                None,
                "Ee-fF-33",
            ),
            (
                "aa-bb, cc-dd, eE-Ff;q=0",
                ["Ee-fF", "eE"],
                "EE-FF-33",
                "default-tag",
                None,
                "eE",
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, and the `default_tag`
            # argument is not None and does not match any range in the header
            # with q=0, then the `default_tag` argument is returned.
            ("aa-bb, cc-dd", ["ee-ff", "ee"], None, "default-tag", None, "default-tag"),
            (
                "aa-bb, cc-dd",
                ["ee-ff", "ee"],
                "gg-hh",
                "default-tag",
                None,
                "default-tag",
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, the `default_tag` argument is
            # not None, and there is a '*' range in the header with q=0, then
            # the `default_tag` argument is not acceptable.
            (
                "aa-bb, cc-dd, *;q=0",
                ["ee-ff", "ee"],
                "gg-hh",
                "ii-jj",
                "default",
                "default",
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, the `default_tag` argument is
            # not None and matches a non-'*' range in the header with q=0
            # exactly, then the `default_tag` argument is not acceptable.
            (
                "aa-bb, cc-dd, iI-jJ;q=0",
                ["ee-ff", "ee"],
                "gg-hh",
                "Ii-Jj",
                "default",
                "default",
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, and the `default_tag`
            # argument is None, then we proceed to the `default` argument.
            ("aa-bb, cc-dd", ["ee-ff", "ee"], None, None, "default", "default"),
            ("aa-bb, cc-dd", ["ee-ff", "ee"], "gg-hh", None, "default", "default"),
            # If we fall back to the `default` argument, and it is not a
            # callable, the argument itself is returned.
            ("aa", ["bb"], None, None, 0, 0),
            (
                "Aa, cC;q=0",
                ["bb"],
                "aA-Cc",
                "Cc",
                ["non-callable object"],
                ["non-callable object"],
            ),
            # If we fall back to the `default` argument, and it is a callable,
            # it is called, and the callable's return value is returned by the
            # method.
            ("aa", ["bb"], None, None, lambda: "callable called", "callable called"),
            (
                "Aa, cc;q=0",
                ["bb"],
                "aA-cC",
                "cc",
                lambda: "callable called",
                "callable called",
            ),
            # Even if the 'default' argument is a str that matches a q=0 range
            # in the header, it is still returned.
            ("aa, *;q=0", ["bb"], None, None, "cc", "cc"),
            ("aa, cc;q=0", ["bb"], None, None, "cc", "cc"),
            # If the `default_tag` argument is not acceptable because of a q=0
            # range in the header, and the `default` argument is None, then
            # None is returned.
            ("aa, Bb;q=0", ["cc"], None, "bB", None, None),
            ("aa, *;q=0", ["cc"], None, "bb", None, None),
            # Test that method works with empty `language_tags`:
            ("range", [], None, "default-tag", None, "default-tag"),
            # Test that method works with empty `default_range`:
            ("range", [], "", "default-tag", None, "default-tag"),
            ("range", ["tag"], "", "default-tag", None, "default-tag"),
            # Test that method works with empty `default_tag`:
            ("range", [], "", "", None, ""),
            ("range", ["tag"], "default-range", "", None, ""),
        ],
    )
    def test_lookup(
        self, header_value, language_tags, default_range, default_tag, default, expected
    ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.lookup(
            language_tags=language_tags,
            default_range=default_range,
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    @pytest.mark.parametrize(
        "header_value, offer, expected_returned",
        [
            ("en-gb", "en-gb", 1),
            ("en-gb;q=0.5", "en-gb", 0.5),
            ("en-gb", "sr-Cyrl", None),
        ],
    )
    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self, header_value, offer, expected_returned):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.quality(offer=offer)
        assert returned == expected_returned


class TestAcceptLanguageNoHeader:
    def test___init__(self):
        instance = AcceptLanguageNoHeader()
        assert instance.header_value is None
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        instance = AcceptLanguageNoHeader()
        result = instance + None
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not instance

    @pytest.mark.parametrize(
        "right_operand",
        ["", [], (), {}, "en_gb", ["en_gb"], ("en_gb",), {"en_gb": 1.0}],
    )
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize("str_", ["", "en_gb"])
    def test___add___other_type_with_invalid___str__(self, str_):
        left_operand = AcceptLanguageNoHeader()

        class Other:
            def __str__(self):
                return str_

        result = left_operand + Other()
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("en-gb;q=0.5, fr;q=0, es", "en-gb;q=0.5, fr;q=0, es"),
            ([("en-gb", 0.5), ("fr", 0.0), "es"], "en-gb;q=0.5, fr;q=0, es"),
            ((("en-gb", 0.5), ("fr", 0.0), "es"), "en-gb;q=0.5, fr;q=0, es"),
            ({"en-gb": 0.5, "fr": 0.0, "es": 1.0}, "es, en-gb;q=0.5, fr;q=0"),
        ],
    )
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptLanguageNoHeader() + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str__(self):
        class Other:
            def __str__(self):
                return "en-gb;q=0.5, fr;q=0, es"

        right_operand = Other()
        result = AcceptLanguageNoHeader() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptLanguageValidHeader(self):
        right_operand = AcceptLanguageValidHeader(header_value=", ,fr;q=0, \tes;q=1,")
        result = AcceptLanguageNoHeader() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value

    def test___add___AcceptLanguageNoHeader(self):
        left_operand = AcceptLanguageNoHeader()
        right_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand
        assert result is not right_operand

    @pytest.mark.parametrize("invalid_header_value", ["", "en_gb"])
    def test___add___AcceptLanguageInvalidHeader(self, invalid_header_value):
        left_operand = AcceptLanguageNoHeader()
        result = left_operand + AcceptLanguageInvalidHeader(
            header_value=invalid_header_value
        )
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    def test___bool__(self):
        instance = AcceptLanguageNoHeader()
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptLanguageNoHeader()
        returned = "any-tag" in instance
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptLanguageNoHeader()
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptLanguageNoHeader()
        result = None + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize(
        "left_operand", ["", [], (), {}, "en_gb", ["en_gb"], ("en_gb",), {"en_gb": 1.0}]
    )
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize("str_", ["", "en_gb", ","])
    def test___radd___other_type_with_invalid___str__(self, str_):
        right_operand = AcceptLanguageNoHeader()

        class Other:
            def __str__(self):
                return str_

        result = Other() + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("en-gb;q=0.5, fr;q=0, es", "en-gb;q=0.5, fr;q=0, es"),
            ([("en-gb", 0.5), ("fr", 0.0), "es"], "en-gb;q=0.5, fr;q=0, es"),
            ((("en-gb", 0.5), ("fr", 0.0), "es"), "en-gb;q=0.5, fr;q=0, es"),
            ({"en-gb": 0.5, "fr": 0.0, "es": 1.0}, "es, en-gb;q=0.5, fr;q=0"),
        ],
    )
    def test___radd___valid_value(self, value, value_as_header):
        result = value + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str__(self):
        class Other:
            def __str__(self):
                return "en-gb;q=0.5, fr;q=0, es"

        left_operand = Other()
        result = left_operand + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptLanguageNoHeader()
        assert repr(instance) == "<AcceptLanguageNoHeader>"

    def test___str__(self):
        instance = AcceptLanguageNoHeader()
        assert str(instance) == "<no header in request>"

    def test_basic_filtering(self):
        instance = AcceptLanguageNoHeader()
        returned = instance.basic_filtering(language_tags=["tag1", "tag2"])
        assert returned == []

    @pytest.mark.parametrize(
        "offers, default_match, expected_returned",
        [
            (["foo", "bar"], None, "foo"),
            ([("foo", 1), ("bar", 0.5)], None, "foo"),
            ([("foo", 0.5), ("bar", 1)], None, "bar"),
            ([("foo", 0.5), "bar"], None, "bar"),
            ([("foo", 0.5), "bar"], object(), "bar"),
            ([], "fallback", "fallback"),
        ],
    )
    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self, offers, default_match, expected_returned):
        instance = AcceptLanguageNoHeader()
        returned = instance.best_match(offers=offers, default_match=default_match)
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageNoHeader()
        with pytest.raises(TypeError):
            instance.lookup(default_tag=None, default=None)

    @pytest.mark.parametrize(
        "default_tag, default, expected",
        [
            # If `default_tag` is not None, it is returned.
            ("default-tag", "default", "default-tag"),
            # If `default_tag` is None, we proceed to the `default` argument. If
            # `default` is not a callable, the argument itself is returned.
            (None, 0, 0),
            # If `default` is a callable, it is called, and the callable's return
            # value is returned by the method.
            (None, lambda: "callable called", "callable called"),
        ],
    )
    def test_lookup(self, default_tag, default, expected):
        instance = AcceptLanguageNoHeader()
        returned = instance.lookup(default_tag=default_tag, default=default)
        assert returned == expected

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptLanguageNoHeader()
        returned = instance.quality(offer="any-tag")
        assert returned == 1.0


class TestAcceptLanguageInvalidHeader:
    def test___init__(self):
        header_value = "invalid header"
        instance = AcceptLanguageInvalidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        result = instance + None
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize(
        "right_operand",
        ["", [], (), {}, "en_gb", ["en_gb"], ("en_gb",), {"en_gb": 1.0}],
    )
    def test___add___invalid_value(self, right_operand):
        result = AcceptLanguageInvalidHeader(header_value="") + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize("str_", ["", "en_gb"])
    def test___add___other_type_with_invalid___str__(self, str_):
        class Other:
            def __str__(self):
                return str_

        result = AcceptLanguageInvalidHeader(header_value="") + Other()
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize("value", ["en", ["en"], ("en",), {"en": 1.0}])
    def test___add___valid_header_value(self, value):
        result = AcceptLanguageInvalidHeader(header_value="") + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == "en"

    def test___add___other_type_valid_header_value(self):
        class Other:
            def __str__(self):
                return "en"

        result = AcceptLanguageInvalidHeader(header_value="") + Other()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == "en"

    def test___add___AcceptLanguageValidHeader(self):
        right_operand = AcceptLanguageValidHeader(header_value="en")
        result = AcceptLanguageInvalidHeader(header_value="") + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptLanguageNoHeader(self):
        right_operand = AcceptLanguageNoHeader()
        result = AcceptLanguageInvalidHeader(header_value="") + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    def test___add___AcceptLanguageInvalidHeader(self):
        result = AcceptLanguageInvalidHeader(
            header_value=""
        ) + AcceptLanguageInvalidHeader(header_value="")
        assert isinstance(result, AcceptLanguageNoHeader)

    def test___bool__(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = "any-tag" in instance
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        result = None + instance
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize(
        "left_operand", ["", [], (), {}, "en_gb", ["en_gb"], ("en_gb",), {"en_gb": 1.0}]
    )
    def test___radd___invalid_value(self, left_operand):
        result = left_operand + AcceptLanguageInvalidHeader(header_value="")
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize("str_", ["", "en_gb"])
    def test___radd___other_type_with_invalid___str__(self, str_):
        class Other:
            def __str__(self):
                return str_

        result = Other() + AcceptLanguageInvalidHeader(header_value="")
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize("value", ["en", ["en"], ("en",), {"en": 1.0}])
    def test___radd___valid_header_value(self, value):
        result = value + AcceptLanguageInvalidHeader(header_value="")
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == "en"

    def test___radd___other_type_valid_header_value(self):
        class Other:
            def __str__(self):
                return "en"

        result = Other() + AcceptLanguageInvalidHeader(header_value="")
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == "en"

    def test___repr__(self):
        instance = AcceptLanguageInvalidHeader(header_value="\x00")
        assert repr(instance) == "<AcceptLanguageInvalidHeader>"

    def test___str__(self):
        instance = AcceptLanguageInvalidHeader(header_value="invalid header")
        assert str(instance) == "<invalid header value>"

    def test_basic_filtering(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = instance.basic_filtering(language_tags=["tag1", "tag2"])
        assert returned == []

    @pytest.mark.parametrize(
        "offers, default_match, expected_returned",
        [
            (["foo", "bar"], None, "foo"),
            ([("foo", 1), ("bar", 0.5)], None, "foo"),
            ([("foo", 0.5), ("bar", 1)], None, "bar"),
            ([("foo", 0.5), "bar"], None, "bar"),
            ([("foo", 0.5), "bar"], object(), "bar"),
            ([], "fallback", "fallback"),
        ],
    )
    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self, offers, default_match, expected_returned):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = instance.best_match(offers=offers, default_match=default_match)
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        with pytest.raises(TypeError):
            instance.lookup(default_tag=None, default=None)

    @pytest.mark.parametrize(
        "default_tag, default, expected",
        [
            # If `default_tag` is not None, it is returned.
            ("default-tag", "default", "default-tag"),
            # If `default_tag` is None, we proceed to the `default` argument. If
            # `default` is not a callable, the argument itself is returned.
            (None, 0, 0),
            # If `default` is a callable, it is called, and the callable's return
            # value is returned by the method.
            (None, lambda: "callable called", "callable called"),
        ],
    )
    def test_lookup(self, default_tag, default, expected):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = instance.lookup(default_tag=default_tag, default=default)
        assert returned == expected

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptLanguageInvalidHeader(header_value="")
        returned = instance.quality(offer="any-tag")
        assert returned == 1.0


class TestCreateAcceptLanguageHeader:
    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageNoHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_language_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    def test_header_value_is_valid(self):
        header_value = "es, ja"
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageValidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_language_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    @pytest.mark.parametrize("header_value", ["", "en_gb"])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageInvalidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_language_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value


class TestAcceptLanguageProperty:
    def test_fget_header_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": None})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageNoHeader)

    def test_fget_header_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "es"})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageValidHeader)

    def test_fget_header_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "en_gb"})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageInvalidHeader)

    def test_fset_value_is_None(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "es"})
        property_ = accept_language_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert "HTTP_ACCEPT_LANGUAGE" not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "es"})
        property_ = accept_language_property()
        property_.fset(request=request, value="en_GB")
        assert isinstance(request.accept_language, AcceptLanguageInvalidHeader)
        assert request.environ["HTTP_ACCEPT_LANGUAGE"] == "en_GB"

    def test_fset_value_is_valid(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "es"})
        property_ = accept_language_property()
        property_.fset(request=request, value="en-GB")
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ["HTTP_ACCEPT_LANGUAGE"] == "en-GB"

    @pytest.mark.parametrize(
        "value, value_as_header",
        [
            ("en-gb;q=0.5, fr;q=0, es", "en-gb;q=0.5, fr;q=0, es"),
            ([("en-gb", 0.5), ("fr", 0.0), "es"], "en-gb;q=0.5, fr;q=0, es"),
            ((("en-gb", 0.5), ("fr", 0.0), "es"), "en-gb;q=0.5, fr;q=0, es"),
            ({"en-gb": 0.5, "fr": 0.0, "es": 1.0}, "es, en-gb;q=0.5, fr;q=0"),
        ],
    )
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": ""})
        property_ = accept_language_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ["HTTP_ACCEPT_LANGUAGE"] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": ""})
        property_ = accept_language_property()

        class Other:
            def __str__(self):
                return "en-gb;q=0.5, fr;q=0, es"

        value = Other()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ["HTTP_ACCEPT_LANGUAGE"] == str(value)

    def test_fset_AcceptLanguageNoHeader(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "en"})
        property_ = accept_language_property()
        header = AcceptLanguageNoHeader()
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert "HTTP_ACCEPT_LANGUAGE" not in request.environ

    def test_fset_AcceptLanguageValidHeader(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": ""})
        property_ = accept_language_property()
        header = AcceptLanguageValidHeader("es")
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ["HTTP_ACCEPT_LANGUAGE"] == header.header_value

    def test_fset_AcceptLanguageInvalidHeader(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": ""})
        property_ = accept_language_property()
        header = AcceptLanguageInvalidHeader("en_gb")
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageInvalidHeader)
        assert request.environ["HTTP_ACCEPT_LANGUAGE"] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank("/", environ={"HTTP_ACCEPT_LANGUAGE": "es"})
        property_ = accept_language_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert "HTTP_ACCEPT_LANGUAGE" not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank("/")
        property_ = accept_language_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert "HTTP_ACCEPT_LANGUAGE" not in request.environ
