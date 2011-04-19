from __future__ import unicode_literals
import re
from codeutil.parser import create_match


OTHER_LANGUAGE = 'o'

IGNORE_KIND = 'ignore'


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
