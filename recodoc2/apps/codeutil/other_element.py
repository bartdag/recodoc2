from __future__ import unicode_literals
import re
from codeutil.parser import create_match


OTHER_LANGUAGE = 'o'

IGNORE_KIND = 'ignore'

LOG_STD_THRESHOLD = 0.4

LOG_CONFIDENT_THRESHOLD = 0.3

LOG_LANGUAGE = 'l'

### REGEX ###

XML_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    xml                    # extension
    \b
    ''', re.VERBOSE)


INI_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    ini                    # extension
    \b
    ''', re.VERBOSE)


CONF_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    conf                   # extension
    \b
    ''', re.VERBOSE)


PROPERTIES_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    properties             # extension
    \b
    ''', re.VERBOSE)


LOG_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    log                    # extension
    \b
    ''', re.VERBOSE)


JAR_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    jar                    # extension
    \b
    ''', re.VERBOSE)


JAVA_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    java                   # extension
    \b
    ''', re.VERBOSE)


PYTHON_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    py                     # extension
    \b
    ''', re.VERBOSE)


HBM_FILE_RE = re.compile(r'''
    \b
    ([.\-_\w]+)            # file name
    \.                     # .
    hbm                    # extension
    \b
    ''', re.VERBOSE)


EMAIL_PATTERN_RE = re.compile(r'''
    \b
    ["'<]?
    [A-Z0-9+_.-]+
    @
    (?:[A-Z0-9-]+\.)+
    [A-Z]{2,6}              # domain name
    [>"']?
    \b                      # will not prevent .com.abcdefg with search()
    ''', re.VERBOSE | re.IGNORECASE)


URL_PATTERN_RE = re.compile(r'''
    [<"']?
    (https?|ftp|file)://[\S]+
    [>"']?
    ''', re.VERBOSE | re.IGNORECASE)
    

ANCHOR_EMAIL_PATTERN_RE = re.compile(r'''
    <\s*
    [A-Z0-9+_.-]+
    @
    (?:[A-Z0-9-]+\.)+
    [A-Z]{2,6}              # domain name
    \s*>
    ''', re.VERBOSE | re.IGNORECASE)


ANCHOR_URL_PATTERN_RE = re.compile(r'''
    <\s*
    (https?|ftp|file)://[\S]+
    \s*>
    ''', re.VERBOSE | re.IGNORECASE)


DEFINITION_ELEMENT_RE = re.compile(r'''
    (?P<element>[\w_\-.#]+):
    ''', re.VERBOSE)


### LOG TRACE REGEX ###

LOG_LEVEL_RE = re.compile(r'''
    (?:\[)?
    (DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|CRIT|ERR)
    (?:\])?
    ''', re.VERBOSE)

LOG_DATE_RE = re.compile(r'''
    \d{2,4}
    -|/
    \d{2}
    -|/
    \d{2}
    \s+
    \d{2}
    :|-
    \d{2}
    :|-
    \d{2}
    ,
    \d{3}
    ''', re.VERBOSE)

LOG_HOUR_RE = re.compile(r'''
    \d{2}
    \.|:
    \d{2}
    \.|:
    \d{2}
    \.|:
    ''', re.VERBOSE)

LOG_SOURCE_LOCATION_RE = re.compile(r'''
    [a-zA-Z_\-.]+
    :
    \d+
    ''', re.VERBOSE)


### Paragraph Language Identification ###

def is_empty_lines(lines):
    return (sum(1 for line in lines if line.strip() != '') == 0, 1.0)


def is_log_lines(lines):
    log_lines = 0
    empty_lines = 0
    strong_hint = False
    for line in lines:
        if line.strip() == '':
            empty_lines += 1
        elif LOG_LEVEL_RE.search(line) is not None:
            log_lines += 1
            if LOG_DATE_RE.search(line) is not None or\
               LOG_SOURCE_LOCATION_RE.search(line) is not None or\
               LOG_HOUR_RE.search(line) is not None:
                strong_hint = True
        elif LOG_DATE_RE.search(line) is not None:
            log_lines += 1
        elif LOG_SOURCE_LOCATION_RE.search(line) is not None:
            log_lines += 1
    confidence = float(log_lines) / (len(lines) - empty_lines)

    if strong_hint:
        is_log_kind = confidence >= LOG_CONFIDENT_THRESHOLD
    else:
        is_log_kind = confidence >= LOG_STD_THRESHOLD

    #print(is_log_kind, confidence)

    return (is_log_kind, confidence)

### Identification and Classification ###


class FileStrategy(object):

    priority = 100
    
    def match(self, text):
        matches = set()
        for m in XML_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'xml file', self.priority)))
        for m in CONF_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'conf file', self.priority)))
        for m in INI_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'ini file', self.priority)))
        for m in PROPERTIES_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'properties file', self.priority)))
        for m in LOG_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'log file', self.priority)))
        for m in JAR_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'jar file', self.priority)))
        for m in JAVA_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'java file', self.priority)))
        for m in PYTHON_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'python file', self.priority)))
        for m in HBM_FILE_RE.finditer(text):
            matches.add(create_match(
                (m.start(), m.end(), 'hbm file', self.priority)))
        return matches


class DefinitionStrategy(object):

    priority = 1
    
    def match(self, text):
        matches = set()
        for m in DEFINITION_ELEMENT_RE.finditer(text):
            matches.add(create_match(
                (m.start(1), m.end(1), 'unknown', self.priority)))
        return matches


class IgnoreStrategy(object):

    priority = 200
    
    def __init__(self, regexes):
        self.regexes = regexes
    
    def match(self, text):
        matches = set()
        for regex in self.regexes:
            for m in regex.finditer(text):
                #print('IGNORED: %s' % m.group(0))
                matches.add(
                        create_match(
                            (m.start(), m.end(), IGNORE_KIND, self.priority)))
        return matches
