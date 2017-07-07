"""
Parses a variety of ``Accept-*`` headers.

These headers generally take the form of::

    value1; q=0.5, value2; q=0

Where the ``q`` parameter is optional.  In theory other parameters
exists, but this ignores them.
"""

import re

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


class AcceptLanguage(Accept):
    """
    Represents an ``Accept-Language`` header.
    """
    def _match(self, mask, item):
        item = item.replace('_', '-').lower()
        mask = mask.lower()
        return (mask == '*'
            or item == mask
            or item.split('-')[0] == mask
            or item == mask.split('-')[0]
        )


class AcceptLanguageValidHeader(AcceptLanguage):
    """
    Represent a valid ``Accept-Language`` header.

    A valid header is one that conforms to :rfc:`RFC 7231, section 5.3.5
    <7231#section-5.3.5>`.

    We take the reference from the ``language-range`` syntax rule in :rfc:`RFC
    7231, section 5.3.5 <7231#section-5.3.5>` to :rfc:`RFC 4647, section 2.1
    <4647#section-2.1>` to mean that only basic language ranges (and not
    extended language ranges) are expected in the ``Accept-Language`` header.
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
        # If there is one or more '*' ranges in the header, this stores the
        # highest qvalue from these ranges

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
            not_acceptable = False
            for range_ in not_acceptable_ranges:
                if match(tag=tag, range_=range_):
                    not_acceptable = True
                    break
            if not_acceptable:
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
