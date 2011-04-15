from __future__ import unicode_literals
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
        text = None
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
        text = None
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
        text = None
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.get_text(elem)
        return normalize(text)

    def get_text(self, element):
        stop = self.first_filter(element)
        text = ''
        for child in element:
            if child not in stop:
                text += self.xtext(child)
                text += ' '
        return normalize(text)
