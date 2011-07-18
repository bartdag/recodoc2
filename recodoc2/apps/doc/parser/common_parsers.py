from __future__ import unicode_literals
import re
import logging
from docutil.str_util import find_list
from docutil.etree_util import HierarchyXPath, SingleXPath, FlatXPath
from doc.parser.generic_parser import GenericParser

NUMBERS_PATTERN = [
    re.compile(r'((?:[\d]+[.]?)+) .'),
    re.compile(r'Chapter (\d+\.) .+', re.IGNORECASE),
]

logger = logging.getLogger("recodoc.doc.parser.common")


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


class FlatParentMixin(object):

    def _find_section_parent(self, page, load, sections, sections_number):
        for section in sections:
            if section.xpath.find('h1') > -1:
                # This is a top level section. No parent!
                continue
            element = load.tree.xpath(section.xpath)[0]
            parent = element.getparent()
            section_index = parent.index(element)
            section_parent = None
            max_index = -1

            for temp in sections:
                if temp == section:
                    continue
                else:
                    temp_elem = load.tree.xpath(temp.xpath)[0]
                    parent_index = parent.index(temp_elem)
                    if section_index > parent_index > max_index and \
                            self._can_be_parent(temp.xpath, section.xpath):
                        max_index = parent_index
                        section_parent = temp

            if section_parent is not None:
                section.parent = section_parent
                section.save()

    def _can_be_parent(self, parent_xpath, child_xpath):
        return (parent_xpath.find('h1') > -1 and child_xpath.find('h2') > -1) \
                or \
                (parent_xpath.find('h2') > -1 and child_xpath.find('h3') > -1)


    def _find_section(self, reference, sections, page, load):
        parent_section = None

        if len(sections) == 0:
            reference.delete()
            return

        parent = load.tree.xpath(sections[0].xpath)[0].getparent()
        ref_element = load.tree.xpath(reference.xpath)[0]
        ref_index = self._get_ref_index(parent, ref_element)
        max_index = -1

        if ref_index > -1:
            for section in sections:
                section_index = parent.index(load.tree.xpath(section.xpath)[0])
                if ref_index > section_index > max_index:
                    parent_section = section
                    max_index = section_index

        if parent_section != None:
            reference.local_context = parent_section
            reference.mid_context = self._get_mid_context(parent_section)
            reference.global_context = parent_section.page
            reference.resource = self.document
            reference.save()
        else:
            content = None
            try:
                content = reference.content
            except Exception:
                content = 'SNIPPET'
            logger.debug('orphan ref {0}, path {1}, page {2}'
                    .format(content, reference.xpath, page.title))
            # Delete, otherwise, it won't be deleted when clearning document.
            reference.delete()

    def _get_ref_index(self, parent, ref_element):
        index = -1
        while ref_element is not None:
            temp_parent = ref_element.getparent()
            if temp_parent == parent:
                index = parent.index(ref_element)
                break
            else:
                ref_element = temp_parent
        return index


class NewDocBookParser(NumberDotParentMixin, StandardNumberMixin,
        GenericParser):

    xtopsection = HierarchyXPath('//div[@class="chapter"]',
            'div[@class="section"]')

    xsections = \
        HierarchyXPath('//div[@class="section"]|//div[@class="sect1"]|//div[@class="sect2"]|//div[@class="sect3"]',
            'div[@class="section"]|div[@class="sect1"]|div[@class="sect2"]|div[@class="sect3"]')

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


class XStreamParser(FlatParentMixin, NoNumberMixin, GenericParser):
    xtitles = SingleXPath('//title[1]')

    '''Page title'''

    xsections = FlatXPath('//div[@id="content"]/h1 | //div[@id="content"]/h2'
            ' | //div[@id="content"]/h3 | //body/h1 | //body/h2 | //body/h3')

    xsectiontitle = SingleXPath('.')

    xcoderef_url = 'javadoc'

    xcoderef = SingleXPath('//code | //tt | //em | //a')

    xsnippet = SingleXPath('//pre')

    xparagraphs = FlatXPath('//div[@id="content"]/h1 | //div[@id="content"]/h2'
            ' | //div[@id="content"]/h3 | //body/h1 | //body/h2 | //body/h3',
            './pre | ./div')

    def _process_page_title(self, page, load):
        title = super(XStreamParser, self)._process_page_title(page, load)
        index = title.rfind('-')
        if index > -1 and index < (len(title) + 2):
            title = title[index + 2:]

        return title.strip()

    def _process_init_page(self, page, load):
        load.mix_mode = True
