class _AnyETag(object):

    def __repr__(self):
        return '<ETag *>'

    def __contains__(self, other):
        return True

    def weak_match(self, other):
        return True

    def __str__(self):
        return '*'

AnyETag = _AnyETag()

class _NoETag(object):

    def __repr__(self):
        return '<No ETag>'

    def __contains__(self, other):
        return False

    def weak_match(self, other):
        return False

    def __str__(self):
        return ''

NoETag = _NoETag()

class ETagMatcher(object):

    """
    Represents an ETag request.  Supports containment to see if an
    ETag matches.  You can also use
    ``etag_matcher.weak_contains(etag)`` to allow weak ETags to match
    (allowable for conditional GET requests, but not ranges or other
    methods).
    """

    def __init__(self, etags, weak_etags=()):
        self.etags = etags
        self.weak_etags = weak_etags

    def __contains__(self, other):
        return other in self.etags

    def weak_match(self, other):
        if other.lower().startswith('w/'):
            other = other[2:]
        return other in self.etags or other in self.weak_etags

    def __repr__(self):
        return '<ETag %s>' % (
            ' or '.join(self.etags))

    def parse(cls, value):
        results = []
        weak_results = []
        while value:
            if value.lower().startswith('w/'):
                # Next item is weak
                weak = True
                value = value[2:]
            else:
                weak = False
            if value.startswith('"'):
                try:
                    etag, rest = value[1:].split('"', 1)
                except ValueError:
                    etag = value.strip(' ",')
                    rest = ''
                else:
                    rest = rest.strip(', ')
            else:
                if ',' in value:
                    etag, rest = value.split(',', 1)
                    rest = rest.strip()
                else:
                    etag = value
                    rest = ''
            if etag == '*':
                return AnyTag
            if etag:
                if weak:
                    weak_results.append(etag)
                else:
                    results.append(etag)
            value = rest
        return cls(results, weak_results)
    parse = classmethod(parse)
                    
    def __str__(self):
        # FIXME: should I quote these?
        items = list(self.etags)
        for weak in self.weak_etags:
            items.append('W/%s' % weak)
        return ', '.join(items)
