from __future__ import unicode_literals
import re
from docutil.str_util import find_list
from docutil.etree_util import HierarchyXPath, SingleXPath
from doc.parser.generic_parser import GenericParser

NUMBERS_PATTERN = [
    re.compile(r'((?:[\d]+[.]?)+) .'),
    re.compile(r'Chapter (\d+\.) .+', re.IGNORECASE),
]


def get_number_from_title(title, regexes=NUMBERS_PATTERN):
    number = '1.'
    for regex in regexes:
        match = regex.match(title)
        if match is not None:
            number = match.group(1)
            break
    return number.strip()


class StandardNumberMixin(object):

    def _get_section_number(self, page, load, section_element, title, xpath):
        return get_number_from_title(title)


class NoNumberMixin(object):

    def _get_section_number(self, page, load, section_element, title, xpath):
        return ''


class NumberDotParentMixin(object):

    def _find_section_parent(self, page, load, sections, sections_number):
        for section in sections:
            indexes = find_list(section.number, '.')
            number_of_dots = len(indexes)
            parent_number1 = parent_number2 = None
            end_with_dot = section.number.strip().endswith('.')

            if end_with_dot and number_of_dots > 1:
                # e.g., if section.number = 2.3.4.
                # then parent_number = 2.3.
                # unlikely parent_number = 2.3
                parent_number1 = section.number[:indexes[-2] + 1]
                parent_number2 = section.number[:indexes[-2]]
            elif not end_with_dot and number_of_dots > 0:
                # e.g., if section number = 2.3.4
                # then likely parent_number = 2.3
                # unlikely parent_number 2.3.
                parent_number1 = section.number[:indexes[-1]]
                parent_number2 = section.number[:indexes[-1] + 1]

            if parent_number1 is not None and parent_number1 in sections_number:
                section.parent = sections_number[parent_number1]
                section.save()
            elif parent_number2 is not None and \
                    parent_number2 in sections_number:
                section.parent = sections_number[parent_number2]
                section.save()

class XPathParentMixin(object):

    def _find_section_parent(self, page, load, sections, sections_number):
        for section in sections:
            element = load.tree.xpath(section.xpath)[0]
            parent_xpath = load.tree.getpath(element.getparent())
            for temp in sections:
                if temp.xpath == parent_xpath:
                    section.parent = temp
                    section.save()
                    break


class NewDocBookParser(NumberDotParentMixin, StandardNumberMixin,
        GenericParser):

    xtopsection = HierarchyXPath('//div[@class="chapter"]',
            'div[@class="section"]')

    xsections = HierarchyXPath('//div[@class="section"]',
            'div[@class="section"]')

    xsectiontitle = SingleXPath('.//div[@class="titlepage"]')

    xcoderef = SingleXPath('//code | //tt | //em | //span[@class="property"]')

    xsnippet = SingleXPath('//pre')

    def __init__(self, document_pk):
        super(NewDocBookParser, self).__init__(document_pk)


class MavenParser(XPathParentMixin, NoNumberMixin, GenericParser):
    xtitles = SingleXPath('//title[1]')
    '''Page title'''

    xsections = HierarchyXPath(
            '//div[@class="section"] | //div[@class="subsection"]',
            'div[@class="section"] | div[@class="subsection"]')

    xsectiontitle = SingleXPath('h2[1] | h3[1] | h4[1]')

    xcoderef = SingleXPath('//code | //tt | //em | //a')

    xcoderef_url = 'api'

    xsnippet = SingleXPath('//pre')

    def _process_page_title(self, page, load):
        title = super(MavenParser, self)._process_page_title(page, load)
        index = title.rfind('-')
        if index > -1 and index < (len(title) + 2):
            title = title[index + 2:]

        return title.strip()
