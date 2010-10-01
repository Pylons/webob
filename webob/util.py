def rfc_reference(header, section):
    if not section:
        return ''
    major_section = section.split('.')[0]
    link = 'http://www.w3.org/Protocols/rfc2616/rfc2616-sec%s.html#sec%s' % (major_section, section)
    if header.startswith('HTTP_'):
        header = header[5:].title().replace('_', '-')
    return " For more information on %s see `section %s <%s>`_." % (header, section, link)
