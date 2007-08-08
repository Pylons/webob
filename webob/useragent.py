import re
import urlparse
import urllib
import cgi

__all__ = ['UserAgent']

class UserAgent(object):

    """
    Represents a User-Agent.

    Exposes the following attributes:

    ``str(user_agent)``: return the original string

    ``.platform``: the platform: windows macos linux solaris bsd

    ``.browser``: the browser: aol msie firefox galeon safari opera
    camino konqueror k-meleon netscape psp playstation3 lynx other

    ``.version``: the browser version or None

    ``.language``: the browser language if present or None
    """

    platforms = [
        (re.compile(r'Win', re.I), 'windows'),
        (re.compile(r'Mac', re.I), 'macos'),
        (re.compile(r'Linux', re.I), 'linux'),
        (re.compile(r'SunOS', re.I), 'solaris'),
        (re.compile(r'BSD', re.I), 'bsd'),
        ]

    browsers = []
    for regex, name in [
        ('AOL|America Online Browser','aol'),
        ('MSIE', 'msie'),
        ('Firefox|Firebird|Phoenix|Iceweasel', 'firefox'),
        ('Galeon', 'galeon'),
        ('Safari', 'safari'),
        ('Opera', 'opera'),
        ('Camino', 'camino'),
        ('Konqueror', 'konqueror'),
        ('K-Meleon', 'k-meleon'),
        ('Netscape', 'netscape'),
        ('PlayStation Portable', 'psp'),
        ('PlayStation 3', 'playstation3'),
        ('Lynx', 'lynx'),
        ]:
        browsers.append(
            (re.compile(r'%s[/;]?\s*([\d.-:]+)?' % regex, re.I),
             name))
    del regex, name

    lang_re = re.compile(r'\s+(\w\w(?:-\w\w)?)\)|(\[\w\w(?:-\w\w)?)]|\s+(\w\w(?:-\w\w)?); rv:')

    def __init__(self, user_agent):
        self.user_agent = user_agent
        for regex, name in self.platforms:
            if regex.search(user_agent):
                self.platform = name
                break
        else:
            self.platform = 'other'
        for regex, name in self.browsers:
            match = regex.search(user_agent)
            if match:
                self.browser = name
                self.version = match.group(1) or None
                break
        else:
            self.browser = 'other'
            self.version = None
        match = self.lang_re.search(user_agent)
        if match:
            self.language = match.group(1) or match.group(2) or match.group(3)
            if self.language.lower() == 'xp':
                self.language = None
        else:
            self.language = None
        
    def __str__(self):
        return self.user_agent

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.user_agent)
            
_search_domain_re = re.compile(
    r'google|alltheweb|search\.msn|ask\.com|del\.icio\.us|yahoo|reddit|rollyo|search\.aol|search\.live|mywebsearch|askcache')

def parse_search_query(referer, extra_hosts=(), extra_keys=()):
    scheme, netloc, path, query, fragment = urlparse.urlsplit(referer)
    if not netloc or not query:
        return None
    if (not _search_domain_re.search(netloc)
        and netloc.lower() not in extra_hosts):
        return None
    if netloc.startswith('mail'):
        return None
    q = cgi.parse_qs(query)
    for key in ('q', 'query', 'search', 'p') + tuple(extra_keys):
        if key in q:
            return ' '.join(map(urllib.unquote, q[key]))
    return None

