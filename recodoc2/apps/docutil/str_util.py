from __future__ import unicode_literals
import re
import unicodedata


CAMELCASE_TOKEN = re.compile(r'((?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z]))')


def smart_decode(s):
    if isinstance(s, unicode):
        return s
    elif isinstance(s, str):
        # Should never reach this case in Python 3
        return unicode(s, 'utf-8')
    else:
        return unicode(s)


def tokenize(s):
    return CAMELCASE_TOKEN.sub(' ', s).split()


def normalize(uni_str):
    '''Ensures that a unicode string does not have strange characters.
       Necessary with lxml because it does not handle encoding well...'''
    if uni_str is None:
        return None
    return unicodedata.normalize('NFKD', uni_str)
