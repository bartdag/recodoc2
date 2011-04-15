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


class NumberDotParentMixin(object):

    def _find_section_parent(self, page, load, sections, sections_number):
        for section in sections:
            indexes = find_list(section.number, '.')
            if len(indexes) > 1:
                # e.g., if section.number = 2.3.4.
                # then parent_number = 2.3.
                parent_number = section.number[:indexes[-2] + 1]
                if parent_number in sections_number:
                    section.parent = sections_number[parent_number]
                    section.save()


class NewDocBookParser(NumberDotParentMixin, StandardNumberMixin,
        GenericParser):

    xtopsection = HierarchyXPath('//div[@class="chapter"]',
            'div[@class="section"]')

    xsections = HierarchyXPath('//div[@class="section"]',
            'div[@class="section"]')

    xsectiontitle = SingleXPath('.//div[@class="titlepage"]')

    def __init__(self, document_pk):
        super(NewDocBookParser, self).__init__(document_pk)
