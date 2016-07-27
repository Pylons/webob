class URLDecodeError(UnicodeDecodeError):
    """
    subclass of :class:`~UnicodeDecodeError

    This indicates that the server received an invalid URL.
    """
    def __init__(self, exc):
        super(UnicodeDecodeError, self).__init__(exc.encoding,
                                                 exc.reason,
                                                 exc.object,
                                                 exc.start,
                                                 exc.end)
