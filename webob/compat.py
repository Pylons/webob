try:
    # This will succeed on Python 2.4, and fail on Python 2.3.

    [].sort(key=lambda: None)

    def sorted(iterable, cmp=None, key=None, reverse=False):
        l = list(iterable)
        l.sort(cmp=cmp, key=key, reverse=reverse)
        return l

except TypeError:
    # Implementation for Python 2.3.
    
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
