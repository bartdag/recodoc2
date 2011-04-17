from __future__ import unicode_literals
import re


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
