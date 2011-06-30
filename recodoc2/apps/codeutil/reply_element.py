from __future__ import unicode_literals
import re
import docutil.str_util as su

### CONSTANTS ####
REPLY_LANGUAGE = 'r'
STOP_LANGUAGE = 's'

REPLY_START_CHARACTERS = set(['>'])
THRESHOLD_REPLY = 0.40


### REPLY REGEXES ###

WROTE_RE = re.compile(r'''
    ^
    (\s|-)*
    on
    \s+
    .*
    \s+
    wrote:
    ''', re.VERBOSE | re.IGNORECASE)


ORIGIN_RE = re.compile(r'''
    ^
    \s*
    -{3,}
    \s*
    original\s*message
    \s*
    -{3,}
    \s*
    $
    ''', re.VERBOSE | re.IGNORECASE)


DASH_RE = re.compile(r'''
    ^
    -{5,}
    \s*
    $
    ''', re.VERBOSE)


UNDERSCORE_RE = re.compile(r'''
    ^
    _{5,}
    \s*
    $
    ''', re.VERBOSE)


### Paragraph Identification ###

def is_reply_lines(lines):
    reply_lines = 0
    empty_lines = 0
    for line in lines:
        if len(line.strip()) == 0:
            empty_lines += 1
        elif line.strip()[0] in REPLY_START_CHARACTERS:
            reply_lines += 1

    confidence = float(reply_lines) / (len(lines) - empty_lines)

    is_reply_kind = confidence >= THRESHOLD_REPLY

    return (is_reply_kind, confidence)


def is_reply_header(lines):
    text = su.merge_lines(lines, False).strip()
    return (WROTE_RE.match(text) is not None, 1.0)


def is_rest_reply(lines):
    #print('Considering stop: {0}'.format(lines))
    is_stop = False
    for line in lines:
        line = line.strip()
        if ORIGIN_RE.match(line) or DASH_RE.match(line) or \
           UNDERSCORE_RE.match(line):
            is_stop = True
            break
    return (is_stop, 1.0)
