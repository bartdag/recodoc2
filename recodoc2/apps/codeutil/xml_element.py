from __future__ import unicode_literals
import re


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
