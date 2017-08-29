"""
Parses a variety of ``Accept-*`` headers.

These headers generally take the form of::

    value1; q=0.5, value2; q=0

Where the ``q`` parameter is optional.  In theory other parameters
exists, but this ignores them.
"""

import re
import textwrap
import warnings

from webob.headers import _trans_name as header_to_key
from webob.util import (
    header_docstring,
    )

part_re = re.compile(
    r',\s*([^\s;,\n]+)(?:[^,]*?;\s*q=([0-9.]*))?')

# RFC 7230 Section 3.2.3 "Whitespace"
# OWS            = *( SP / HTAB )
#                ; optional whitespace
OWS_re = '[ \t]*'

# RFC 7230 Section 3.2.6 "Field Value Components":
# tchar          = "!" / "#" / "$" / "%" / "&" / "'" / "*"
#                / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~"
#                / DIGIT / ALPHA
tchar_re = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]"

# token          = 1*tchar
token_re = tchar_re + '+'
token_compiled_re = re.compile('^' + token_re + '$')

# RFC 7231 Section 5.3.1 "Quality Values"
# qvalue = ( "0" [ "." 0*3DIGIT ] )
#        / ( "1" [ "." 0*3("0") ] )
qvalue_re = (
    r'(?:0(?:\.[0-9]{0,3})?)'
    '|'
    r'(?:1(?:\.0{0,3})?)'
)
# weight = OWS ";" OWS "q=" qvalue
weight_re = OWS_re + ';' + OWS_re + '[qQ]=(' + qvalue_re + ')'


def _item_n_weight_re(item_re):
    return '(' + item_re + ')(?:' + weight_re + ')?'


def _item_qvalue_pair_to_header_element(pair):
    item, qvalue = pair
    if qvalue == 1.0:
        element = item
    elif qvalue == 0.0:
        element = '{};q=0'.format(item)
    else:
        element = '{};q={}'.format(item, qvalue)
    return element


def _list_0_or_more__compiled_re(element_re):
    # RFC 7230 Section 7 "ABNF List Extension: #rule":
    # #element => [ ( "," / element ) *( OWS "," [ OWS element ] ) ]
    return re.compile(
        '^(?:$)|' +
        '(?:' +
        '(?:,|(?:' + element_re + '))' +
        '(?:' + OWS_re + ',(?:' + OWS_re + element_re + ')?)*' +
        ')$',
    )


def _list_1_or_more__compiled_re(element_re):
    # RFC 7230 Section 7 "ABNF List Extension: #rule":
    # 1#element => *( "," OWS ) element *( OWS "," [ OWS element ] )
    # and RFC 7230 Errata ID: 4169
    return re.compile(
        '^(?:,' + OWS_re + ')*' + element_re +
        '(?:' + OWS_re + ',(?:' + OWS_re + element_re + ')?)*$',
    )


class Accept(object):
    """
    Represents a generic ``Accept-*`` style header.
class Accept(object):
    """
    Represent an ``Accept`` header.

    Base class for :class:`AcceptValidHeader`, :class:`AcceptNoHeader`, and
    :class:`AcceptInvalidHeader`.
    """

    # RFC 6838 describes syntax rules for media types that are different to
    # (and stricter than) those in RFC 7231, but if RFC 7231 intended us to
    # follow the rules in RFC 6838 for media ranges, it would not have
    # specified its own syntax rules for media ranges, so it appears we should
    # use the rules in RFC 7231 for now.

    # RFC 5234 Appendix B.1 "Core Rules":
    # VCHAR         =  %x21-7E
    #                       ; visible (printing) characters
    vchar_re = '\x21-\x7e'
    # RFC 7230 Section 3.2.6 "Field Value Components":
    # quoted-string = DQUOTE *( qdtext / quoted-pair ) DQUOTE
    # qdtext        = HTAB / SP /%x21 / %x23-5B / %x5D-7E / obs-text
    # obs-text      = %x80-FF
    # quoted-pair   = "\" ( HTAB / SP / VCHAR / obs-text )
    obs_text_re = '\x80-\xff'
    qdtext_re = '[\t \x21\x23-\x5b\\\x5d-\x7e' + obs_text_re + ']'
    # The '\\' between \x5b and \x5d is needed to escape \x5d (']')
    quoted_pair_re = r'\\' + '[\t ' + vchar_re + obs_text_re + ']'
    quoted_string_re = \
        '"(?:(?:' + qdtext_re + ')|(?:' + quoted_pair_re + '))*"'

    # RFC 7231 Section 3.1.1.1 "Media Type":
    # type       = token
    # subtype    = token
    # parameter  = token "=" ( token / quoted-string )
    type_re = token_re
    subtype_re = token_re
    parameter_re = token_re + '=' + \
        '(?:(?:' + token_re + ')|(?:' + quoted_string_re + '))'

    # Section 5.3.2 "Accept":
    # media-range    = ( "*/*"
    #                  / ( type "/" "*" )
    #                  / ( type "/" subtype )
    #                  ) *( OWS ";" OWS parameter )
    media_range_re = (
        '(' +
        '(?:' + type_re + '/' + subtype_re + ')' +
        # '*' is included through type_re and subtype_re, so this covers */*
        # and type/*
        ')' +
        '(' +
        '(?:' + OWS_re + ';' + OWS_re +
        '(?![qQ]=)' +  # media type parameter cannot be named "q"
        parameter_re + ')*' +
        ')'
    )
    # accept-params  = weight *( accept-ext )
    # accept-ext = OWS ";" OWS token [ "=" ( token / quoted-string ) ]
    accept_ext_re = (
        OWS_re + ';' + OWS_re + token_re + '(?:' +
        '=(?:' +
        '(?:' + token_re + ')|(?:' + quoted_string_re + ')' +
        ')' +
        ')?'
    )
    accept_params_re = weight_re + '((?:' + accept_ext_re + ')*)'

    media_range_n_accept_params_re = media_range_re + '(?:' + \
        accept_params_re + ')?'
    media_range_n_accept_params_compiled_re = re.compile(
        media_range_n_accept_params_re,
    )

    accept_compiled_re = _list_0_or_more__compiled_re(
        element_re=media_range_n_accept_params_re,
    )

    # For parsing repeated groups within the media type parameters and
    # extension parameters segments
    parameters_compiled_re = re.compile(
        OWS_re + ';' + OWS_re + '(' + token_re + ')=(' + token_re + '|' +
        quoted_string_re + ')',
    )
    accept_ext_compiled_re = re.compile(
        OWS_re + ';' + OWS_re + '(' + token_re + ')' +
        '(?:' +
        '=(' +
        '(?:' +
        '(?:' + token_re + ')|(?:' + quoted_string_re + ')' +
        ')' +
        ')' +
        ')?',
    )

    # For parsing the media types in the `offers` argument to
    # .acceptable_offers(), we re-use the media range regex for media types.
    # This is not intended to be a validation of the offers; its main purpose
    # is to extract the media type and any media type parameters.
    media_type_re = media_range_re
    media_type_compiled_re = re.compile('^' + media_type_re + '$')

    @classmethod
    def _escape_and_quote_parameter_value(cls, param_value):
        """
        Escape and quote parameter value where necessary.

        For media type and extension parameter values.
        """
        if param_value == '':
            param_value = '""'
        else:
            param_value = param_value.replace('\\', '\\\\').replace(
                '"', r'\"',
            )
            if not token_compiled_re.match(param_value):
                param_value = '"' + param_value + '"'
        return param_value

    @classmethod
    def _form_extension_params_segment(cls, extension_params):
        """
        Convert iterable of extension parameters to str segment for header.

        `extension_params` is an iterable where each item is either a parameter
        string or a (name, value) tuple.
        """
        extension_params_segment = ''
        for item in extension_params:
            try:
                extension_params_segment += (';' + item)
            except TypeError:
                param_name, param_value = item
                param_value = cls._escape_and_quote_parameter_value(
                    param_value=param_value,
                )
                extension_params_segment += (
                    ';' + param_name + '=' + param_value
                )
        return extension_params_segment

    @classmethod
    def _form_media_range(cls, type_subtype, media_type_params):
        """
        Combine `type_subtype` and `media_type_params` to form a media range.

        `type_subtype` is a ``str``, and `media_type_params` is an iterable of
        (parameter name, parameter value) tuples.
        """
        media_type_params_segment = ''
        for param_name, param_value in media_type_params:
            param_value = cls._escape_and_quote_parameter_value(
                param_value=param_value,
            )
            media_type_params_segment += (';' + param_name + '=' + param_value)
        return type_subtype + media_type_params_segment

    @classmethod
    def _iterable_to_header_element(cls, iterable):
        """
        Convert iterable of tuples into header element ``str``.

        Each tuple is expected to be in one of two forms: (media_range, qvalue,
        extension_params_segment), or (media_range, qvalue).
        """
        try:
            media_range, qvalue, extension_params_segment = iterable
        except ValueError:
            media_range, qvalue = iterable
            extension_params_segment = ''

        if qvalue == 1.0:
            if extension_params_segment:
                element = '{};q=1{}'.format(
                    media_range, extension_params_segment,
                )
            else:
                element = media_range
        elif qvalue == 0.0:
            element = '{};q=0{}'.format(media_range, extension_params_segment)
        else:
            element = '{};q={}{}'.format(
                media_range, qvalue, extension_params_segment,
            )
        return element

    @classmethod
    def _parse_media_type_params(cls, media_type_params_segment):
        """
        Parse media type parameters segment into list of (name, value) tuples.
        """
        media_type_params = cls.parameters_compiled_re.findall(
            media_type_params_segment,
        )
        for index, (name, value) in enumerate(media_type_params):
            if value.startswith('"') and value.endswith('"'):
                value = cls._process_quoted_string_token(token=value)
                media_type_params[index] = (name, value)
        return media_type_params

    @classmethod
    def _process_quoted_string_token(cls, token):
        """
        Return unescaped and unquoted value from quoted token.
        """
        # RFC 7230, section 3.2.6 "Field Value Components": "Recipients that
        # process the value of a quoted-string MUST handle a quoted-pair as if
        # it were replaced by the octet following the backslash."
        return re.sub(r'\\(?![\\])', '', token[1:-1]).replace('\\\\', '\\')

    @classmethod
    def _python_value_to_header_str(cls, value):
        """
        Convert Python value to header string for __add__/__radd__.
        """
        if isinstance(value, str):
            return value
        if hasattr(value, 'items'):
            if value == {}:
                value = []
            else:
                value_list = []
                for media_range, item in value.items():
                    # item is either (media range, (qvalue, extension
                    # parameters segment)), or (media range, qvalue) (supported
                    # for backward compatibility)
                    if isinstance(item, (float, int)):
                        value_list.append((media_range, item, ''))
                    else:
                        value_list.append((media_range, item[0], item[1]))
                value = sorted(
                    value_list,
                    key=lambda item: item[1],  # qvalue
                    reverse=True,
                )
        if isinstance(value, (tuple, list)):
            header_elements = []
            for item in value:
                if isinstance(item, (tuple, list)):
                    item = cls._iterable_to_header_element(iterable=item)
                header_elements.append(item)
            header_str = ', '.join(header_elements)
        else:
            header_str = str(value)
        return header_str

    @classmethod
    def parse(cls, value):
        """
        Parse an ``Accept`` header.

        :param value: (``str``) header value
        :return: If `value` is a valid ``Accept`` header, returns an iterator
                 of (*media_range*, *qvalue*, *media_type_params*,
                 *extension_params*) tuples, as parsed from the header from
                 left to right.

                 | *media_range* is the media range, including any media type
                   parameters. The media range is returned in a canonicalised
                   form (except the case of the characters are unchanged):
                   unnecessary spaces around the semicolons before media type
                   parameters are removed; the parameter values are returned in
                   a form where only the '``\``' and '``"``' characters are
                   escaped, and the values are quoted with double quotes only
                   if they need to be quoted.

                 | *qvalue* is the quality value of the media range.

                 | *media_type_params* is the media type parameters, as a list
                   of (parameter name, value) tuples.

                 | *extension_params* is the extension parameters, as a list
                   where each item is either a parameter string or a (parameter
                   name, value) tuple.
        :raises ValueError: if `value` is an invalid header
        """
        # Check if header is valid
        # Using Python stdlib's `re` module, there is currently no way to check
        # the match *and* get all the groups using the same regex, so we have
        # to do this in steps using multiple regexes.
        if cls.accept_compiled_re.match(value) is None:
            raise ValueError('Invalid value for an Accept header.')
        def generator(value):
            for match in (
                cls.media_range_n_accept_params_compiled_re.finditer(value)
            ):
                groups = match.groups()

                type_subtype = groups[0]

                media_type_params = cls._parse_media_type_params(
                    media_type_params_segment=groups[1],
                )

                media_range = cls._form_media_range(
                    type_subtype=type_subtype,
                    media_type_params=media_type_params,
                )

                # qvalue (groups[2]) and extension_params (groups[3]) are both
                # None if neither qvalue or extension parameters are found in
                # the match.

                qvalue = groups[2]
                qvalue = float(qvalue) if qvalue else 1.0

                extension_params = groups[3]
                if extension_params:
                    extension_params = cls.accept_ext_compiled_re.findall(
                        extension_params,
                    )
                    for index, (token_key, token_value) in enumerate(
                        extension_params
                    ):
                        if token_value:
                            if (
                                token_value.startswith('"') and
                                token_value.endswith('"')
                            ):
                                token_value = cls._process_quoted_string_token(
                                    token=token_value,
                                )
                                extension_params[index] = (
                                    token_key, token_value,
                                )
                        else:
                            extension_params[index] = token_key
                else:
                    extension_params = []

                yield (
                    media_range, qvalue, media_type_params, extension_params,
                )
        return generator(value=value)

    This object should not be modified.  To add items you can use
    ``accept_obj + 'accept_thing'`` to get a new object

class AcceptValidHeader(Accept):
    """
    Represent a valid ``Accept`` header.

    A valid header is one that conforms to :rfc:`RFC 7231, section 5.3.2
    <7231#section-5.3.2>`.

    This object should not be modified. To add to the header, we can use the
    addition operators (``+`` and ``+=``), which return a new object (see the
    docstring for :meth:`AcceptValidHeader.__add__`).
    """

    @property
    def header_value(self):
        """(``str`` or ``None``) The header value."""
        return self._header_value

    @property
    def parsed(self):
        """
        (``list`` or ``None``) Parsed form of the header.

        A list of (*media_range*, *qvalue*, *media_type_params*,
        *extension_params*) tuples, where

        *media_range* is the media range, including any media type parameters.
        The media range is returned in a canonicalised form (except the case of
        the characters are unchanged): unnecessary spaces around the semicolons
        before media type parameters are removed; the parameter values are
        returned in a form where only the '``\``' and '``"``' characters are
        escaped, and the values are quoted with double quotes only if they need
        to be quoted.

        *qvalue* is the quality value of the media range.

        *media_type_params* is the media type parameters, as a list of
        (parameter name, value) tuples.

        *extension_params* is the extension parameters, as a list where each
        item is either a parameter string or a (parameter name, value) tuple.
        """
        return self._parsed

    def __init__(self, header_value):
        self.header_value = header_value
        self.parsed = list(self.parse(header_value))
        self._parsed_nonzero = [(m,q) for (m,q) in self.parsed if q]
        """
        Create an :class:`AcceptValidHeader` instance.

        :param header_value: (``str``) header value.
        :raises ValueError: if `header_value` is an invalid value for an
                            ``Accept`` header.
        """
        self._header_value = header_value
        self._parsed = list(self.parse(header_value))
        self._parsed_nonzero = [item for item in self.parsed if item[1]]
        # item[1] is the qvalue

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * ``None``
        * a ``str`` header value
        * a ``dict``, with media ranges ``str``\ s (including any media type
          parameters) as keys, and either qvalues ``float``\ s or (*qvalues*,
          *extension_params*) tuples as values, where *extension_params* is a
          ``str`` of the extension parameters segment of the header element,
          starting with the first '``;``'
        * a ``tuple`` or ``list``, where each item is either a header element
          ``str``, or a (*media_range*, *qvalue*, *extension_params*) ``tuple``
          or ``list`` where *media_range* is a ``str`` of the media range
          including any media type parameters, and *extension_params* is a
          ``str`` of the extension parameters segment of the header element,
          starting with the first '``;``'
        * an :class:`AcceptValidHeader`, :class:`AcceptNoHeader`, or
          :class:`AcceptInvalidHeader` instance
        * object of any other type that returns a value for ``__str__``

        If `other` is a valid header value or another
        :class:`AcceptValidHeader` instance, and the header value it represents
        is not `''`, then the two header values are joined with ``', '``, and a
        new :class:`AcceptValidHeader` instance with the new header value is
        returned.

        If `other` is a valid header value or another
        :class:`AcceptValidHeader` instance representing a header value of
        `''`; or if it is ``None`` or an :class:`AcceptNoHeader` instance; or
        if it is an invalid header value, or an :class:`AcceptInvalidHeader`
        instance, then a new :class:`AcceptValidHeader` instance with the same
        header value as ``self`` is returned.
        """
        if isinstance(other, AcceptValidHeader):
            if other.header_value == '':
                return self.__class__(header_value=self.header_value)
            else:
                return create_accept_header(
                    header_value=self.header_value + ', ' + other.header_value,
                )

        if isinstance(other, (AcceptNoHeader, AcceptInvalidHeader)):
            return self.__class__(header_value=self.header_value)

        return self._add_instance_and_non_accept_type(
            instance=self, other=other,
        )

    def __bool__(self):
        """
        Return whether ``self`` represents a valid ``Accept`` header.

        Return ``True`` if ``self`` represents a valid header, and ``False`` if
        it represents an invalid header, or the header not being in the
        request.

        For this class, it always returns ``True``.
        """
        return True
    __nonzero__ = __bool__  # Python 2

    def __contains__(self, offer):
        """
        Return ``bool`` indicating whether `offer` is acceptable.

        .. warning::

           The behavior of :meth:`AcceptValidHeader.__contains__` is currently
           being maintained for backward compatibility, but it will change in
           the future to better conform to the RFC.

        :param offer: (``str``) media type offer
        :return: (``bool``) Whether ``offer`` is acceptable according to the
                 header.

        This uses the old criterion of a match in
        :meth:`AcceptValidHeader._old_match`, which is not as specified in
        :rfc:`RFC 7231, section 5.3.2 <7231#section-5.3.2>`. It does not
        correctly take into account media type parameters:

            >>> 'text/html;p=1' in AcceptValidHeader('text/html')
            False

        or media ranges with ``q=0`` in the header::

            >>> 'text/html' in AcceptValidHeader('text/*, text/html;q=0')
            True
            >>> 'text/html' in AcceptValidHeader('text/html;q=0, */*')
            True

        (See the docstring for :meth:`AcceptValidHeader._old_match` for other
        problems with the old criterion for matching.)
        """
        warnings.warn(
            'The behavior of AcceptValidHeader.__contains__ is '
            'currently being maintained for backward compatibility, but it '
            'will change in the future to better conform to the RFC.',
            DeprecationWarning,
        )
        for (
            media_range, quality, media_type_params, extension_params
        ) in self._parsed_nonzero:
            if self._old_match(media_range, offer):
                return True
        return False

    def __iter__(self):
        """
        Return all the ranges with non-0 qvalues, in order of preference.

        .. warning::

           The behavior of this method is currently maintained for backward
           compatibility, but will change in the future.

        :return: iterator of all the media ranges in the header with non-0
                 qvalues, in descending order of qvalue. If two ranges have the
                 same qvalue, they are returned in the order of their positions
                 in the header, from left to right.

        Please note that this is a simple filter for the ranges in the header
        with non-0 qvalues, and is not necessarily the same as what the client
        prefers, e.g. ``'audio/basic;q=0, */*'`` means 'everything but
        audio/basic', but ``list(instance)`` would return only ``['*/*']``.
        """
        warnings.warn(
            'The behavior of AcceptLanguageValidHeader.__iter__ is currently '
            'maintained for backward compatibility, but will change in the '
            'future.',
            DeprecationWarning,
        )

        for media_range, qvalue, media_type_params, extension_params in sorted(
            self._parsed_nonzero,
            key=lambda i: i[1],
            reverse=True
        ):
            yield media_range

    def __radd__(self, other):
        """
        Add to header, creating a new header object.

        See the docstring for :meth:`AcceptValidHeader.__add__`.
        """
        return self._add_instance_and_non_accept_type(
            instance=self, other=other, instance_on_the_right=True,
        )

    def __repr__(self):
        return '<{} ({!r})>'.format(self.__class__.__name__, str(self))

    def __str__(self):
        r"""
        Return a tidied up version of the header value.

        e.g. If ``self.header_value`` is ``r',,text/html ; p1="\"\1\"" ;
        q=0.50; e1=1 ;e2  ,  text/plain ,'``, ``str(instance)`` returns
        ``r'text/html;p1="\"1\"";q=0.5;e1=1;e2, text/plain'``.
        """
        # self.parsed tuples are in the form: (media_range, qvalue,
        # media_type_params, extension_params)
        # self._iterable_to_header_element() requires iterable to be in the
        # form: (media_range, qvalue, extension_params_segment).
        return ', '.join(
            self._iterable_to_header_element(
                iterable=(
                    tuple_[0],  # media_range
                    tuple_[1],  # qvalue
                    self._form_extension_params_segment(
                        extension_params=tuple_[3],  # extension_params
                    )
                ),
            ) for tuple_ in self.parsed
        )

    def _add_instance_and_non_accept_type(
        self, instance, other, instance_on_the_right=False,
    ):
        if not other:
            return self.__class__(header_value=instance.header_value)

        other_header_value = self._python_value_to_header_str(value=other)

        if other_header_value == '':
            # if ``other`` is an object whose type we don't recognise, and
            # str(other) returns ''
            return self.__class__(header_value=instance.header_value)

        try:
            self.parse(value=other_header_value)
        except ValueError:  # invalid header value
            return self.__class__(header_value=instance.header_value)

        new_header_value = (
            (other_header_value + ', ' + instance.header_value)
            if instance_on_the_right
            else (instance.header_value + ', ' + other_header_value)
        )
        return self.__class__(header_value=new_header_value)

    def _old_match(self, mask, offer):
        """
        Check if the offer is covered by the mask

        ``offer`` may contain wildcards to facilitate checking if a ``mask``
        would match a 'permissive' offer.

        Wildcard matching forces the match to take place against the type or
        subtype of the mask and offer (depending on where the wildcard matches)

        .. warning::

           This is maintained for backward compatibility, and will be
           deprecated in the future.

        This method was WebOb's old criterion for deciding whether a media type
        matches a media range, used in

        - :meth:`AcceptValidHeader.__contains__`
        - :meth:`AcceptValidHeader.best_match`
        - :meth:`AcceptValidHeader.quality`

        It allows offers of *, */*, type/*, */subtype and types with no
        subtypes, which are not media types as specified in :rfc:`RFC 7231,
        section 5.3.2 <7231#section-5.3.2>`. This is also undocumented in any
        of the public APIs that uses this method.
        """
        # Match if comparisons are the same or either is a complete wildcard
        if (mask.lower() == offer.lower() or
                '*/*' in (mask, offer) or
                '*' == offer):
            return True

        # Set mask type with wildcard subtype for malformed masks
        try:
            mask_type, mask_subtype = [x.lower() for x in mask.split('/')]
        except ValueError:
            mask_type = mask
            mask_subtype = '*'

        # Set offer type with wildcard subtype for malformed offers
        try:
            offer_type, offer_subtype = [x.lower() for x in offer.split('/')]
        except ValueError:
            offer_type = offer
            offer_subtype = '*'

        if mask_subtype == '*':
            # match on type only
            if offer_type == '*':
                return True
            else:
                return mask_type.lower() == offer_type.lower()

        if mask_type == '*':
            # match on subtype only
            if offer_subtype == '*':
                return True
            else:
                return mask_subtype.lower() == offer_subtype.lower()

        if offer_subtype == '*':
            # match on type only
            return mask_type.lower() == offer_type.lower()

        if offer_type == '*':
            # match on subtype only
            return mask_subtype.lower() == offer_subtype.lower()

        return offer.lower() == mask.lower()

    def accept_html(self):
        """
        Return ``True`` if any HTML-like type is accepted.

        The HTML-like types are 'text/html', 'application/xhtml+xml',
        'application/xml' and 'text/xml'.
        """
        return bool(
            self.acceptable_offers(
                offers=[
                    'text/html',
                    'application/xhtml+xml',
                    'application/xml',
                    'text/xml',
                ],
            )
        )
    accepts_html = property(fget=accept_html, doc=accept_html.__doc__)
    # note the plural

    def acceptable_offers(self, offers):
        """
        Return the offers that are acceptable according to the header.

        The offers are returned in descending order of preference, where
        preference is indicated by the qvalue of the media range in the header
        that best matches the offer.

        This uses the matching rules described in :rfc:`RFC 7231, section 5.3.2
        <7231#section-5.3.2>`.

        :param offers: ``iterable`` of ``str`` media types (media types can
                       include media type parameters)
        :return: A list of tuples of the form (media type, qvalue), in
                 descending order of qvalue. Where two offers have the same
                 qvalue, they are returned in the same order as their order in
                 `offers`.
        """
        parsed = self.parsed

        # RFC 7231, section 3.1.1.1 "Media Type":
        # "The type, subtype, and parameter name tokens are case-insensitive.
        # Parameter values might or might not be case-sensitive, depending on
        # the semantics of the parameter name."
        lowercased_ranges = [
            (
                media_range.partition(';')[0].lower(), qvalue,
                [(name.lower(), value) for name, value in media_type_params],
                [(name.lower(), value) for name, value in extension_params],
            )
            for media_range, qvalue, media_type_params, extension_params in
            parsed
        ]
        lowercased_offers = [offer.lower() for offer in offers]

        lowercased_offers_parsed = []
        for offer in lowercased_offers:
            match = self.media_type_compiled_re.match(offer)
            # The regex here is only used for parsing, and not intended to
            # validate the offer
            if not match:
                raise ValueError(repr(offer) + ' is not a media type.')
            lowercased_offers_parsed.append(match.groups())

        acceptable_offers_n_quality_factors = {}
        for (
            offer_index, (offer_type_subtype, offer_media_type_params)
        ) in enumerate(lowercased_offers_parsed):
            offer_media_type_params = self._parse_media_type_params(
                media_type_params_segment=offer_media_type_params,
            )
            for (
                range_type_subtype, range_qvalue, range_media_type_params, __,
            ) in lowercased_ranges:
                # The specificity values below are based on the list in the
                # example in RFC 7231 section 5.3.2 explaining how "media
                # ranges can be overridden by more specific media ranges or
                # specific media types". We assign specificity to the list
                # items in reverse order, so specificity 4, 3, 2, 1 correspond
                # to 1, 2, 3, 4 in the list, respectively (so that higher
                # specificity has higher precedence).
                if offer_type_subtype == range_type_subtype:
                    if range_media_type_params == []:
                        # If offer_media_type_params == [], the offer and the
                        # range match exactly, with neither having media type
                        # parameters.
                        # If offer_media_type_params is not [], the offer and
                        # the range are a match. See the table towards the end
                        # of RFC 7231 section 5.3.2, where the media type
                        # 'text/html;level=3' matches the range 'text/html' in
                        # the header.
                        # Both cases are a match with a specificity of 3.
                        specificity = 3
                    elif offer_media_type_params == range_media_type_params:
                        specificity = 4
                    else:  # pragma: no cover
                        # no cover because of
                        # https://bitbucket.org/ned/coveragepy/issues/254/incorrect-coverage-on-continue-statement
                        continue
                else:
                    offer_type = offer_type_subtype.split('/')[0]
                    range_type, range_subtype = range_type_subtype.split('/')
                    if range_subtype == '*' and offer_type == range_type:
                        specificity = 2
                    elif range_type_subtype == '*/*':
                        specificity = 1
                    else:  # pragma: no cover
                        # no cover because of
                        # https://bitbucket.org/ned/coveragepy/issues/254/incorrect-coverage-on-continue-statement
                        continue
                try:
                    if specificity <= acceptable_offers_n_quality_factors[
                        offers[offer_index]
                    ][2]:
                        continue
                except KeyError:
                    # the entry for the offer is not already in
                    # acceptable_offers_n_quality_factors
                    pass
                acceptable_offers_n_quality_factors[offers[offer_index]] = (
                    range_qvalue,  # qvalue of matched range
                    offer_index,
                    specificity,  # specifity of matched range
                )

        acceptable_offers_n_quality_factors = [
            # key is offer, value[0] is qvalue, value[1] is offer_index
            (key, value[0], value[1])
            for key, value in acceptable_offers_n_quality_factors.items()
            if value[0]  # != 0.0
            # We have to filter out the offers with qvalues of 0 here instead
            # of just skipping them early in the large ``for`` loop because
            # that would not work for e.g. when the header is 'text/html;q=0,
            # text/html' (which does not make sense, but is nonetheless valid),
            # and offers is ['text/html']
        ]
        # sort by offer_index, ascending
        acceptable_offers_n_quality_factors.sort(key=lambda tuple_: tuple_[2])
        # (stable) sort by qvalue, descending
        acceptable_offers_n_quality_factors.sort(
            key=lambda tuple_: tuple_[1], reverse=True,
        )
        # drop offer_index
        acceptable_offers_n_quality_factors = [
            (item[0], item[1]) for item in acceptable_offers_n_quality_factors
        ]
        return acceptable_offers_n_quality_factors
        # If a media range is repeated in the header (which would not make
        # sense, but would be valid according to the rules in the RFC), an
        # offer for which the media range is the most specific match would take
        # its qvalue from the first appearance of the range in the header.

    def best_match(self, offers, default_match=None):
        """
        Return the best match from the sequence of media type `offers`.

        .. warning::

           This is currently maintained for backward compatibility, and will be
           deprecated in the future.

           :meth:`AcceptValidHeader.best_match` uses its own algorithm (one not
           specified in :rfc:`RFC 7231 <7231>`) to determine what is a best
           match. The algorithm has many issues, and does not conform to
           :rfc:`RFC 7231 <7231>`.

        Each media type in `offers` is checked against each non-``q=0`` range
        in the header. If the two are a match according to WebOb's old
        criterion for a match, the quality value of the match is the qvalue of
        the media range from the header multiplied by the server quality value
        of the offer (if the server quality value is not supplied, it is 1).

        The offer in the match with the highest quality value is the best
        match. If there is more than one match with the highest qvalue, the
        match where the media range has a lower number of '*'s is the best
        match. If the two have the same number of '*'s, the one that shows up
        first in `offers` is the best match.

        :param offers: (iterable)

                       | Each item in the iterable may be a ``str`` media type,
                         or a (media type, server quality value) ``tuple`` or
                         ``list``. (The two may be mixed in the iterable.)

        :param default_match: (optional, any type) the value to be returned if
                              there is no match

        :return: (``str``, or the type of `default_match`)

                 | The offer that is the best match. If there is no match, the
                   value of `default_match` is returned.

        This uses the old criterion of a match in
        :meth:`AcceptValidHeader._old_match`, which is not as specified in
        :rfc:`RFC 7231, section 5.3.2 <7231#section-5.3.2>`. It does not
        correctly take into account media type parameters:

            >>> instance = AcceptValidHeader('text/html')
            >>> instance.best_match(offers=['text/html;p=1']) is None
            True

        or media ranges with ``q=0`` in the header::

            >>> instance = AcceptValidHeader('text/*, text/html;q=0')
            >>> instance.best_match(offers=['text/html'])
            'text/html'

            >>> instance = AcceptValidHeader('text/html;q=0, */*')
            >>> instance.best_match(offers=['text/html'])
            'text/html'

        (See the docstring for :meth:`AcceptValidHeader._old_match` for other
        problems with the old criterion for matching.)

        Another issue is that this method considers the best matching range for
        an offer to be the matching range with the highest quality value,
        (where quality values are tied, the most specific media range is
        chosen); whereas :rfc:`RFC 7231, section 5.3.2 <7231#section-5.3.2>`
        specifies that we should consider the best matching range for a media
        type offer to be the most specific matching range.::

            >>> instance = AcceptValidHeader('text/html;q=0.5, text/*')
            >>> instance.best_match(offers=['text/html', 'text/plain'])
            'text/html'
        """
        warnings.warn(
            'The behavior of AcceptValidHeader.best_match is currently being '
            'maintained for backward compatibility, but it will be deprecated'
            ' in the future, as it does not conform to the RFC.',
            DeprecationWarning,
        )
        best_quality = -1
        best_offer = default_match
        matched_by = '*/*'
        for offer in offers:
            if isinstance(offer, (tuple, list)):
                offer, server_quality = offer
            else:
                server_quality = 1
            for item in self._parsed_nonzero:
                mask = item[0]
                quality = item[1]
                possible_quality = server_quality * quality
                if possible_quality < best_quality:
                    continue
                elif possible_quality == best_quality:
                    # 'text/plain' overrides 'message/*' overrides '*/*'
                    # (if all match w/ the same q=)
                    if matched_by.count('*') <= mask.count('*'):
                        continue
                if self._old_match(mask, offer):
                    best_quality = possible_quality
                    best_offer = offer
                    matched_by = mask
        return best_offer

    def quality(self, offer):
        """
        Return quality value of given offer, or ``None`` if there is no match.

        .. warning::

           This is currently maintained for backward compatibility, and will be
           deprecated in the future.

        :param offer: (``str``) media type offer
        :return: (``float`` or ``None``)

                 | The highest quality value from the media range(s) that match
                   the `offer`, or ``None`` if there is no match.

        This uses the old criterion of a match in
        :meth:`AcceptValidHeader._old_match`, which is not as specified in
        :rfc:`RFC 7231, section 5.3.2 <7231#section-5.3.2>`. It does not
        correctly take into account media type parameters:

            >>> instance = AcceptValidHeader('text/html')
            >>> instance.quality('text/html;p=1') is None
            True

        or media ranges with ``q=0`` in the header::

            >>> instance = AcceptValidHeader('text/*, text/html;q=0')
            >>> instance.quality('text/html')
            1.0
            >>> AcceptValidHeader('text/html;q=0, */*').quality('text/html')
            1.0

        (See the docstring for :meth:`AcceptValidHeader._old_match` for other
        problems with the old criterion for matching.)

        Another issue is that this method considers the best matching range for
        an offer to be the matching range with the highest quality value,
        whereas :rfc:`RFC 7231, section 5.3.2 <7231#section-5.3.2>` specifies
        that we should consider the best matching range for a media type offer
        to be the most specific matching range.::

            >>> instance = AcceptValidHeader('text/html;q=0.5, text/*')
            >>> instance.quality('text/html')
            1.0
        """
        warnings.warn(
            'The behavior of AcceptValidHeader.quality is currently being '
            'maintained for backward compatibility, but it will be deprecated '
            'in the future, as it does not conform to the RFC.',
            DeprecationWarning,
        )
        bestq = 0
        for item in self.parsed:
            media_range = item[0]
            qvalue = item[1]
            if self._old_match(media_range, offer):
                bestq = max(bestq, qvalue)
        return bestq or None



    @staticmethod
    def parse(value):
        """
        Parse ``Accept-*`` style header.

        Return iterator of ``(value, quality)`` pairs.
        ``quality`` defaults to 1.
        """
        for match in part_re.finditer(','+value):
            name = match.group(1)
            quality = match.group(2) or ''
            if quality:
                try:
                    quality = max(min(float(quality), 1), 0)
                    yield (name, quality)
                    continue
                except ValueError:
                    pass
            yield (name, 1)

    def __repr__(self):
        return '<%s(%r)>' % (self.__class__.__name__, str(self))

    def __iter__(self):
        for m,q in sorted(
            self._parsed_nonzero,
            key=lambda i: i[1],
            reverse=True
        ):
            yield m

    def __str__(self):
        result = []
        for mask, quality in self.parsed:
            if quality != 1:
                mask = '%s;q=%0.*f' % (
                    mask, min(len(str(quality).split('.')[1]), 3), quality)
            result.append(mask)
        return ', '.join(result)

    def __add__(self, other, reversed=False):
        if isinstance(other, Accept):
            other = other.header_value
        if hasattr(other, 'items'):
            other = sorted(other.items(), key=lambda item: -item[1])
        if isinstance(other, (list, tuple)):
            result = []
            for item in other:
                if isinstance(item, (list, tuple)):
                    name, quality = item
                    result.append('%s; q=%s' % (name, quality))
                else:
                    result.append(item)
            other = ', '.join(result)
        other = str(other)
        my_value = self.header_value
        if reversed:
            other, my_value = my_value, other
        if not other:
            new_value = my_value
        elif not my_value:
            new_value = other
        else:
            new_value = my_value + ', ' + other
        return self.__class__(new_value)

    def __radd__(self, other):
        return self.__add__(other, True)

    def __contains__(self, offer):
        """
        Returns true if the given object is listed in the accepted
        types.
        """
        for mask, quality in self._parsed_nonzero:
            if self._match(mask, offer):
                return True

    def quality(self, offer):
        """
        Return the quality of the given offer.  Returns None if there
        is no match (not 0).
        """
        bestq = 0
        for mask, q in self.parsed:
            if self._match(mask, offer):
                bestq = max(bestq, q)
        return bestq or None

    def best_match(self, offers, default_match=None):
        """
        Returns the best match in the sequence of offered types.

        The sequence can be a simple sequence, or you can have
        ``(match, server_quality)`` items in the sequence.  If you
        have these tuples then the client quality is multiplied by the
        server_quality to get a total.  If two matches have equal
        weight, then the one that shows up first in the `offers` list
        will be returned.

        But among matches with the same quality the match to a more specific
        requested type will be chosen. For example a match to text/* trumps */*.

        default_match (default None) is returned if there is no intersection.
        """
        best_quality = -1
        best_offer = default_match
        matched_by = '*/*'
        for offer in offers:
            if isinstance(offer, (tuple, list)):
                offer, server_quality = offer
            else:
                server_quality = 1
            for mask, quality in self._parsed_nonzero:
                possible_quality = server_quality * quality
                if possible_quality < best_quality:
                    continue
                elif possible_quality == best_quality:
                    # 'text/plain' overrides 'message/*' overrides '*/*'
                    # (if all match w/ the same q=)
                    if matched_by.count('*') <= mask.count('*'):
                        continue
                if self._match(mask, offer):
                    best_quality = possible_quality
                    best_offer = offer
                    matched_by = mask
        return best_offer

    def _match(self, mask, offer):
        _check_offer(offer)
        return mask == '*' or offer.lower() == mask.lower()


class NilAccept(object):
    """
    Represents a generic ``Accept-*`` style header when it is not present in
    the request or is empty.
    """
    MasterClass = Accept

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.MasterClass)

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False
    __bool__ = __nonzero__ # python 3

    def __iter__(self):
        return iter(())

    def __add__(self, item):
        if isinstance(item, self.MasterClass):
            return item
        else:
            return self.MasterClass('') + item

    def __radd__(self, item):
        if isinstance(item, self.MasterClass):
            return item
        else:
            return item + self.MasterClass('')

    def __contains__(self, item):
        _check_offer(item)
        return True

    def quality(self, offer):
        return 0

    def best_match(self, offers, default_match=None):
        best_quality = -1
        best_offer = default_match
        for offer in offers:
            _check_offer(offer)
            if isinstance(offer, (list, tuple)):
                offer, quality = offer
            else:
                quality = 1
            if quality > best_quality:
                best_offer = offer
                best_quality = quality
        return best_offer


class NoAccept(NilAccept):
    """
    Represents an ``Accept-Encoding`` header when it is not present in the
    request or is empty.
    """
    def __contains__(self, item):
        return False

class AcceptCharset(Accept):
    """
    Represents an ``Accept-Charset`` header.
    """
    @staticmethod
    def parse(value):
        """
        Parse ``Accept-Charset`` header.

        Return iterator of ``(charset, qvalue)`` pairs.
        """
        latin1_found = False
        for m, q in Accept.parse(value):
            _m = m.lower()
            if _m == '*' or _m == 'iso-8859-1':
                latin1_found = True
            yield _m, q
        if not latin1_found:
            yield ('iso-8859-1', 1)




class AcceptLanguage(object):
    """
    Represent an ``Accept-Language`` header.

    Base class for :class:`AcceptLanguageValidHeader`,
    :class:`AcceptLanguageNoHeader`, and :class:`AcceptLanguageInvalidHeader`.
    """

    # RFC 7231 Section 5.3.5 "Accept-Language":
    # Accept-Language = 1#( language-range [ weight ] )
    # language-range  =
    #           <language-range, see [RFC4647], Section 2.1>
    # RFC 4647 Section 2.1 "Basic Language Range":
    # language-range   = (1*8ALPHA *("-" 1*8alphanum)) / "*"
    # alphanum         = ALPHA / DIGIT
    lang_range_re = (
        r'\*|'
        '(?:'
        '[A-Za-z]{1,8}'
        '(?:-[A-Za-z0-9]{1,8})*'
        ')'
    )
    lang_range_n_weight_re = _item_n_weight_re(item_re=lang_range_re)
    lang_range_n_weight_compiled_re = re.compile(lang_range_n_weight_re)
    accept_language_compiled_re = _list_1_or_more__compiled_re(
        element_re=lang_range_n_weight_re,
    )

    @classmethod
    def _python_value_to_header_str(cls, value):
        if isinstance(value, str):
            header_str = value
        else:
            if hasattr(value, 'items'):
                value = sorted(
                    value.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            if isinstance(value, (tuple, list)):
                result = []
                for item in value:
                    if isinstance(item, (tuple, list)):
                        item = _item_qvalue_pair_to_header_element(pair=item)
                    result.append(item)
                header_str = ', '.join(result)
            else:
                header_str = str(value)
        return header_str

    @classmethod
    def parse(cls, value):
        """
        Parse an ``Accept-Language`` header.

        :param value: (``str``) header value
        :return: If `value` is a valid ``Accept-Language`` header, returns an
                 iterator of (language range, quality value) tuples, as parsed
                 from the header from left to right.
        :raises ValueError: if `value` is an invalid header
        """
        # Check if header is valid
        # Using Python stdlib's `re` module, there is currently no way to check
        # the match *and* get all the groups using the same regex, so we have
        # to use one regex to check the match, and another to get the groups.
        if cls.accept_language_compiled_re.match(value) is None:
            raise ValueError('Invalid value for an Accept-Language header.')
        def generator(value):
            for match in (
                cls.lang_range_n_weight_compiled_re.finditer(value)
            ):
                lang_range = match.group(1)
                qvalue = match.group(2)
                qvalue = float(qvalue) if qvalue else 1.0
                yield (lang_range, qvalue)
        return generator(value=value)


class AcceptLanguageValidHeader(AcceptLanguage):
    """
    Represent a valid ``Accept-Language`` header.

    A valid header is one that conforms to :rfc:`RFC 7231, section 5.3.5
    <7231#section-5.3.5>`.

    We take the reference from the ``language-range`` syntax rule in :rfc:`RFC
    7231, section 5.3.5 <7231#section-5.3.5>` to :rfc:`RFC 4647, section 2.1
    <4647#section-2.1>` to mean that only basic language ranges (and not
    extended language ranges) are expected in the ``Accept-Language`` header.

    This object should not be modified. To add to the header, we can use the
    addition operators (``+`` and ``+=``), which return a new object (see the
    docstring for :meth:`AcceptLanguageValidHeader.__add__`).
    """

    def __init__(self, header_value):
        """
        Create an :class:`AcceptLanguageValidHeader` instance.

        :param header_value: (``str``) header value.
        :raises ValueError: if `header_value` is an invalid value for an
                            ``Accept-Language`` header.
        """
        self._header_value = header_value
        self._parsed = list(self.parse(header_value))
        self._parsed_nonzero = [item for item in self.parsed if item[1]]
        # item[1] is the qvalue

    @property
    def header_value(self):
        """(``str`` or ``None``) The header value."""
        return self._header_value

    @property
    def parsed(self):
        """
        (``list`` or ``None``) Parsed form of the header.

        A list of (language range, quality value) tuples.
        """
        return self._parsed

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * ``None``
        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``\ s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``\ s and pairs can
          be mixed within the ``tuple`` or ``list``)
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance
        * object of any other type that returns a value for ``__str__``

        If `other` is a valid header value or another
        :class:`AcceptLanguageValidHeader` instance, the two header values are
        joined with ``', '``, and a new :class:`AcceptLanguageValidHeader`
        instance with the new header value is returned.

        If `other` is ``None``, an :class:`AcceptLanguageNoHeader` instance, an
        invalid header value, or an :class:`AcceptLanguageInvalidHeader`
        instance, a new :class:`AcceptLanguageValidHeader` instance with the
        same header value as ``self`` is returned.
        """
        if isinstance(other, AcceptLanguageValidHeader):
            return create_accept_language_header(
                header_value=self.header_value + ', ' + other.header_value,
            )

        if isinstance(
            other, (AcceptLanguageNoHeader, AcceptLanguageInvalidHeader)
        ):
            return self.__class__(header_value=self.header_value)

        return self._add_instance_and_non_accept_language_type(
            instance=self, other=other,
        )

    def __nonzero__(self):
        """
        Return whether ``self`` represents a valid ``Accept-Language`` header.

        Return ``True`` if ``self`` represents a valid header, and ``False`` if
        it represents an invalid header, or the header not being in the
        request.

        For this class, it always returns ``True``.
        """
        return True
    __bool__ = __nonzero__  # Python 3

    def __contains__(self, offer):
        """
        Return ``bool`` indicating whether `offer` is acceptable.

        .. warning::

           The behavior of :meth:`AcceptLanguageValidHeader.__contains__` is
           currently being maintained for backward compatibility, but it will
           change in the future to better conform to the RFC.

           What is 'acceptable' depends on the needs of your application.
           :rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>` suggests three
           matching schemes from :rfc:`RFC 4647 <4647>`, two of which WebOb
           supports with :meth:`AcceptLanguageValidHeader.basic_filtering` and
           :meth:`AcceptLanguageValidHeader.lookup` (we interpret the RFC to
           mean that Extended Filtering cannot apply for the
           ``Accept-Language`` header, as the header only accepts basic
           language ranges.) If these are not suitable for the needs of your
           application, you may need to write your own matching using
           :attr:`AcceptLanguageValidHeader.parsed`.

        :param offer: (``str``) language tag offer
        :return: (``bool``) Whether ``offer`` is acceptable according to the
                 header.

        This uses the old criterion of a match in
        :meth:`AcceptLanguageValidHeader._old_match`, which does not conform to
        :rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>` or any of the
        matching schemes suggested there. It also does not properly take into
        account ranges with ``q=0`` in the header::

            >>> 'en-gb' in AcceptLanguageValidHeader('en, en-gb;q=0')
            True
            >>> 'en' in AcceptLanguageValidHeader('en;q=0, *')
            True

        (See the docstring for :meth:`AcceptLanguageValidHeader._old_match` for
        other problems with the old criterion for a match.)
        """
        warnings.warn(
            'The behavior of AcceptLanguageValidHeader.__contains__ is '
            'currently being maintained for backward compatibility, but it '
            'will change in the future to better conform to the RFC.',
            DeprecationWarning,
        )
        for mask, quality in self._parsed_nonzero:
            if self._old_match(mask, offer):
                return True
        return False

    def __iter__(self):
        """
        Return all the ranges with non-0 qvalues, in order of preference.

        .. warning::

           The behavior of this method is currently maintained for backward
           compatibility, but will change in the future.

        :return: iterator of all the language ranges in the header with non-0
                 qvalues, in descending order of qvalue. If two ranges have the
                 same qvalue, they are returned in the order of their positions
                 in the header, from left to right.

        Please note that this is a simple filter for the ranges in the header
        with non-0 qvalues, and is not necessarily the same as what the client
        prefers, e.g. ``'en-gb;q=0, *'`` means 'everything but British
        English', but ``list(instance)`` would return only ``['*']``.
        """
        warnings.warn(
            'The behavior of AcceptLanguageValidHeader.__iter__ is currently '
            'maintained for backward compatibility, but will change in the '
            'future.',
            DeprecationWarning,
        )

        for m, q in sorted(
            self._parsed_nonzero,
            key=lambda i: i[1],
            reverse=True
        ):
            yield m

    def __radd__(self, other):
        """
        Add to header, creating a new header object.

        See the docstring for :meth:`AcceptLanguageValidHeader.__add__`.
        """
        return self._add_instance_and_non_accept_language_type(
            instance=self, other=other, instance_on_the_right=True,
        )

    def __repr__(self):
        return '<{} ({!r})>'.format(self.__class__.__name__, str(self))

    def __str__(self):
        r"""
        Return a tidied up version of the header value.

        e.g. If the ``header_value`` is ``', \t,de;q=0.000 \t, es;q=1.000, zh,
        jp;q=0.210  ,'``, ``str(instance)`` returns ``'de;q=0, es, zh,
        jp;q=0.21'``.
        """
        return ', '.join(
            _item_qvalue_pair_to_header_element(pair=tuple_)
            for tuple_ in self.parsed
        )

    def _add_instance_and_non_accept_language_type(
        self, instance, other, instance_on_the_right=False,
    ):
        if not other:
            return self.__class__(header_value=instance.header_value)

        other_header_value = self._python_value_to_header_str(value=other)

        try:
            self.parse(value=other_header_value)
        except ValueError:  # invalid header value
            return self.__class__(header_value=instance.header_value)

        new_header_value = (
            (other_header_value + ', ' + instance.header_value)
            if instance_on_the_right
            else (instance.header_value + ', ' + other_header_value)
        )
        return self.__class__(header_value=new_header_value)

    def _old_match(self, mask, item):
        """
        Return whether a language tag matches a language range.

        .. warning::

           This is maintained for backward compatibility, and will be
           deprecated in the future.

        This method was WebOb's old criterion for deciding whether a language
        tag matches a language range, used in

        - :meth:`AcceptLanguageValidHeader.__contains__`
        - :meth:`AcceptLanguageValidHeader.best_match`
        - :meth:`AcceptLanguageValidHeader.quality`

        It does not conform to :rfc:`RFC 7231, section 5.3.5
        <7231#section-5.3.5>`, or any of the matching schemes suggested there.

        :param mask: (``str``)

                     | language range

        :param item: (``str``)

                     | language tag. Subtags in language tags are separated by
                       ``-`` (hyphen). If there are underscores (``_``) in this
                       argument, they will be converted to hyphens before
                       checking the match.

        :return: (``bool``) whether the tag in `item` matches the range in
                 `mask`.

        `mask` and `item` are a match if:

        - ``mask == *``.
        - ``mask == item``.
        - If the first subtag of `item` equals `mask`, or if the first subtag
          of `mask` equals `item`.
          This means that::

              >>> instance._old_match(mask='en-gb', item='en')
              True
              >>> instance._old_match(mask='en', item='en-gb')
              True

          Which is different from any of the matching schemes suggested in
          :rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>`, in that none of
          those schemes match both more *and* less specific tags.

          However, this method appears to be only designed for language tags
          and ranges with at most two subtags. So with an `item`/language tag
          with more than two subtags like ``zh-Hans-CN``::

              >>> instance._old_match(mask='zh', item='zh-Hans-CN')
              True
              >>> instance._old_match(mask='zh-Hans', item='zh-Hans-CN')
              False

          From commit history, this does not appear to have been from a
          decision to match only the first subtag, but rather because only
          language ranges and tags with at most two subtags were expected.
        """
        item = item.replace('_', '-').lower()
        mask = mask.lower()
        return (mask == '*'
            or item == mask
            or item.split('-')[0] == mask
            or item == mask.split('-')[0]
        )

    def basic_filtering(self, language_tags):
        """
        Return the tags that match the header, using Basic Filtering.

        This is an implementation of the Basic Filtering matching scheme,
        suggested as a matching scheme for the ``Accept-Language`` header in
        :rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>`, and defined in
        :rfc:`RFC 4647, section 3.3.1 <4647#section-3.3.1>`. It filters the
        tags in the `language_tags` argument and returns the ones that match
        the header according to the matching scheme.

        :param language_tags: (``iterable``) language tags
        :return: A list of tuples of the form (language tag, qvalue), in
                 descending order of qvalue. If two or more tags have the same
                 qvalue, they are returned in the same order as that in the
                 header of the ranges they matched. If the matched range is the
                 same for two or more tags (i.e. their matched ranges have the
                 same qvalue and the same position in the header), then they
                 are returned in the same order as that in the `language_tags`
                 argument. If `language_tags` is unordered, e.g. if it is a set
                 or a dict, then that order may not be reliable.

        For each tag in `language_tags`:

        1. If the tag matches a non-``*`` language range in the header with
           ``q=0`` (meaning "not acceptable", see :rfc:`RFC 7231, section 5.3.1
           <7231#section-5.3.1>`), the tag is filtered out.
        2. The non-``*`` language ranges in the header that do not have ``q=0``
           are considered in descending order of qvalue; where two or more
           language ranges have the same qvalue, they are considered in the
           order in which they appear in the header.
        3. A language range 'matches a particular language tag if, in a
           case-insensitive comparison, it exactly equals the tag, or if it
           exactly equals a prefix of the tag such that the first character
           following the prefix is "-".' (:rfc:`RFC 4647, section 3.3.1
           <4647#section-3.3.1>`)
        4. If the tag does not match any of the non-``*`` language ranges, and
           there is a ``*`` language range in the header, then if the ``*``
           language range has ``q=0``, the language tag is filtered out,
           otherwise the tag is considered a match.

        (If a range (``*`` or non-``*``) appears in the header more than once
        -- this would not make sense, but is nonetheless a valid header
        according to the RFC -- the first in the header is used for matching,
        and the others are ignored.)
        """
        # The Basic Filtering matching scheme as applied to the Accept-Language
        # header is very under-specified by RFCs 7231 and 4647. This
        # implementation combines the description of the matching scheme in RFC
        # 4647 and the rules of the Accept-Language header in RFC 7231 to
        # arrive at an algorithm for Basic Filtering as applied to the
        # Accept-Language header.

        lowercased_parsed = [
            (range_.lower(), qvalue) for (range_, qvalue) in self.parsed
        ]
        lowercased_tags = [tag.lower() for tag in language_tags]

        not_acceptable_ranges = set()
        acceptable_ranges = dict()
        asterisk_qvalue = None

        for position_in_header, (range_, qvalue) in enumerate(
            lowercased_parsed
        ):
            if range_ == '*':
                if asterisk_qvalue is None:
                    asterisk_qvalue = qvalue
                    asterisk_position = position_in_header
            elif (
                range_ not in acceptable_ranges and range_ not in
                not_acceptable_ranges
                # if we have not already encountered this range in the header
            ):
                if qvalue == 0.0:
                    not_acceptable_ranges.add(range_)
                else:
                    acceptable_ranges[range_] = (qvalue, position_in_header)
        acceptable_ranges = [
            (range_, qvalue, position_in_header)
            for range_, (qvalue, position_in_header)
            in acceptable_ranges.items()
        ]
        # Sort acceptable_ranges by position_in_header, ascending order
        acceptable_ranges.sort(key=lambda tuple_: tuple_[2])
        # Sort acceptable_ranges by qvalue, descending order
        acceptable_ranges.sort(key=lambda tuple_: tuple_[1], reverse=True)
        # Sort guaranteed to be stable with Python >= 2.2, so position in
        # header is tiebreaker when two ranges have the same qvalue

        def match(tag, range_):
            # RFC 4647, section 2.1: 'A language range matches a particular
            # language tag if, in a case-insensitive comparison, it exactly
            # equals the tag, or if it exactly equals a prefix of the tag such
            # that the first character following the prefix is "-".'
            return (tag == range_) or tag.startswith(range_ + '-')
            # We can assume here that the language tags are valid tags, so we
            # do not have to worry about them being malformed and ending with
            # '-'.

        filtered_tags = []
        for index, tag in enumerate(lowercased_tags):
            # If tag matches a non-* range with q=0, it is filtered out
            if any((
                match(tag=tag, range_=range_)
                for range_ in not_acceptable_ranges
            )):
                continue

            matched_range_qvalue = None
            for range_, qvalue, position_in_header in acceptable_ranges:
                # acceptable_ranges is in descending order of qvalue, and tied
                # ranges are in ascending order of position_in_header, so the
                # first range_ that matches the tag is the best match
                if match(tag=tag, range_=range_):
                    matched_range_qvalue = qvalue
                    matched_range_position = position_in_header
                    break
            else:
                if asterisk_qvalue:
                    # From RFC 4647, section 3.3.1: '...HTTP/1.1 [RFC2616]
                    # specifies that the range "*" matches only languages not
                    # matched by any other range within an "Accept-Language"
                    # header.' (Though RFC 2616 is obsolete, and there is no
                    # mention of the meaning of "*" in RFC 7231, as the
                    # ``language-range`` syntax rule in RFC 7231 section 5.3.1
                    # directs us to RFC 4647, we can only assume that the
                    # meaning of "*" in the Accept-Language header remains the
                    # same).
                    matched_range_qvalue = asterisk_qvalue
                    matched_range_position = asterisk_position
            if matched_range_qvalue is not None:  # if there was a match
                filtered_tags.append((
                    language_tags[index], matched_range_qvalue,
                    matched_range_position
                ))

        # sort by matched_range_position, ascending
        filtered_tags.sort(key=lambda tuple_: tuple_[2])
        # When qvalues are tied, matched range position in the header is the
        # tiebreaker.

        # sort by qvalue, descending
        filtered_tags.sort(key=lambda tuple_: tuple_[1], reverse=True)

        return [(item[0], item[1]) for item in filtered_tags]
        # (tag, qvalue), dropping the matched_range_position

        # We return a list of tuples with qvalues, instead of just a set or
        # a list of language tags, because
        # RFC 4647 section 3.3: "If the language priority list contains more
        # than one range, the content returned is typically ordered in
        # descending level of preference, but it MAY be unordered, according to
        # the needs of the application or protocol."
        # We return the filtered tags in order of preference, each paired with
        # the qvalue of the range that was their best match, as the ordering
        # and the qvalues may well be needed in some applications, and a simple
        # set or list of language tags can always be easily obtained from the
        # returned list if the qvalues are not required. One use for qvalues,
        # for example, would be to indicate that two tags are equally preferred
        # (same qvalue), which we would not be able to do easily with a set or
        # a list without e.g. making a member of the set or list a sequence.

    def best_match(self, offers, default_match=None):
        """
        Return the best match from the sequence of language tag `offers`.

        .. warning::

           This is currently maintained for backward compatibility, and will be
           deprecated in the future.

           :meth:`AcceptLanguageValidHeader.best_match` uses its own algorithm
           (one not specified in :rfc:`RFC 7231 <7231>`) to determine what is a
           best match. The algorithm has many issues, and does not conform to
           :rfc:`RFC 7231 <7231>`.

           :meth:`AcceptLanguageValidHeader.lookup` is a possible alternative
           for finding a best match -- it conforms to, and is suggested as a
           matching scheme for the ``Accept-Language`` header in, :rfc:`RFC
           7231, section 5.3.5 <7231#section-5.3.5>` -- but please be aware
           that there are differences in how it determines what is a best
           match. If that is not suitable for the needs of your application,
           you may need to write your own matching using
           :attr:`AcceptLanguageValidHeader.parsed`.

        Each language tag in `offers` is checked against each non-0 range in
        the header. If the two are a match according to WebOb's old criterion
        for a match, the quality value of the match is the qvalue of the
        language range from the header multiplied by the server quality value
        of the offer (if the server quality value is not supplied, it is 1).

        The offer in the match with the highest quality value is the best
        match. If there is more than one match with the highest qvalue, the
        match where the language range has a lower number of '*'s is the best
        match. If the two have the same number of '*'s, the one that shows up
        first in `offers` is the best match.

        :param offers: (iterable)

                       | Each item in the iterable may be a ``str`` language
                         tag, or a (language tag, server quality value)
                         ``tuple`` or ``list``. (The two may be mixed in the
                         iterable.)

        :param default_match: (optional, any type) the value to be returned if
                              there is no match

        :return: (``str``, or the type of `default_match`)

                 | The language tag that is the best match. If there is no
                   match, the value of `default_match` is returned.


        **Issues**:

        - Incorrect tiebreaking when quality values of two matches are the same
          (https://github.com/Pylons/webob/issues/256)::

              >>> header = AcceptLanguageValidHeader(
              ...     header_value='en-gb;q=1, en;q=0.8'
              ... )
              >>> header.best_match(offers=['en', 'en-GB'])
              'en'
              >>> header.best_match(offers=['en-GB', 'en'])
              'en-GB'

              >>> header = AcceptLanguageValidHeader(header_value='en-gb, en')
              >>> header.best_match(offers=['en', 'en-gb'])
              'en'
              >>> header.best_match(offers=['en-gb', 'en'])
              'en-gb'

        - Incorrect handling of ``q=0``::

              >>> header = AcceptLanguageValidHeader(header_value='en;q=0, *')
              >>> header.best_match(offers=['en'])
              'en'

              >>> header = AcceptLanguageValidHeader(header_value='fr, en;q=0')
              >>> header.best_match(offers=['en-gb'], default_match='en')
              'en'

        - Matching only takes into account the first subtag when matching a
          range with more specific or less specific tags::

              >>> header = AcceptLanguageValidHeader(header_value='zh')
              >>> header.best_match(offers=['zh-Hans-CN'])
              'zh-Hans-CN'
              >>> header = AcceptLanguageValidHeader(header_value='zh-Hans')
              >>> header.best_match(offers=['zh-Hans-CN'])
              >>> header.best_match(offers=['zh-Hans-CN']) is None
              True

              >>> header = AcceptLanguageValidHeader(header_value='zh-Hans-CN')
              >>> header.best_match(offers=['zh'])
              'zh'
              >>> header.best_match(offers=['zh-Hans'])
              >>> header.best_match(offers=['zh-Hans']) is None
              True

        """
        warnings.warn(
            'The behavior of AcceptLanguageValidHeader.best_match is '
            'currently being maintained for backward compatibility, but it '
            'will be deprecated in the future as it does not conform to the '
            'RFC.',
            DeprecationWarning,
        )
        best_quality = -1
        best_offer = default_match
        matched_by = '*/*'
        # [We can see that this was written for the ``Accept`` header and not
        # the ``Accept-Language`` header, as there are no '/'s in a valid
        # ``Accept-Language`` header.]
        for offer in offers:
            if isinstance(offer, (tuple, list)):
                offer, server_quality = offer
            else:
                server_quality = 1
            for mask, quality in self._parsed_nonzero:
                possible_quality = server_quality * quality
                if possible_quality < best_quality:
                    continue
                elif possible_quality == best_quality:
                    # 'text/plain' overrides 'message/*' overrides '*/*'
                    # (if all match w/ the same q=)
                    if matched_by.count('*') <= mask.count('*'):
                        continue
                    # [This tiebreaking was written for the `Accept` header. A
                    # basic language range in a valid ``Accept-Language``
                    # header can only be either '*' or a range with no '*' in
                    # it. This happens to work here, but is not sufficient as a
                    # tiebreaker.
                    #
                    # A best match here, given this algorithm uses
                    # self._old_match() which matches both more *and* less
                    # specific tags, should be the match where the absolute
                    # value of the difference between the subtag counts of
                    # `mask` and `offer` is the lowest.]
                if self._old_match(mask, offer):
                    best_quality = possible_quality
                    best_offer = offer
                    matched_by = mask
        return best_offer

    def lookup(
        self, language_tags, default_range=None, default_tag=None,
        default=None,
    ):
        """
        Return the language tag that best matches the header, using Lookup.

        This is an implementation of the Lookup matching scheme,
        suggested as a matching scheme for the ``Accept-Language`` header in
        :rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>`, and described in
        :rfc:`RFC 4647, section 3.4 <4647#section-3.4>`.

        Each language range in the header is considered in turn, by descending
        order of qvalue; where qvalues are tied, ranges are considered from
        left to right.

        Each language range in the header represents the most specific tag that
        is an acceptable match: Lookup progressively truncates subtags from the
        end of the range until a matching language tag is found. An example is
        given in :rfc:`RFC 4647, section 3.4 <4647#section-3.4>`, under
        "Example of a Lookup Fallback Pattern":

        ::

            Range to match: zh-Hant-CN-x-private1-private2
            1. zh-Hant-CN-x-private1-private2
            2. zh-Hant-CN-x-private1
            3. zh-Hant-CN
            4. zh-Hant
            5. zh
            6. (default)

        :param language_tags: (``iterable``) language tags

        :param default_range: (optional, ``None`` or ``str``)

                              | If Lookup finds no match using the ranges in
                                the header, and this argument is not None,
                                Lookup will next attempt to match the range in
                                this argument, using the same subtag
                                truncation.

                              | `default_range` cannot be '*', as '*' is
                                skipped in Lookup. See :ref:`note
                                <acceptparse-lookup-asterisk-note>`.

                              | This parameter corresponds to the functionality
                                described in :rfc:`RFC 4647, section 3.4.1
                                <4647#section-3.4.1>`, in the paragraph
                                starting with "One common way to provide for a
                                default is to allow a specific language range
                                to be set as the default..."

        :param default_tag: (optional, ``None`` or ``str``)

                            | At least one of `default_tag` or `default` must
                              be supplied as an argument to the method, to
                              define the defaulting behaviour.

                            | If Lookup finds no match using the ranges in the
                              header and `default_range`, this argument is not
                              ``None``, and it does not match any range in the
                              header with ``q=0`` (exactly, with no subtag
                              truncation), then this value is returned.

                            | This parameter corresponds to "return a
                              particular language tag designated for the
                              operation", one of the examples of "defaulting
                              behavior" described in :rfc:`RFC 4647, section
                              3.4.1 <4647#section-3.4.1>`.

        :param default: (optional, ``None`` or any type, including a callable)

                        | At least one of `default_tag` or `default` must be
                          supplied as an argument to the method, to define the
                          defaulting behaviour.

                        | If Lookup finds no match using the ranges in the
                          header and `default_range`, and `default_tag` is
                          ``None`` or not acceptable because it matches a
                          ``q=0`` range in the header, then Lookup will next
                          examine the `default` argument.

                        | If `default` is a callable, it will be called, and
                          the callable's return value will be returned.

                        | If `default` is not a callable, the value itself will
                          be returned.

                        | The difference between supplying a ``str`` to
                          `default_tag` and `default` is that `default_tag` is
                          checked against ``q=0`` ranges in the header to see
                          if it matches one of the ranges specified as not
                          acceptable, whereas a ``str`` for the `default`
                          argument is simply returned.

                        | This parameter corresponds to the "defaulting
                          behavior" described in :rfc:`RFC 4647, section 3.4.1
                          <4647#section-3.4.1>`

        :return: (``str``, ``None``, or any type)

                 | The best match according to the Lookup matching scheme, or a
                   return value from one of the default arguments.

        **Notes**:

        .. _acceptparse-lookup-asterisk-note:

        - Lookup's behaviour with '*' language ranges in the header may be
          surprising. From :rfc:`RFC 4647, section 3.4 <4647#section-3.4>`:

              In the lookup scheme, this range does not convey enough
              information by itself to determine which language tag is most
              appropriate, since it matches everything.  If the language range
              "*" is followed by other language ranges, it is skipped.  If the
              language range "*" is the only one in the language priority list
              or if no other language range follows, the default value is
              computed and returned.

          So

          ::

              >>> header = AcceptLanguageValidHeader('de, zh, *')
              >>> header.lookup(language_tags=['ja', 'en'], default='default')
              'default'

        - Any tags in `language_tags` and `default_tag` and any tag matched
          during the subtag truncation search for `default_range`, that are an
          exact match for a non-``*`` range with ``q=0`` in the header, are
          considered not acceptable and ruled out.

        - If there is a ``*;q=0`` in the header, then `default_range` and
          `default_tag` have no effect, as ``*;q=0`` means that all languages
          not already matched by other ranges within the header are
          unacceptable.
        """
        if default_tag is None and default is None:
            raise TypeError(
                '`default_tag` and `default` arguments cannot both be None.'
            )

        # We need separate `default_tag` and `default` arguments because if we
        # only had the `default` argument, there would be no way to tell
        # whether a str is a language tag (in which case we have to check
        # whether it has been specified as not acceptable with a q=0 range in
        # the header) or not (in which case we can just return the value).

        if default_range == '*':
            raise ValueError('default_range cannot be *.')

        parsed = list(self.parsed)

        tags = language_tags
        not_acceptable_ranges = []
        acceptable_ranges = []

        asterisk_non0_found = False
        # Whether there is a '*' range in the header with q={not 0}

        asterisk_q0_found = False
        # Whether there is a '*' range in the header with q=0
        # While '*' is skipped in Lookup because it "does not convey enough
        # information by itself to determine which language tag is most
        # appropriate" (RFC 4647, section 3.4), '*;q=0' is clear in meaning:
        # languages not matched by any other range within the header are not
        # acceptable.

        for range_, qvalue in parsed:
            if qvalue == 0.0:
                if range_ == '*':  # *;q=0
                    asterisk_q0_found = True
                else:  # {non-* range};q=0
                    not_acceptable_ranges.append(range_.lower())
            elif not asterisk_q0_found and range_ == '*':  # *;q={not 0}
                asterisk_non0_found = True
                # if asterisk_q0_found, then it does not matter whether
                # asterisk_non0_found
            else:  # {non-* range};q={not 0}
                acceptable_ranges.append((range_, qvalue))
        # Sort acceptable_ranges by qvalue, descending order
        acceptable_ranges.sort(key=lambda tuple_: tuple_[1], reverse=True)
        # Sort guaranteed to be stable with Python >= 2.2, so position in
        # header is tiebreaker when two ranges have the same qvalue

        acceptable_ranges = [tuple_[0] for tuple_ in acceptable_ranges]
        lowered_tags = [tag.lower() for tag in tags]

        def best_match(range_):
            subtags = range_.split('-')
            while True:
                for index, tag in enumerate(lowered_tags):
                    if tag in not_acceptable_ranges:
                        continue
                        # We think a non-'*' range with q=0 represents only
                        # itself as a tag, and there should be no falling back
                        # with subtag truncation. For example, with
                        # 'en-gb;q=0', it should not mean 'en;q=0': the client
                        # is unlikely to expect that specifying 'en-gb' as not
                        # acceptable would mean that 'en' is also not
                        # acceptable. There is no guidance on this at all in
                        # the RFCs, so it is left to us to decide how it should
                        # work.

                    if tag == range_:
                        return tags[index]  # return the pre-lowered tag

                try:
                    subtag_before_this = subtags[-2]
                except IndexError:  # len(subtags) == 1
                    break
                # len(subtags) >= 2
                if len(subtag_before_this) == 1 and (
                    subtag_before_this.isdigit() or
                    subtag_before_this.isalpha()
                ):  # if subtag_before_this is a single-letter or -digit subtag
                    subtags.pop(-1)  # pop twice instead of once
                subtags.pop(-1)
                range_ = '-'.join(subtags)

        for range_ in acceptable_ranges:
            match = best_match(range_=range_.lower())
            if match is not None:
                return match

        if not asterisk_q0_found:
            if default_range is not None:
                lowered_default_range = default_range.lower()
                match = best_match(range_=lowered_default_range)
                if match is not None:
                    return match

            if default_tag is not None:
                lowered_default_tag = default_tag.lower()
                if lowered_default_tag not in not_acceptable_ranges:
                    return default_tag

        try:
            return default()
        except TypeError:  # default is not a callable
            return default

    def quality(self, offer):
        """
        Return quality value of given offer, or ``None`` if there is no match.

        .. warning::

           This is currently maintained for backward compatibility, and will be
           deprecated in the future.

           :meth:`AcceptLanguageValidHeader.quality` uses its own algorithm
           (one not specified in :rfc:`RFC 7231 <7231>`) to determine what is a
           best match. The algorithm has many issues, and does not conform to
           :rfc:`RFC 7231 <7231>`.

           What should be considered a match depends on the needs of your
           application (for example, should a language range in the header
           match a more specific language tag offer, or a less specific tag
           offer?) :rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>` suggests
           three matching schemes from :rfc:`RFC 4647 <4647>`, two of which
           WebOb supports with
           :meth:`AcceptLanguageValidHeader.basic_filtering` and
           :meth:`AcceptLanguageValidHeader.lookup` (we interpret the RFC to
           mean that Extended Filtering cannot apply for the
           ``Accept-Language`` header, as the header only accepts basic
           language ranges.) :meth:`AcceptLanguageValidHeader.basic_filtering`
           returns quality values with the matched language tags.
           :meth:`AcceptLanguageValidHeader.lookup` returns a language tag
           without the quality value, but the quality value is less likely to
           be useful when we are looking for a best match.

           If these are not suitable or sufficient for the needs of your
           application, you may need to write your own matching using
           :attr:`AcceptLanguageValidHeader.parsed`.

        :param offer: (``str``) language tag offer
        :return: (``float`` or ``None``)

                 | The highest quality value from the language range(s) that
                   match the `offer`, or ``None`` if there is no match.


        **Issues**:

        - Incorrect handling of ``q=0`` and ``*``::

              >>> header = AcceptLanguageValidHeader(header_value='en;q=0, *')
              >>> header.quality(offer='en')
              1.0

        - Matching only takes into account the first subtag when matching a
          range with more specific or less specific tags::

              >>> header = AcceptLanguageValidHeader(header_value='zh')
              >>> header.quality(offer='zh-Hans-CN')
              1.0
              >>> header = AcceptLanguageValidHeader(header_value='zh-Hans')
              >>> header.quality(offer='zh-Hans-CN')
              >>> header.quality(offer='zh-Hans-CN') is None
              True

              >>> header = AcceptLanguageValidHeader(header_value='zh-Hans-CN')
              >>> header.quality(offer='zh')
              1.0
              >>> header.quality(offer='zh-Hans')
              >>> header.quality(offer='zh-Hans') is None
              True

        """
        warnings.warn(
            'The behavior of AcceptLanguageValidHeader.quality is'
            'currently being maintained for backward compatibility, but it '
            'will be deprecated in the future as it does not conform to the '
            'RFC.',
            DeprecationWarning,
        )
        bestq = 0
        for mask, q in self.parsed:
            if self._old_match(mask, offer):
                bestq = max(bestq, q)
        return bestq or None


class _AcceptLanguageInvalidOrNoHeader(AcceptLanguage):
    """
    Represent when an ``Accept-Language`` header is invalid or not in request.

    This is the base class for the behaviour that
    :class:`.AcceptLanguageInvalidHeader` and :class:`.AcceptLanguageNoHeader`
    have in common.

    :rfc:`7231` does not provide any guidance on what should happen if the
    ``Accept-Language`` header has an invalid value. This implementation
    disregards the header when the header is invalid, so
    :class:`.AcceptLanguageInvalidHeader` and :class:`.AcceptLanguageNoHeader`
    have much behaviour in common.
    """

    def __nonzero__(self):
        """
        Return whether ``self`` represents a valid ``Accept-Language`` header.

        Return ``True`` if ``self`` represents a valid header, and ``False`` if
        it represents an invalid header, or the header not being in the
        request.

        For this class, it always returns ``False``.
        """
        return False
    __bool__ = __nonzero__  # Python 3

    def __contains__(self, offer):
        """
        Return ``bool`` indicating whether `offer` is acceptable.

        .. warning::

           The behavior of ``.__contains__`` for the ``AcceptLanguage`` classes
           is currently being maintained for backward compatibility, but it
           will change in the future to better conform to the RFC.

        :param offer: (``str``) language tag offer
        :return: (``bool``) Whether ``offer`` is acceptable according to the
                 header.

        For this class, either there is no ``Accept-Language`` header in the
        request, or the header is invalid, so any language tag is acceptable,
        and this always returns ``True``.
        """
        warnings.warn(
            'The behavior of .__contains__ for the AcceptLanguage classes is '
            'currently being maintained for backward compatibility, but it '
            'will change in the future to better conform to the RFC.',
            DeprecationWarning,
        )
        return True

    def __iter__(self):
        """
        Return all the ranges with non-0 qvalues, in order of preference.

        .. warning::

           The behavior of this method is currently maintained for backward
           compatibility, but will change in the future.

        :return: iterator of all the language ranges in the header with non-0
                 qvalues, in descending order of qvalue. If two ranges have the
                 same qvalue, they are returned in the order of their positions
                 in the header, from left to right.

        For this class, either there is no ``Accept-Language`` header in the
        request, or the header is invalid, so there are no language ranges, and
        this always returns an empty iterator.
        """
        warnings.warn(
            'The behavior of AcceptLanguageValidHeader.__iter__ is currently '
            'maintained for backward compatibility, but will change in the '
            'future.',
            DeprecationWarning,
        )
        return iter(())

    def basic_filtering(self, language_tags):
        """
        Return the tags that match the header, using Basic Filtering.

        :param language_tags: (``iterable``) language tags
        :return: A list of tuples of the form (language tag, qvalue), in
                 descending order of preference.

        When the header is invalid and when the header is not in the request,
        there are no matches, so this method always returns an empty list.
        """
        return []

    def best_match(self, offers, default_match=None):
        """
        Return the best match from the sequence of language tag `offers`.

        This is the ``.best_match()`` method for when the header is invalid or
        not found in the request, corresponding to
        :meth:`AcceptLanguageValidHeader.best_match`.

        .. warning::

           This is currently maintained for backward compatibility, and will be
           deprecated in the future (see the documentation for
           :meth:`AcceptLanguageValidHeader.best_match`).

        When the header is invalid, or there is no `Accept-Language` header in
        the request, any of the language tags in `offers` are considered
        acceptable, so the best match is the tag in `offers` with the highest
        server quality value (if the server quality value is not supplied, it
        is 1).

        If more than one language tags in `offers` have the same highest server
        quality value, then the one that shows up first in `offers` is the best
        match.

        :param offers: (iterable)

                       | Each item in the iterable may be a ``str`` language
                         tag, or a (language tag, server quality value)
                         ``tuple`` or ``list``. (The two may be mixed in the
                         iterable.)

        :param default_match: (optional, any type) the value to be returned if
                              `offers` is empty.

        :return: (``str``, or the type of `default_match`)

                 | The language tag that has the highest server quality value.
                   If `offers` is empty, the value of `default_match` is
                   returned.
        """
        warnings.warn(
            'The behavior of .best_match for the AcceptLanguage classes is '
            'currently being maintained for backward compatibility, but the '
            'method will be deprecated in the future, as its behavior is not '
            'specified in (and currently does not conform to) RFC 7231.',
            DeprecationWarning,
        )
        best_quality = -1
        best_offer = default_match
        for offer in offers:
            if isinstance(offer, (list, tuple)):
                offer, quality = offer
            else:
                quality = 1
            if quality > best_quality:
                best_offer = offer
                best_quality = quality
        return best_offer

    def lookup(
        self, language_tags=None, default_range=None, default_tag=None,
        default=None,
    ):
        """
        Return the language tag that best matches the header, using Lookup.

        When the header is invalid, or there is no ``Accept-Language`` header
        in the request, all language tags are considered acceptable, so it is
        as if the header is '*'. As specified for the Lookup matching scheme in
        :rfc:`RFC 4647, section 3.4 <4647#section-3.4>`, when the header is
        '*', the default value is to be computed and returned. So this method
        will ignore the `language_tags` and `default_range` arguments, and
        proceed to `default_tag`, then `default`.

        :param language_tags: (optional, any type)

                              | This argument is ignored, and is only used as a
                                placeholder so that the method signature
                                corresponds to that of
                                :meth:`AcceptLanguageValidHeader.lookup`.

        :param default_range: (optional, any type)

                              | This argument is ignored, and is only used as a
                                placeholder so that the method signature
                                corresponds to that of
                                :meth:`AcceptLanguageValidHeader.lookup`.

        :param default_tag: (optional, ``None`` or ``str``)

                            | At least one of `default_tag` or `default` must
                              be supplied as an argument to the method, to
                              define the defaulting behaviour.

                            | If this argument is not ``None``, then it is
                              returned.

                            | This parameter corresponds to "return a
                              particular language tag designated for the
                              operation", one of the examples of "defaulting
                              behavior" described in :rfc:`RFC 4647, section
                              3.4.1 <4647#section-3.4.1>`.

        :param default: (optional, ``None`` or any type, including a callable)

                        | At least one of `default_tag` or `default` must be
                          supplied as an argument to the method, to define the
                          defaulting behaviour.

                        | If `default_tag` is ``None``, then Lookup will next
                          examine the `default` argument.

                        | If `default` is a callable, it will be called, and
                          the callable's return value will be returned.

                        | If `default` is not a callable, the value itself will
                          be returned.

                        | This parameter corresponds to the "defaulting
                          behavior" described in :rfc:`RFC 4647, section 3.4.1
                          <4647#section-3.4.1>`

        :return: (``str``, or any type)

                 | the return value from `default_tag` or `default`.
        """
        if default_tag is None and default is None:
            raise TypeError(
                '`default_tag` and `default` arguments cannot both be None.'
            )

        if default_tag is not None:
            return default_tag

        try:
            return default()
        except TypeError:  # default is not a callable
            return default

    def quality(self, offer):
        """
        Return quality value of given offer, or ``None`` if there is no match.

        This is the ``.quality()`` method for when the header is invalid or not
        found in the request, corresponding to
        :meth:`AcceptLanguageValidHeader.quality`.

        .. warning::

           This is currently maintained for backward compatibility, and will be
           deprecated in the future (see the documentation for
           :meth:`AcceptLanguageValidHeader.quality`).

        :param offer: (``str``) language tag offer
        :return: (``float``) ``1.0``.

        When the ``Accept-Language`` header is invalid or not in the request,
        all offers are equally acceptable, so 1.0 is always returned.
        """
        warnings.warn(
            'The behavior of .quality for the AcceptLanguage classes is '
            'currently being maintained for backward compatibility, but the '
            'method will be deprecated in the future, as its behavior is not '
            'specified in (and currently does not conform to) RFC 7231.',
            DeprecationWarning,
        )
        return 1.0


class AcceptLanguageNoHeader(_AcceptLanguageInvalidOrNoHeader):
    """
    Represent when there is no ``Accept-Language`` header in the request.

    This object should not be modified. To add to the header, we can use the
    addition operators (``+`` and ``+=``), which return a new object (see the
    docstring for :meth:`AcceptLanguageNoHeader.__add__`).
    """

    def __init__(self):
        """
        Create an :class:`AcceptLanguageNoHeader` instance.
        """
        self._header_value = None
        self._parsed = None
        self._parsed_nonzero = None

    @property
    def header_value(self):
        """
        (``str`` or ``None``) The header value.

        As there is no header in the request, this is ``None``.
        """
        return self._header_value

    @property
    def parsed(self):
        """
        (``list`` or ``None``) Parsed form of the header.

        As there is no header in the request, this is ``None``.
        """
        return self._parsed

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * ``None``
        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``\ s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``\ s and pairs can be
          mixed within the ``tuple`` or ``list``)
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance
        * object of any other type that returns a value for ``__str__``

        If `other` is a valid header value or an
        :class:`AcceptLanguageValidHeader` instance, a new
        :class:`AcceptLanguageValidHeader` instance with the valid header value
        is returned.

        If `other` is ``None``, an :class:`AcceptLanguageNoHeader` instance, an
        invalid header value, or an :class:`AcceptLanguageInvalidHeader`
        instance, a new :class:`AcceptLanguageNoHeader` instance is returned.
        """
        if isinstance(other, AcceptLanguageValidHeader):
            return AcceptLanguageValidHeader(header_value=other.header_value)

        if isinstance(
            other, (AcceptLanguageNoHeader, AcceptLanguageInvalidHeader)
        ):
            return self.__class__()

        return self._add_instance_and_non_accept_language_type(
            instance=self, other=other,
        )

    def __radd__(self, other):
        """
        Add to header, creating a new header object.

        See the docstring for :meth:`AcceptLanguageNoHeader.__add__`.
        """
        return self.__add__(other=other)

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def __str__(self):
        """Return the ``str`` ``'<no header in request>'``."""
        return '<no header in request>'

    def _add_instance_and_non_accept_language_type(self, instance, other):
        if not other:
            return self.__class__()

        other_header_value = self._python_value_to_header_str(value=other)

        try:
            return AcceptLanguageValidHeader(header_value=other_header_value)
        except ValueError:  # invalid header value
            return self.__class__()


class AcceptLanguageInvalidHeader(_AcceptLanguageInvalidOrNoHeader):
    """
    Represent an invalid ``Accept-Language`` header.

    An invalid header is one that does not conform to
    :rfc:`7231#section-5.3.5`. As specified in the RFC, an empty header is an
    invalid ``Accept-Language`` header.

    :rfc:`7231` does not provide any guidance on what should happen if the
    ``Accept-Language`` header has an invalid value. This implementation
    disregards the header, and treats it as if there is no ``Accept-Language``
    header in the request.

    This object should not be modified. To add to the header, we can use the
    addition operators (``+`` and ``+=``), which return a new object (see the
    docstring for :meth:`AcceptLanguageInvalidHeader.__add__`).
    """

    def __init__(self, header_value):
        """
        Create an :class:`AcceptLanguageInvalidHeader` instance.
        """
        self._header_value = header_value
        self._parsed = None
        self._parsed_nonzero = None

    @property
    def header_value(self):
        """(``str`` or ``None``) The header value."""
        return self._header_value

    @property
    def parsed(self):
        """
        (``list`` or ``None``) Parsed form of the header.

        As the header is invalid and cannot be parsed, this is ``None``.
        """
        return self._parsed

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * ``None``
        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``\ s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``\ s and pairs can
          be mixed within the ``tuple`` or ``list``)
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance
        * object of any other type that returns a value for ``__str__``

        If `other` is a valid header value or an
        :class:`AcceptLanguageValidHeader` instance, a new
        :class:`AcceptLanguageValidHeader` instance with the valid header value
        is returned.

        If `other` is ``None``, an :class:`AcceptLanguageNoHeader` instance, an
        invalid header value, or an :class:`AcceptLanguageInvalidHeader`
        instance, a new :class:`AcceptLanguageNoHeader` instance is returned.
        """
        if isinstance(other, AcceptLanguageValidHeader):
            return AcceptLanguageValidHeader(header_value=other.header_value)

        if isinstance(
            other, (AcceptLanguageNoHeader, AcceptLanguageInvalidHeader)
        ):
            return AcceptLanguageNoHeader()

        return self._add_instance_and_non_accept_language_type(
            instance=self, other=other,
        )

    def __radd__(self, other):
        """
        Add to header, creating a new header object.

        See the docstring for :meth:`AcceptLanguageValidHeader.__add__`.
        """
        return self._add_instance_and_non_accept_language_type(
            instance=self, other=other, instance_on_the_right=True,
        )

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)
        # We do not display the header_value, as it is untrusted input. The
        # header_value could always be easily obtained from the .header_value
        # property.

    def __str__(self):
        """Return the ``str`` ``'<invalid header value>'``."""
        return '<invalid header value>'

    def _add_instance_and_non_accept_language_type(
        self, instance, other, instance_on_the_right=False,
    ):
        if not other:
            return AcceptLanguageNoHeader()

        other_header_value = self._python_value_to_header_str(value=other)

        try:
            return AcceptLanguageValidHeader(header_value=other_header_value)
        except ValueError:  # invalid header value
            return AcceptLanguageNoHeader()


def create_accept_language_header(header_value):
    """
    Create an object representing the ``Accept-Language`` header in a request.

    :param header_value: (``str``) header value
    :return: If `header_value` is ``None``, an :class:`AcceptLanguageNoHeader`
             instance.

             | If `header_value` is a valid ``Accept-Language`` header, an
               :class:`AcceptLanguageValidHeader` instance.

             | If `header_value` is an invalid ``Accept-Language`` header, an
               :class:`AcceptLanguageInvalidHeader` instance.
    """
    if header_value is None:
        return AcceptLanguageNoHeader()
    try:
        return AcceptLanguageValidHeader(header_value=header_value)
    except ValueError:
        return AcceptLanguageInvalidHeader(header_value=header_value)


def accept_language_property():
    doc = """
        Property representing the ``Accept-Language`` header.

        (:rfc:`RFC 7231, section 5.3.5 <7231#section-5.3.5>`)

        The header value in the request environ is parsed and a new object
        representing the header is created every time we *get* the value of the
        property. (*set* and *del* change the header value in the request
        environ, and do not involve parsing.)
    """

    ENVIRON_KEY = 'HTTP_ACCEPT_LANGUAGE'

    def fget(request):
        """Get an object representing the header in the request."""
        return create_accept_language_header(
            header_value=request.environ.get(ENVIRON_KEY)
        )

    def fset(request, value):
        """
        Set the corresponding key in the request environ.

        `value` can be:

        * ``None``
        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``\ s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``\ s and pairs can
          be mixed within the ``tuple`` or ``list``)
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance
        * object of any other type that returns a value for ``__str__``
        """
        if value is None or isinstance(value, AcceptLanguageNoHeader):
            fdel(request=request)
        else:
            if isinstance(
                value, (AcceptLanguageValidHeader, AcceptLanguageInvalidHeader)
            ):
                header_value = value.header_value
            else:
                header_value = AcceptLanguage._python_value_to_header_str(
                    value=value,
                )
            request.environ[ENVIRON_KEY] = header_value

    def fdel(request):
        """Delete the corresponding key from the request environ."""
        try:
            del request.environ[ENVIRON_KEY]
        except KeyError:
            pass

    return property(fget, fset, fdel, textwrap.dedent(doc))


class MIMEAccept(Accept):
    """
    Represents an ``Accept`` header, which is a list of mimetypes.

    This class knows about mime wildcards, like ``image/*``
    """
    @staticmethod
    def parse(value):
        """
        Parse ``Accept`` header.

        Return iterator of ``(media range, qvalue)`` pairs.
        """
        for mask, q in Accept.parse(value):
            try:
                mask_major, mask_minor = [x.lower() for x in mask.split('/')]
            except ValueError:
                continue
            if mask_major == '*' and mask_minor != '*':
                continue
            if mask_major != "*" and "*" in mask_major:
                continue
            if mask_minor != "*" and "*" in mask_minor:
                continue
            yield ("%s/%s" % (mask_major, mask_minor), q)

    def accept_html(self):
        """
        Returns true if any HTML-like type is accepted
        """
        return ('text/html' in self
                or 'application/xhtml+xml' in self
                or 'application/xml' in self
                or 'text/xml' in self)

    accepts_html = property(accept_html) # note the plural

    def _match(self, mask, offer):
        """
            Check if the offer is covered by the mask

            ``offer`` may contain wildcards to facilitate checking if a
            ``mask`` would match a 'permissive' offer.

            Wildcard matching forces the match to take place against the
            type or subtype of the mask and offer (depending on where
            the wildcard matches)
        """
        # Match if comparisons are the same or either is a complete wildcard
        if (mask.lower() == offer.lower() or
                '*/*' in (mask, offer) or
                '*' == offer):
            return True

        # Set mask type with wildcard subtype for malformed masks
        try:
            mask_type, mask_subtype = [x.lower() for x in mask.split('/')]
        except ValueError:
            mask_type = mask
            mask_subtype = '*'

        # Set offer type with wildcard subtype for malformed offers
        try:
            offer_type, offer_subtype = [x.lower() for x in offer.split('/')]
        except ValueError:
            offer_type = offer
            offer_subtype = '*'

        if mask_subtype == '*':
            # match on type only
            if offer_type == '*':
                return True
            else:
                return mask_type.lower() == offer_type.lower()

        if mask_type == '*':
            # match on subtype only
            if offer_subtype == '*':
                return True
            else:
                return mask_subtype.lower() == offer_subtype.lower()

        if offer_subtype == '*':
            # match on type only
            return mask_type.lower() == offer_type.lower()

        if offer_type == '*':
            # match on subtype only
            return mask_subtype.lower() == offer_subtype.lower()

        return offer.lower() == mask.lower()



class MIMENilAccept(NilAccept):
    """
    Represents an ``Accept`` header when it is not present in the request or is
    empty.
    """
    MasterClass = MIMEAccept

def _check_offer(offer):
    if '*' in offer:
        raise ValueError("The application should offer specific types, got %r" % offer)


def accept_property(header, rfc_section,
    AcceptClass=Accept, NilClass=NilAccept
):
    key = header_to_key(header)
    doc = header_docstring(header, rfc_section)
    # doc += "  Converts it as a %s." % convert_name
    def fget(req):
        value = req.environ.get(key)
        if not value:
            return NilClass()
        return AcceptClass(value)
    def fset(req, val):
        if val:
            if isinstance(val, (list, tuple, dict)):
                val = AcceptClass('') + val
            val = str(val)
        req.environ[key] = val or None
    def fdel(req):
        del req.environ[key]
    return property(fget, fset, fdel, doc)
