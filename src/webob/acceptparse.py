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

# RFC 7231 Section 5.3.1 "Quality Values"
# qvalue = ( "0" [ "." 0*3DIGIT ] )
#        / ( "1" [ "." 0*3("0") ] )
qvalue_re = r"""
    (?:0(?:\.[0-9]{0,3})?)
    |
    (?:1(?:\.0{0,3})?)
    """
# weight = OWS ";" OWS "q=" qvalue
weight_re = r'[ \t]*;[ \t]*[qQ]=(' + qvalue_re + r')'


def _item_qvalue_pair_to_header_element(pair):
    item, qvalue = pair
    if qvalue == 1.0:
        element = item
    elif qvalue == 0.0:
        element = '{};q=0'.format(item)
    else:
        element = '{};q={}'.format(item, qvalue)
    return element


class Accept(object):
    """
    Represents a generic ``Accept-*`` style header.

    This object should not be modified.  To add items you can use
    ``accept_obj + 'accept_thing'`` to get a new object
    """

    def __init__(self, header_value):
        self.header_value = header_value
        self.parsed = list(self.parse(header_value))
        self._parsed_nonzero = [(m,q) for (m,q) in self.parsed if q]

    @staticmethod
    def parse(value):
        """
        Parse ``Accept-*`` style header.

        Return iterator of ``(value, quality)`` pairs.
        ``quality`` defaults to 1.
        """
        for match in part_re.finditer(','+value):
            name = match.group(1)
            if name == 'q':
                continue
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

    def quality(self, offer, modifier=1):
        """
        Return the quality of the given offer.  Returns None if there
        is no match (not 0).
        """
        bestq = 0
        for mask, q in self.parsed:
            if self._match(mask, offer):
                bestq = max(bestq, q * modifier)
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

    def quality(self, offer, default_quality=1):
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


class AcceptEncoding(Accept):
    """
    Represents an ``Accept-Encoding`` header.
    """


class AcceptLanguage(object):
    """
    Represent an ``Accept-Language`` header.

    Base class for :class:`AcceptLanguageValidHeader`,
    :class:`AcceptLanguageNoHeader`, and :class:`AcceptLanguageInvalidHeader`.
    """


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

    # RFC 7231 Section 5.3.5 "Accept-Language":
    # Accept-Language = 1#( language-range [ weight ] )
    # language-range  =
    #           <language-range, see [RFC4647], Section 2.1>
    # RFC 4647 Section 2.1 "Basic Language Range":
    # language-range   = (1*8ALPHA *("-" 1*8alphanum)) / "*"
    # alphanum         = ALPHA / DIGIT
    lang_range_re = r"""
        \*|
        (?:
        [A-Za-z]{1,8}
        (?:-[A-Za-z0-9]{1,8})*
        )
    """
    lang_range_n_weight_re = r'(' + lang_range_re + r')(?:' + weight_re + r')?'
    lang_range_n_weight_compiled_re = re.compile(
        lang_range_n_weight_re,
        re.VERBOSE
    )
    # RFC 7230 Section 7 "ABNF List Extension: #rule":
    # 1#element => *( "," OWS ) element *( OWS "," [ OWS element ] )
    # and RFC 7230 Errata ID: 4169
    accept_language_compiled_re = re.compile(
        r'^(?:,[ \t]*)*' + lang_range_n_weight_re +
        r'(?:[ \t]*,(?:[ \t]*' + lang_range_n_weight_re + r')?)*$',
        re.VERBOSE
    )

    def __init__(self, header_value):
        """
        Create an :class:`AcceptLanguageValidHeader` instance.

        :param header_value: (``str``) header value.
        :raises ValueError: if `header_value` is an invalid value for an
                            ``Accept-Language`` header.
        """
        self.header_value = header_value
        """(``str``) The header value."""

        self.parsed = list(self.parse(header_value))
        """(``list``) Parsed form of the header: a list of (language range,
        quality value) tuples."""

        self._parsed_nonzero = [(m, q) for (m, q) in self.parsed if q]

    @classmethod
    def parse(cls, value):
        """
        Parse an ``Accept-Language`` header.

        :param value: (``str``) header value
        :return: If `value` is a valid ``Accept-Language`` header, returns a
                 generator that yields (language range, quality value) tuples,
                 as parsed from the header from left to right.
        :raises ValueError: if `value` is an invalid header
        """
        # Check if header is valid
        # Using Python stdlib's `re` module, there is currently no way to check
        # the match *and* get all the groups using the same regex, so we have
        # to use one regex to check the match, and another to get the groups.
        if cls.accept_language_compiled_re.match(value) is None:
            raise ValueError  # invalid header
        else:
            def generator(value):
                for match in (
                    cls.lang_range_n_weight_compiled_re.finditer(value)
                ):
                    lang_range = match.group(1)
                    qvalue = match.group(2)
                    qvalue = float(qvalue) if qvalue else 1.0
                    yield (lang_range, qvalue)
            return generator(value=value)

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``s and pairs can be
          mixed within the ``tuple`` or ``list``)
        * any object that returns a value for `__str__`
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance

        If neither operands are empty (header value ``''``) or
        ``None``/:class:`AcceptLanguageNoHeader`, the two header values are
        joined with ``', '``.
        """
        if isinstance(other, AcceptLanguageNoHeader):
            return self.__class__(header_value=self.header_value)

        if isinstance(other, AcceptLanguageValidHeader):
            return create_accept_language_header(
                header_value=self.header_value + ', ' + other.header_value,
            )

        if isinstance(other, AcceptLanguageInvalidHeader):
            if other.header_value == '':
                return self.__class__(header_value=self.header_value)
            return create_accept_language_header(
                header_value=self.header_value + ', ' + other.header_value,
            )

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
           currently being maintained for backward compatibility, but it may
           change in future to better conform to the RFC.

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
            'The behavior of AcceptLanguageValidHeader.__contains__ is'
            'currently being maintained for backward compatibility, but it may'
            ' change in future to better conform to the RFC.',
            PendingDeprecationWarning,
        )
        for mask, quality in self._parsed_nonzero:
            if self._old_match(mask, offer):
                return True
        return False

    def __iter__(self):
        """
        Return all the ranges with non-0 qvalues, in order of preference.

        :return: iterator of all the language ranges in the header with non-0
                 qvalues, in descending order of qvalue. If two ranges have the
                 same qvalue, they are returned in the order of their positions
                 in the header, from left to right.

        Please note that this is a simple filter for the ranges in the header
        with non-0 qvalues, and is not necessarily the same as what the client
        prefers, e.g. ``'en-gb;q=0, *'`` means 'everything but British
        English', but ``list(instance)`` would return only ``['*']``.
        """
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
        return "{}(header_value={!r})".format(
            # ``!r`` escapes the header value
            self.__class__.__name__,
            self.header_value,
        )

    def __str__(self):
        """
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

        if isinstance(other, str):
            other_header_value = other
        else:
            if hasattr(other, 'items'):
                other = sorted(
                    other.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            if isinstance(other, (tuple, list)):
                result = []
                for element in other:
                    if isinstance(element, (tuple, list)):
                        element = _item_qvalue_pair_to_header_element(
                            pair=element
                        )
                    result.append(element)
                other_header_value = ', '.join(result)
            else:
                other_header_value = str(other)
                if other_header_value == '':
                    return self.__class__(header_value=instance.header_value)

        new_header_value = (
            (other_header_value + ', ' + instance.header_value)
            if instance_on_the_right
            else (instance.header_value + ', ' + other_header_value)
        )

        return create_accept_language_header(header_value=new_header_value)

    def _old_match(self, mask, item):
        """
        Return whether a language tag matches a language range.

        .. warning::

           This is maintained for backward compatibility, and may be deprecated
           in future.

        This method was WebOb's old criteron for deciding whether a language
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

              >>> instance._match(mask='zh', item='zh-Hans-CN')
              True
              >>> instance._match(mask='zh-Hans', item='zh-Hans-CN')
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
        tags in the `language_tags` argument, and returns a list of the tags
        that match the language ranges in the header according to the Basic
        Filtering matching scheme, in descending order of preference, together
        with the qvalue of the range each tag matched.

        :param language_tags: (``iterable``) language tags
        :return: A list of tuples of the form (language tag, qvalue), in
                 descending order of preference.

        For each tag in `language_tags`:

        1. If the tag matches any language range in the header with ``q=0``
           (meaning "not acceptable", see :rfc:`RFC 7231, section 5.3.1
           <7231#section-5.3.1>`), the tag is filtered out.
        2. The language ranges in the header that do not have ``q=0`` and are
           not ``*`` are considered in descending order of preference: first in
           descending order of qvalue; where two or more language ranges have
           the same qvalue, we consider the language range that appears earlier
           in the header to have higher preference.
        3. A language range 'matches a particular language tag if, in a
           case-insensitive comparison, it exactly equals the tag, or if it
           exactly equals a prefix of the tag such that the first character
           following the prefix is "-".' (:rfc:`RFC 4647, section 3.3.1
           <4647#section-3.3.1>`)
        4. If a language tag has not matched any of the language ranges so far,
           and there is one or more ``*`` language ranges in the header: if any
           of the ``*`` language ranges have ``q=0``, the language tag is
           filtered out. Otherwise, the language tag is considered a match.

        The method returns a list of tuples of the form (language tag, qvalue),
        in descending order of preference: in descending order of qvalue, and
        if two tags have equal qvalues, we consider the tag whose matched range
        appears earlier in the header to have higher preference. If the matched
        range is the same for two or more tags (i.e. their matched ranges have
        the same qvalue and the same position in the header), their order in
        the `language_tags` argument is used as tiebreaker. (If `language_tags`
        is unordered, e.g. if it is a set or a dict, then that order may not be
        reliable.)
        """
        # The Basic Filtering matching scheme as applied to the Accept-Language
        # header is very under-specified by RFCs 7231 and 4647. This
        # implementation combines the description of the matching scheme in RFC
        # 4647 and the rules of the Accept-Language header in RFC 7231 to
        # arrive at an algorithm for Basic Filtering as applied to the
        # Accept-Language header.

        parsed = list(self.parsed)
        tags = language_tags

        not_acceptable_ranges = []
        acceptable_ranges = []

        asterisk_range_highest_qvalue = None
        # The highest qvalue from '*' ranges in the header with non-0 qvalues

        asterisk_q0_found = False
        # Whether there is a '*' range in the header with q=0

        for position_in_header, (range_, qvalue) in enumerate(parsed):
            if qvalue == 0.0:
                if range_ == '*':
                    asterisk_q0_found = True
                else:
                    not_acceptable_ranges.append(range_)
            elif not asterisk_q0_found and range_ == '*':
                if (
                    (asterisk_range_highest_qvalue is None) or
                    (qvalue > asterisk_range_highest_qvalue)
                ):
                    asterisk_range_highest_qvalue = qvalue
                    asterisk_range_highest_qvalue_position = position_in_header
                    # We take the highest qvalue to handle the case where there
                    # is more than one '*' range in the header (which would not
                    # make sense, but as it's still a valid header, we'll
                    # handle it anyway)
            else:
                acceptable_ranges.append((range_, qvalue, position_in_header))
        # Sort acceptable_ranges by qvalue, descending order
        acceptable_ranges.sort(key=lambda tuple_: tuple_[1], reverse=True)

        def match(tag, range_):
            tag = tag.lower()
            range_ = range_.lower()
            # RFC 4647, section 2.1: 'A language range matches a particular
            # language tag if, in a case-insensitive comparison, it exactly
            # equals the tag, or if it exactly equals a prefix of the tag such
            # that the first character following the prefix is "-".'
            return (range_ == tag) or tag.startswith(range_ + '-')
            # We can assume here that the language tags are valid tags, so we
            # do not have to worry about them being malformed and ending with
            # '-'.

        filtered_tags = []
        for tag in tags:
            # If tag matches a range with q=0, it is filtered out
            if any((
                match(tag=tag, range_=range_)
                for range_ in not_acceptable_ranges
            )):
                continue

            matched_range_qvalue = None
            for range_, qvalue, position_in_header in acceptable_ranges:
                if match(tag=tag, range_=range_):
                    matched_range_qvalue = qvalue
                    matched_range_position = position_in_header
                    break
            else:
                if (
                    # there is no *;q=0 in header, and
                    (not asterisk_q0_found) and
                    # there is one or more * range in header
                    (asterisk_range_highest_qvalue is not None)
                ):
                    # From RFC 4647, section 3.3.1: '...HTTP/1.1 [RFC2616]
                    # specifies that the range "*" matches only languages not
                    # matched by any other range within an "Accept-Language"
                    # header.'
                    # (Though RFC 2616 is obsolete, and there is no mention of
                    # the meaning of "*" in RFC 7231, as the ``language-range``
                    # syntax rule in RFC 7231 section 5.3.1 directs us to RFC
                    # 4647, we can only assume that the meaning of "*" in the
                    # Accept-Language header remains the same).
                    matched_range_qvalue = asterisk_range_highest_qvalue
                    matched_range_position = \
                        asterisk_range_highest_qvalue_position
            if matched_range_qvalue is not None:  # if there was a match
                filtered_tags.append(
                    (tag, matched_range_qvalue, matched_range_position)
                )

        # sort by matched_range_position, ascending
        filtered_tags.sort(key=lambda tuple_: tuple_[2])
        # When qvalues are tied, matched range position in the header is the
        # tiebreaker.

        # sort by qvalue, descending
        filtered_tags.sort(key=lambda tuple_: tuple_[1], reverse=True)

        return [(item[0], item[1]) for item in filtered_tags]
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
        # returned list if the qvalues are not required.
        # One use for qvalues, for example, would be to indicate that two tags
        # are equally preferred (same qvalue), which we would not be able to do
        # easily with a set or a list without e.g. making a member of the set
        # or list a sequence.

    def best_match(self, offers, default_match=None):
        """
        Return the best match from the sequence of language tag `offers`.

        .. warning::

           This is currently maintained for backward compatibility, and may be
           deprecated in future.

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
            'currently being maintained for backward compatibility, but it may'
            ' be deprecated in future as it does not conform to the RFC.',
            PendingDeprecationWarning,
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

        Each language range in the header is considered in turn, in descending
        order of qvalue; where qvalue is tied, ranges are considered from left
        to right.

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
        assert not (default_tag is None and default is None), \
            '`default_tag` and `default` arguments cannot both be None.'

        # We need separate `default_tag` and `default` arguments because if we
        # only had the `default` argument, there would be no way to tell
        # whether a str is a language tag (in which case we have to check
        # whether it has been specified as not acceptable with a q=0 range in
        # the header) or not (in which case we can just return the value).

        assert default_range != '*', 'default_range cannot be *.'

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

    def quality(self, offer, modifier=1):
        """
        Return quality value of given offer, or ``None`` if there is no match.

        .. warning::

           This is currently maintained for backward compatibility, and may be
           deprecated in future.

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
            'currently being maintained for backward compatibility, but it may'
            ' be deprecated in future as it does not conform to the RFC.',
            PendingDeprecationWarning,
        )
        # [If ``modifier`` is positive, it would not change the result of the
        # comparison using ``max()`` (apart from the first comparison with
        # bestq, when it is 0), because all the ``q``s are multiplied by the
        # same modifier. So in effect, it is just multiplying the highest
        # quality value by the ``modifier``.
        #
        # If ``modifier`` is negative, bestq would always be 0, because it
        # starts off as 0, and max(0, negative number) is always 0. So the
        # method would always return None.
        #
        # If ``modifier`` is 0, bestq would always be 0, so the method would
        # always return None.
        #
        # There was no explanation of the parameter in the existing
        # documentation, and it is unclear what it was intended to do, so I
        # have left it undocumented for now.]
        bestq = 0
        for mask, q in self.parsed:
            if self._old_match(mask, offer):
                bestq = max(bestq, q * modifier)
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

    HeaderClass = AcceptLanguage

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
           is currently being maintained for backward compatibility, but it may
           change in future to better conform to the RFC.

        :param offer: (``str``) language tag offer
        :return: (``bool``) Whether ``offer`` is acceptable according to the
                 header.

        For this class, either there is no ``Accept-Language`` header in the
        request, or the header is invalid, so any language tag is acceptable,
        and this always returns ``True``.
        """
        warnings.warn(
            'The behavior of .__contains__ for the AcceptLanguage classes is'
            'currently being maintained for backward compatibility, but it may'
            ' change in future to better conform to the RFC.',
            PendingDeprecationWarning,
        )
        return True

    def __iter__(self):
        """
        Return all the ranges with non-0 qvalues, in order of preference.

        :return: iterator of all the language ranges in the header with non-0
                 qvalues, in descending order of qvalue. If two ranges have the
                 same qvalue, they are returned in the order of their positions
                 in the header, from left to right.

        For this class, either there is no ``Accept-Language`` header in the
        request, or the header is invalid, so there are no language ranges, and
        this always returns an empty iterator.
        """
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

           This is currently maintained for backward compatibility, and may be
           deprecated in future (see the documentation for
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
            'method may be deprecated in future, as its behavior is not '
            'specified in (and currently does not conform to) RFC 7231.',
            PendingDeprecationWarning,
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
        assert not (default_tag is None and default is None), \
            '`default_tag` and `default` arguments cannot both be None.'

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

           This is currently maintained for backward compatibility, and may be
           deprecated in future (see the documentation for
           :meth:`AcceptLanguageValidHeader.quality`).

        :param offer: (``str``) language tag offer
        :return: (``float``) ``1.0``.

        When the ``Accept-Language`` header is invalid or not in the request,
        all offers are equally acceptable, so 1.0 is always returned.
        """
        warnings.warn(
            'The behavior of .quality for the AcceptLanguage classes is '
            'currently being maintained for backward compatibility, but the '
            'method may be deprecated in future, as its behavior is not '
            'specified in (and currently does not conform to) RFC 7231.',
            PendingDeprecationWarning,
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
        self.header_value = None
        """(``str``) The header value. As there is no header in the request,
        this is ``None``."""

        self.parsed = None
        """(``list``) Parsed form of the header. As there is no header in the
        request, this is ``None``."""

        self._parsed_nonzero = None

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``s and pairs can be
          mixed within the ``tuple`` or ``list``)
        * any object that returns a value for `__str__`
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance

        If neither operands are empty (header value ``''``) or
        ``None``/:class:`AcceptLanguageNoHeader`, the two header values are
        joined with ``', '``.
        """
        if isinstance(other, AcceptLanguageNoHeader):
            return self.__class__()

        if isinstance(other, AcceptLanguageValidHeader):
            return create_accept_language_header(
                header_value=other.header_value
            )

        if isinstance(other, AcceptLanguageInvalidHeader):
            return AcceptLanguageInvalidHeader(header_value=other.header_value)

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
        return '{}()'.format(self.__class__.__name__)

    def __str__(self):
        """Return the ``str`` ``'<no header in request>'``."""
        return '<no header in request>'

    def _add_instance_and_non_accept_language_type(self, instance, other):
        if other is None:
            return self.__class__()
        if other in ('', (), [], {}):
            return AcceptLanguageInvalidHeader(header_value='')

        if isinstance(other, str):
            other_header_value = other
        else:
            if hasattr(other, 'items'):
                other = sorted(
                    other.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            if isinstance(other, (tuple, list)):
                result = []
                for element in other:
                    if isinstance(element, (tuple, list)):
                        element = _item_qvalue_pair_to_header_element(
                            pair=element
                        )
                    result.append(element)
                other_header_value = ', '.join(result)
            else:
                other_header_value = str(other)
                if other_header_value == '':
                    return AcceptLanguageInvalidHeader(header_value='')

        return create_accept_language_header(header_value=other_header_value)


class AcceptLanguageInvalidHeader(_AcceptLanguageInvalidOrNoHeader):
    """
    Represent an invalid ``Accept-Language`` header.

    An invalid header is one that does not conform to
    :rfc:`7231#section-5.3.5`. As specified in the RFC, an empty header is an
    invalid ``Accept-Language`` header.

    :rfc:`7231` does not provide any guidance on what should happen if the
    ``Accept-Language`` has an invalid value. This implementation disregards
    the header, and treats it as if there is no ``Accept-Language`` header in
    the request.

    This object should not be modified. To add to the header, we can use the
    addition operators (``+`` and ``+=``), which return a new object (see the
    docstring for :meth:`AcceptLanguageInvalidHeader.__add__`).
    """
    def __init__(self, header_value):
        """
        Create an :class:`AcceptLanguageInvalidHeader` instance.
        """
        self.header_value = header_value
        """(``str``) The header value."""

        self.parsed = None
        """(``list``) Parsed form of the header. As the header is invalid and
        cannot be parsed, this is ``None``."""

        self._parsed_nonzero = None

    def __add__(self, other):
        """
        Add to header, creating a new header object.

        `other` can be:

        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``s and pairs can be
          mixed within the ``tuple`` or ``list``)
        * any object that returns a value for `__str__`
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance

        If neither operands are empty (header value ``''``) or
        ``None``/:class:`AcceptLanguageNoHeader`, the two header values are
        joined with ``', '``.
        """
        if isinstance(other, AcceptLanguageNoHeader):
            return self.__class__(header_value=self.header_value)

        if isinstance(other, AcceptLanguageValidHeader):
            if self.header_value == '':
                return AcceptLanguageValidHeader(
                    header_value=other.header_value,
                )
            return create_accept_language_header(
                header_value=self.header_value + ', ' + other.header_value
            )

        if isinstance(other, AcceptLanguageInvalidHeader):
            if self.header_value == '':
                return self.__class__(header_value=other.header_value)
            if other.header_value == '':
                return self.__class__(header_value=self.header_value)
            return create_accept_language_header(
                header_value=self.header_value + ', ' + other.header_value
            )

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
        return "{}(header_value={!r})".format(
            # ``!r`` escapes the header value
            self.__class__.__name__,
            self.header_value,
        )

    def __str__(self):
        """Return the ``str`` ``'<invalid header value>'``."""
        return '<invalid header value>'

    def _add_instance_and_non_accept_language_type(
        self, instance, other, instance_on_the_right=False,
    ):
        if not other:
            return self.__class__(header_value=instance.header_value)

        if isinstance(other, str):
            other_header_value = other
        else:
            if hasattr(other, 'items'):
                other = sorted(
                    other.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )
            if isinstance(other, (tuple, list)):
                result = []
                for element in other:
                    if isinstance(element, (tuple, list)):
                        element = _item_qvalue_pair_to_header_element(
                            pair=element
                        )
                    result.append(element)
                other_header_value = ', '.join(result)
            else:
                other_header_value = str(other)
                if other_header_value == '':
                    return self.__class__(header_value=instance.header_value)

        if instance.header_value == '':
            new_header_value = other_header_value
        else:
            new_header_value = (
                (other_header_value + ', ' + instance.header_value)
                if instance_on_the_right
                else (instance.header_value + ', ' + other_header_value)
            )

        return create_accept_language_header(header_value=new_header_value)


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
        environ, and do not involve parsing.)'
    """

    ENVIRON_KEY = 'HTTP_ACCEPT_LANGUAGE'

    def fget(request):
        """
        Get an object representing the header in the request.

        This creates a new object (and re-parses the header) on every call.
        """
        return create_accept_language_header(
            header_value=request.environ.get(ENVIRON_KEY)
        )

    def fset(request, value):
        """
        Set the corresponding key in the request environ.

        `value` can be:

        * a ``str``
        * a ``dict``, with language ranges as keys and qvalues as values
        * a ``tuple`` or ``list``, of language range ``str``s or of ``tuple``
          or ``list`` (language range, qvalue) pairs (``str``s and pairs can be
          mixed within the ``tuple`` or ``list``)
        * any object that returns a value for `__str__`
        * an :class:`AcceptLanguageValidHeader`,
          :class:`AcceptLanguageNoHeader`, or
          :class:`AcceptLanguageInvalidHeader` instance
        """
        if value is None or isinstance(value, AcceptLanguageNoHeader):
            fdel(request=request)
        else:
            request.environ[ENVIRON_KEY] = (
                AcceptLanguageNoHeader() + value
            ).header_value

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
