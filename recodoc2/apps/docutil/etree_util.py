from __future__ import unicode_literals
from copy import deepcopy
from lxml import etree
from docutil.str_util import normalize, find_list, find_sentence,\
        smart_decode, clean_breaks

XTEXT = etree.XPath("string()")
XSCRIPTS = etree.XPath(".//script")
PARAGRAPHS = {'div', 'p'}


def texttail(text, tail):
    if text is None:
        text = ''
    else:
        text = text + ' '

    if tail is None:
        tail = ''

    return '{0}{1}'.format(text, tail).strip()


def get_recursive_text(element, text_parts):
    # Terminal
    if element.tag == 'pre':
        text_parts.append('')
        text_parts.append(XTEXT(element))
        text_parts.append('')
    # Terminal
    elif element.tag == 'br':
        tail = element.tail
        # This is a lone <br>
        if tail is None:
            text_parts.append('')
        else:
            text_parts.append(clean_breaks(smart_decode(tail).strip()))
    else:
        if element.tag in PARAGRAPHS:
            text_parts.append('')

        text = element.text
        if text is None:
            text = ''

        # If it is a paragraph, separate the content.
        # Otherwise, inline the content with previous line.
        if element.tag in PARAGRAPHS or len(text_parts) == 0:
            text_parts.append(clean_breaks(smart_decode(text).strip()))
        else:
            text_parts[-1] = '{0} {1}'.format(
                    text_parts[-1], clean_breaks(smart_decode(text).strip()))

        for child in element:
            get_recursive_text(child, text_parts)

        if element.tag in PARAGRAPHS:
            text_parts.append('')

        tail = element.tail
        if tail is None:
            tail = ''

        # If it is a paragraph, separate the content.
        # Otherwise, inline the content with previous line.
        if element.tag in PARAGRAPHS or len(text_parts) == 0:
            text_parts.append(clean_breaks(smart_decode(tail).strip()))
        else:
            text_parts[-1] = '{0} {1}'.format(
                    text_parts[-1], clean_breaks(smart_decode(tail).strip()))


def get_html_tree(ucontent, encoding=None):
    if encoding is not None:
        parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
    else:
        parser = etree.HTMLParser(remove_comments=True)

    tree = etree.fromstring(ucontent, parser)
    tree = tree.getroottree()
    clean_tree(tree)
    return tree


def clean_tree(tree):
    etree.strip_elements(tree, 'script', with_tail=False)


def get_word_count(elements):
    word_count = 0
    for element in elements:
        word_count += len(XTEXT(element).split())

    return word_count


def get_word_count_text(text):
    return len(text.split())


def get_text(element, xtext=XTEXT):
    return normalize(xtext(element))


def get_text_context(element, xtext=XTEXT):
    text = ''
    parent = element.getparent()
    if parent is not None:
        text = get_text(parent, xtext)
    return text.strip()


def get_sentence(element, element_text, text_context, xtext=XTEXT):
    indexes = find_list(text_context, element_text)
    size = len(indexes)
    if size == 0:
        return ''
    elif size == 1:
        return find_sentence(text_context, indexes[0],
                indexes[0] + len(element_text))
    else:
        parent = element.getparent()
        child_index_in_parent = 0
        for child in parent:
            if child == element:
                break
            else:
                temp_text = normalize(xtext(child))
                # We have encountered a child that has the same text,
                # so the first index is not the good one.
                if temp_text.find(element_text) != -1:
                    child_index_in_parent += 1

        if child_index_in_parent < size:
            return find_sentence(text_context, indexes[child_index_in_parent],
                    indexes[child_index_in_parent] + len(element_text))
        else:
            # Something went wrong.
            return find_sentence(element_text, indexes[0],
                    indexes[0] + len(element_text))


def get_complex_text(element):
    text_parts = []
    get_recursive_text(element, text_parts)
    text = '\n'.join(text_parts)
    return text


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

    def get_text_from_parent(self, parent, index=0, complex_text=False):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.get_text(elem, complex_text)
        return normalize(text)

    def get_text(self, element, complex_text=False):
        if complex_text:
            text = get_complex_text(element)
        else:
            text = self.xtext(element)
        return normalize(text)


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

    def get_text_from_parent(self, parent, index=0, complex_text=False):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.get_text(elem, complex_text)
        return normalize(text)

    def get_text(self, element, complex_text=False):
        if complex_text:
            text = get_complex_text(element)
        else:
            text = self.xtext(element)
        return normalize(text)


class HierarchyXPath(SingleXPath):
    def __init__(self, xpath_str, xpath_str_filter):
        super(HierarchyXPath, self).__init__(xpath_str, None)
        self.first_filter = etree.XPath(xpath_str_filter)

    def get_element_as_list(self, element):
        elements = []

        stop = self.first_filter(element)

        for child in element:
            if child not in stop:
                elements.append(child)
        return elements

    def get_text_from_parent(self, parent, index=0, complex_text=False):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.get_text(elem, complex_text)
        return normalize(text)

    def get_text(self, element, complex_text=False):
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
        if complex_text:
            text_parts = []
            get_recursive_text(new_element, text_parts)
        else:
            text_parts = new_element.xpath('.//text()')
        text = '\n'.join(text_parts)
        return normalize(text)


class FlatXPath(object):
    def __init__(self, xpath_str, xpath_str_filter=None, xtext=XTEXT):
        self.xpath = etree.XPath(xpath_str)
        self.xtext = xtext
        if xpath_str_filter is not None:
            self.first_filter = etree.XPath(xpath_str_filter)
        else:
            self.first_filter = None

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

    def get_text_from_parent(self, parent, index=0, complex_text=False):
        text = ''
        elem = self.get_element(parent, index)
        if elem is not None:
            text = self.get_text(elem, complex_text)
        return normalize(text)

    def get_text(self, element, complex_text=False):
        parent = element.getparent()
        if self.first_filter is not None:
            bad_elements = self.first_filter(parent)
        else:
            bad_elements = set()
        index = parent.index(element)
        majors = self.get_elements(parent)
        potentials = parent[index + 1:]
        reals = [element]
        for potential in potentials:
            if potential in majors:
                break
            elif potential not in bad_elements:
                reals.append(potential)
        text_parts = []
        for real in reals:
            get_recursive_text(real, text_parts)
            text_parts.append('')

        text = '\n'.join(text_parts)
        return normalize(text)
