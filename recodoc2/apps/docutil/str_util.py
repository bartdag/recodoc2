from __future__ import unicode_literals
import re
import unicodedata


CAMELCASE_TOKEN = re.compile(r'((?=[A-Z][a-z])|(?<=[a-z])(?=[A-Z]))')

STOPPERS = {'.', '!', '?', '\n', '\r'}


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
    elif not isinstance(uni_str, unicode):
        uni_str = smart_decode(uni_str)
    return unicodedata.normalize('NFKD', uni_str)


def find_list(original, to_find):
    '''Finds all ocurrences of a string and return a list of the positions.'''

    indexes = []
    index = 0
    size = len(original)
    while index < size:
        index = original.find(to_find, index)
        if (index > -1):
            indexes.append(index)
            index += 1
        else:
            break
    return indexes


def clean_for_re(original):
    return original.replace('\n', ' ')


def clean_breaks(original):
    return original.replace('\n', ' ').replace('\t', ' ').replace('\r', '')


def lower_stopper_index(paragraph, start, end):
    index = end
    for i, c in enumerate(reversed(paragraph[start:end])):
        if c in STOPPERS:
            index = end - i
    return index


def upper_stopper_index(paragraph, start, end):
    index = start
    for i, c in enumerate(paragraph[start: end]):
        if c in STOPPERS:
            index = start + i
    return index


def find_sentence(paragraph, start, end):
    paragraph_size = len(paragraph)
    first_stopper = upper_stopper_index(paragraph, 0, start)
    if first_stopper > 0:
        first_stopper += 1
    second_stopper = lower_stopper_index(paragraph, end, paragraph_size)
    return paragraph[first_stopper:second_stopper].strip()
