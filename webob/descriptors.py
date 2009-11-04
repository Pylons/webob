class environ_getter(object):
    """For delegating an attribute to a key in self.environ."""

    def __init__(self, key, default='', default_factory=None,
                 settable=True, deletable=True, doc=None,
                 rfc_section=None):
        self.key = key
        self.default = default
        self.default_factory = default_factory
        self.settable = settable
        self.deletable = deletable
        docstring = "Gets"
        if self.settable:
            docstring += " and sets"
        if self.deletable:
            docstring += " and deletes"
        docstring += " the %r key from the environment." % self.key
        docstring += _rfc_reference(self.key, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        if self.key not in obj.environ:
            if self.default_factory:
                val = obj.environ[self.key] = self.default_factory()
                return val
            else:
                return self.default
        return obj.environ[self.key]

    def __set__(self, obj, value):
        if not self.settable:
            raise AttributeError("Read-only attribute (key %r)" % self.key)
        if value is None:
            if self.key in obj.environ:
                del obj.environ[self.key]
        else:
            obj.environ[self.key] = value

    def __delete__(self, obj):
        if not self.deletable:
            raise AttributeError("You cannot delete the key %r" % self.key)
        del obj.environ[self.key]

    def __repr__(self):
        return '<Proxy for WSGI environ %r key>' % self.key

def _rfc_reference(header, section):
    if not section:
        return ''
    major_section = section.split('.')[0]
    link = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec%s.html#sec%s' % (
        major_section, section)
    if header.startswith('HTTP_'):
        header = header[5:].title().replace('_', '-')
    return "  For more information on %s see `section %s <%s>`_." % (
        header, section, link)


class header_getter(object):
    """For delegating an attribute to a header in self.headers"""

    def __init__(self, header, default=None,
                 settable=True, deletable=True, doc=None, rfc_section=None):
        self.header = header
        self.default = default
        self.settable = settable
        self.deletable = deletable
        docstring = "Gets"
        if self.settable:
            docstring += " and sets"
        if self.deletable:
            docstring += " and deletes"
        docstring += " the %s header" % self.header
        docstring += _rfc_reference(self.header, rfc_section)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        return obj.headers.get(self.header, self.default)

    def __set__(self, obj, value):
        if not self.settable:
            raise AttributeError("Read-only attribute (header %s)" % self.header)
        if value is None:
            if self.header in obj.headers:
                del obj.headers[self.header]
        else:
            if isinstance(value, unicode):
                # This is the standard encoding for headers:
                value = value.encode('ISO-8859-1')
            obj.headers[self.header] = value

    def __delete__(self, obj):
        if not self.deletable:
            raise AttributeError("You cannot delete the header %s" % self.header)
        del obj.headers[self.header]

    def __repr__(self):
        return '<Proxy for header %s>' % self.header

class set_via_call(object):
    def __init__(self, func, adapt_args=None):
        self.func = func
        self.adapt_args = adapt_args
    def __get__(self, obj, type=None):
        return self.__class__(self.func.__get__(obj, type))
    def __set__(self, obj, value):
        if self.adapt_args is None:
            args, kw = (value,), {}
        else:
            result = self.adapt_args(value)
            if result is None:
                return
            args, kw = result
        self.func(obj, *args, **kw)
    def __repr__(self):
        return 'set_via_call(%r)' % self.func
    def __call__(self, *args, **kw):
        return self.func(*args, **kw)


class converter(object):
    """
    Wraps a descriptor, and applies additional conversions when reading and writing
    """
    def __init__(self, descriptor, getter_converter, setter_converter, convert_name=None, doc=None, converter_args=()):
        self.descriptor = descriptor
        self.getter_converter = getter_converter
        self.setter_converter = setter_converter
        self.convert_name = convert_name
        self.converter_args = converter_args
        docstring = descriptor.__doc__ or ''
        docstring += "  Converts it as a "
        if convert_name:
            docstring += convert_name + '.'
        else:
            docstring += "%r and %r." % (getter_converter, setter_converter)
        if doc:
            docstring += '\n\n' + textwrap.dedent(doc)
        self.__doc__ = docstring

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = self.descriptor.__get__(obj, type)
        return self.getter_converter(value, *self.converter_args)

    def __set__(self, obj, value):
        value = self.setter_converter(value, *self.converter_args)
        self.descriptor.__set__(obj, value)

    def __delete__(self, obj):
        self.descriptor.__delete__(obj)

    def __repr__(self):
        if self.convert_name:
            name = ' %s' % self.convert_name
        else:
            name = ''
        return '<Converted %r%s>' % (self.descriptor, name)


class deprecated_property(object):
    """
    Wraps a descriptor, with a deprecation warning or error
    """
    def __init__(self, descriptor, attr, message, warning=True):
        self.descriptor = descriptor
        self.attr = attr
        self.message = message
        self.warning = warning

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        self.warn()
        return self.descriptor.__get__(obj, type)

    def __set__(self, obj, value):
        self.warn()
        self.descriptor.__set__(obj, value)

    def __delete__(self, obj):
        self.warn()
        self.descriptor.__delete__(obj)

    def __repr__(self):
        return '<Deprecated attribute %s: %r>' % (
            self.attr,
            self.descriptor)

    def warn(self):
        if not self.warning:
            raise DeprecationWarning(
                'The attribute %s is deprecated: %s' % (self.attr, self.message))
        else:
            warnings.warn(
                'The attribute %s is deprecated: %s' % (self.attr, self.message),
                DeprecationWarning,
                stacklevel=3)
