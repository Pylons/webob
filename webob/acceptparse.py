"""
Parses a variety of ``Accept-*`` headers.

These headers generally take the form of::

    value1; q=0.5, value2; q=0

Where the ``q`` parameter is optional.  In theory other parameters
exists, but this ignores them.
"""

import re
try:
    sorted
except NameError:
    from webob.compat import sorted

part_re = re.compile(
    r',\s*([^\s;,\n]+)(?:[^,]*?;\s*q=([0-9.]*))?')

def parse_accept(value):
    """
    Parses an ``Accept-*`` style header.

    A list of ``[(value, quality), ...]`` is returned.  ``quality``
    will be 1 if it was not given.
    """
    result = []
    for match in part_re.finditer(','+value):
        name = match.group(1)
        if name == 'q':
            continue
        quality = match.group(2) or ''
        if not quality:
            quality = 1
        else:
            try:
                quality = max(min(float(quality), 1), 0)
            except ValueError:
                quality = 1
        result.append((name, quality))
    return result

class Accept(object):
    """
    Represents a generic ``Accept-*`` style header.

    This object should not be modified.  To add items you can use
    ``accept_obj + 'accept_thing'`` to get a new object
    """

    def __init__(self, header_name, header_value):
        self.header_name = header_name
        self.header_value = header_value
        self._parsed = parse_accept(header_value)

    def __repr__(self):
        return '<%s at 0x%x %s: %s>' % (
            self.__class__.__name__,
            abs(id(self)),
            self.header_name, str(self))

    def __str__(self):
        result = []
        for match, quality in self._parsed:
            if quality != 1:
                match = '%s;q=%0.1f' % (match, quality)
            result.append(match)
        return ', '.join(result)

    # FIXME: should subtraction be allowed?
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
        return self.__class__(self.header_name, new_value)

    def __radd__(self, other):
        return self.__add__(other, True)

    def __contains__(self, offer):
        """
        Returns true if the given object is listed in the accepted
        types.
        """
        for mask, quality in self._parsed:
            if self._match(mask, offer):
                return True

    def quality(self, offer, modifier=1):
        """
        Return the quality of the given offer.  Returns None if there
        is no match (not 0).
        """
        # FIXME: this does not return best quality, just quality of the first match
        for mask, quality in self._parsed:
            if self._match(mask, offer):
                return quality * modifier
        return None

    def first_match(self, offers):
        """
        Returns the first match in the sequences of matches that is
        allowed.  Ignores quality.  Returns the first item if nothing
        else matches; or if you include None at the end of the match
        list then that will be returned.
        """
        if not offers:
            raise ValueError("You must pass in a non-empty list")
        for offer in offers:
            if offer is None:
                return None
            for mask, quality in self._parsed:
                if self._match(mask, offer):
                    return offer
        return offers[0]

    def best_match(self, offers, default_match=None):
        """
        Returns the best match in the sequence of offered types.

        The sequence can be a simple sequence, or you can have
        ``(match, server_quality)`` items in the sequence.  If you
        have these tuples then the client quality is multiplied by the
        server_quality to get a total.  If two matches have equal
        weight, then the one that shows up first in the `matches` list
        will be returned.

        But among matches with the same quality the match to a more specific
        requested type will be chosen. For example a match to text/* trumps */*.

        default_match (default None) is returned if there is no intersection.
        """
        best_quality = -1
        best_offer = default_match
        matched_by = '*/*'
        for offer in offers:
            if '*' in offer:
                raise ValueError("The application should offer specific types, got %r" % offer)
            if isinstance(offer, (tuple, list)):
                offer, server_quality = offer
            else:
                server_quality = 1
            for mask, quality in self._parsed:
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

    def best_matches(self, fallback=None):
        """
        Return all the matches in order of quality, with fallback (if
        given) at the end.
        """
        items = [i for i, q
                    in sorted(self._parsed, key=lambda iq: -iq[1])]
        if fallback:
            for index, item in enumerate(items):
                if self._match(item, fallback):
                    items[index+1:] = []
                    break
            else:
                items.append(fallback)
        return items

    def _match(self, mask, item):
        return mask == '*' or item.lower() == mask.lower()



class NilAccept(object):

    """
    Represents an Accept header with no value.
    """

    MasterClass = Accept

    def __init__(self, header_name):
        self.header_name = header_name

    def __repr__(self):
        return '<%s for %s: %s>' % (
            self.__class__.__name__, self.header_name, self.MasterClass)

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False

    def __add__(self, item):
        if isinstance(item, self.MasterClass):
            return item
        else:
            return self.MasterClass(self.header_name, '') + item

    def __radd__(self, item):
        if isinstance(item, self.MasterClass):
            return item
        else:
            return item + self.MasterClass(self.header_name, '')

    def __contains__(self, item):
        return True

    def quality(self, match, default_quality=1):
        return 0

    def first_match(self, matches):
        return matches[0]

    def best_match(self, matches, default_match=None):
        best_quality = -1
        best_match = default_match
        for match_item in matches:
            if isinstance(match_item, (list, tuple)):
                match, quality = match_item
            else:
                match = match_item
                quality = 1
            if quality > best_quality:
                best_match = match
                best_quality = quality
        return best_match

    def best_matches(self, fallback=None):
        if fallback:
            return [fallback]
        else:
            return []

class NoAccept(NilAccept):
    def __contains__(self, item):
        return False


class MIMEAccept(Accept):
    """
        Represents the ``Accept`` header, which is a list of mimetypes.

        This class knows about mime wildcards, like ``image/*``
    """
    def __init__(self, header_name, header_value):
        Accept.__init__(self, header_name, header_value)
        parsed = []
        for mask, q in self._parsed:
            try:
                mask_major, mask_minor = mask.split('/')
            except ValueError:
                continue
            if mask_major == '*' and mask_minor != '*':
                continue
            parsed.append((mask, q))
        self._parsed = parsed

    def accept_html(self):
        """
        Returns true if any HTML-like type is accepted
        """
        return ('text/html' in self
                or 'application/xhtml+xml' in self
                or 'application/xml' in self
                or 'text/xml' in self)

    accepts_html = property(accept_html) # note the plural

    def _match(self, mask, item):
        # checks if item is covered by the mask
        assert '*' not in item, "item must be a specific type"
        if '*' not in mask:
            return item == mask
        elif mask == '*/*':
            return True
        else:
            assert mask.endswith('/*')
            mask_major = mask[:-2]
            item_major = item.split('/', 1)[0]
            return item_major == mask_major


class MIMENilAccept(NilAccept):
    MasterClass = MIMEAccept

