from __future__ import unicode_literals
from lxml import etree

XTEXT = etree.XPath("string()")
XSCRIPTS = etree.XPath("script")


def get_word_count(element):
    word_count = len(XTEXT(element).split())

    # Remove script content because they are counted in the previous
    # statement.
    for script_element in XSCRIPTS(element):
        word_count -= len(XTEXT(script_element).split())

    return word_count
