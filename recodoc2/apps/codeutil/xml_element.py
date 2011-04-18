from __future__ import unicode_literals
import re
from codeutil.parser import create_match
from codeutil.other_element import ANCHOR_EMAIL_PATTERN_RE,\
    ANCHOR_URL_PATTERN_RE


### CONSTANTS ###

XML_LANGUAGE = 'x'


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

