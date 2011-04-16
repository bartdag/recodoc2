from __future__ import unicode_literals
from copy import deepcopy
from lxml import etree
from docutil.str_util import normalize

XTEXT = etree.XPath("string()")
XSCRIPTS = etree.XPath(".//script")


def clean_tree(tree):
    etree.strip_elements(tree, 'script', with_tail=False)


def get_word_count(elements):
    word_count = 0
    for element in elements:
        word_count += len(XTEXT(element).split())

    return word_count


def get_word_count_text(text):
    return len(text.split())


class XPathList(object):
    def __init__(self, xpath_strs, xtext=XTEXT):
        xpaths = []
        for xpath_str in xpath_strs:
            xpaths.append(etree.XPath(xpath_str))
        self.xpaths = xpaths
        self.xtext = xtext

    def get_element(self, parent, index=0):
        elem = None
        elems = self.get_elements(parent)
        if len(elems) > 0:
            elem = elems[index]
        return elem

    def get_element_as_list(self, element):
        return [element]

    def get_elements(self, parent):
        elems = []
        for xpath in self.xpaths:
            temp = xpath(parent)
            if len(temp) > 0:
                elems = temp
                break
        return elems

    def get_text_from_parent(self, parent, index=0):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.xtext(elem)
        return normalize(text)

    def get_text(self, element):
        return normalize(self.xtext(element))


class SingleXPath(object):
    def __init__(self, xpath_str, xtext=XTEXT):
        self.xpath = etree.XPath(xpath_str)
        self.xtext = xtext

    def get_element(self, parent, index=0):
        elems = self.xpath(parent)
        if len(elems) > 0:
            return elems[index]
        else:
            return None

    def get_element_as_list(self, element):
        return [element]

    def get_elements(self, parent):
        elems = self.xpath(parent)
        if len(elems) > 0:
            return elems
        else:
            return []

    def get_text_from_parent(self, parent, index=0):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.xtext(elem)
        return normalize(text)

    def get_text(self, element):
        return normalize(self.xtext(element))


class HierarchyXPath(SingleXPath):
    def __init__(self, xpath_str, xpath_str_filter, xtext=XTEXT):
        super(HierarchyXPath, self).__init__(xpath_str, xtext)
        self.first_filter = etree.XPath(xpath_str_filter)

    def get_element_as_list(self, element):
        elements = []

        stop = self.first_filter(element)

        for child in element:
            if child not in stop:
                elements.append(child)
        return elements

    def get_text_from_parent(self, parent, index=0):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.get_text(elem)
        return normalize(text)

    def get_text(self, element):
        '''Computes the text of this element by creating a deepcopy of the
           element, removing the bad children, getting the text 
           representation.
           
           This is quite inefficient, but it's the best way to get a good
           representation of the text in a hierarchical section.'''
        new_element = deepcopy(element)
        bad_elements = self.first_filter(new_element)
        for bad_element in bad_elements:
            if bad_element in new_element:
                new_element.remove(bad_element)
        text = self.xtext(new_element)
        return normalize(text)
