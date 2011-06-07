from __future__ import unicode_literals
import re
import logging
from codeutil.parser import create_match
from codeutil.other_element import ANCHOR_EMAIL_PATTERN_RE,\
    ANCHOR_URL_PATTERN_RE


logger = logging.getLogger("recodoc.codeutil.xml")


### CONSTANTS ###

XML_LANGUAGE = 'x'

THRESHOLD_XML = 0.50


### REGEX ###

XML_PATTERN_RE = re.compile(r'''
    <                      # Tag opening
    [?!/]?                 # Optional tag closing
    (?P<tag_name>[A-Z][-:_A-Z0-9]*) # Anything except 
    [^>]*                  # Anything else, probably attributes
    >                      # Tag ending
    ''', re.VERBOSE | re.IGNORECASE)


FUZZY_XML_PATTERN_RE = re.compile(r'''
    <                             # Tag opening
    [/]?                          # Optional tag closing
    (?P<tag_name>[A-Z][-_:A-Z0-9]*) # Anything except 
    \s*
    (?:[^>\s]*\s*=\s*[^>\s]*)*    # Anything else, probably attributes
    \s*
    [>]?                          # Tag ending
    ''', re.VERBOSE | re.IGNORECASE)


XML_ATTRIBUTE_VALUE_PAIR_RE = re.compile(r'''
    (?P<attribute_name>[\w_\-]*)        # Attribute name
    [\s]*=[\s]*
    (?P<value>
    "[^"]*" |
    '[^']*'
    )
    ''', re.VERBOSE | re.IGNORECASE)


# For Snippet identification
XML_ATTRIBUTE_VALUE_PAIR_STRICT_RE = re.compile(r'''
    (?P<attribute_name>[\w_\-]*)        # Attribute name
    =                                   # No space allowed near =
    (?P<value>
    "[^"]*" |
    '[^']*'
    )
    ''', re.VERBOSE | re.IGNORECASE)

# Starts with an xml tag
XML_STRICT_PATTERN1_RE = re.compile(r'''
    ^[\s]*
    <                      # Tag opening
    [?!/]?                 # Optional tag closing
    (?P<tag_name>[A-Z][-:_A-Z0-9]*) # Anything except 
    [^>]*                  # Anything else, probably attributes
    >                      # Tag ending                 
    ''', re.VERBOSE | re.IGNORECASE)


# Ends with an xml tag
XML_STRICT_PATTERN2_RE = re.compile(r'''
    .*
    <                      # Tag opening
    [/]?                   # Optional tag closing
    (?P<tag_name>[A-Z][-:_A-Z0-9]*) # Anything except 
    [^>]*                  # Anything else, probably attributes
    >                      # Tag ending 
    [\s]*$                                 
    ''', re.VERBOSE | re.IGNORECASE)


XML_STRICT_OPENING_RE = re.compile(r'''
    ^[\s]*
    <
    [?!]?
    (?P<tag_name>[A-Z][-:_A-Z0-9]*\b) # Anything except 
    [^>]*                  # Anything else, probably attributes
    ''', re.VERBOSE | re.IGNORECASE)


XML_STRICT_CLOSING_RE = re.compile(r'''
    [^>]*
    \b(?P<tag_name>[A-Z][-:_A-Z0-9]*) # Anything except 
    [/]?
    >
    [\s]*$
    ''', re.VERBOSE | re.IGNORECASE)


XML_STRICT_COMMENT_RE = re.compile(r'''
    <!--.*?-->
        ''', re.VERBOSE)

### Functions ###

def get_xml_pair(xml_text, offset, priority):
    children = []
    for pair in XML_ATTRIBUTE_VALUE_PAIR_RE.finditer(xml_text):
        children.append(
                (pair.start(1) + offset,
                 pair.end(1) + offset,
                 'xml attribute',
                 priority))
        children.append(
                (pair.start(2) + offset,
                 pair.end(2) + offset,
                 'xml attribute value',
                 priority))
    return children

### Snippet Identification ###

def is_xml_snippet(text):
    return is_xml_lines(text.split('\n'))


def is_xml_lines(lines):
    xml_lines = 0
    empty_lines = 0
    confidence = 0.0
    lines_size = len(lines)
    
    for line in lines:
        if len(line.strip()) == 0:
            empty_lines += 1
        elif (XML_STRICT_PATTERN1_RE.match(line) or
                XML_STRICT_PATTERN2_RE.match(line) or
                XML_STRICT_COMMENT_RE.match(line)) and not \
                (ANCHOR_URL_PATTERN_RE.search(line) or \
                 ANCHOR_EMAIL_PATTERN_RE.search(line)):
            xml_lines += 1
        elif lines_size > 1:
            if XML_STRICT_OPENING_RE.match(line) or \
            XML_STRICT_CLOSING_RE.match(line) or \
            line.strip().startswith('<--') or \
            line.strip().endswith('-->') or \
            XML_ATTRIBUTE_VALUE_PAIR_STRICT_RE.search(line):
                xml_lines += 1

    non_empty_lines = lines_size - empty_lines

    if non_empty_lines > 0:
        confidence = float(xml_lines) / (len(lines) - empty_lines)
    
    if -0.10 <= (confidence - THRESHOLD_XML) <= 0:
        logger.info('Almost reached XML threshold: {0}'.format(lines))
    
    return (confidence >= THRESHOLD_XML, confidence)


### Identification and Classification ###

class XMLStrategy(object):

    priority = 25

    def match(self, text):
        matches = set()
        for m in XML_PATTERN_RE.finditer(text):
            if ANCHOR_URL_PATTERN_RE.search(m.group(0)) or\
                ANCHOR_EMAIL_PATTERN_RE.match(m.group(0)):
                continue
            xml_element = m.group(0)
            offset = m.start()
            children = get_xml_pair(xml_element,offset,self.priority)
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'xml element', self.priority),
                        children))
        for m in FUZZY_XML_PATTERN_RE.finditer(text):
            if ANCHOR_URL_PATTERN_RE.match(m.group(0)) or\
                ANCHOR_EMAIL_PATTERN_RE.match(m.group(0)):
                continue
            xml_element = m.group(0)
            offset = m.start()
            children = get_xml_pair(xml_element,offset,self.priority)
            matches.add(
                    create_match(
                        (m.start(), m.end(), 'xml element', self.priority),
                        children))
        return matches

