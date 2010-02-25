"""Cookie fixes for the standard library

These fixed SimpleCookie classes are from werkzeug.

"""
from Cookie import BaseCookie, Morsel, CookieError

class _ExtendedMorsel(Morsel):
    _reserved = {'httponly': 'HttpOnly'}
    _reserved.update(Morsel._reserved)

    def __init__(self, name=None, value=None):
        Morsel.__init__(self)
        if name is not None:
            self.set(name, value, value)

    def OutputString(self, attrs=None):
        httponly = self.pop('httponly', False)
        result = Morsel.OutputString(self, attrs).rstrip('\t ;')
        if httponly:
            result += '; HttpOnly'
        return result


class _ExtendedCookie(BaseCookie):
    """Form of the base cookie that doesn't raise a `CookieError` for
    malformed keys.  This has the advantage that broken cookies submitted
    by nonstandard browsers don't cause the cookie to be empty.
    """

    def _BaseCookie__set(self, key, real_value, coded_value):
        morsel = self.get(key, _ExtendedMorsel())
        try:
            morsel.set(key, real_value, coded_value)
        except CookieError:
            pass
        dict.__setitem__(self, key, morsel)
