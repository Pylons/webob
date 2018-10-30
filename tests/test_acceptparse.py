import re
import warnings

import pytest
from webob.acceptparse import (
    Accept,
    AcceptCharset,
    AcceptCharsetInvalidHeader,
    AcceptCharsetNoHeader,
    AcceptCharsetValidHeader,
    AcceptEncoding,
    AcceptEncodingInvalidHeader,
    AcceptEncodingNoHeader,
    AcceptEncodingValidHeader,
    AcceptInvalidHeader,
    AcceptLanguage,
    AcceptLanguageInvalidHeader,
    AcceptLanguageNoHeader,
    AcceptLanguageValidHeader,
    AcceptNoHeader,
    AcceptValidHeader,
    MIMEAccept,
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

IGNORE_BEST_MATCH = 'ignore:.*best_match.*'
IGNORE_QUALITY = 'ignore:.*quality.*'
IGNORE_CONTAINS = 'ignore:.*__contains__.*'
IGNORE_ITER = 'ignore:.*__iter__.*'
IGNORE_MIMEACCEPT = 'ignore:.*MIMEAccept.*'

class Test_ItemNWeightRe(object):
    @pytest.mark.parametrize('header_value', [
        'q=',
        'q=1',
        ';q',
        ';q=',
        ';q=1',
        'foo;',
        'foo;q',
        'foo;q1',
        'foo;q=',
        'foo;q=-1',
        'foo;q=2',
        'foo;q=1.001',
        'foo;q=0.0001',
        'foo;q=00',
        'foo;q=01',
        'foo;q=00.1',
        'foo,q=0.1',
        'foo;q =1',
        'foo;q= 1',
    ])
    def test_invalid(self, header_value):
        regex = _item_n_weight_re(item_re='foo')
        assert re.match('^' + regex + '$', header_value, re.VERBOSE) is None

    @pytest.mark.parametrize('header_value, groups', [
        ('foo', ('foo', None)),
        ('foo;q=0', ('foo', '0')),
        ('foo;q=0.0', ('foo', '0.0')),
        ('foo;q=0.00', ('foo', '0.00')),
        ('foo;q=0.000', ('foo', '0.000')),
        ('foo;q=1', ('foo', '1')),
        ('foo;q=1.0', ('foo', '1.0')),
        ('foo;q=1.00', ('foo', '1.00')),
        ('foo;q=1.000', ('foo', '1.000')),
        ('foo;q=0.1', ('foo', '0.1')),
        ('foo;q=0.87', ('foo', '0.87')),
        ('foo;q=0.382', ('foo', '0.382')),
        ('foo;Q=0.382', ('foo', '0.382')),
        ('foo ;Q=0.382', ('foo', '0.382')),
        ('foo; Q=0.382', ('foo', '0.382')),
        ('foo  ;  Q=0.382', ('foo', '0.382')),
    ])
    def test_valid(self, header_value, groups):
        regex = _item_n_weight_re(item_re='foo')
        assert re.match(
            '^' + regex + '$', header_value, re.VERBOSE,
        ).groups() == groups


class Test_List1OrMoreCompiledRe(object):
    @pytest.mark.parametrize('header_value', [
        # RFC 7230 Section 7
        ',',
        ',   ,',
        # RFC 7230 Errata ID: 4169
        'foo , ,bar,charlie   ',
        # Our tests
        ' foo , ,bar,charlie',
        ' ,foo , ,bar,charlie',
        ',foo , ,bar,charlie, ',
        '\tfoo , ,bar,charlie',
        '\t,foo , ,bar,charlie',
        ',foo , ,bar,charlie\t',
        ',foo , ,bar,charlie,\t',
    ])
    def test_invalid(self, header_value):
        regex = _list_1_or_more__compiled_re(element_re='([a-z]+)')
        assert regex.match(header_value) is None

    @pytest.mark.parametrize('header_value', [
        # RFC 7230 Section 7
        'foo,bar',
        'foo, bar,',
        # RFC 7230 Errata ID: 4169
        'foo , ,bar,charlie',
        # Our tests
        'foo , ,bar,charlie',
        ',foo , ,bar,charlie',
        ',foo , ,bar,charlie,',
        ',\t ,,,  \t \t,   ,\t\t\t,foo \t\t,, bar,  ,\tcharlie \t,,  ,',
    ])
    def test_valid(self, header_value):
        regex = _list_1_or_more__compiled_re(element_re='([a-z]+)')
        assert regex.match(header_value)


class TestAccept(object):
    @pytest.mark.parametrize('value', [
        ', ',
        ', , ',
        'noslash',
        '/',
        'text/',
        '/html',
        'text/html;',
        'text/html;param',
        'text/html;param=',
        'text/html ;param=val;',
        'text/html; param=val;',
        'text/html;param=val;',
        'text/html;param=\x19',
        'text/html;param=\x22',
        'text/html;param=\x5c',
        'text/html;param=\x7f',
        r'text/html;param="\"',
        r'text/html;param="\\\"',
        r'text/html;param="\\""',
        'text/html;param="\\\x19"',
        'text/html;param="\\\x7f"',
        'text/html;q',
        'text/html;q=',
        'text/html;q=-1',
        'text/html;q=2',
        'text/html;q=1.001',
        'text/html;q=0.0001',
        'text/html;q=00',
        'text/html;q=01',
        'text/html;q=00.1',
        'text/html,q=0.1',
        'text/html;q =1',
        'text/html;q= 1',
        'text/html;q=1;',
        'text/html;param;q=1',
        'text/html;q=1;extparam;',
        'text/html;q=1;extparam=val;',
        'text/html;q=1;extparam="val";',
        'text/html;q=1;extparam="',
        'text/html;q=1;extparam="val',
        'text/html;q=1;extparam=val"',
        'text/html;q=1;extparam=\x19',
        'text/html;q=1;extparam=\x22',
        'text/html;q=1;extparam=\x5c',
        'text/html;q=1;extparam=\x7f',
        r'text/html;q=1;extparam="\"',
        r'text/html;q=1;extparam="\\\"',
        r'text/html;q=1;extparam="\\""',
        'text/html;q=1;extparam="\\\x19"',
        'text/html;q=1;extparam="\\\x7f"',
        'text/html;param=\x19;q=1;extparam',
        'text/html;param=val;q=1;extparam=\x19',
    ])
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptValidHeader.parse(value=value)

    @pytest.mark.parametrize('value, expected_list', [
        # Examples from RFC 7231, Section 5.3.2 "Accept":
        (
            'audio/*; q=0.2, audio/basic',
            [('audio/*', 0.2, [], []), ('audio/basic', 1.0, [], [])],
        ),
        (
            'text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c',
            [
                ('text/plain', 0.5, [], []),
                ('text/html', 1.0, [], []),
                ('text/x-dvi', 0.8, [], []),
                ('text/x-c', 1.0, [], []),
            ],
        ),
        (
            'text/*, text/plain, text/plain;format=flowed, */*',
            [
                ('text/*', 1.0, [], []),
                ('text/plain', 1.0, [], []),
                ('text/plain;format=flowed', 1.0, [('format', 'flowed')], []),
                ('*/*', 1.0, [], []),
            ],
        ),
        (
            'text/*;q=0.3, text/html;q=0.7, text/html;level=1, '
            'text/html;level=2;q=0.4, */*;q=0.5',
            [
                ('text/*', 0.3, [], []),
                ('text/html', 0.7, [], []),
                ('text/html;level=1', 1.0, [('level', '1')], []),
                ('text/html;level=2', 0.4, [('level', '2')], []),
                ('*/*', 0.5, [], []),
            ],
        ),
        # Our tests
        ('', []),
        (',', []),
        (', ,', []),
        (
            '*/*, text/*, text/html',
            [
                ('*/*', 1.0, [], []),
                ('text/*', 1.0, [], []),
                ('text/html', 1.0, [], []),
            ]
        ),
        # It does not seem from RFC 7231, section 5.3.2 "Accept" that the '*'
        # in a range like '*/html' was intended to have any special meaning
        # (the section lists '*/*', 'type/*' and 'type/subtype', but not
        # '*/subtype'). However, because type and subtype are tokens (section
        # 3.1.1.1), and a token may contain '*'s, '*/subtype' is valid.
        ('*/html', [('*/html', 1.0, [], [])]),
        (
            'text/html \t;\t param1=val1\t; param2="val2" ' +
            r'; param3="\"\\\\"',
            [(
                r'text/html;param1=val1;param2=val2;param3="\"\\\\"', 1.0,
                [('param1', 'val1'), ('param2', 'val2'), ('param3', r'"\\')],
                [],
            )],
        ),
        (
            'text/html;param=!#$%&\'*+-.^_`|~09AZaz',
            [(
                'text/html;param=!#$%&\'*+-.^_`|~09AZaz', 1.0,
                [('param', '!#$%&\'*+-.^_`|~09AZaz')], [],
            )],
        ),
        (
            'text/html;param=""',
            [('text/html;param=""', 1.0, [('param', '')], [])],
        ),
        (
            'text/html;param="\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"',
            [(
                'text/html;param="\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"',
                1.0,
                [('param', '\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e')], [],
            )],
        ),
        (
            'text/html;param="\x80\x81\xfe\xff\\\x22\\\x5c"',
            [(
                'text/html;param="\x80\x81\xfe\xff\\\x22\\\x5c"', 1.0,
                [('param', '\x80\x81\xfe\xff\x22\x5c')], [],
            )],
        ),
        (
            'text/html;param="\\\t\\ \\\x21\\\x7e\\\x80\\\xff"',
            [(
                'text/html;param="\t \x21\x7e\x80\xff"', 1.0,
                [('param', '\t \x21\x7e\x80\xff')], [],
            )],
        ),
        (
            "text/html;param='val'",
            # This makes it look like the media type parameter value could be
            # surrounded with single quotes instead of double quotes, but the
            # single quotes are actually part of the media type parameter value
            # token
            [("text/html;param='val'", 1.0, [('param', "'val'")], [])],
        ),
        ('text/html;q=0.9', [('text/html', 0.9, [], [])]),
        ('text/html;q=0', [('text/html', 0.0, [], [])]),
        ('text/html;q=0.0', [('text/html', 0.0, [], [])]),
        ('text/html;q=0.00', [('text/html', 0.0, [], [])]),
        ('text/html;q=0.000', [('text/html', 0.0, [], [])]),
        ('text/html;q=1', [('text/html', 1.0, [], [])]),
        ('text/html;q=1.0', [('text/html', 1.0, [], [])]),
        ('text/html;q=1.00', [('text/html', 1.0, [], [])]),
        ('text/html;q=1.000', [('text/html', 1.0, [], [])]),
        ('text/html;q=0.1', [('text/html', 0.1, [], [])]),
        ('text/html;q=0.87', [('text/html', 0.87, [], [])]),
        ('text/html;q=0.382', [('text/html', 0.382, [], [])]),
        ('text/html;Q=0.382', [('text/html', 0.382, [], [])]),
        ('text/html ;Q=0.382', [('text/html', 0.382, [], [])]),
        ('text/html; Q=0.382', [('text/html', 0.382, [], [])]),
        ('text/html  ;  Q=0.382', [('text/html', 0.382, [], [])]),
        ('text/html;q=0.9;q=0.8', [('text/html', 0.9, [], [('q', '0.8')])]),
        (
            'text/html;q=1;q=1;q=1',
            [('text/html', 1.0, [], [('q', '1'), ('q', '1')])],
        ),
        (
            'text/html;q=0.9;extparam1;extparam2=val2;extparam3="val3"',
            [(
                'text/html', 0.9, [],
                ['extparam1', ('extparam2', 'val2'), ('extparam3', 'val3')]
            )],
        ),
        (
            'text/html;q=1;extparam=!#$%&\'*+-.^_`|~09AZaz',
            [('text/html', 1.0, [], [('extparam', '!#$%&\'*+-.^_`|~09AZaz')])],
        ),
        (
            'text/html;q=1;extparam=""',
            [('text/html', 1.0, [], [('extparam', '')])],
        ),
        (
            'text/html;q=1;extparam="\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e"',
            [(
                'text/html', 1.0, [],
                [('extparam', '\t \x21\x23\x24\x5a\x5b\x5d\x5e\x7d\x7e')],
            )],
        ),
        (
            'text/html;q=1;extparam="\x80\x81\xfe\xff\\\x22\\\x5c"',
            [(
                'text/html', 1.0, [],
                [('extparam', '\x80\x81\xfe\xff\x22\x5c')],
            )],
        ),
        (
            'text/html;q=1;extparam="\\\t\\ \\\x21\\\x7e\\\x80\\\xff"',
            [('text/html', 1.0, [], [('extparam', '\t \x21\x7e\x80\xff')])],
        ),
        (
            "text/html;q=1;extparam='val'",
            # This makes it look like the extension parameter value could be
            # surrounded with single quotes instead of double quotes, but the
            # single quotes are actually part of the extension parameter value
            # token
            [('text/html', 1.0, [], [('extparam', "'val'")])],
        ),
        (
            'text/html;param1="val1";param2=val2;q=0.9;extparam1="val1"'
            ';extparam2;extparam3=val3',
            [(
                'text/html;param1=val1;param2=val2', 0.9,
                [('param1', 'val1'), ('param2', 'val2')],
                [('extparam1', 'val1'), 'extparam2', ('extparam3', 'val3')],
            )],
        ),
        (
            ', ,, a/b \t;\t p1=1  ;\t\tp2=2  ;  q=0.6\t \t;\t\t e1\t; e2,  ,',
            [('a/b;p1=1;p2=2', 0.6, [('p1', '1'), ('p2', '2')], ['e1', 'e2'])],
        ),
        (
            (
                ',\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, ' +
                'g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,'
            ),
            [
                ('a/b', 1.0, [], ['e1', ('e2', 'v2')]),
                ('c/d', 1.0, [], []),
                ('e/f;p1=v1', 0.0, [('p1', 'v1')], ['e1']),
                ('g/h;p1=v1;p2=v2', 0.5, [('p1', 'v1'), ('p2', 'v2')], []),
            ],
        ),
    ])
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptValidHeader.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list

    @pytest.mark.parametrize('offer, expected_return, expected_str', [
        ['text/html', ('text', 'html', ()), 'text/html'],
        [
            'text/html;charset=utf8',
            ('text', 'html', (('charset', 'utf8'),)),
            'text/html;charset=utf8',
        ],
        [
            'text/html;charset=utf8;x-version=1',
            ('text', 'html', (('charset', 'utf8'), ('x-version', '1'))),
            'text/html;charset=utf8;x-version=1',
        ],
        [
            'text/HtMl;cHaRseT=UtF-8;X-Version=1',
            ('text', 'html', (('charset', 'UtF-8'), ('x-version', '1'))),
            'text/html;charset=UtF-8;x-version=1',
        ],
    ])
    def test_parse_offer__valid(self, offer, expected_return, expected_str):
        result = Accept.parse_offer(offer)
        assert result == expected_return
        assert str(result) == expected_str
        assert result is Accept.parse_offer(result)

    @pytest.mark.parametrize('offer', [
        '',
        'foo',
        'foo/bar/baz',
        '*/plain',
        '*/plain;charset=utf8',
        '*/plain;charset=utf8;x-version=1',
        '*/*;charset=utf8',
        'text/*;charset=utf8',
        'text/*',
        '*/*',
    ])
    def test_parse_offer__invalid(self, offer):
        with pytest.raises(ValueError):
            Accept.parse_offer(offer)


class TestAcceptValidHeader(object):
    def test_parse__inherited(self):
        returned = AcceptValidHeader.parse(
            value=(
                ',\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, '
                + 'g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,'
            ),
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ('a/b', 1.0, [], ['e1', ('e2', 'v2')]),
            ('c/d', 1.0, [], []),
            ('e/f;p1=v1', 0.0, [('p1', 'v1')], ['e1']),
            ('g/h;p1=v1;p2=v2', 0.5, [('p1', 'v1'), ('p2', 'v2')], []),
        ]

    @pytest.mark.parametrize('header_value', [
        ', ',
        'text/html;param=val;q=1;extparam=\x19',
    ])
    def test___init___invalid_header(self, header_value):
        with pytest.raises(ValueError):
            AcceptValidHeader(header_value=header_value)

    def test___init___valid_header(self):
        header_value = (
            ',\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, ' +
            'g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,'
        )
        instance = AcceptValidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed == [
            ('a/b', 1.0, [], ['e1', ('e2', 'v2')]),
            ('c/d', 1.0, [], []),
            ('e/f;p1=v1', 0.0, [('p1', 'v1')], ['e1']),
            ('g/h;p1=v1;p2=v2', 0.5, [('p1', 'v1'), ('p2', 'v2')], []),
        ]
        assert instance._parsed_nonzero == [
            ('a/b', 1.0, [], ['e1', ('e2', 'v2')]),
            ('c/d', 1.0, [], []),
            ('g/h;p1=v1;p2=v2', 0.5, [('p1', 'v1'), ('p2', 'v2')], []),
        ]
        assert isinstance(instance, Accept)

    def test___add___None(self):
        left_operand = AcceptValidHeader(header_value='text/html')
        result = left_operand + None
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('right_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
        {', ;level=1': (1.0, ';e1=1')},
        'a/b, c/d;q=1;e1;',
        ['a/b', 'c/d;q=1;e1;'],
        ('a/b', 'c/d;q=1;e1;',),
        {'a/b': 1.0, 'cd': 1.0},
        {'a/b': (1.0, ';e1=1'), 'c/d': (1.0, ';e2=2;')},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptValidHeader(header_value='text/html')
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('str_', [', ', 'a/b, c/d;q=1;e1;'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptValidHeader(header_value='text/html')
        class Other(object):
            def __str__(self):
                return str_
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___add___valid_empty_value(self, value):
        left_operand = AcceptValidHeader(header_value=',\t ,i/j, k/l;q=0.333,')
        result = left_operand + value
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    def test___add___other_type_with_valid___str___empty(self):
        left_operand = AcceptValidHeader(header_value=',\t ,i/j, k/l;q=0.333,')
        class Other(object):
            def __str__(self):
                return ''
        result = left_operand + Other()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        header = ',\t ,i/j, k/l;q=0.333,'
        result = AcceptValidHeader(header_value=header) + value
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == header + ', ' + value_as_header

    def test___add___other_type_with_valid___str___not_empty(self):
        header = ',\t ,i/j, k/l;q=0.333,'
        class Other(object):
            def __str__(self):
                return 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        right_operand = Other()
        result = AcceptValidHeader(header_value=header) + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == header + ', ' + str(right_operand)

    def test___add___AcceptValidHeader_header_value_empty(self):
        left_operand = AcceptValidHeader(
            header_value='a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        )
        right_operand = AcceptValidHeader(header_value='')
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    def test___add___AcceptValidHeader_header_value_not_empty(self):
        left_operand = AcceptValidHeader(
            header_value='a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        )
        right_operand = AcceptValidHeader(
            header_value=',\t ,i/j, k/l;q=0.333,',
        )
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == left_operand.header_value + ', ' + \
            right_operand.header_value

    def test___add___AcceptNoHeader(self):
        valid_header_instance = AcceptValidHeader(header_value='a/b')
        result = valid_header_instance + AcceptNoHeader()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    @pytest.mark.parametrize('header_value', [
        ', ',
        'a/b;p1=1;p2=2;q=0.8;e1;e2="',
    ])
    def test___add___AcceptInvalidHeader(self, header_value):
        valid_header_instance = AcceptValidHeader(header_value='a/b')
        result = valid_header_instance + AcceptInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    def test___bool__(self):
        instance = AcceptValidHeader(header_value='type/subtype')
        returned = bool(instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        accept = AcceptValidHeader('A/a, B/b, C/c')
        assert 'A/a' in accept
        assert 'A/*' in accept
        assert '*/a' in accept
        assert 'A/b' not in accept
        assert 'B/a' not in accept
        for mask in ['*/*', 'text/html', 'TEXT/HTML']:
            assert 'text/html' in AcceptValidHeader(mask)

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptValidHeader(
            header_value=(
                'text/plain; q=0.5, text/html; q=0, text/x-dvi; q=0.8, '
                'text/x-c'
            ),
        )
        assert list(instance) == ['text/x-c', 'text/x-dvi', 'text/plain']

    def test___radd___None(self):
        right_operand = AcceptValidHeader(header_value='a/b')
        result = None + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
        {', ;level=1': (1.0, ';e1=1')},
        'a/b, c/d;q=1;e1;',
        ['a/b', 'c/d;q=1;e1;'],
        ('a/b', 'c/d;q=1;e1;',),
        {'a/b': 1.0, 'cd': 1.0},
        {'a/b': (1.0, ';e1=1'), 'c/d': (1.0, ';e2=2;')},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptValidHeader(header_value='a/b')
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('str_', [', ', 'a/b, c/d;q=1;e1;'])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptValidHeader(header_value='a/b')
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___radd___valid_empty_value(self, value):
        right_operand = AcceptValidHeader(header_value='a/b')
        result = value + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___radd___other_type_with_valid___str___empty(self):
        right_operand = AcceptValidHeader(
            header_value=',\t ,i/j, k/l;q=0.333,',
        )
        class Other(object):
            def __str__(self):
                return ''
        result = Other() + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test___radd___valid_non_empty_value(self, value, value_as_header):
        header = ',\t ,i/j, k/l;q=0.333,'
        result = value + AcceptValidHeader(header_value=header)
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == value_as_header + ', ' + header

    def test___radd___other_type_with_valid___str___not_empty(self):
        header = ',\t ,i/j, k/l;q=0.333,'
        class Other(object):
            def __str__(self):
                return 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        left_operand = Other()
        result = left_operand + AcceptValidHeader(header_value=header)
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == str(left_operand) + ', ' + header

    @pytest.mark.parametrize('header_value, expected_returned', [
        ('', "<AcceptValidHeader ('')>"),
        (
            r',,text/html ; p1="\"\1\"" ; q=0.50; e1=1 ;e2  ,  text/plain ,',
            r'''<AcceptValidHeader ('text/html;p1="\\"1\\"";q=0.5;e1=1;e2''' +
            ", text/plain')>",
        ),
        (
            ',\t, a/b ;  p1=1 ; p2=2 ;\t q=0.20 ;\te1="\\"\\1\\""\t; e2 ; ' +
            'e3=3, c/d ,,',
            r'''<AcceptValidHeader ('a/b;p1=1;p2=2;q=0.2;e1="\\"1\\"";e2''' +
            ";e3=3, c/d')>"
        ),
    ])
    def test___repr__(self, header_value, expected_returned):
        instance = AcceptValidHeader(header_value=header_value)
        assert repr(instance) == expected_returned

    @pytest.mark.parametrize('header_value, expected_returned', [
        ('', ''),
        (
            r',,text/html ; p1="\"\1\"" ; q=0.50; e1=1 ;e2  ,  text/plain ,',
            r'text/html;p1="\"1\"";q=0.5;e1=1;e2, text/plain',
        ),
        (
            ',\t, a/b ;  p1=1 ; p2=2 ;\t q=0.20 ;\te1="\\"\\1\\""\t; e2 ; ' +
            'e3=3, c/d ,,',
            'a/b;p1=1;p2=2;q=0.2;e1="\\"1\\"";e2;e3=3, c/d'
        ),
    ])
    def test___str__(self, header_value, expected_returned):
        instance = AcceptValidHeader(header_value=header_value)
        assert str(instance) == expected_returned

    def test__old_match(self):
        accept = AcceptValidHeader('image/jpg')
        assert accept._old_match('image/jpg', 'image/jpg')
        assert accept._old_match('image/*', 'image/jpg')
        assert accept._old_match('*/*', 'image/jpg')
        assert not accept._old_match('text/html', 'image/jpg')

        mismatches = [
            ('B/b', 'A/a'),
            ('B/b', 'B/a'),
            ('B/b', 'A/b'),
            ('A/a', 'B/b'),
            ('B/a', 'B/b'),
            ('A/b', 'B/b')
        ]
        for mask, offer in mismatches:
            assert not accept._old_match(mask, offer)

    def test__old_match_wildcard_matching(self):
        """
        Wildcard matching forces the match to take place against the type or
        subtype of the mask and offer (depending on where the wildcard matches)
        """
        accept = AcceptValidHeader('type/subtype')
        matches = [
            ('*/*', '*/*'),
            ('*/*', 'A/*'),
            ('*/*', '*/a'),
            ('*/*', 'A/a'),
            ('A/*', '*/*'),
            ('A/*', 'A/*'),
            ('A/*', '*/a'),
            ('A/*', 'A/a'),
            ('*/a', '*/*'),
            ('*/a', 'A/*'),
            ('*/a', '*/a'),
            ('*/a', 'A/a'),
            ('A/a', '*/*'),
            ('A/a', 'A/*'),
            ('A/a', '*/a'),
            ('A/a', 'A/a'),
            # Offers might not contain a subtype
            ('*/*', '*'),
            ('A/*', '*'),
            ('*/a', '*')]
        for mask, offer in matches:
            assert accept._old_match(mask, offer)
            # Test malformed mask and offer variants where either is missing a
            # type or subtype
            assert accept._old_match('A', offer)
            assert accept._old_match(mask, 'a')

        mismatches = [
            ('B/b', 'A/*'),
            ('B/*', 'A/a'),
            ('B/*', 'A/*'),
            ('*/b', '*/a')]
        for mask, offer in mismatches:
            assert not accept._old_match(mask, offer)

    @pytest.mark.parametrize('header_value, returned', [
        ('tExt/HtMl', True),
        ('APPlication/XHTML+xml', True),
        ('appliCATION/xMl', True),
        ('TeXt/XmL', True),
        ('image/jpg', False),
        ('TeXt/Plain', False),
        ('image/jpg, text/html', True),
    ])
    def test_accept_html(self, header_value, returned):
        instance = AcceptValidHeader(header_value=header_value)
        assert instance.accept_html() is returned

    @pytest.mark.parametrize('header_value, returned', [
        ('tExt/HtMl', True),
        ('APPlication/XHTML+xml', True),
        ('appliCATION/xMl', True),
        ('TeXt/XmL', True),
        ('image/jpg', False),
        ('TeXt/Plain', False),
        ('image/jpg, text/html', True),
    ])
    def test_accepts_html(self, header_value, returned):
        instance = AcceptValidHeader(header_value=header_value)
        assert instance.accepts_html is returned

    @pytest.mark.parametrize('header, offers, expected_returned', [
        (AcceptValidHeader('text/html'), ['text/html;p=1;q=0.5'], []),
        (AcceptValidHeader('text/html'), ['text/html;q=0.5'], []),
        (AcceptValidHeader('text/html'), ['text/html;q=0.5;e=1'], []),
        (
            AcceptValidHeader('text/html'),
            ['text/html', 'text/plain;p=1;q=0.5;e=1', 'foo'],
            [('text/html', 1.0)],
        ),
        (
            AcceptInvalidHeader('foo'),
            ['text/html', 'text/plain;p=1;q=0.5;e=1', 'foo'],
            [('text/html', 1.0)],
        ),
        (
            AcceptNoHeader(),
            ['text/html', 'text/plain;p=1;q=0.5;e=1', 'foo'],
            [('text/html', 1.0)],
        ),
    ])
    def test_acceptable_offers__invalid_offers(
        self, header, offers, expected_returned,
    ):
        assert header.acceptable_offers(offers=offers) == expected_returned

    @pytest.mark.parametrize('header_value, offers, expected_returned', [
        # RFC 7231, section 5.3.2
        (
            'audio/*; q=0.2, audio/basic',
            ['audio/mpeg', 'audio/basic'],
            [('audio/basic', 1.0), ('audio/mpeg', 0.2)],
        ),
        (
            'text/plain; q=0.5, text/html, text/x-dvi; q=0.8, text/x-c',
            ['text/x-dvi', 'text/x-c', 'text/html', 'text/plain'],
            [
                ('text/x-c', 1.0), ('text/html', 1.0), ('text/x-dvi', 0.8),
                ('text/plain', 0.5),
            ],
        ),
        (
            'text/*;q=0.3, text/html;q=0.7, text/html;level=1, ' +
            'text/html;level=2;q=0.4, */*;q=0.5',
            [
                'text/html;level=1',
                'text/html',
                'text/plain',
                'image/jpeg',
                'text/html;level=2',
                'text/html;level=3',
            ],
            [
                ('text/html;level=1', 1.0),
                ('text/html', 0.7),
                ('text/html;level=3', 0.7),
                ('image/jpeg', 0.5),
                ('text/html;level=2', 0.4),
                ('text/plain', 0.3),
            ],
        ),
        # Our tests
        (
            'teXT/*;Q=0.5, TeXt/hTmL;LeVeL=1',
            ['tExT/HtMl;lEvEl=1', 'TExt/PlAiN'],
            [('tExT/HtMl;lEvEl=1', 1.0), ('TExt/PlAiN', 0.5)],
        ),
        (
            'text/html, application/json',
            ['text/html', 'application/json'],
            [('text/html', 1.0), ('application/json', 1.0)],
        ),
        (
            'text/html  ;\t level=1',
            ['text/html\t\t ; \tlevel=1'],
            [('text/html\t\t ; \tlevel=1', 1.0)],
        ),
        ('', ['text/html'], []),
        ('text/html, image/jpeg', ['audio/basic', 'text/plain'], []),
        (
            r'text/html;p1=1;p2=2;p3="\""', [r'text/html;p1=1;p2="2";p3="\""'],
            [(r'text/html;p1=1;p2="2";p3="\""', 1.0)],
        ),
        ('text/html;p1=1', ['text/html;p1=2'], []),
        ('text/html', ['text/html;p1=1'], [('text/html;p1=1', 1.0)]),
        ('text/html;p1=1', ['text/html'], []),
        ('text/html', ['text/html'], [('text/html', 1.0)]),
        ('text/*', ['text/html;p=1'], [('text/html;p=1', 1.0)]),
        ('*/*', ['text/html;p=1'], [('text/html;p=1', 1.0)]),
        ('text/*', ['text/html'], [('text/html', 1.0)]),
        ('*/*', ['text/html'], [('text/html', 1.0)]),
        ('text/html;p1=1;q=0', ['text/html;p1=1'], []),
        ('text/html;q=0', ['text/html;p1=1', 'text/html'], []),
        ('text/*;q=0', ['text/html;p1=1', 'text/html', 'text/plain'], []),
        (
            '*/*;q=0',
            ['text/html;p1=1', 'text/html', 'text/plain', 'image/jpeg'], [],
        ),
        (
            '*/*;q=0, audio/mpeg',
            [
                'text/html;p1=1', 'audio/mpeg', 'text/html', 'text/plain',
                'image/jpeg',
            ],
            [('audio/mpeg', 1.0)],
        ),
        (
            'text/html;p1=1, text/html;q=0',
            ['text/html;p1=1'],
            [('text/html;p1=1', 1.0)],
        ),
        ('text/html, text/*;q=0', ['text/html'], [('text/html', 1.0)]),
        ('text/*, */*;q=0', ['text/html'], [('text/html', 1.0)]),
        ('text/html;q=0, text/html', ['text/html'], []),
        (
            'text/html',
            ['text/html;level=1', 'text/html', 'text/html;level=2'],
            [
                ('text/html;level=1', 1.0),
                ('text/html', 1.0),
                ('text/html;level=2', 1.0),
            ],
        ),
        (
            'text/*;q=0.3, text/html;q=0, image/png, text/html;level=1, ' +
            'text/html;level=2;q=0.4, image/jpeg;q=0.5',
            [
                'text/html;level=1',
                'text/html',
                'text/plain',
                'image/jpeg',
                'text/html;level=2',
                'text/html;level=3',
                'audio/basic',
            ],
            [
                ('text/html;level=1', 1.0),
                ('image/jpeg', 0.5),
                ('text/html;level=2', 0.4),
                ('text/plain', 0.3),
            ],
        ),
        (
            'text/*;q=0.3, text/html;q=0.5, text/html;level=1;q=0.7',
            ['text/*', '*/*', 'text/html', 'image/*'],
            [('text/html', 0.5)],
        ),
        (
            'text/html;level=1;q=0.7',
            ['text/*', '*/*', 'text/html', 'text/html;level=1', 'image/*'],
            [('text/html;level=1', 0.7)],
        ),
        (
            '*/*',
            ['text/*'],
            [],
        ),
        (
            '',
            ['text/*', '*/*', 'text/html', 'text/html;level=1', 'image/*'],
            [],
        ),
    ])
    def test_acceptable_offers__valid_offers(
        self, header_value, offers, expected_returned,
    ):
        instance = AcceptValidHeader(header_value=header_value)
        returned = instance.acceptable_offers(offers=offers)
        assert returned == expected_returned

    def test_acceptable_offers_uses_AcceptOffer_objects(self):
        from webob.acceptparse import AcceptOffer
        offer = AcceptOffer('text', 'html', (('level', '1'),))
        instance = AcceptValidHeader(header_value='text/*;q=0.5')
        result = instance.acceptable_offers([offer])
        assert result == [(offer, 0.5)]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptValidHeader('text/html, foo/bar')
        assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
        assert accept.best_match(['foo/bar', 'text/html']) == 'foo/bar'
        assert accept.best_match([('foo/bar', 0.5),
                                  'text/html']) == 'text/html'
        assert accept.best_match([('foo/bar', 0.5),
                                  ('text/html', 0.4)]) == 'foo/bar'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_with_one_lower_q(self):
        accept = AcceptValidHeader('text/html, foo/bar;q=0.5')
        assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
        accept = AcceptValidHeader('text/html;q=0.5, foo/bar')
        assert accept.best_match(['text/html', 'foo/bar']) == 'foo/bar'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_with_complex_q(self):
        accept = AcceptValidHeader(
            'text/html, foo/bar;q=0.55, baz/gort;q=0.59'
        )
        assert accept.best_match(['text/html', 'foo/bar']) == 'text/html'
        accept = AcceptValidHeader(
            'text/html;q=0.5, foo/bar;q=0.586, baz/gort;q=0.596'
        )
        assert accept.best_match(['text/html', 'baz/gort']) == 'baz/gort'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_json(self):
        accept = AcceptValidHeader('text/html, */*; q=0.2')
        assert accept.best_match(['application/json']) == 'application/json'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_mixedcase(self):
        accept = AcceptValidHeader(
            'image/jpg; q=0.2, Image/pNg; Q=0.4, image/*; q=0.05'
        )
        assert accept.best_match(['Image/JpG']) == 'Image/JpG'
        assert accept.best_match(['image/Tiff']) == 'image/Tiff'
        assert accept.best_match(['image/Tiff', 'image/PnG', 'image/jpg']) == \
            'image/PnG'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test_best_match_zero_quality(self):
        assert AcceptValidHeader('text/plain, */*;q=0').best_match(
            ['text/html']
        ) is None
        assert 'audio/basic' not in AcceptValidHeader('*/*;q=0')

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        accept = AcceptValidHeader('text/html')
        assert accept.quality('text/html') == 1
        accept = AcceptValidHeader('text/html;q=0.5')
        assert accept.quality('text/html') == 0.5

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality_not_found(self):
        accept = AcceptValidHeader('text/html')
        assert accept.quality('foo/bar') is None


class TestAcceptNoHeader(object):
    def test_parse__inherited(self):
        returned = AcceptNoHeader.parse(
            value=(
                ',\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, '
                + 'g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,'
            ),
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ('a/b', 1.0, [], ['e1', ('e2', 'v2')]),
            ('c/d', 1.0, [], []),
            ('e/f;p1=v1', 0.0, [('p1', 'v1')], ['e1']),
            ('g/h;p1=v1;p2=v2', 0.5, [('p1', 'v1'), ('p2', 'v2')], []),
        ]

    def test___init__(self):
        instance = AcceptNoHeader()
        assert instance.header_value is None
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, Accept)

    def test___add___None(self):
        left_operand = AcceptNoHeader()
        result = left_operand + None
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('right_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
        {', ;level=1': (1.0, ';e1=1')},
        'a/b, c/d;q=1;e1;',
        ['a/b', 'c/d;q=1;e1;'],
        ('a/b', 'c/d;q=1;e1;',),
        {'a/b': 1.0, 'cd': 1.0},
        {'a/b': (1.0, ';e1=1'), 'c/d': (1.0, ';e2=2;')},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('str_', [', ', 'a/b, c/d;q=1;e1;'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___add___valid_empty_value(self, value):
        left_operand = AcceptNoHeader()
        result = left_operand + value
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    def test___add___other_type_with_valid___str___empty(self):
        left_operand = AcceptNoHeader()
        class Other(object):
            def __str__(self):
                return ''
        result = left_operand + Other()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptNoHeader() + value
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        right_operand = Other()
        result = AcceptNoHeader() + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptValidHeader_header_value_empty(self):
        right_operand = AcceptValidHeader(header_value='')
        result = AcceptNoHeader() + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptValidHeader_header_value_not_empty(self):
        right_operand = AcceptValidHeader(
            header_value=',\t ,i/j, k/l;q=0.333,',
        )
        result = AcceptNoHeader() + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value

    def test___add___AcceptNoHeader(self):
        left_operand = AcceptNoHeader()
        right_operand = AcceptNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)
        assert result is not left_operand
        assert result is not right_operand

    @pytest.mark.parametrize('header_value', [
        ', ',
        'a/b;p1=1;p2=2;q=0.8;e1;e2="',
    ])
    def test___add___AcceptInvalidHeader(self, header_value):
        left_operand = AcceptNoHeader()
        result = left_operand + AcceptInvalidHeader(header_value=header_value)
        assert isinstance(result, AcceptNoHeader)
        assert result is not left_operand

    def test___bool__(self):
        instance = AcceptNoHeader()
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptNoHeader()
        returned = ('type/subtype' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptNoHeader()
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptNoHeader()
        result = None + right_operand
        assert isinstance(result, AcceptNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
        {', ;level=1': (1.0, ';e1=1')},
        'a/b, c/d;q=1;e1;',
        ['a/b', 'c/d;q=1;e1;'],
        ('a/b', 'c/d;q=1;e1;',),
        {'a/b': 1.0, 'cd': 1.0},
        {'a/b': (1.0, ';e1=1'), 'c/d': (1.0, ';e2=2;')},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('str_', [', ', 'a/b, c/d;q=1;e1;'])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___radd___valid_empty_value(self, value):
        result = value + AcceptNoHeader()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    def test___radd___other_type_with_valid___str___empty(self):
        class Other(object):
            def __str__(self):
                return ''
        result = Other() + AcceptNoHeader()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test___radd___valid_non_empty_value(self, value, value_as_header):
        result = value + AcceptNoHeader()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        left_operand = Other()
        result = left_operand + AcceptNoHeader()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptNoHeader()
        assert repr(instance) == '<AcceptNoHeader>'

    def test___str__(self):
        instance = AcceptNoHeader()
        assert str(instance) == '<no header in request>'

    def test_accept_html(self):
        instance = AcceptNoHeader()
        assert instance.accept_html() is True

    def test_accepts_html(self):
        instance = AcceptNoHeader()
        assert instance.accepts_html is True

    def test_acceptable_offers(self):
        instance = AcceptNoHeader()
        returned = instance.acceptable_offers(offers=['a/b', 'c/d', 'e/f'])
        assert returned == [('a/b', 1.0), ('c/d', 1.0), ('e/f', 1.0)]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptNoHeader()
        assert accept.best_match(['text/html', 'audio/basic']) == 'text/html'
        assert accept.best_match([('text/html', 1), ('audio/basic', 0.5)]) == \
            'text/html'
        assert accept.best_match([('text/html', 0.5), ('audio/basic', 1)]) == \
            'audio/basic'
        assert accept.best_match([('text/html', 0.5), 'audio/basic']) == \
            'audio/basic'
        assert accept.best_match(
            [('text/html', 0.5), 'audio/basic'], default_match=True
        ) == 'audio/basic'
        assert accept.best_match(
            [('text/html', 0.5), 'audio/basic'], default_match=False
        ) == 'audio/basic'
        assert accept.best_match([], default_match='fallback') == 'fallback'

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptNoHeader()
        returned = instance.quality(offer='type/subtype')
        assert returned == 1.0


class TestAcceptInvalidHeader(object):
    def test_parse__inherited(self):
        returned = AcceptInvalidHeader.parse(
            value=(
                ',\t , a/b;q=1;e1;e2=v2 \t,\t\t c/d, e/f;p1=v1;q=0;e1, '
                + 'g/h;p1=v1\t ;\t\tp2=v2;q=0.5 \t,'
            ),
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ('a/b', 1.0, [], ['e1', ('e2', 'v2')]),
            ('c/d', 1.0, [], []),
            ('e/f;p1=v1', 0.0, [('p1', 'v1')], ['e1']),
            ('g/h;p1=v1;p2=v2', 0.5, [('p1', 'v1'), ('p2', 'v2')], []),
        ]

    def test___init__(self):
        header_value = ', '
        instance = AcceptInvalidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, Accept)

    def test___add___None(self):
        left_operand = AcceptInvalidHeader(header_value=', ')
        result = left_operand + None
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('right_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
        {', ;level=1': (1.0, ';e1=1')},
        'a/b, c/d;q=1;e1;',
        ['a/b', 'c/d;q=1;e1;'],
        ('a/b', 'c/d;q=1;e1;',),
        {'a/b': 1.0, 'cd': 1.0},
        {'a/b': (1.0, ';e1=1'), 'c/d': (1.0, ';e2=2;')},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptInvalidHeader(header_value='invalid header')
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('str_', [', ', 'a/b, c/d;q=1;e1;'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptInvalidHeader(header_value='invalid header')
        class Other(object):
            def __str__(self):
                return str_
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___add___valid_empty_value(self, value):
        left_operand = AcceptInvalidHeader(header_value=', ')
        result = left_operand + value
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    def test___add___other_type_with_valid___str___empty(self):
        left_operand = AcceptInvalidHeader(header_value=', ')
        class Other(object):
            def __str__(self):
                return ''
        result = left_operand + Other()
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptInvalidHeader(header_value=', ') + value
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        right_operand = Other()
        result = AcceptInvalidHeader(header_value=', ') + \
            right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptValidHeader_header_value_empty(self):
        left_operand = AcceptInvalidHeader(header_value=', ')
        right_operand = AcceptValidHeader(header_value='')
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptValidHeader_header_value_not_empty(self):
        left_operand = AcceptInvalidHeader(header_value=', ')
        right_operand = AcceptValidHeader(
            header_value=',\t ,i/j, k/l;q=0.333,',
        )
        result = left_operand + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == right_operand.header_value

    def test___add___AcceptNoHeader(self):
        left_operand = AcceptInvalidHeader(header_value=', ')
        right_operand = AcceptNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('header_value', [
        ', ',
        'a/b;p1=1;p2=2;q=0.8;e1;e2="',
    ])
    def test___add___AcceptInvalidHeader(self, header_value):
        result = AcceptInvalidHeader(header_value=', ') + \
            AcceptInvalidHeader(header_value=header_value)
        assert isinstance(result, AcceptNoHeader)

    def test___bool__(self):
        instance = AcceptInvalidHeader(header_value=', ')
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptInvalidHeader(header_value=', ')
        returned = ('type/subtype' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptInvalidHeader(header_value=', ')
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptInvalidHeader(header_value=', ')
        result = None + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('left_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
        {', ;level=1': (1.0, ';e1=1')},
        'a/b, c/d;q=1;e1;',
        ['a/b', 'c/d;q=1;e1;'],
        ('a/b', 'c/d;q=1;e1;',),
        {'a/b': 1.0, 'cd': 1.0},
        {'a/b': (1.0, ';e1=1'), 'c/d': (1.0, ';e2=2;')},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptInvalidHeader(header_value=', ')
        result = left_operand + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('str_', [', ', 'a/b, c/d;q=1;e1;'])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptInvalidHeader(header_value=', ')
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptNoHeader)

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___radd___valid_empty_value(self, value):
        right_operand = AcceptInvalidHeader(header_value='invalid header')
        result = value + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    def test___radd___other_type_with_valid___str___empty(self):
        right_operand = AcceptInvalidHeader(header_value='invalid header')
        class Other(object):
            def __str__(self):
                return ''
        result = Other() + right_operand
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test___radd___valid_non_empty_value(self, value, value_as_header):
        result = value + AcceptInvalidHeader(header_value='invalid header')
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        left_operand = Other()
        result = left_operand + AcceptInvalidHeader(
            header_value='invalid header',
        )
        assert isinstance(result, AcceptValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptInvalidHeader(header_value='\x00')
        assert repr(instance) == '<AcceptInvalidHeader>'

    def test___str__(self):
        instance = AcceptInvalidHeader(header_value=", ")
        assert str(instance) == '<invalid header value>'

    def test_accept_html(self):
        instance = AcceptInvalidHeader(header_value=', ')
        assert instance.accept_html() is True

    def test_accepts_html(self):
        instance = AcceptInvalidHeader(header_value=', ')
        assert instance.accepts_html is True

    def test_acceptable_offers(self):
        instance = AcceptInvalidHeader(header_value=', ')
        returned = instance.acceptable_offers(offers=['a/b', 'c/d', 'e/f'])
        assert returned == [('a/b', 1.0), ('c/d', 1.0), ('e/f', 1.0)]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptInvalidHeader(header_value=', ')
        assert accept.best_match(['text/html', 'audio/basic']) == 'text/html'
        assert accept.best_match([('text/html', 1), ('audio/basic', 0.5)]) == \
            'text/html'
        assert accept.best_match([('text/html', 0.5), ('audio/basic', 1)]) == \
            'audio/basic'
        assert accept.best_match([('text/html', 0.5), 'audio/basic']) == \
            'audio/basic'
        assert accept.best_match(
            [('text/html', 0.5), 'audio/basic'], default_match=True
        ) == 'audio/basic'
        assert accept.best_match(
            [('text/html', 0.5), 'audio/basic'], default_match=False
        ) == 'audio/basic'
        assert accept.best_match([], default_match='fallback') == 'fallback'

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptInvalidHeader(header_value=', ')
        returned = instance.quality(offer='type/subtype')
        assert returned == 1.0


class TestCreateAcceptHeader(object):
    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_header(header_value=header_value)
        assert isinstance(returned, AcceptNoHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    def test_header_value_is_valid(self):
        header_value = 'text/html, text/plain;q=0.9'
        returned = create_accept_header(header_value=header_value)
        assert isinstance(returned, AcceptValidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    @pytest.mark.parametrize('header_value', [', ', 'noslash'])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_header(header_value=header_value)
        assert isinstance(returned, AcceptInvalidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value


class TestAcceptProperty(object):
    def test_fget_header_is_valid(self):
        header_value = 'text/html;p1="1";p2=v2;q=0.9;e1="1";e2, audio/basic'
        request = Request.blank('/', environ={'HTTP_ACCEPT': header_value})
        property_ = accept_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptValidHeader)
        assert returned.header_value == header_value

    def test_fget_header_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT': None})
        property_ = accept_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptNoHeader)

    def test_fget_header_is_invalid(self):
        header_value = 'invalid'
        request = Request.blank('/', environ={'HTTP_ACCEPT': header_value})
        property_ = accept_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptInvalidHeader)
        assert returned.header_value == header_value

    def test_fset_value_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        header_value = 'text/html;p1="1";p2=v2;q=0.9;e1="1";e2, audio/basic'
        property_ = accept_property()
        property_.fset(request=request, value=header_value)
        assert request.environ['HTTP_ACCEPT'] == header_value

    def test_fset_value_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        property_ = accept_property()
        property_.fset(request=request, value=None)
        assert 'HTTP_ACCEPT' not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        header_value = 'invalid'
        property_ = accept_property()
        property_.fset(request=request, value=header_value)
        assert request.environ['HTTP_ACCEPT'] == header_value

    @pytest.mark.parametrize('value, value_as_header', [
        ('', ''),
        ([], ''),
        ((), ''),
        ({}, ''),
        # str
        (
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of strs
        (
            ['a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 3-item tuples, with extension parameters
        (
            [
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # list of 2-item tuples, without extension parameters
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # list of a mixture of strs, 3-item tuples and 2-item tuples
        (
            [
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ],
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of strs
        (
            ('a/b;q=0.5', 'c/d;p1=1;q=0', 'e/f', 'g/h;p1=1;q=1;e1=1'),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 3-item tuples, with extension parameters
        (
            (
                ('a/b', 0.5, ''), ('c/d;p1=1', 0.0, ''),
                ('e/f', 1.0, ''), ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # tuple of 2-item tuples, without extension parameters
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0),
                ('e/f', 1.0), ('g/h;p1=1', 1.0),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1',
        ),
        # tuple of a mixture of strs, 3-item tuples and 2-item tuples
        (
            (
                ('a/b', 0.5), ('c/d;p1=1', 0.0, ''),
                'e/f', ('g/h;p1=1', 1.0, ';e1=1'),
            ),
            'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
        ),
        # dict
        (
            {
                'a/b': (0.5, ';e1=1'), 'c/d': 0.0,
                'e/f;p1=1': (1.0, ';e1=1;e2=2')
            },
            'e/f;p1=1;q=1;e1=1;e2=2, a/b;q=0.5;e1=1, c/d;q=0',
        ),
    ])
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        property_ = accept_property()
        property_.fset(request=request, value=value)
        assert request.environ['HTTP_ACCEPT'] == value_as_header

    @pytest.mark.parametrize('header_value', [
        '',
        'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1',
    ])
    def test_fset_other_type_with___str__(self, header_value):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        property_ = accept_property()
        class Other(object):
            def __str__(self):
                return header_value
        value = Other()
        property_.fset(request=request, value=value)
        assert request.environ['HTTP_ACCEPT'] == str(value)

    def test_fset_AcceptValidHeader(self):
        request = Request.blank('/', environ={})
        header_value = 'a/b;q=0.5, c/d;p1=1;q=0, e/f, g/h;p1=1;q=1;e1=1'
        header = AcceptValidHeader(header_value=header_value)
        property_ = accept_property()
        property_.fset(request=request, value=header)
        assert request.environ['HTTP_ACCEPT'] == header.header_value

    def test_fset_AcceptNoHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        property_ = accept_property()
        header = AcceptNoHeader()
        property_.fset(request=request, value=header)
        assert 'HTTP_ACCEPT' not in request.environ

    def test_fset_AcceptInvalidHeader(self):
        request = Request.blank('/', environ={})
        header_value = 'invalid'
        header = AcceptInvalidHeader(header_value=header_value)
        property_ = accept_property()
        property_.fset(request=request, value=header)
        assert request.environ['HTTP_ACCEPT'] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT': 'text/html'})
        property_ = accept_property()
        property_.fdel(request=request)
        assert 'HTTP_ACCEPT' not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank('/')
        property_ = accept_property()
        property_.fdel(request=request)
        assert 'HTTP_ACCEPT' not in request.environ


class TestAcceptCharset(object):
    @pytest.mark.parametrize('value', [
        '',
        '"',
        '(',
        ')',
        '/',
        ':',
        ';',
        '<',
        '=',
        '>',
        '?',
        '@',
        '[',
        '\\',
        ']',
        '{',
        '}',
        'foo, bar, baz;q= 0.001',
        'foo , ,bar,charlie   ',
    ])
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptCharset.parse(value=value)

    @pytest.mark.parametrize('value, expected_list', [
        ('*', [('*', 1.0)]),
        ("!#$%&'*+-.^_`|~;q=0.5", [("!#$%&'*+-.^_`|~", 0.5)]),
        ('0123456789', [('0123456789', 1.0)]),
        (
            ',\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tcharlie \t,,  ,',
            [('foo', 0.345), ('bar', 0.456), ('charlie', 1.0)]
        ),
        (
            'iso-8859-5;q=0.372,unicode-1-1;q=0.977,UTF-8, *;q=0.000',
            [
                ('iso-8859-5', 0.372), ('unicode-1-1', 0.977), ('UTF-8', 1.0),
                ('*', 0.0)
            ]
        ),
        # RFC 7230 Section 7
        ('foo,bar', [('foo', 1.0), ('bar', 1.0)]),
        ('foo, bar,', [('foo', 1.0), ('bar', 1.0)]),
        # RFC 7230 Errata ID: 4169
        ('foo , ,bar,charlie', [('foo', 1.0), ('bar', 1.0), ('charlie', 1.0)]),
    ])
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptCharset.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptCharsetValidHeader(object):
    def test_parse__inherited(self):
        returned = AcceptCharsetValidHeader.parse(
            value=',iso-8859-5 ; q=0.333 , ,utf-8,unicode-1-1 ;q=0.90,',
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ('iso-8859-5', 0.333),
            ('utf-8', 1.0),
            ('unicode-1-1', 0.9),
        ]

    @pytest.mark.parametrize('header_value', [
        '',
        ', iso-8859-5 ',
    ])
    def test___init___invalid_header(self, header_value):
        with pytest.raises(ValueError):
            AcceptCharsetValidHeader(header_value=header_value)

    def test___init___valid_header(self):
        header_value = \
            'iso-8859-5;q=0.372,unicode-1-1;q=0.977,UTF-8, *;q=0.000'
        instance = AcceptCharsetValidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed == [
            ('iso-8859-5', 0.372), ('unicode-1-1', 0.977), ('UTF-8', 1.0),
            ('*', 0.0)
        ]
        assert instance._parsed_nonzero == [
            ('iso-8859-5', 0.372), ('unicode-1-1', 0.977), ('UTF-8', 1.0),
        ]
        assert isinstance(instance, AcceptCharset)

    def test___add___None(self):
        left_operand = AcceptCharsetValidHeader(header_value='iso-8859-5')
        result = left_operand + None
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'UTF/8',
        ['UTF/8'],
        ('UTF/8',),
        {'UTF/8': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptCharsetValidHeader(header_value='iso-8859-5')
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('str_', ['', 'UTF/8'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptCharsetValidHeader(header_value='iso-8859-5')
        class Other(object):
            def __str__(self):
                return str_
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            [('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'],
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            (('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'),
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            {'UTF-7': 0.5, 'unicode-1-1': 0.0, 'UTF-8': 1.0},
            'UTF-8, UTF-7;q=0.5, unicode-1-1;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        left_operand = AcceptCharsetValidHeader(
            header_value=',\t ,iso-8859-5;q=0.333,',
        )
        result = left_operand + value
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == left_operand.header_value + ', ' + \
            value_as_header

    def test___add___other_type_with_valid___str__(self):
        left_operand = AcceptCharsetValidHeader(
            header_value=',\t ,iso-8859-5;q=0.333,',
        )
        class Other(object):
            def __str__(self):
                return 'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8'
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == left_operand.header_value + ', ' + \
            str(right_operand)

    def test___add___AcceptCharsetValidHeader(self):
        left_operand = AcceptCharsetValidHeader(
            header_value=',\t ,iso-8859-5;q=0.333,',
        )
        right_operand = AcceptCharsetValidHeader(
            header_value=', ,utf-7;q=0, \tutf-8;q=1,',
        )
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == left_operand.header_value + ', ' + \
            right_operand.header_value

    def test___add___AcceptCharsetNoHeader(self):
        valid_header_instance = AcceptCharsetValidHeader(
            header_value=', ,utf-7;q=0, \tutf-8;q=1,'
        )
        result = valid_header_instance + AcceptCharsetNoHeader()
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    @pytest.mark.parametrize('header_value', ['', 'utf/8'])
    def test___add___AcceptCharsetInvalidHeader(self, header_value):
        valid_header_instance = AcceptCharsetValidHeader(
            header_value='header',
        )
        result = valid_header_instance + AcceptCharsetInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    def test___bool__(self):
        instance = AcceptCharsetValidHeader(header_value='valid-header')
        returned = bool(instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        for mask in ['*', 'utf-8', 'UTF-8']:
            assert 'utf-8' in AcceptCharsetValidHeader(mask)
        assert 'utf-8' not in AcceptCharsetValidHeader('utf-7')

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains___not(self):
        accept = AcceptCharsetValidHeader('utf-8')
        assert 'utf-7' not in accept

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains___zero_quality(self):
        assert 'foo' not in AcceptCharsetValidHeader('*;q=0')

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptCharsetValidHeader(
            header_value=\
                'utf-8; q=0.5, utf-7; q=0, iso-8859-5; q=0.8, unicode-1-1',
        )
        assert list(instance) == ['unicode-1-1', 'iso-8859-5', 'utf-8']

    def test___radd___None(self):
        right_operand = AcceptCharsetValidHeader(header_value='iso-8859-5')
        result = None + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'UTF/8',
        ['UTF/8'],
        ('UTF/8',),
        {'UTF/8': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptCharsetValidHeader(header_value='iso-8859-5')
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('str_', ['', 'UTF/8'])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptCharsetValidHeader(header_value='iso-8859-5')
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            [('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'],
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            (('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'),
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            {'UTF-7': 0.5, 'unicode-1-1': 0.0, 'UTF-8': 1.0},
            'UTF-8, UTF-7;q=0.5, unicode-1-1;q=0',
        ),
    ])
    def test___radd___valid_value(self, value, value_as_header):
        right_operand = AcceptCharsetValidHeader(
            header_value=',\t ,iso-8859-5;q=0.333,',
        )
        result = value + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == value_as_header + ', ' + \
            right_operand.header_value

    def test___radd___other_type_with_valid___str__(self):
        right_operand = AcceptCharsetValidHeader(
            header_value=',\t ,iso-8859-5;q=0.333,',
        )
        class Other(object):
            def __str__(self):
                return 'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8'
        left_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == str(left_operand) + ', ' + \
            right_operand.header_value

    def test___repr__(self):
        instance = AcceptCharsetValidHeader(
            header_value=',utf-7;q=0.200,UTF-8;q=0.300',
        )
        assert repr(instance) == \
            "<AcceptCharsetValidHeader ('utf-7;q=0.2, UTF-8;q=0.3')>"

    def test___str__(self):
        header_value = (
            ', \t,iso-8859-5;q=0.000 \t, utf-8;q=1.000, UTF-7, '
            'unicode-1-1;q=0.210  ,'
        )
        instance = AcceptCharsetValidHeader(header_value=header_value)
        assert str(instance) == \
            'iso-8859-5;q=0, utf-8, UTF-7, unicode-1-1;q=0.21'

    @pytest.mark.parametrize('header_value, offers, returned', [
        ('UTF-7, unicode-1-1', ['UTF-8', 'iso-8859-5'], []),
        (
            'utf-8, unicode-1-1, iSo-8859-5',
            ['UTF-8', 'iso-8859-5'],
            [('UTF-8', 1.0), ('iso-8859-5', 1.0)],
        ),
        (
            'utF-8;q=0.2, uniCode-1-1;q=0.9, iSo-8859-5;q=0.8',
            ['iso-8859-5', 'unicode-1-1', 'utf-8'],
            [('unicode-1-1', 0.9), ('iso-8859-5', 0.8), ('utf-8', 0.2)],
        ),
        (
            'utf-8, unicode-1-1;q=0.9, iSo-8859-5;q=0.9',
            ['iso-8859-5', 'utf-8', 'unicode-1-1'],
            [('utf-8', 1.0), ('iso-8859-5', 0.9), ('unicode-1-1', 0.9)],
        ),
        ('*', ['UTF-8', 'iso-8859-5'], [('UTF-8', 1.0), ('iso-8859-5', 1.0)]),
        (
            '*;q=0.8',
            ['UTF-8', 'iso-8859-5'],
            [('UTF-8', 0.8), ('iso-8859-5', 0.8)],
        ),
        ('UTF-7, *', ['UTF-8', 'UTF-7'], [('UTF-8', 1.0), ('UTF-7', 1.0)]),
        (
            'UTF-7;q=0.5, *',
            ['UTF-7', 'UTF-8'],
            [('UTF-8', 1.0), ('UTF-7', 0.5)],
        ),
        ('UTF-8, *;q=0', ['UTF-7'], []),
        ('UTF-8, *;q=0', ['UTF-8'], [('UTF-8', 1.0)]),
        ('UTF-8;q=0, *', ['UTF-8'], []),
        ('UTF-8;q=0, *;q=0', ['UTF-8', 'UTF-7'], []),
        ('UTF-8, UTF-8;q=0', ['UTF-8'], [('UTF-8', 1.0)]),
        (
            'UTF-8, UTF-8;q=0, UTF-7',
            ['UTF-8', 'UTF-7'],
            [('UTF-8', 1.0), ('UTF-7', 1.0)]
        ),
        (
            'UTF-8;q=0.5, UTF-8;q=0.7, UTF-8;q=0.6, UTF-7',
            ['UTF-8', 'UTF-7'],
            [('UTF-7', 1.0), ('UTF-8', 0.5)],
        ),
        (
            'UTF-8;q=0.8, *;q=0.9, *;q=0',
            ['UTF-8', 'UTF-7'],
            [('UTF-7', 0.9), ('UTF-8', 0.8)]
        ),
        (
            'UTF-8;q=0.8, *;q=0, *;q=0.9',
            ['UTF-8', 'UTF-7'],
            [('UTF-8', 0.8)]
        ),
    ])
    def test_acceptable_offers(self, header_value, offers, returned):
        instance = AcceptCharsetValidHeader(header_value=header_value)
        assert instance.acceptable_offers(offers=offers) == returned

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptCharsetValidHeader('utf-8, iso-8859-5')
        assert accept.best_match(['utf-8', 'iso-8859-5']) == 'utf-8'
        assert accept.best_match(['iso-8859-5', 'utf-8']) == 'iso-8859-5'
        assert accept.best_match([('iso-8859-5', 0.5), 'utf-8']) == 'utf-8'
        assert accept.best_match([('iso-8859-5', 0.5), ('utf-8', 0.4)]) == \
            'iso-8859-5'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_with_one_lower_q(self):
        accept = AcceptCharsetValidHeader('utf-8, iso-8859-5;q=0.5')
        assert accept.best_match(['utf-8', 'iso-8859-5']) == 'utf-8'
        accept = AcceptCharsetValidHeader('utf-8;q=0.5, iso-8859-5')
        assert accept.best_match(['utf-8', 'iso-8859-5']) == 'iso-8859-5'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_with_complex_q(self):
        accept = AcceptCharsetValidHeader(
            'utf-8, iso-8859-5;q=0.55, utf-7;q=0.59'
        )
        assert accept.best_match(['utf-8', 'iso-8859-5']) == 'utf-8'
        accept = AcceptCharsetValidHeader(
            'utf-8;q=0.5, iso-8859-5;q=0.586, utf-7;q=0.596'
        )
        assert accept.best_match(['utf-8', 'utf-7']) == 'utf-7'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_mixedcase(self):
        accept = AcceptCharsetValidHeader(
            'uTf-8; q=0.2, UtF-7; Q=0.4, *; q=0.05'
        )
        assert accept.best_match(['UtF-8']) == 'UtF-8'
        assert accept.best_match(['IsO-8859-5']) == 'IsO-8859-5'
        assert accept.best_match(['iSo-8859-5', 'uTF-7', 'UtF-8']) == 'uTF-7'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test_best_match_zero_quality(self):
        assert AcceptCharsetValidHeader('utf-7, *;q=0').best_match(
            ['utf-8']
        ) is None
        assert 'char-set' not in AcceptCharsetValidHeader('*;q=0')

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        accept = AcceptCharsetValidHeader('utf-8')
        assert accept.quality('utf-8') == 1.0
        accept = AcceptCharsetValidHeader('utf-8;q=0.5')
        assert accept.quality('utf-8') == 0.5

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality_not_found(self):
        accept = AcceptCharsetValidHeader('utf-8')
        assert accept.quality('iso-8859-5') is None


class TestAcceptCharsetNoHeader(object):
    def test_parse__inherited(self):
        returned = AcceptCharsetNoHeader.parse(
            value=',iso-8859-5 ; q=0.333 , ,utf-8,unicode-1-1 ;q=0.90,',
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ('iso-8859-5', 0.333),
            ('utf-8', 1.0),
            ('unicode-1-1', 0.9),
        ]

    def test___init__(self):
        instance = AcceptCharsetNoHeader()
        assert instance.header_value is None
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptCharset)

    def test___add___None(self):
        instance = AcceptCharsetNoHeader()
        result = instance + None
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not instance

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'UTF/8',
        ['UTF/8'],
        ('UTF/8',),
        {'UTF/8': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptCharsetNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize('str_', ['', 'UTF/8'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptCharsetNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = left_operand + Other()
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            [('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'],
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            (('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'),
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            {'UTF-7': 0.5, 'unicode-1-1': 0.0, 'UTF-8': 1.0},
            'UTF-8, UTF-7;q=0.5, unicode-1-1;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptCharsetNoHeader() + value
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str__(self):
        class Other(object):
            def __str__(self):
                return 'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8'
        right_operand = Other()
        result = AcceptCharsetNoHeader() + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptCharsetValidHeader(self):
        right_operand = AcceptCharsetValidHeader(
            header_value=', ,utf-7;q=0, \tutf-8;q=1,',
        )
        result = AcceptCharsetNoHeader() + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptCharsetNoHeader(self):
        left_operand = AcceptCharsetNoHeader()
        right_operand = AcceptCharsetNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not left_operand
        assert result is not right_operand

    @pytest.mark.parametrize('header_value', ['', 'utf/8'])
    def test___add___AcceptCharsetInvalidHeader(self, header_value):
        left_operand = AcceptCharsetNoHeader()
        result = left_operand + AcceptCharsetInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not left_operand

    def test___bool__(self):
        instance = AcceptCharsetNoHeader()
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptCharsetNoHeader()
        returned = ('char-set' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptCharsetNoHeader()
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptCharsetNoHeader()
        result = None + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'UTF/8',
        ['UTF/8'],
        ('UTF/8',),
        {'UTF/8': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptCharsetNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('str_', ['', 'UTF/8'])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptCharsetNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            [('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'],
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            (('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'),
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            {'UTF-7': 0.5, 'unicode-1-1': 0.0, 'UTF-8': 1.0},
            'UTF-8, UTF-7;q=0.5, unicode-1-1;q=0',
        ),
    ])
    def test___radd___valid_value(self, value, value_as_header):
        result = value + AcceptCharsetNoHeader()
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str__(self):
        class Other(object):
            def __str__(self):
                return 'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8'
        left_operand = Other()
        result = left_operand + AcceptCharsetNoHeader()
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptCharsetNoHeader()
        assert repr(instance) == '<AcceptCharsetNoHeader>'

    def test___str__(self):
        instance = AcceptCharsetNoHeader()
        assert str(instance) == '<no header in request>'

    def test_acceptable_offers(self):
        instance = AcceptCharsetNoHeader()
        returned = instance.acceptable_offers(
            offers=['utf-8', 'utf-7', 'unicode-1-1'],
        )
        assert returned == [
            ('utf-8', 1.0), ('utf-7', 1.0), ('unicode-1-1', 1.0)
        ]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptCharsetNoHeader()
        assert accept.best_match(['utf-8', 'iso-8859-5']) == 'utf-8'
        assert accept.best_match([('utf-8', 1), ('iso-8859-5', 0.5)]) == \
            'utf-8'
        assert accept.best_match([('utf-8', 0.5), ('iso-8859-5', 1)]) == \
            'iso-8859-5'
        assert accept.best_match([('utf-8', 0.5), 'iso-8859-5']) == \
            'iso-8859-5'
        assert accept.best_match(
            [('utf-8', 0.5), 'iso-8859-5'], default_match=True
        ) == 'iso-8859-5'
        assert accept.best_match(
            [('utf-8', 0.5), 'iso-8859-5'], default_match=False
        ) == 'iso-8859-5'
        assert accept.best_match([], default_match='fallback') == 'fallback'

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptCharsetNoHeader()
        returned = instance.quality(offer='char-set')
        assert returned == 1.0


class TestAcceptCharsetInvalidHeader(object):
    def test_parse__inherited(self):
        returned = AcceptCharsetInvalidHeader.parse(
            value=',iso-8859-5 ; q=0.333 , ,utf-8,unicode-1-1 ;q=0.90,',
        )
        list_of_returned = list(returned)
        assert list_of_returned == [
            ('iso-8859-5', 0.333),
            ('utf-8', 1.0),
            ('unicode-1-1', 0.9),
        ]

    def test___init__(self):
        header_value = 'invalid header'
        instance = AcceptCharsetInvalidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptCharset)

    def test___add___None(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        result = instance + None
        assert isinstance(result, AcceptCharsetNoHeader)

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'UTF/8',
        ['UTF/8'],
        ('UTF/8',),
        {'UTF/8': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        result = AcceptCharsetInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)

    @pytest.mark.parametrize('str_', ['', 'UTF/8'])
    def test___add___other_type_with_invalid___str__(self, str_):
        class Other(object):
            def __str__(self):
                return str_
        result = AcceptCharsetInvalidHeader(header_value='') + Other()
        assert isinstance(result, AcceptCharsetNoHeader)

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            [('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'],
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            (('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'),
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            {'UTF-7': 0.5, 'unicode-1-1': 0.0, 'UTF-8': 1.0},
            'UTF-8, UTF-7;q=0.5, unicode-1-1;q=0',
        ),
    ])
    def test___add___valid_header_value(self, value, value_as_header):
        result = AcceptCharsetInvalidHeader(header_value='') + value
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_valid_header_value(self):
        class Other(object):
            def __str__(self):
                return 'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8'
        right_operand = Other()
        result = AcceptCharsetInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptCharsetValidHeader(self):
        right_operand = AcceptCharsetValidHeader(
            header_value=', ,utf-7;q=0, \tutf-8;q=1,',
        )
        result = AcceptCharsetInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptCharsetNoHeader(self):
        right_operand = AcceptCharsetNoHeader()
        result = AcceptCharsetInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptCharsetNoHeader)
        assert result is not right_operand

    def test___add___AcceptCharsetInvalidHeader(self):
        result = AcceptCharsetInvalidHeader(header_value='') + \
            AcceptCharsetInvalidHeader(header_value='utf/8')
        assert isinstance(result, AcceptCharsetNoHeader)

    def test___bool__(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        returned = ('char-set' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        result = None + AcceptCharsetInvalidHeader(header_value='')
        assert isinstance(result, AcceptCharsetNoHeader)

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'UTF/8',
        ['UTF/8'],
        ('UTF/8',),
        {'UTF/8': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        result = left_operand + AcceptCharsetInvalidHeader(header_value='')
        assert isinstance(result, AcceptCharsetNoHeader)

    @pytest.mark.parametrize('str_', ['', 'UTF/8'])
    def test___radd___other_type_with_invalid___str__(self, str_):
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + AcceptCharsetInvalidHeader(header_value='')
        assert isinstance(result, AcceptCharsetNoHeader)

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            [('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'],
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            (('UTF-7', 0.5), ('unicode-1-1', 0.0), 'UTF-8'),
            'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8',
        ),
        (
            {'UTF-7': 0.5, 'unicode-1-1': 0.0, 'UTF-8': 1.0},
            'UTF-8, UTF-7;q=0.5, unicode-1-1;q=0',
        ),
    ])
    def test___radd___valid_header_value(self, value, value_as_header):
        result = value + AcceptCharsetInvalidHeader(header_value='')
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_valid_header_value(self):
        class Other(object):
            def __str__(self):
                return 'UTF-7;q=0.5, unicode-1-1;q=0, UTF-8'
        left_operand = Other()
        result = left_operand + AcceptCharsetInvalidHeader(header_value='')
        assert isinstance(result, AcceptCharsetValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptCharsetInvalidHeader(header_value='\x00')
        assert repr(instance) == '<AcceptCharsetInvalidHeader>'

    def test___str__(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        assert str(instance) == '<invalid header value>'

    def test_acceptable_offers(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        returned = instance.acceptable_offers(
            offers=['utf-8', 'utf-7', 'unicode-1-1'],
        )
        assert returned == [
            ('utf-8', 1.0), ('utf-7', 1.0), ('unicode-1-1', 1.0)
        ]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptCharsetInvalidHeader(header_value='')
        assert accept.best_match(['utf-8', 'iso-8859-5']) == 'utf-8'
        assert accept.best_match([('utf-8', 1), ('iso-8859-5', 0.5)]) == \
            'utf-8'
        assert accept.best_match([('utf-8', 0.5), ('iso-8859-5', 1)]) == \
            'iso-8859-5'
        assert accept.best_match([('utf-8', 0.5), 'iso-8859-5']) == \
            'iso-8859-5'
        assert accept.best_match(
            [('utf-8', 0.5), 'iso-8859-5'], default_match=True
        ) == 'iso-8859-5'
        assert accept.best_match(
            [('utf-8', 0.5), 'iso-8859-5'], default_match=False
        ) == 'iso-8859-5'
        assert accept.best_match([], default_match='fallback') == 'fallback'

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptCharsetInvalidHeader(header_value='')
        returned = instance.quality(offer='char-set')
        assert returned == 1.0


class TestCreateAcceptCharsetHeader(object):
    def test_header_value_is_valid(self):
        header_value = 'iso-8859-5, unicode-1-1;q=0.8'
        returned = create_accept_charset_header(header_value=header_value)
        assert isinstance(returned, AcceptCharsetValidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_charset_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_charset_header(header_value=header_value)
        assert isinstance(returned, AcceptCharsetNoHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_charset_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    @pytest.mark.parametrize('header_value', ['', 'iso-8859-5, unicode/1'])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_charset_header(header_value=header_value)
        assert isinstance(returned, AcceptCharsetInvalidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_charset_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value


class TestAcceptCharsetProperty(object):
    def test_fget_header_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': None})
        property_ = accept_charset_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptCharsetNoHeader)

    def test_fget_header_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'UTF-8'})
        property_ = accept_charset_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptCharsetValidHeader)

    def test_fget_header_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': ''})
        property_ = accept_charset_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptCharsetInvalidHeader)

    def test_fset_value_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'UTF-8'})
        property_ = accept_charset_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_charset, AcceptCharsetNoHeader)
        assert 'HTTP_ACCEPT_CHARSET' not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'UTF-8'})
        property_ = accept_charset_property()
        property_.fset(request=request, value='')
        assert isinstance(request.accept_charset, AcceptCharsetInvalidHeader)
        assert request.environ['HTTP_ACCEPT_CHARSET'] == ''

    def test_fset_value_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'UTF-8'})
        property_ = accept_charset_property()
        property_.fset(request=request, value='UTF-7')
        assert isinstance(request.accept_charset, AcceptCharsetValidHeader)
        assert request.environ['HTTP_ACCEPT_CHARSET'] == 'UTF-7'

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'utf-8;q=0.5, iso-8859-5;q=0, utf-7',
            'utf-8;q=0.5, iso-8859-5;q=0, utf-7',
        ),
        (
            [('utf-8', 0.5), ('iso-8859-5', 0.0), 'utf-7'],
            'utf-8;q=0.5, iso-8859-5;q=0, utf-7',
        ),
        (
            (('utf-8', 0.5), ('iso-8859-5', 0.0), 'utf-7'),
            'utf-8;q=0.5, iso-8859-5;q=0, utf-7',
        ),
        (
            {'utf-8': 0.5, 'iso-8859-5': 0.0, 'utf-7': 1.0},
            'utf-7, utf-8;q=0.5, iso-8859-5;q=0',
        ),
    ])
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': ''})
        property_ = accept_charset_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_charset, AcceptCharsetValidHeader)
        assert request.environ['HTTP_ACCEPT_CHARSET'] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': ''})
        property_ = accept_charset_property()
        class Other(object):
            def __str__(self):
                return 'utf-8;q=0.5, iso-8859-5;q=0, utf-7'
        value = Other()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_charset, AcceptCharsetValidHeader)
        assert request.environ['HTTP_ACCEPT_CHARSET'] == str(value)

    def test_fset_AcceptCharsetNoHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'utf-8'})
        property_ = accept_charset_property()
        header = AcceptCharsetNoHeader()
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_charset, AcceptCharsetNoHeader)
        assert 'HTTP_ACCEPT_CHARSET' not in request.environ

    def test_fset_AcceptCharsetValidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'utf-8'})
        property_ = accept_charset_property()
        header = AcceptCharsetValidHeader('utf-7')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_charset, AcceptCharsetValidHeader)
        assert request.environ['HTTP_ACCEPT_CHARSET'] == header.header_value

    def test_fset_AcceptCharsetInvalidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'utf-8'})
        property_ = accept_charset_property()
        header = AcceptCharsetInvalidHeader('')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_charset, AcceptCharsetInvalidHeader)
        assert request.environ['HTTP_ACCEPT_CHARSET'] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_CHARSET': 'utf-8'})
        property_ = accept_charset_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_charset, AcceptCharsetNoHeader)
        assert 'HTTP_ACCEPT_CHARSET' not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank('/')
        property_ = accept_charset_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_charset, AcceptCharsetNoHeader)
        assert 'HTTP_ACCEPT_CHARSET' not in request.environ


class TestAcceptEncoding(object):
    @pytest.mark.parametrize('value', [
        '"',
        '(',
        ')',
        '/',
        ':',
        ';',
        '<',
        '=',
        '>',
        '?',
        '@',
        '[',
        '\\',
        ']',
        '{',
        '}',
        ', ',
        ', , ',
        'gzip;q=1.0, identity; q =0.5, *;q=0',
    ])
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptEncoding.parse(value=value)

    @pytest.mark.parametrize('value, expected_list', [
        (',', []),
        (', ,', []),
        ('*', [('*', 1.0)]),
        ("!#$%&'*+-.^_`|~;q=0.5", [("!#$%&'*+-.^_`|~", 0.5)]),
        ('0123456789', [('0123456789', 1.0)]),
        (
            ',,\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tCHARLIE \t,,  ,',
            [('foo', 0.345), ('bar', 0.456), ('CHARLIE', 1.0)]
        ),
        # RFC 7231, section 5.3.4
        ('compress, gzip', [('compress', 1.0), ('gzip', 1.0)]),
        ('', []),
        ('*', [('*', 1.0)]),
        ('compress;q=0.5, gzip;q=1.0', [('compress', 0.5), ('gzip', 1.0)]),
        (
            'gzip;q=1.0, identity; q=0.5, *;q=0',
            [('gzip', 1.0), ('identity', 0.5), ('*', 0.0)],
        ),
    ])
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptEncoding.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptEncodingValidHeader(object):
    def test_parse__inherited(self):
        returned = AcceptEncodingValidHeader.parse(
            value=',,\t gzip;q=1.0, identity; q=0.5, *;q=0 \t ,',
        )
        list_of_returned = list(returned)
        assert list_of_returned == \
            [('gzip', 1.0), ('identity', 0.5), ('*', 0.0)]

    @pytest.mark.parametrize('header_value', [
        ', ',
        'gzip;q=1.0, identity; q =0.5, *;q=0',
    ])
    def test___init___invalid_header(self, header_value):
        with pytest.raises(ValueError):
            AcceptEncodingValidHeader(header_value=header_value)

    def test___init___valid_header(self):
        header_value = ',,\t gzip;q=1.0, identity; q=0, *;q=0.5 \t ,'
        instance = AcceptEncodingValidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed == [
            ('gzip', 1.0), ('identity', 0.0), ('*', 0.5),
        ]
        assert instance._parsed_nonzero == [('gzip', 1.0), ('*', 0.5)]
        assert isinstance(instance, AcceptEncoding)

    def test___add___None(self):
        left_operand = AcceptEncodingValidHeader(header_value='gzip')
        result = left_operand + None
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('right_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptEncodingValidHeader(header_value='gzip')
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    def test___add___other_type_with_invalid___str__(self):
        left_operand = AcceptEncodingValidHeader(header_value='gzip')
        class Other(object):
            def __str__(self):
                return ', '
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___add___valid_empty_value(self, value):
        left_operand = AcceptEncodingValidHeader(header_value='gzip')
        result = left_operand + value
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    def test___add___other_type_with_valid___str___empty(self):
        left_operand = AcceptEncodingValidHeader(header_value='gzip')
        class Other(object):
            def __str__(self):
                return ''
        result = left_operand + Other()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('compress;q=0.5, deflate;q=0, *', 'compress;q=0.5, deflate;q=0, *'),
        (
            ['compress;q=0.5', 'deflate;q=0', '*'],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            [('compress', 0.5), ('deflate', 0.0), ('*', 1.0)],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            ('compress;q=0.5', 'deflate;q=0', '*'),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            (('compress', 0.5), ('deflate', 0.0), ('*', 1.0)),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            {'compress': 0.5, 'deflate': 0.0, '*': 1.0},
            '*, compress;q=0.5, deflate;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        header = ',\t ,gzip, identity;q=0.333,'
        result = AcceptEncodingValidHeader(header_value=header) + value
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == header + ', ' + value_as_header

    def test___add___other_type_with_valid___str___not_empty(self):
        header = ',\t ,gzip, identity;q=0.333,'
        class Other(object):
            def __str__(self):
                return 'compress;q=0.5, deflate;q=0, *'
        right_operand = Other()
        result = AcceptEncodingValidHeader(header_value=header) + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == header + ', ' + str(right_operand)

    def test___add___AcceptEncodingValidHeader_header_value_empty(self):
        left_operand = AcceptEncodingValidHeader(
            header_value=',\t ,gzip, identity;q=0.333,'
        )
        right_operand = AcceptEncodingValidHeader(header_value='')
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    def test___add___AcceptEncodingValidHeader_header_value_not_empty(self):
        left_operand = AcceptEncodingValidHeader(
            header_value=',\t ,gzip, identity;q=0.333,',
        )
        right_operand = AcceptEncodingValidHeader(
            header_value='compress;q=0.5, deflate;q=0, *',
        )
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == left_operand.header_value + ', ' + \
            right_operand.header_value

    def test___add___AcceptEncodingNoHeader(self):
        valid_header_instance = AcceptEncodingValidHeader(header_value='gzip')
        result = valid_header_instance + AcceptEncodingNoHeader()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    @pytest.mark.parametrize('header_value', [
        ', ',
        'compress;q=1.001',
    ])
    def test___add___AcceptEncodingInvalidHeader(self, header_value):
        valid_header_instance = AcceptEncodingValidHeader(header_value='gzip')
        result = valid_header_instance + AcceptEncodingInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    def test___bool__(self):
        instance = AcceptEncodingValidHeader(header_value='gzip')
        returned = bool(instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        accept = AcceptEncodingValidHeader('gzip, compress')
        assert 'gzip' in accept
        assert 'deflate' not in accept
        for mask in ['*', 'gzip', 'gZIP']:
            assert 'gzip' in AcceptEncodingValidHeader(mask)

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptEncodingValidHeader(
            header_value='gzip; q=0.5, *; q=0, deflate; q=0.8, compress',
        )
        assert list(instance) == ['compress', 'deflate', 'gzip']

    def test___radd___None(self):
        right_operand = AcceptEncodingValidHeader(header_value='gzip')
        result = None + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptEncodingValidHeader(header_value='gzip')
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___radd___other_type_with_invalid___str__(self):
        right_operand = AcceptEncodingValidHeader(header_value='gzip')
        class Other(object):
            def __str__(self):
                return ', '
        result = Other() + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___radd___valid_empty_value(self, value):
        right_operand = AcceptEncodingValidHeader(header_value='gzip')
        result = value + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___radd___other_type_with_valid___str___empty(self):
        right_operand = AcceptEncodingValidHeader(header_value='gzip')
        class Other(object):
            def __str__(self):
                return ''
        result = Other() + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('compress;q=0.5, deflate;q=0, *', 'compress;q=0.5, deflate;q=0, *'),
        (
            ['compress;q=0.5', 'deflate;q=0', '*'],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            [('compress', 0.5), ('deflate', 0.0), ('*', 1.0)],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            ('compress;q=0.5', 'deflate;q=0', '*'),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            (('compress', 0.5), ('deflate', 0.0), ('*', 1.0)),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            {'compress': 0.5, 'deflate': 0.0, '*': 1.0},
            '*, compress;q=0.5, deflate;q=0',
        ),
    ])
    def test___radd___valid_non_empty_value(self, value, value_as_header):
        header = ',\t ,gzip, identity;q=0.333,'
        result = value + AcceptEncodingValidHeader(header_value=header)
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == value_as_header + ', ' + header

    def test___radd___other_type_with_valid___str___not_empty(self):
        header = ',\t ,gzip, identity;q=0.333,'
        class Other(object):
            def __str__(self):
                return 'compress;q=0.5, deflate;q=0, *'
        left_operand = Other()
        result = left_operand + AcceptEncodingValidHeader(header_value=header)
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == str(left_operand) + ', ' + header

    @pytest.mark.parametrize('header_value, expected_returned', [
        ('', "<AcceptEncodingValidHeader ('')>"),
        (
            ",\t, a ;\t q=0.20 , b ,',",
            # single quote is valid character in token
            """<AcceptEncodingValidHeader ("a;q=0.2, b, \'")>"""
        ),
    ])
    def test___repr__(self, header_value, expected_returned):
        instance = AcceptEncodingValidHeader(header_value=header_value)
        assert repr(instance) == expected_returned

    @pytest.mark.parametrize('header_value, expected_returned', [
        ('', ''),
        (",\t, a ;\t q=0.20 , b ,',", "a;q=0.2, b, '"),
    ])
    def test___str__(self, header_value, expected_returned):
        instance = AcceptEncodingValidHeader(header_value=header_value)
        assert str(instance) == expected_returned

    @pytest.mark.parametrize('header_value, offers, expected_returned', [
        ('', [], []),
        ('gzip, compress', [], []),
        ('', ['gzip', 'deflate'], []),
        ('', ['gzip', 'identity'], [('identity', 1.0)]),
        ('compress, deflate, gzip', ['identity'], [('identity', 1.0)]),
        ('compress, identity;q=0, gzip', ['identity'], []),
        # *;q=0 does not make sense, but is valid
        ('*;q=0', ['identity'], []),
        ('*;q=0, deflate, gzip', ['identity'], []),
        ('*;q=0, deflate, identity;q=0, gzip', ['identity'], []),
        (
            '*;q=0, deflate, identity;q=0.1, gzip',
            ['identity'],
            [('identity', 0.1)],
        ),
        (
            'compress, deflate, gzip',
            ['identity', 'gzip'],
            [('identity', 1.0), ('gzip', 1.0)],
        ),
        (
            'compress, deflate, gzip',
            ['gzip', 'identity'],
            [('gzip', 1.0), ('identity', 1.0)],
        ),
        (
            'IDentity;q=0.5, deflATE;q=0, gZIP;q=0, COMPress',
            ['GZip', 'DEFlate', 'IDENTity', 'comPRESS'],
            [('comPRESS', 1.0), ('IDENTity', 0.5)],
        ),
        (
            'compress;q=0, identity, *;q=0.5, identity;q=0, *;q=0, compress',
            # does not make sense, but is valid
            ['compress', 'identity', 'deflate', 'gzip'],
            [('identity', 1.0), ('deflate', 0.5), ('gzip', 0.5)],
        ),
    ])
    def test_acceptable_offers(
        self, header_value, offers, expected_returned,
    ):
        instance = AcceptEncodingValidHeader(header_value=header_value)
        returned = instance.acceptable_offers(offers=offers)
        assert returned == expected_returned

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptEncodingValidHeader('gzip, iso-8859-5')
        assert accept.best_match(['gzip', 'iso-8859-5']) == 'gzip'
        assert accept.best_match(['iso-8859-5', 'gzip']) == 'iso-8859-5'
        assert accept.best_match([('iso-8859-5', 0.5), 'gzip']) == 'gzip'
        assert accept.best_match([('iso-8859-5', 0.5), ('gzip', 0.4)]) == \
            'iso-8859-5'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_with_one_lower_q(self):
        accept = AcceptEncodingValidHeader('gzip, compress;q=0.5')
        assert accept.best_match(['gzip', 'compress']) == 'gzip'
        accept = AcceptEncodingValidHeader('gzip;q=0.5, compress')
        assert accept.best_match(['gzip', 'compress']) == 'compress'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_with_complex_q(self):
        accept = AcceptEncodingValidHeader(
            'gzip, compress;q=0.55, deflate;q=0.59'
        )
        assert accept.best_match(['gzip', 'compress']) == 'gzip'
        accept = AcceptEncodingValidHeader(
            'gzip;q=0.5, compress;q=0.586, deflate;q=0.596'
        )
        assert accept.best_match(['gzip', 'deflate']) == 'deflate'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match_mixedcase(self):
        accept = AcceptEncodingValidHeader(
            'gZiP; q=0.2, COMPress; Q=0.4, *; q=0.05'
        )
        assert accept.best_match(['gzIP']) == 'gzIP'
        assert accept.best_match(['DeFlAte']) == 'DeFlAte'
        assert accept.best_match(['deflaTe', 'compRess', 'UtF-8']) == \
            'compRess'

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test_best_match_zero_quality(self):
        assert AcceptEncodingValidHeader('deflate, *;q=0').best_match(
            ['gzip']
        ) is None
        assert 'content-coding' not in AcceptEncodingValidHeader('*;q=0')

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        accept = AcceptEncodingValidHeader('gzip')
        assert accept.quality('gzip') == 1
        accept = AcceptEncodingValidHeader('gzip;q=0.5')
        assert accept.quality('gzip') == 0.5

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality_not_found(self):
        accept = AcceptEncodingValidHeader('gzip')
        assert accept.quality('compress') is None


class TestAcceptEncodingNoHeader(object):
    def test_parse__inherited(self):
        returned = AcceptEncodingNoHeader.parse(
            value=',,\t gzip;q=1.0, identity; q=0.5, *;q=0 \t ,',
        )
        list_of_returned = list(returned)
        assert list_of_returned == \
            [('gzip', 1.0), ('identity', 0.5), ('*', 0.0)]

    def test___init__(self):
        instance = AcceptEncodingNoHeader()
        assert instance.header_value is None
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptEncoding)

    def test___add___None(self):
        left_operand = AcceptEncodingNoHeader()
        result = left_operand + None
        assert isinstance(result, AcceptEncodingNoHeader)

    @pytest.mark.parametrize('right_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptEncodingNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    def test___add___other_type_with_invalid___str__(self):
        left_operand = AcceptEncodingNoHeader()
        class Other(object):
            def __str__(self):
                return ', '
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___add___valid_empty_value(self, value):
        left_operand = AcceptEncodingNoHeader()
        result = left_operand + value
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    def test___add___other_type_with_valid___str___empty(self):
        left_operand = AcceptEncodingNoHeader()
        class Other(object):
            def __str__(self):
                return ''
        result = left_operand + Other()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        ('compress;q=0.5, deflate;q=0, *', 'compress;q=0.5, deflate;q=0, *'),
        (
            ['compress;q=0.5', 'deflate;q=0', '*'],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            [('compress', 0.5), ('deflate', 0.0), ('*', 1.0)],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            ('compress;q=0.5', 'deflate;q=0', '*'),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            (('compress', 0.5), ('deflate', 0.0), ('*', 1.0)),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            {'compress': 0.5, 'deflate': 0.0, '*': 1.0},
            '*, compress;q=0.5, deflate;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptEncodingNoHeader() + value
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'compress;q=0.5, deflate;q=0, *'
        right_operand = Other()
        result = AcceptEncodingNoHeader() + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptEncodingValidHeader_header_value_empty(self):
        right_operand = AcceptEncodingValidHeader(header_value='')
        result = AcceptEncodingNoHeader() + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptEncodingValidHeader_header_value_not_empty(self):
        right_operand = AcceptEncodingValidHeader(
            header_value='compress;q=0.5, deflate;q=0, *',
        )
        result = AcceptEncodingNoHeader() + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value

    def test___add___AcceptEncodingNoHeader(self):
        left_operand = AcceptEncodingNoHeader()
        right_operand = AcceptEncodingNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)
        assert result is not left_operand
        assert result is not right_operand

    @pytest.mark.parametrize('header_value', [
        ', ',
        'compress;q=1.001',
    ])
    def test___add___AcceptEncodingInvalidHeader(self, header_value):
        left_operand = AcceptEncodingNoHeader()
        result = left_operand + AcceptEncodingInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptEncodingNoHeader)
        assert result is not left_operand

    def test___bool__(self):
        instance = AcceptEncodingNoHeader()
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptEncodingNoHeader()
        returned = ('content-coding' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptEncodingNoHeader()
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptEncodingNoHeader()
        result = None + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptEncodingNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)
        assert result is not right_operand

    def test___radd___other_type_with_invalid___str__(self):
        right_operand = AcceptEncodingNoHeader()
        class Other(object):
            def __str__(self):
                return ', '
        result = Other() + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___radd___valid_empty_value(self, value):
        result = value + AcceptEncodingNoHeader()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    def test___radd___other_type_with_valid___str___empty(self):
        class Other(object):
            def __str__(self):
                return ''
        result = Other() + AcceptEncodingNoHeader()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        ('compress;q=0.5, deflate;q=0, *', 'compress;q=0.5, deflate;q=0, *'),
        (
            ['compress;q=0.5', 'deflate;q=0', '*'],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            [('compress', 0.5), ('deflate', 0.0), ('*', 1.0)],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            ('compress;q=0.5', 'deflate;q=0', '*'),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            (('compress', 0.5), ('deflate', 0.0), ('*', 1.0)),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            {'compress': 0.5, 'deflate': 0.0, '*': 1.0},
            '*, compress;q=0.5, deflate;q=0',
        ),
    ])
    def test___radd___valid_non_empty_value(self, value, value_as_header):
        result = value + AcceptEncodingNoHeader()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'compress;q=0.5, deflate;q=0, *'
        left_operand = Other()
        result = left_operand + AcceptEncodingNoHeader()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptEncodingNoHeader()
        assert repr(instance) == '<AcceptEncodingNoHeader>'

    def test___str__(self):
        instance = AcceptEncodingNoHeader()
        assert str(instance) == '<no header in request>'

    def test_acceptable_offers(self):
        instance = AcceptEncodingNoHeader()
        returned = instance.acceptable_offers(offers=['a', 'b', 'c'])
        assert returned == [('a', 1.0), ('b', 1.0), ('c', 1.0)]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptEncodingNoHeader()
        assert accept.best_match(['gzip', 'compress']) == 'gzip'
        assert accept.best_match([('gzip', 1), ('compress', 0.5)]) == 'gzip'
        assert accept.best_match([('gzip', 0.5), ('compress', 1)]) == \
            'compress'
        assert accept.best_match([('gzip', 0.5), 'compress']) == 'compress'
        assert accept.best_match(
            [('gzip', 0.5), 'compress'], default_match=True
        ) == 'compress'
        assert accept.best_match(
            [('gzip', 0.5), 'compress'], default_match=False
        ) == 'compress'
        assert accept.best_match([], default_match='fallback') == 'fallback'

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptEncodingNoHeader()
        returned = instance.quality(offer='content-coding')
        assert returned == 1.0


class TestAcceptEncodingInvalidHeader(object):
    def test_parse__inherited(self):
        returned = AcceptEncodingInvalidHeader.parse(
            value=',,\t gzip;q=1.0, identity; q=0.5, *;q=0 \t ,',
        )
        list_of_returned = list(returned)
        assert list_of_returned == \
            [('gzip', 1.0), ('identity', 0.5), ('*', 0.0)]

    def test___init__(self):
        header_value = 'invalid header'
        instance = AcceptEncodingInvalidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptEncoding)

    def test___add___None(self):
        left_operand = AcceptEncodingInvalidHeader(header_value=', ')
        result = left_operand + None
        assert isinstance(result, AcceptEncodingNoHeader)

    @pytest.mark.parametrize('right_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptEncodingInvalidHeader(
            header_value='invalid header',
        )
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    def test___add___other_type_with_invalid___str__(self):
        left_operand = AcceptEncodingInvalidHeader(
            header_value='invalid header',
        )
        class Other(object):
            def __str__(self):
                return ', '
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___add___valid_empty_value(self, value):
        left_operand = AcceptEncodingInvalidHeader(header_value=', ')
        result = left_operand + value
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    def test___add___other_type_with_valid___str___empty(self):
        left_operand = AcceptEncodingInvalidHeader(header_value=', ')
        class Other(object):
            def __str__(self):
                return ''
        result = left_operand + Other()
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        ('compress;q=0.5, deflate;q=0, *', 'compress;q=0.5, deflate;q=0, *'),
        (
            ['compress;q=0.5', 'deflate;q=0', '*'],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            [('compress', 0.5), ('deflate', 0.0), ('*', 1.0)],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            ('compress;q=0.5', 'deflate;q=0', '*'),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            (('compress', 0.5), ('deflate', 0.0), ('*', 1.0)),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            {'compress': 0.5, 'deflate': 0.0, '*': 1.0},
            '*, compress;q=0.5, deflate;q=0',
        ),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptEncodingInvalidHeader(header_value=', ') + value
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return '*, compress;q=0.5, deflate;q=0'
        right_operand = Other()
        result = AcceptEncodingInvalidHeader(header_value=', ') + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptEncodingValidHeader_header_value_empty(self):
        left_operand = AcceptEncodingInvalidHeader(header_value=', ')
        right_operand = AcceptEncodingValidHeader(header_value='')
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptEncodingValidHeader_header_value_not_empty(self):
        left_operand = AcceptEncodingInvalidHeader(header_value=', ')
        right_operand = AcceptEncodingValidHeader(
            header_value='compress;q=0.5, deflate;q=0, *',
        )
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == right_operand.header_value

    def test___add___AcceptEncodingNoHeader(self):
        left_operand = AcceptEncodingInvalidHeader(header_value=', ')
        right_operand = AcceptEncodingNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('header_value', [
        ', ',
        'compress;q=1.001',
    ])
    def test___add___AcceptEncodingInvalidHeader(self, header_value):
        result = AcceptEncodingInvalidHeader(header_value='gzip;;q=1') + \
            AcceptEncodingInvalidHeader(header_value=header_value)
        assert isinstance(result, AcceptEncodingNoHeader)

    def test___bool__(self):
        instance = AcceptEncodingInvalidHeader(header_value=', ')
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptEncodingInvalidHeader(header_value=', ')
        returned = ('content-coding' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptEncodingInvalidHeader(header_value=', ')
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        right_operand = AcceptEncodingInvalidHeader(header_value=', ')
        result = None + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    @pytest.mark.parametrize('left_operand', [
        ', ',
        [', '],
        (', ',),
        {', ': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptEncodingInvalidHeader(header_value='gzip;q= 1')
        result = left_operand + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    def test___radd___other_type_with_invalid___str__(self):
        right_operand = AcceptEncodingInvalidHeader(header_value='gzip;q= 1')
        class Other(object):
            def __str__(self):
                return ', '
        result = Other() + right_operand
        assert isinstance(result, AcceptEncodingNoHeader)

    @pytest.mark.parametrize('value', [
        '',
        [],
        (),
        {},
    ])
    def test___radd___valid_empty_value(self, value):
        right_operand = AcceptEncodingInvalidHeader(header_value=', ')
        result = value + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    def test___radd___other_type_with_valid___str___empty(self):
        right_operand = AcceptEncodingInvalidHeader(header_value=', ')
        class Other(object):
            def __str__(self):
                return ''
        result = Other() + right_operand
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == ''

    @pytest.mark.parametrize('value, value_as_header', [
        ('compress;q=0.5, deflate;q=0, *', 'compress;q=0.5, deflate;q=0, *'),
        (
            ['compress;q=0.5', 'deflate;q=0', '*'],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            [('compress', 0.5), ('deflate', 0.0), ('*', 1.0)],
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            ('compress;q=0.5', 'deflate;q=0', '*'),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            (('compress', 0.5), ('deflate', 0.0), ('*', 1.0)),
            'compress;q=0.5, deflate;q=0, *',
        ),
        (
            {'compress': 0.5, 'deflate': 0.0, '*': 1.0},
            '*, compress;q=0.5, deflate;q=0',
        ),
    ])
    def test___radd___valid_non_empty_value(self, value, value_as_header):
        result = value + AcceptEncodingInvalidHeader(header_value=', ')
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str___not_empty(self):
        class Other(object):
            def __str__(self):
                return 'compress;q=0.5, deflate;q=0, *'
        left_operand = Other()
        result = left_operand + AcceptEncodingInvalidHeader(header_value=', ')
        assert isinstance(result, AcceptEncodingValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptEncodingInvalidHeader(header_value='\x00')
        assert repr(instance) == '<AcceptEncodingInvalidHeader>'

    def test___str__(self):
        instance = AcceptEncodingInvalidHeader(header_value=", ")
        assert str(instance) == '<invalid header value>'

    def test_acceptable_offers(self):
        instance = AcceptEncodingInvalidHeader(header_value=', ')
        returned = instance.acceptable_offers(offers=['a', 'b', 'c'])
        assert returned == [('a', 1.0), ('b', 1.0), ('c', 1.0)]

    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self):
        accept = AcceptEncodingInvalidHeader(header_value=', ')
        assert accept.best_match(['gzip', 'compress']) == 'gzip'
        assert accept.best_match([('gzip', 1), ('compress', 0.5)]) == 'gzip'
        assert accept.best_match([('gzip', 0.5), ('compress', 1)]) == \
            'compress'
        assert accept.best_match([('gzip', 0.5), 'compress']) == 'compress'
        assert accept.best_match(
            [('gzip', 0.5), 'compress'], default_match=True
        ) == 'compress'
        assert accept.best_match(
            [('gzip', 0.5), 'compress'], default_match=False
        ) == 'compress'
        assert accept.best_match([], default_match='fallback') == 'fallback'

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptEncodingInvalidHeader(header_value=', ')
        returned = instance.quality(offer='content-coding')
        assert returned == 1.0


class TestCreateAcceptEncodingHeader(object):
    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_encoding_header(header_value=header_value)
        assert isinstance(returned, AcceptEncodingNoHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_encoding_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    def test_header_value_is_valid(self):
        header_value = 'gzip, identity;q=0.9'
        returned = create_accept_encoding_header(header_value=header_value)
        assert isinstance(returned, AcceptEncodingValidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_encoding_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    @pytest.mark.parametrize('header_value', [', ', 'gzip;q= 1'])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_encoding_header(header_value=header_value)
        assert isinstance(returned, AcceptEncodingInvalidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_encoding_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value


class TestAcceptEncodingProperty(object):
    def test_fget_header_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': None})
        property_ = accept_encoding_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptEncodingNoHeader)

    def test_fget_header_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': 'gzip'})
        property_ = accept_encoding_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptEncodingValidHeader)

    def test_fget_header_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': ', '})
        property_ = accept_encoding_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptEncodingInvalidHeader)

    def test_fset_value_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': 'gzip'})
        property_ = accept_encoding_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_encoding, AcceptEncodingNoHeader)
        assert 'HTTP_ACCEPT_ENCODING' not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': 'gzip'})
        property_ = accept_encoding_property()
        property_.fset(request=request, value=', ')
        assert isinstance(request.accept_encoding, AcceptEncodingInvalidHeader)
        assert request.environ['HTTP_ACCEPT_ENCODING'] == ', '

    def test_fset_value_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': 'gzip'})
        property_ = accept_encoding_property()
        property_.fset(request=request, value='compress')
        assert isinstance(request.accept_encoding, AcceptEncodingValidHeader)
        assert request.environ['HTTP_ACCEPT_ENCODING'] == 'compress'

    @pytest.mark.parametrize('value, value_as_header', [
        (
            'gzip;q=0.5, compress;q=0, deflate',
            'gzip;q=0.5, compress;q=0, deflate',
        ),
        (
            [('gzip', 0.5), ('compress', 0.0), 'deflate'],
            'gzip;q=0.5, compress;q=0, deflate',
        ),
        (
            (('gzip', 0.5), ('compress', 0.0), 'deflate'),
            'gzip;q=0.5, compress;q=0, deflate',
        ),
        (
            {'gzip': 0.5, 'compress': 0.0, 'deflate': 1.0},
            'deflate, gzip;q=0.5, compress;q=0',
        ),
    ])
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': ''})
        property_ = accept_encoding_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_encoding, AcceptEncodingValidHeader)
        assert request.environ['HTTP_ACCEPT_ENCODING'] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': ''})
        property_ = accept_encoding_property()
        class Other(object):
            def __str__(self):
                return 'gzip;q=0.5, compress;q=0, deflate'
        value = Other()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_encoding, AcceptEncodingValidHeader)
        assert request.environ['HTTP_ACCEPT_ENCODING'] == str(value)

    def test_fset_AcceptEncodingNoHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': ''})
        property_ = accept_encoding_property()
        header = AcceptEncodingNoHeader()
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_encoding, AcceptEncodingNoHeader)
        assert 'HTTP_ACCEPT_ENCODING' not in request.environ

    def test_fset_AcceptEncodingValidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': ''})
        property_ = accept_encoding_property()
        header = AcceptEncodingValidHeader('gzip')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_encoding, AcceptEncodingValidHeader)
        assert request.environ['HTTP_ACCEPT_ENCODING'] == header.header_value

    def test_fset_AcceptEncodingInvalidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': 'gzip'})
        property_ = accept_encoding_property()
        header = AcceptEncodingInvalidHeader(', ')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_encoding, AcceptEncodingInvalidHeader)
        assert request.environ['HTTP_ACCEPT_ENCODING'] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_ENCODING': 'gzip'})
        property_ = accept_encoding_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_encoding, AcceptEncodingNoHeader)
        assert 'HTTP_ACCEPT_ENCODING' not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank('/')
        property_ = accept_encoding_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_encoding, AcceptEncodingNoHeader)
        assert 'HTTP_ACCEPT_ENCODING' not in request.environ


class TestAcceptLanguage(object):
    @pytest.mark.parametrize('value', [
        '',
        '*s',
        '*-a',
        'a-*',
        'a' * 9,
        'a-' + 'a' * 9,
        'a-a-' + 'a' * 9,
        '-',
        'a-',
        '-a',
        '---',
        '--a',
        '1-a',
        '1-a-a',
        'en_gb',
        'en/gb',
        'foo, bar, baz;q= 0.001',
        'foo , ,bar,charlie   ',
    ])
    def test_parse__invalid_header(self, value):
        with pytest.raises(ValueError):
            AcceptLanguage.parse(value=value)

    @pytest.mark.parametrize('value, expected_list', [
        ('*', [('*', 1.0)]),
        ('fR;q=0.5', [('fR', 0.5)]),
        ('zh-Hant;q=0.500', [('zh-Hant', 0.5)]),
        ('zh-Hans-CN;q=1', [('zh-Hans-CN', 1.0)]),
        ('de-CH-x-phonebk;q=1.0', [('de-CH-x-phonebk', 1.0)]),
        ('az-Arab-x-AZE-derbend;q=1.00', [('az-Arab-x-AZE-derbend', 1.0)]),
        ('zh-CN-a-myExt-x-private;q=1.000', [('zh-CN-a-myExt-x-private', 1.0)]),
        ('aaaaaaaa', [('aaaaaaaa', 1.0)]),
        ('aaaaaaaa-a', [('aaaaaaaa-a', 1.0)]),
        ('aaaaaaaa-aaaaaaaa', [('aaaaaaaa-aaaaaaaa', 1.0)]),
        ('a-aaaaaaaa-aaaaaaaa', [('a-aaaaaaaa-aaaaaaaa', 1.0)]),
        ('aaaaaaaa-a-aaaaaaaa', [('aaaaaaaa-a-aaaaaaaa', 1.0)]),
        (
            'zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000',
            [
                ('zh-Hant', 0.372), ('zh-CN-a-myExt-x-private', 0.977),
                ('de', 1.0), ('*', 0.0)
            ]
        ),
        (
            ',\t foo \t;\t q=0.345,, bar ; Q=0.456 \t,  ,\tcharlie \t,,  ,',
            [('foo', 0.345), ('bar', 0.456), ('charlie', 1.0)]
        ),
        # RFC 7230 Section 7
        ('foo,bar', [('foo', 1.0), ('bar', 1.0)]),
        ('foo, bar,', [('foo', 1.0), ('bar', 1.0)]),
        # RFC 7230 Errata ID: 4169
        ('foo , ,bar,charlie', [('foo', 1.0), ('bar', 1.0), ('charlie', 1.0)]),
    ])
    def test_parse__valid_header(self, value, expected_list):
        returned = AcceptLanguage.parse(value=value)
        list_of_returned = list(returned)
        assert list_of_returned == expected_list


class TestAcceptLanguageValidHeader(object):
    @pytest.mark.parametrize('header_value', [
        '',
        ', da;q=0.2, en-gb;q=0.3 ',
    ])
    def test___init___invalid_header(self, header_value):
        with pytest.raises(ValueError):
            AcceptLanguageValidHeader(header_value=header_value)

    def test___init___valid_header(self):
        header_value = \
            'zh-Hant;q=0.372,zh-CN-a-myExt-x-private;q=0.977,de,*;q=0.000'
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed == [
            ('zh-Hant', 0.372), ('zh-CN-a-myExt-x-private', 0.977),
            ('de', 1.0), ('*', 0.0)
        ]
        assert instance._parsed_nonzero == [
            ('zh-Hant', 0.372), ('zh-CN-a-myExt-x-private', 0.977),
            ('de', 1.0)
        ]
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        left_operand = AcceptLanguageValidHeader(header_value='en')
        result = left_operand + None
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
        ',',
        [','],
        (',',),
        {',': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptLanguageValidHeader(header_value='en')
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb', ','])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptLanguageValidHeader(header_value='en')
        class Other(object):
            def __str__(self):
                return str_
        right_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == left_operand.header_value
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___add___valid_value(self, value, value_as_header):
        header = ',\t ,de, zh-Hans;q=0.333,'
        result = AcceptLanguageValidHeader(header_value=header) + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header + ', ' + value_as_header

    def test___add___other_type_with_valid___str__(self):
        header = ',\t ,de, zh-Hans;q=0.333,'
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        right_operand = Other()
        result = AcceptLanguageValidHeader(header_value=header) + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header + ', ' + str(right_operand)

    def test___add___AcceptLanguageValidHeader(self):
        header1 = ',\t ,de, zh-Hans;q=0.333,'
        header2 = ', ,fr;q=0, \tes;q=1,'
        result = AcceptLanguageValidHeader(header_value=header1) + \
            AcceptLanguageValidHeader(header_value=header2)
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == header1 + ', ' + header2

    def test___add___AcceptLanguageNoHeader(self):
        valid_header_instance = AcceptLanguageValidHeader(header_value='es')
        result = valid_header_instance + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    @pytest.mark.parametrize('header_value', ['', 'en_gb', ','])
    def test___add___AcceptLanguageInvalidHeader(self, header_value):
        valid_header_instance = AcceptLanguageValidHeader(
            header_value='header',
        )
        result = valid_header_instance + AcceptLanguageInvalidHeader(
            header_value=header_value,
        )
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == valid_header_instance.header_value
        assert result is not valid_header_instance

    def test___bool__(self):
        instance = AcceptLanguageValidHeader(header_value='valid-header')
        returned = bool(instance)
        assert returned is True

    @pytest.mark.parametrize('header_value, offer', [
        ('*', 'da'),
        ('da', 'DA'),
        ('en', 'en-gb'),
        ('en-gb', 'en-gb'),
        ('en-gb', 'en'),
        ('en-gb', 'en_GB'),
    ])
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains___in(self, header_value, offer):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert offer in instance

    @pytest.mark.parametrize('header_value, offer', [
        ('en-gb', 'en-us'),
        ('en-gb', 'fr-fr'),
        ('en-gb', 'fr'),
        ('en', 'fr-fr'),
    ])
    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains___not_in(self, header_value, offer):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert offer not in instance

    @pytest.mark.parametrize('header_value, expected_list', [
        ('fr;q=0, jp;q=0', []),
        ('en-gb, da', ['en-gb', 'da']),
        ('en-gb;q=0.5, da;q=0.5', ['en-gb', 'da']),
        (
            'de;q=0.8, de-DE-1996;q=0.5, de-Deva;q=0, de-Latn-DE',
            ['de-Latn-DE', 'de', 'de-DE-1996']
        ),
        # __iter__ is currently a simple filter for the ranges in the header
        # with non-0 qvalues, and does not attempt to account for the special
        # meanings of q=0 and *:
        ('en-gb;q=0, *', ['*']),
        ('de, de;q=0', ['de']),
    ])
    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self, header_value, expected_list):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert list(instance) == expected_list

    def test___radd___None(self):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        result = None + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
        ',',
        [','],
        (',',),
        {',': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb', ','])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___radd___valid_value(self, value, value_as_header):
        right_operand = AcceptLanguageValidHeader(
            header_value=',\t ,de, zh-Hans;q=0.333,',
        )
        result = value + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header + ', ' + \
            right_operand.header_value

    def test___radd___other_type_with_valid___str__(self):
        right_operand = AcceptLanguageValidHeader(
            header_value=',\t ,de, zh-Hans;q=0.333,',
        )
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        left_operand = Other()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(left_operand) + ', ' + \
            right_operand.header_value

    def test___repr__(self):
        instance = AcceptLanguageValidHeader(
            header_value=',da;q=0.200,en-gb;q=0.300',
        )
        assert repr(instance) == \
            "<AcceptLanguageValidHeader ('da;q=0.2, en-gb;q=0.3')>"

    def test___str__(self):
        header_value = \
            ', \t,de;q=0.000 \t, es;q=1.000, zh, jp;q=0.210  ,'
        instance = AcceptLanguageValidHeader(header_value=header_value)
        assert str(instance) == 'de;q=0, es, zh, jp;q=0.21'

    @pytest.mark.parametrize(
        'header_value, language_tags, expected_returned',
        [
            # Example from RFC 4647, Section 3.4
            (
                'de-de',
                ['de', 'de-DE-1996', 'de-Deva', 'de-Latn-DE'],
                [('de-DE-1996', 1.0)]
            ),
            # Empty `language_tags`
            (
                'a',
                [],
                []
            ),
            # No matches
            (
                'a, b',
                ['c', 'd'],
                []
            ),
            # Several ranges and tags, no matches
            (
                'a-b;q=0.9, c-d;q=0.5, e-f',
                ('a', 'b', 'c', 'd', 'e', 'f'),
                []
            ),
            # Case-insensitive match
            (
                'foO, BaR',
                ['foo', 'bar'],
                [('foo', 1.0), ('bar', 1.0)]
            ),
            # If a tag matches a non-'*' range with q=0, tag is filtered out
            (
                'b-c, a, b;q=0, d;q=0',
                ['b-c', 'a', 'b-c-d', 'd-e-f'],
                [('a', 1.0)]
            ),
            # Match if a range exactly equals a tag
            (
                'd-e-f',
                ['a-b-c', 'd-e-f'],
                [('d-e-f', 1.0)]
            ),
            # Match if a range exactly equals a prefix of the tag such that the
            # first character following the prefix is '-'
            (
                'a-b-c-d, a-b-c-d-e, a-b-c-d-f-g-h',
                ['a-b-c-d-f-g'],
                [('a-b-c-d-f-g', 1.0)]
            ),
            # '*', when it is the only range in the header, matches everything
            (
                '*',
                ['a', 'b'],
                [('a', 1.0), ('b', 1.0)]
            ),
            # '*' range matches only tags not matched by any other range
            (
                '*;q=0.2, a;q=0.5, b',
                ['a-a', 'b-a', 'c-a', 'd-a'],
                [('b-a', 1.0), ('a-a', 0.5), ('c-a', 0.2), ('d-a', 0.2)]
            ),
            # '*' range without a qvalue gives a matched qvalue of 1.0
            (
                'a;q=0.5, b, *',
                ['a-a', 'b-a', 'c-a', 'd-a'],
                [('b-a', 1.0), ('c-a', 1.0), ('d-a', 1.0), ('a-a', 0.5)]
            ),
            # The qvalue for the '*' range works the same way as qvalues for
            # non-'*' ranges.
            (
                'a;q=0.5, *;q=0.9',
                # (meaning: prefer anything other than 'a', with 'a' as a
                # fallback)
                ['a', 'b'],
                [('b', 0.9), ('a', 0.5)]
            ),
            # More than one range matching the same tag: range with the highest
            # qvalue is matched
            (
                'a-b-c;q=0.7, a;q=0.9, a-b;q=0.8',
                ['a-b-c'],
                [('a-b-c', 0.9)]
            ),
            # More than one range with the same qvalue matching the same tag:
            # the range in an earlier position in the header is matched
            (
                'a-b-c;q=0.7, a;q=0.9, b;q=0.9, a-b;q=0.9',
                ['a-b-c', 'b'],
                [('a-b-c', 0.9), ('b', 0.9)]
            ),
            # The returned list of tuples is sorted in descending order of qvalue
            (
                'a;q=0.7, b;q=0.3, c, d;q=0.5',
                ['d', 'c', 'b', 'a'],
                [('c', 1.0), ('a', 0.7), ('d', 0.5), ('b', 0.3)]
            ),
            # When qvalues are the same, the tag whose matched range appears
            # earlier in the header comes first
            (
                'a, c, b',
                ['b', 'a', 'c'],
                [('a', 1.0), ('c', 1.0), ('b', 1.0)]
            ),
            # When many tags match the same range (so same qvalue and same
            # matched range position in header), they are returned in order of
            # their position in the `language_tags` argument
            (
                'a',
                ['a-b', 'a', 'a-b-c'],
                [('a-b', 1.0), ('a', 1.0), ('a-b-c', 1.0)]
            ),
            # When a non-'*' range appears in the header more than once, we use
            # the first one for matching and ignore the others
            (
                'a;q=0.5, c;q=0.6, b;q=0.7, c;q=0.9',
                ['a', 'b', 'c'],
                [('b', 0.7), ('c', 0.6), ('a', 0.5)]
            ),
            (
                'a, b, c;q=0.5, c;q=0',
                ['a-a', 'b-a', 'c-a'],
                [('a-a', 1.0), ('b-a', 1.0), ('c-a', 0.5)]
            ),
            (
                'a;q=0.5, c;q=0.9, b;q=0.9, c;q=0.9',
                ['a', 'b', 'c'],
                [('c', 0.9), ('b', 0.9), ('a', 0.5)]
            ),
            # When the '*' range appears in the header more than once, we use
            # the first one for matching and ignore the others
            (
                'a;q=0.5, *;q=0.6, b;q=0.7, *;q=0.9',
                ['a', 'b', 'c'],
                [('b', 0.7), ('c', 0.6), ('a', 0.5)]
            ),
            (
                'a, b, *;q=0.5, *;q=0',
                ['a-a', 'b-a', 'c-a'],
                [('a-a', 1.0), ('b-a', 1.0), ('c-a', 0.5)]
            ),
            (
                'a;q=0.5, *;q=0.9, b;q=0.9, *;q=0.9',
                ['a', 'b', 'c'],
                [('c', 0.9), ('b', 0.9), ('a', 0.5)]
            ),
            # Both '*' and non-'*' ranges appearing more than once
            (
                'a-b;q=0.5, c-d, *, a-b, c-d;q=0.3, *;q=0',
                ['a-b-c', 'c-d-e', 'e-f-g'],
                [('c-d-e', 1.0), ('e-f-g', 1.0), ('a-b-c', 0.5)]
            ),
        ]
    )
    def test_basic_filtering(
            self, header_value, language_tags, expected_returned,
        ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.basic_filtering(language_tags=language_tags)
        assert returned == expected_returned

    @pytest.mark.parametrize(
        'header_value, offers, default_match, expected_returned', [
            ('bar, *;q=0', ['foo'], None, None),
            ('en-gb, sr-Cyrl', ['sr-Cyrl', 'en-gb'], None, 'sr-Cyrl'),
            ('en-gb, sr-Cyrl', ['en-gb', 'sr-Cyrl'], None, 'en-gb'),
            ('en-gb, sr-Cyrl', [('sr-Cyrl', 0.5), 'en-gb'], None, 'en-gb'),
            (
                'en-gb, sr-Cyrl', [('sr-Cyrl', 0.5), ('en-gb', 0.4)], None,
                'sr-Cyrl',
            ),
            ('en-gb, sr-Cyrl;q=0.5', ['en-gb', 'sr-Cyrl'], None, 'en-gb'),
            ('en-gb;q=0.5, sr-Cyrl', ['en-gb', 'sr-Cyrl'], None, 'sr-Cyrl'),
            (
                'en-gb, sr-Cyrl;q=0.55, es;q=0.59', ['en-gb', 'sr-Cyrl'], None,
                'en-gb',
            ),
            (
                'en-gb;q=0.5, sr-Cyrl;q=0.586, es-419;q=0.597',
                ['en-gb', 'es-419'], None, 'es-419',
            ),
        ]
    )
    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(
        self, header_value, offers, default_match, expected_returned,
    ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.best_match(
            offers=offers, default_match=default_match,
        )
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageValidHeader(header_value='valid-header')
        with pytest.raises(TypeError):
            instance.lookup(
                language_tags=['tag'],
                default_range='language-range',
                default_tag=None,
                default=None,
            )

    def test_lookup_default_range_cannot_be_asterisk(self):
        instance = AcceptLanguageValidHeader(header_value='valid-header')
        with pytest.raises(ValueError):
            instance.lookup(
                language_tags=['tag'],
                default_range='*',
                default_tag='default-tag',
                default=None,
            )

    @pytest.mark.parametrize(
        (
            'header_value, language_tags, default_range, default_tag, default'
            ', expected'
        ),
        [
            # Each language range in the header is considered in turn, in
            # descending order of qvalue
            (
                'aA;q=0.3, Bb, cC;q=0.7',
                ['Aa', 'bB', 'Cc'],
                None, 'default-tag', None,
                'bB',
            ),
            # For ranges with the same qvalue, position in header is the
            # tiebreaker.
            (
                'bB-Cc;q=0.8, aA;q=0.9, Bb;q=0.9',
                ['bb', 'aa'],
                None, 'default-tag', None,
                'aa',
            ),
            # Each language range represents the most specific tag that is an
            # acceptable match. Examples from RFC 4647, section 3.4, first
            # paragraph:
            (
                'de-ch',
                ['de-CH-1996', 'de-CH', 'de'],
                None, 'default-tag', None,
                'de-CH',
            ),
            (
                'de-ch',
                ['de-CH-1996', 'de'],
                None, 'default-tag', None,
                'de',
            ),
            # The language range is progressively truncated from the end until
            # a matching language tag is located. From the example of a Lookup
            # Fallback Pattern in RFC 4647, section 3.4:
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN-x-private1-private2',
                    'zh-Hant-CN-x-private1',
                    'zh-Hant-CN-x',
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN-x-private1-private2',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN-x-private1',
                    'zh-Hant-CN-x',
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN-x-private1',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN-x',
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant-CN',
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant-CN',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                [
                    'zh-Hant',
                    'zh',
                ],
                None, 'default-tag', None,
                'zh-Hant',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                ['zh'],
                None, 'default-tag', None,
                'zh',
            ),
            (
                'zh-Hant-CN-x-private1-private2',
                ['some-other-tag-1', 'some-other-tag-2'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # Further tests to check that single-letter or -digit subtags are
            # removed at the same time as their closest trailing subtag:
            (
                'AA-T-subtag',
                ['Aa-t', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            (
                'AA-1-subtag',
                ['aa-1', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            (
                'Aa-P-subtag-8-subtag',
                ['Aa-p-subtag-8', 'Aa-p', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            (
                'aA-3-subTag-C-subtag',
                ['aA-3-subtag-c', 'aA-3', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            # Test that single-letter or -digit subtag in first position works
            # as expected
            (
                'T-subtag',
                ['t-SubTag', 'another'],
                None, 'default-tag', None,
                't-SubTag',
            ),
            (
                'T-subtag',
                ['another'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # If the language range "*" is followed by other language ranges,
            # it is skipped.
            (
                '*, Aa-aA-AA',
                ['bb', 'aA'],
                None, 'default-tag', None,
                'aA',
            ),
            # If the language range "*" is the only one in the header, lookup
            # proceeds to the default arguments.
            (
                '*',
                ['bb', 'aa'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # If no other language range follows the "*" in the header, lookup
            # proceeds to the default arguments.
            (
                'dd, cc, *',
                ['bb', 'aa'],
                None, 'default-tag', None,
                'default-tag',
            ),
            # If a non-'*' range has q=0, any tag that matches the range
            # exactly (without subtag truncation) is not acceptable.
            (
                'aa, bB-Cc-DD;q=0, bB-Cc, cc',
                ['bb', 'bb-Cc-DD', 'bb-cC-dd', 'Bb-cc', 'bb-cC-dd'],
                None, 'default-tag', None,
                'Bb-cc',
            ),
            # ;q=0 and ;q={not 0} both in header: q=0 takes precedence and
            # makes the exact match not acceptable, but the q={not 0} means
            # that tags can still match after subtag truncation.
            (
                'aa, bB-Cc-DD;q=0.9, cc, Bb-cC-dD;q=0',
                ['bb', 'Bb-Cc', 'Bb-cC-dD'],
                None, 'default-tag', None,
                'Bb-Cc',
            ),
            # If none of the ranges in the header match any of the language
            # tags, and the `default_range` argument is not None and does not
            # match any q=0 range in the header, we search through it by
            # progressively truncating from the end, as we do with the ranges
            # in the header. Example from RFC 4647, section 3.4.1:
            (
                'fr-FR, zh-Hant',
                [
                    'fr-FR',
                    'fr',
                    'zh-Hant',
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'fr-FR',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'fr',
                    'zh-Hant',
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'fr',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'zh-Hant',
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'zh-Hant',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'zh',
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'zh',
            ),
            (
                'fr-FR, zh-Hant',
                [
                    'ja-JP',
                    'ja',
                ],
                'ja-JP', 'default-tag', None,
                'ja-JP',
            ),
            (
                'fr-FR, zh-Hant',
                ['ja'],
                'ja-JP', 'default-tag', None,
                'ja',
            ),
            (
                'fr-FR, zh-Hant',
                ['some-other-tag-1', 'some-other-tag-2'],
                'ja-JP', 'default-tag', None,
                'default-tag',
            ),
            # If none of the ranges in the header match the language tags, the
            # `default_range` argument is not None, and there is a '*;q=0'
            # range in the header, then the `default_range` and its substrings
            # from subtag truncation are not acceptable.
            (
                'aa-bb, cc-dd, *;q=0',
                ['ee-ff', 'ee'],
                'ee-ff', None, 'default',
                'default',
            ),
            # If none of the ranges in the header match the language tags, the
            # `default_range` argument is not None, and the argument exactly
            # matches a non-'*' range in the header with q=0 (without fallback
            # subtag truncation), then the `default_range` itself is not
            # acceptable...
            (
                'aa-bb, cc-dd, eE-Ff;q=0',
                ['Ee-fF'],
                'EE-FF', 'default-tag', None,
                'default-tag',
            ),
            # ...but it should still be searched with subtag truncation,
            # because its substrings other than itself are still acceptable:
            (
                'aa-bb, cc-dd, eE-Ff-Gg;q=0',
                ['Ee', 'Ee-fF-gG', 'Ee-fF'],
                'EE-FF-GG', 'default-tag', None,
                'Ee-fF',
            ),
            (
                'aa-bb, cc-dd, eE-Ff-Gg;q=0',
                ['Ee-fF-gG', 'Ee'],
                'EE-FF-GG', 'default-tag', None,
                'Ee',
            ),
            # If `default_range` only has one subtag, then no subtag truncation
            # is possible, and we proceed to `default-tag`:
            (
                'aa-bb, cc-dd, eE;q=0',
                ['Ee'],
                'EE', 'default-tag', None,
                'default-tag',
            ),
            # If the `default_range` argument would only match a non-'*' range
            # in the header with q=0 exactly if the `default_range` had subtags
            # from the end truncated, then it is acceptable, and we attempt to
            # match it with the language tags using subtag truncation. However,
            # the tag equivalent of the range with q=0 would be considered not
            # acceptable and ruled out, if we reach it during the subtag
            # truncation search.
            (
                'aa-bb, cc-dd, eE-Ff;q=0',
                ['Ee-fF', 'Ee-fF-33', 'ee'],
                'EE-FF-33', 'default-tag', None,
                'Ee-fF-33',
            ),
            (
                'aa-bb, cc-dd, eE-Ff;q=0',
                ['Ee-fF', 'eE'],
                'EE-FF-33', 'default-tag', None,
                'eE',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, and the `default_tag`
            # argument is not None and does not match any range in the header
            # with q=0, then the `default_tag` argument is returned.
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                None, 'default-tag', None,
                'default-tag',
            ),
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                'gg-hh', 'default-tag', None,
                'default-tag',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, the `default_tag` argument is
            # not None, and there is a '*' range in the header with q=0, then
            # the `default_tag` argument is not acceptable.
            (
                'aa-bb, cc-dd, *;q=0',
                ['ee-ff', 'ee'],
                'gg-hh', 'ii-jj', 'default',
                'default',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, the `default_tag` argument is
            # not None and matches a non-'*' range in the header with q=0
            # exactly, then the `default_tag` argument is not acceptable.
            (
                'aa-bb, cc-dd, iI-jJ;q=0',
                ['ee-ff', 'ee'],
                'gg-hh', 'Ii-Jj', 'default',
                'default',
            ),
            # If none of the ranges in the header match, the `default_range`
            # argument is None or does not match, and the `default_tag`
            # argument is None, then we proceed to the `default` argument.
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                None, None, 'default',
                'default',
            ),
            (
                'aa-bb, cc-dd',
                ['ee-ff', 'ee'],
                'gg-hh', None, 'default',
                'default',
            ),
            # If we fall back to the `default` argument, and it is not a
            # callable, the argument itself is returned.
            (
                'aa',
                ['bb'],
                None, None, 0,
                0,
            ),
            (
                'Aa, cC;q=0',
                ['bb'],
                'aA-Cc', 'Cc', ['non-callable object'],
                ['non-callable object'],
            ),
            # If we fall back to the `default` argument, and it is a callable,
            # it is called, and the callable's return value is returned by the
            # method.
            (
                'aa',
                ['bb'],
                None, None, lambda: 'callable called',
                'callable called',
            ),
            (
                'Aa, cc;q=0',
                ['bb'],
                'aA-cC', 'cc', lambda: 'callable called',
                'callable called',
            ),
            # Even if the 'default' argument is a str that matches a q=0 range
            # in the header, it is still returned.
            (
                'aa, *;q=0',
                ['bb'],
                None, None, 'cc',
                'cc',
            ),
            (
                'aa, cc;q=0',
                ['bb'],
                None, None, 'cc',
                'cc',
            ),
            # If the `default_tag` argument is not acceptable because of a q=0
            # range in the header, and the `default` argument is None, then
            # None is returned.
            (
                'aa, Bb;q=0',
                ['cc'],
                None, 'bB', None,
                None,
            ),
            (
                'aa, *;q=0',
                ['cc'],
                None, 'bb', None,
                None,
            ),
            # Test that method works with empty `language_tags`:
            (
                'range',
                [],
                None, 'default-tag', None,
                'default-tag',
            ),
            # Test that method works with empty `default_range`:
            (
                'range',
                [],
                '', 'default-tag', None,
                'default-tag',
            ),
            (
                'range',
                ['tag'],
                '', 'default-tag', None,
                'default-tag',
            ),
            # Test that method works with empty `default_tag`:
            (
                'range',
                [],
                '', '', None,
                '',
            ),
            (
                'range',
                ['tag'],
                'default-range', '', None,
                '',
            ),
        ]
    )
    def test_lookup(
            self, header_value, language_tags, default_range, default_tag,
            default, expected,
        ):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.lookup(
            language_tags=language_tags,
            default_range=default_range,
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    @pytest.mark.parametrize('header_value, offer, expected_returned', [
        ('en-gb', 'en-gb', 1),
        ('en-gb;q=0.5', 'en-gb', 0.5),
        ('en-gb', 'sr-Cyrl', None),
    ])
    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self, header_value, offer, expected_returned):
        instance = AcceptLanguageValidHeader(header_value=header_value)
        returned = instance.quality(offer=offer)
        assert returned == expected_returned


class TestAcceptLanguageNoHeader(object):
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

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        left_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb'])
    def test___add___other_type_with_invalid___str__(self, str_,):
        left_operand = AcceptLanguageNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = left_operand + Other()
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not left_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___add___valid_value(self, value, value_as_header):
        result = AcceptLanguageNoHeader() + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header

    def test___add___other_type_with_valid___str__(self):
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        right_operand = Other()
        result = AcceptLanguageNoHeader() + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(right_operand)

    def test___add___AcceptLanguageValidHeader(self):
        right_operand = AcceptLanguageValidHeader(
            header_value=', ,fr;q=0, \tes;q=1,',
        )
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

    @pytest.mark.parametrize('invalid_header_value', ['', 'en_gb'])
    def test___add___AcceptLanguageInvalidHeader(self, invalid_header_value):
        left_operand = AcceptLanguageNoHeader()
        result = left_operand + AcceptLanguageInvalidHeader(
            header_value=invalid_header_value,
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
        returned = ('any-tag' in instance)
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

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        right_operand = AcceptLanguageNoHeader()
        result = left_operand + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('str_', ['', 'en_gb', ','])
    def test___radd___other_type_with_invalid___str__(self, str_,):
        right_operand = AcceptLanguageNoHeader()
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test___radd___valid_value(self, value, value_as_header):
        result = value + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == value_as_header

    def test___radd___other_type_with_valid___str__(self):
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        left_operand = Other()
        result = left_operand + AcceptLanguageNoHeader()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == str(left_operand)

    def test___repr__(self):
        instance = AcceptLanguageNoHeader()
        assert repr(instance) == '<AcceptLanguageNoHeader>'

    def test___str__(self):
        instance = AcceptLanguageNoHeader()
        assert str(instance) == '<no header in request>'

    def test_basic_filtering(self):
        instance = AcceptLanguageNoHeader()
        returned = instance.basic_filtering(language_tags=['tag1', 'tag2'])
        assert returned == []

    @pytest.mark.parametrize('offers, default_match, expected_returned', [
        (['foo', 'bar'], None, 'foo'),
        ([('foo', 1), ('bar', 0.5)], None, 'foo'),
        ([('foo', 0.5), ('bar', 1)], None, 'bar'),
        ([('foo', 0.5), 'bar'], None, 'bar'),
        ([('foo', 0.5), 'bar'], object(), 'bar'),
        ([], 'fallback', 'fallback'),
    ])
    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self, offers, default_match, expected_returned):
        instance = AcceptLanguageNoHeader()
        returned = instance.best_match(
            offers=offers, default_match=default_match,
        )
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageNoHeader()
        with pytest.raises(TypeError):
            instance.lookup(default_tag=None, default=None)

    @pytest.mark.parametrize('default_tag, default, expected', [
        # If `default_tag` is not None, it is returned.
        ('default-tag', 'default', 'default-tag'),
        # If `default_tag` is None, we proceed to the `default` argument. If
        # `default` is not a callable, the argument itself is returned.
        (None, 0, 0),
        # If `default` is a callable, it is called, and the callable's return
        # value is returned by the method.
        (None, lambda: 'callable called', 'callable called'),
    ])
    def test_lookup(self, default_tag, default, expected):
        instance = AcceptLanguageNoHeader()
        returned = instance.lookup(
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptLanguageNoHeader()
        returned = instance.quality(offer='any-tag')
        assert returned == 1.0


class TestAcceptLanguageInvalidHeader(object):
    def test___init__(self):
        header_value = 'invalid header'
        instance = AcceptLanguageInvalidHeader(header_value=header_value)
        assert instance.header_value == header_value
        assert instance.parsed is None
        assert instance._parsed_nonzero is None
        assert isinstance(instance, AcceptLanguage)

    def test___add___None(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        result = instance + None
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('right_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___add___invalid_value(self, right_operand):
        result = AcceptLanguageInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('str_', ['', 'en_gb'])
    def test___add___other_type_with_invalid___str__(self, str_):
        class Other(object):
            def __str__(self):
                return str_
        result = AcceptLanguageInvalidHeader(header_value='') + Other()
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('value', [
        'en',
        ['en'],
        ('en',),
        {'en': 1.0},
    ])
    def test___add___valid_header_value(self, value):
        result = AcceptLanguageInvalidHeader(header_value='') + value
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___add___other_type_valid_header_value(self):
        class Other(object):
            def __str__(self):
                return 'en'
        result = AcceptLanguageInvalidHeader(header_value='') + Other()
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___add___AcceptLanguageValidHeader(self):
        right_operand = AcceptLanguageValidHeader(header_value='en')
        result = AcceptLanguageInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == right_operand.header_value
        assert result is not right_operand

    def test___add___AcceptLanguageNoHeader(self):
        right_operand = AcceptLanguageNoHeader()
        result = AcceptLanguageInvalidHeader(header_value='') + right_operand
        assert isinstance(result, AcceptLanguageNoHeader)
        assert result is not right_operand

    def test___add___AcceptLanguageInvalidHeader(self):
        result = AcceptLanguageInvalidHeader(header_value='') + \
            AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageNoHeader)

    def test___bool__(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = bool(instance)
        assert returned is False

    @pytest.mark.filterwarnings(IGNORE_CONTAINS)
    def test___contains__(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = ('any-tag' in instance)
        assert returned is True

    @pytest.mark.filterwarnings(IGNORE_ITER)
    def test___iter__(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = list(instance)
        assert returned == []

    def test___radd___None(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        result = None + instance
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('left_operand', [
        '',
        [],
        (),
        {},
        'en_gb',
        ['en_gb'],
        ('en_gb',),
        {'en_gb': 1.0},
    ])
    def test___radd___invalid_value(self, left_operand):
        result = left_operand + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('str_', ['', 'en_gb'])
    def test___radd___other_type_with_invalid___str__(self, str_):
        class Other(object):
            def __str__(self):
                return str_
        result = Other() + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageNoHeader)

    @pytest.mark.parametrize('value', [
        'en',
        ['en'],
        ('en',),
        {'en': 1.0},
    ])
    def test___radd___valid_header_value(self, value):
        result = value + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___radd___other_type_valid_header_value(self):
        class Other(object):
            def __str__(self):
                return 'en'
        result = Other() + AcceptLanguageInvalidHeader(header_value='')
        assert isinstance(result, AcceptLanguageValidHeader)
        assert result.header_value == 'en'

    def test___repr__(self):
        instance = AcceptLanguageInvalidHeader(header_value='\x00')
        assert repr(instance) == '<AcceptLanguageInvalidHeader>'

    def test___str__(self):
        instance = AcceptLanguageInvalidHeader(header_value="invalid header")
        assert str(instance) == '<invalid header value>'

    def test_basic_filtering(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.basic_filtering(language_tags=['tag1', 'tag2'])
        assert returned == []

    @pytest.mark.parametrize('offers, default_match, expected_returned', [
        (['foo', 'bar'], None, 'foo'),
        ([('foo', 1), ('bar', 0.5)], None, 'foo'),
        ([('foo', 0.5), ('bar', 1)], None, 'bar'),
        ([('foo', 0.5), 'bar'], None, 'bar'),
        ([('foo', 0.5), 'bar'], object(), 'bar'),
        ([], 'fallback', 'fallback'),
    ])
    @pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
    def test_best_match(self, offers, default_match, expected_returned):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.best_match(
            offers=offers, default_match=default_match,
        )
        assert returned == expected_returned

    def test_lookup_default_tag_and_default_cannot_both_be_None(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        with pytest.raises(TypeError):
            instance.lookup(default_tag=None, default=None)

    @pytest.mark.parametrize('default_tag, default, expected', [
        # If `default_tag` is not None, it is returned.
        ('default-tag', 'default', 'default-tag'),
        # If `default_tag` is None, we proceed to the `default` argument. If
        # `default` is not a callable, the argument itself is returned.
        (None, 0, 0),
        # If `default` is a callable, it is called, and the callable's return
        # value is returned by the method.
        (None, lambda: 'callable called', 'callable called'),
    ])
    def test_lookup(self, default_tag, default, expected):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.lookup(
            default_tag=default_tag,
            default=default,
        )
        assert returned == expected

    @pytest.mark.filterwarnings(IGNORE_QUALITY)
    def test_quality(self):
        instance = AcceptLanguageInvalidHeader(header_value='')
        returned = instance.quality(offer='any-tag')
        assert returned == 1.0


class TestCreateAcceptLanguageHeader(object):
    def test_header_value_is_None(self):
        header_value = None
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageNoHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_language_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    def test_header_value_is_valid(self):
        header_value = 'es, ja'
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageValidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_language_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value

    @pytest.mark.parametrize('header_value', ['', 'en_gb'])
    def test_header_value_is_invalid(self, header_value):
        returned = create_accept_language_header(header_value=header_value)
        assert isinstance(returned, AcceptLanguageInvalidHeader)
        assert returned.header_value == header_value
        returned2 = create_accept_language_header(returned)
        assert returned2 is not returned
        assert returned2._header_value == returned._header_value


class TestAcceptLanguageProperty(object):
    def test_fget_header_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': None})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageNoHeader)

    def test_fget_header_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageValidHeader)

    def test_fget_header_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'en_gb'})
        property_ = accept_language_property()
        returned = property_.fget(request=request)
        assert isinstance(returned, AcceptLanguageInvalidHeader)

    def test_fset_value_is_None(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fset(request=request, value=None)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ

    def test_fset_value_is_invalid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fset(request=request, value='en_GB')
        assert isinstance(request.accept_language, AcceptLanguageInvalidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == 'en_GB'

    def test_fset_value_is_valid(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fset(request=request, value='en-GB')
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == 'en-GB'

    @pytest.mark.parametrize('value, value_as_header', [
        ('en-gb;q=0.5, fr;q=0, es', 'en-gb;q=0.5, fr;q=0, es'),
        ([('en-gb', 0.5), ('fr', 0.0), 'es'], 'en-gb;q=0.5, fr;q=0, es'),
        ((('en-gb', 0.5), ('fr', 0.0), 'es'), 'en-gb;q=0.5, fr;q=0, es'),
        ({'en-gb': 0.5, 'fr': 0.0, 'es': 1.0}, 'es, en-gb;q=0.5, fr;q=0'),
    ])
    def test_fset_value_types(self, value, value_as_header):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == value_as_header

    def test_fset_other_type_with_valid___str__(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        class Other(object):
            def __str__(self):
                return 'en-gb;q=0.5, fr;q=0, es'
        value = Other()
        property_.fset(request=request, value=value)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == str(value)

    def test_fset_AcceptLanguageNoHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'en'})
        property_ = accept_language_property()
        header = AcceptLanguageNoHeader()
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ

    def test_fset_AcceptLanguageValidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        header = AcceptLanguageValidHeader('es')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageValidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == header.header_value

    def test_fset_AcceptLanguageInvalidHeader(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': ''})
        property_ = accept_language_property()
        header = AcceptLanguageInvalidHeader('en_gb')
        property_.fset(request=request, value=header)
        assert isinstance(request.accept_language, AcceptLanguageInvalidHeader)
        assert request.environ['HTTP_ACCEPT_LANGUAGE'] == header.header_value

    def test_fdel_header_key_in_environ(self):
        request = Request.blank('/', environ={'HTTP_ACCEPT_LANGUAGE': 'es'})
        property_ = accept_language_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ

    def test_fdel_header_key_not_in_environ(self):
        request = Request.blank('/')
        property_ = accept_language_property()
        property_.fdel(request=request)
        assert isinstance(request.accept_language, AcceptLanguageNoHeader)
        assert 'HTTP_ACCEPT_LANGUAGE' not in request.environ


# Deprecated tests:


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_init_warns():
    with warnings.catch_warnings(record=True) as warning:
        warnings.simplefilter("always")
        MIMEAccept('image/jpg')

    assert len(warning) == 1


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_init():
    mimeaccept = MIMEAccept('image/jpg')
    assert mimeaccept._parsed == [('image/jpg', 1)]
    mimeaccept = MIMEAccept('image/png, image/jpg;q=0.5')
    assert mimeaccept._parsed == [('image/png', 1), ('image/jpg', 0.5)]
    mimeaccept = MIMEAccept('image, image/jpg;q=0.5')
    assert mimeaccept._parsed == []
    mimeaccept = MIMEAccept('*/*')
    assert mimeaccept._parsed == [('*/*', 1)]
    mimeaccept = MIMEAccept('*/png')
    assert mimeaccept._parsed == [('*/png', 1)]
    mimeaccept = MIMEAccept('image/pn*')
    assert mimeaccept._parsed == [('image/pn*', 1.0)]
    mimeaccept = MIMEAccept('image/*')
    assert mimeaccept._parsed == [('image/*', 1)]


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
@pytest.mark.filterwarnings(IGNORE_CONTAINS)
def test_MIMEAccept_parse():
    assert list(MIMEAccept.parse('image/jpg')) == [('image/jpg', 1)]
    assert list(MIMEAccept.parse('invalid')) == []


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_accept_html():
    mimeaccept = MIMEAccept('image/jpg')
    assert not mimeaccept.accept_html()
    mimeaccept = MIMEAccept('image/jpg, text/html')
    assert mimeaccept.accept_html()


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
@pytest.mark.filterwarnings(IGNORE_CONTAINS)
def test_MIMEAccept_contains():
    mimeaccept = MIMEAccept('A/a, B/b, C/c')
    assert 'A/a' in mimeaccept
    assert 'A/*' in mimeaccept
    assert '*/a' in mimeaccept
    assert 'A/b' not in mimeaccept
    assert 'B/a' not in mimeaccept


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
@pytest.mark.filterwarnings(IGNORE_BEST_MATCH)
def test_MIMEAccept_json():
    mimeaccept = MIMEAccept('text/html, */*; q=.2')
    assert mimeaccept.best_match(['application/json']) == 'application/json'


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_no_raise_invalid():
    assert MIMEAccept('invalid')


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
@pytest.mark.filterwarnings(IGNORE_ITER)
def test_MIMEAccept_iter():
    assert list(iter(MIMEAccept('text/html, other/whatever'))) == [
        'text/html',
        'other/whatever',
    ]


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_str():
    assert str(MIMEAccept('image/jpg')) == 'image/jpg'


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_add():
    assert str(MIMEAccept('image/jpg') + 'image/png') == 'image/jpg, image/png'
    assert str(MIMEAccept('image/jpg') + MIMEAccept('image/png')) == 'image/jpg, image/png'
    assert isinstance(MIMEAccept('image/jpg') + 'image/png', MIMEAccept)
    assert isinstance(MIMEAccept('image/jpg') + MIMEAccept('image/png'), MIMEAccept)


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
def test_MIMEAccept_radd():
    assert str('image/png' + MIMEAccept('image/jpg')) == 'image/png, image/jpg'
    assert isinstance('image/png' + MIMEAccept('image/jpg'), MIMEAccept)


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
@pytest.mark.filterwarnings(IGNORE_CONTAINS)
def test_MIMEAccept_repr():
    assert 'image/jpg' in repr(MIMEAccept('image/jpg'))


@pytest.mark.filterwarnings(IGNORE_MIMEACCEPT)
@pytest.mark.filterwarnings(IGNORE_QUALITY)
def test_MIMEAccept_quality():
    assert MIMEAccept('image/jpg;q=0.9').quality('image/jpg') == 0.9
    assert MIMEAccept('image/png;q=0.9').quality('image/jpg') is None
