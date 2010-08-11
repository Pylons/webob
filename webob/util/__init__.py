import sys

# if sys.version >= '2.6':
#    from collections import MutableMapping as DictMixin
#    # this also requires adding __len__, __iter__ to work
#    # and __repr__ for tests to pass
if sys.version >= '2.3':
    from UserDict import DictMixin
else:
    from webob.util.dictmixin import DictMixin

if sys.version >= '2.4':
    reversed = reversed
    sorted = sorted
else:
    def reversed(seq):
        return iter(list(seq)[::-1])

    def sorted(iterable, key=None, reverse=False):
        l = list(iterable)
        if key:
            l = [(key(i), i) for i in l]
        l.sort()
        if key:
            l = [i[1] for i in l]
        if reverse:
            l.reverse()
        return l


def rfc_reference(header, section):
    if not section:
        return ''
    major_section = section.split('.')[0]
    link = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec%s.html#sec%s' % (major_section, section)
    if header.startswith('HTTP_'):
        header = header[5:].title().replace('_', '-')
    return " For more information on %s see `section %s <%s>`_." % (header, section, link)
