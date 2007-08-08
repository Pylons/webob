def parse_accept_language(header):
    """
    Return a list of language tags sorted by their "q" values.  For example,
    "en-us,en;q=0.5" should return ``["en-us", "en"]``.  If there is no
    ``Accept-Language`` header present, default to ``[]``.
    """
    if header is None:
        return []
    langs = [v.strip() for v in header.split(",") if v.strip()]
    qs = []
    for lang in langs:
        pieces = lang.split(";")
        lang, params = pieces[0].strip().lower(), pieces[1:]
        q = 1
        for param in params:
            if '=' not in param:
                # Malformed request; probably a bot, we'll ignore
                continue
            lvalue, rvalue = param.split("=")
            lvalue = lvalue.strip().lower()
            rvalue = rvalue.strip()
            if lvalue == "q":
                q = float(rvalue)
        qs.append((lang, q))
    qs.sort(lambda a, b: -cmp(a[1], b[1]))
    return [lang for (lang, q) in qs]
