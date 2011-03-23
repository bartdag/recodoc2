def smart_decode(s):
    if isinstance(s, unicode):
        return s
    elif isinstance(s, str):
        # Should never reach this case in Python 3
        return unicode(s, 'utf-8')
    else:
        return unicode(s)
