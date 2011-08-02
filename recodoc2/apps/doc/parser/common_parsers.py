from __future__ import unicode_literals
from traceback import print_exc
from lxml import etree
from copy import deepcopy
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


class JavadocParser(FlatParentMixin, NoNumberMixin, GenericParser):
    
    xtitles = SingleXPath('//title[1]')

    xsections = FlatXPath('//h2 | //h3')

    xcoderef_url = '../'

    xcoderef = SingleXPath('//code')

    xsnippet = SingleXPath('//pre')

    xpackage = SingleXPath('//body/h2[1]/font[1]')

    def _process_page_title(self, page, load):
        title = super(JavadocParser, self)._process_page_title(page, load)
        index = title.find('(')
        if index > -1:
            title[:index-1].strip()
        return title

    def _process_init_page(self, page, load):
        load.current_elements = self._get_current_element(page, load)
        load.tree = self._remove_generated_content(page, load)

    def _is_class_page(self, page):
        url = page.url
        path = url.split('/')[-1]
        # This will indicate whether this is a class or not.
        # Obviously, if a class starts with a lowercase, this does not work.
        return path[0].isupper()

    def _remove_generated_content(self, page, load):
        if self._is_class_page(page):
            transformer = JavadocTransformer(load.current_element['package'],
                    load.current_element['type'])
            return transformer.transform(load.tree)
        else:
            return load.tree

    def _get_current_element(self, page, load):
        current_element = {}
        if self._is_class_page(page):
            package_element = self.xpackage.get_element(load.tree)
            if package_element is not None:
                current_element['package'] = \
                    self.xpackage.get_text(package_element)
                current_element['type'] = self._process_page_title(page, load)


class JavadocTransformer(object):

    xpackage = SingleXPath('//body/h2[1]/font[1]')

    xbody = SingleXPath('//body')

    xtext = etree.XPath("string()")

    xbold = SingleXPath('.//b')

    xcode = SingleXPath('//code')

    def __init__(self, package_name, clazz_name):
        self.package_name = package_name
        self.clazz_name = clazz_name

    def transform(self, tree):
        new_tree = deepcopy(tree)

        # Remove package
        elem = self.xpackage.get_element(new_tree)
        parent = elem.getparent()
        parent.remove(elem)
        self.change_title(parent, False)
         
        body = self.xbody.get_element(new_tree)

        self.remove_headers(body)
        self.remove_tables(body)

        upper_bound = len(body)
        indexes = self.get_toc(body)
        (constructor, method, field, anno, enum) = indexes
        to_remove = []
        if constructor > -1:
            to_remove.extend(self.modify_constructor(body, constructor,
                self.get_upper_bound(constructor, indexes, upper_bound)))
        if method > -1:
            to_remove.extend(self.modify_method(body, method,
                self.get_upper_bound(method, indexes, upper_bound)))
        if field > -1:
            to_remove.extend(self.modify_field(body, field,
                self.get_upper_bound(field, indexes, upper_bound)))
        if anno > -1:
            to_remove.extend(self.modify_field(body, anno,
                self.get_upper_bound(anno, indexes, upper_bound)))
        if enum > -1:
            to_remove.extend(self.modify_field(body, enum,
                self.get_upper_bound(enum, indexes, upper_bound)))
        
        for (parent, elem) in to_remove:
            parent.remove(elem)

        self.modify_code_ref(new_tree)

        return new_tree

    def change_title(self, elem, change_clazz=True):
        text = elem.text.strip()
        temp_index = text.find('(')

        # If this is a method/constructor, spaces exist between parameters
        if temp_index > -1:
            index = text[:temp_index].rfind(' ')
        else:
            index = text.rfind(' ')

        if index > -1:
            text = text[index:].strip()
        
        if change_clazz:
            text = self.package_name + '.' + self.clazz_name + '.' + text
        else:
            text = self.package_name + '.' + text
        elem.text = text

    def remove_headers(self, body):
        to_remove = []
        # Remove headers
        for child in body:
            if child.tag == 'h2':
                break
            to_remove.append((body, child))
        
        for (parent, elem) in to_remove:
            parent.remove(elem)
        to_remove = []

        # Remove other headers (subclasses and that kind of stuff)
        stop = False
        for child in body[1:]:
            if stop:
                to_remove.append((body, child))
                break
            if child.tag == 'hr':
                stop = True
            to_remove.append((body, child))
        for (parent, elem) in to_remove:
            parent.remove(elem)

    def remove_tables(self, body):
        to_remove = []
        for child in body:
            if child.tag == 'table' or child.tag == 'hr':
                to_remove.append((body, child))

        for (parent, elem) in to_remove:
            parent.remove(elem)
        to_remove = []

    def get_upper_bound(self, i, bounds, max_upper):
        upper = max_upper
        for bound in bounds:
            if bound > i and bound < upper:
                upper = bound

        return upper

    def get_toc(self, body):
        constructor = method = field = anno = enum = -1

        for i, child in enumerate(body):
            name = None
            if child.tag == 'p':
                if len(child) == 1 and child[0].tag == 'a':
                    name = child[0].get('name')
            elif child.tag == 'a':
                name = child.get('name')
            if name == 'constructor_detail':
                constructor = i
            elif name == 'method_detail':
                method = i
            elif name == 'field_detail':
                field = i
            elif name == 'annotation_type_element_detail':
                anno = i
            elif name == 'enum_constant_detail':
                enum = i

        return (constructor, method, field, anno, enum)

    def modify_constructor(self, body, constructor, bound):
        to_remove = []
        children = body[constructor+1:bound]
        
        for i, child in enumerate(children):
            if child.tag == 'h3':
                pre = children[i+1]
                child.text = self.xtext(pre)
                self.change_title(child)
                to_remove.append((body, pre))
                to_remove.extend(self.filter_params(children[i+2]))
        
        return to_remove

    def modify_method(self, body, method, bound):
        to_remove = []
        children = body[method+1:bound]

        for i, child in enumerate(children):
            if child.tag == 'h3':
                pre = children[i+1]
                child.text = self.xtext(pre)
                self.change_title(child)
                to_remove.append((body, pre))
                to_remove.extend(self.filter_params(children[i+2]))

        return to_remove

    def modify_field(self, body, field, bound):
        to_remove = []

        children = body[field+1:bound]

        for i, child in enumerate(children):
            if child.tag == 'h3':
                pre = children[i+1]
                child.text = self.xtext(pre)
                self.change_title(child)
                to_remove.append((body, pre))

        return to_remove

    def filter_params(self, description):
        to_remove = []
        
        elements = self.xbold.get_elements(description)

        for element in elements:
            if element.text.strip() == 'Specified by:':
                to_remove.append((element.getparent().getparent().getparent(),
                        element.getparent().getparent()))

        return to_remove

    def modify_code_ref(self, tree):
        elements = self.xcode.get_elements(tree)

        for element in elements:
            try:
                link = ref = None
                parent = element.getparent()
                if self._is_linked_ref(parent):
                    link = parent
                    ref = element

                if len(element) > 0:
                    child = element[0]
                    if self._is_linked_ref(child):
                        link = child
                        ref = child

                if link is not None:
                    self.modify_ref(link, ref)
            except Exception:
                print('Error while modifying a reference')
                print_exc()

    def modify_ref(self, link, ref):
        href = link.get('href')
        rindex = href.rfind('/')
        package = href[:rindex].replace('../','').replace('/','.')

        href = href[rindex+1:]
        index = href.find('.html')
        hindex = href.find('#')

        if index > -1:
            clazz = href[:index].strip()
        else:
            clazz = None
        if hindex > -1:
            member = href[hindex+1].strip()
        else:
            member = None

        addition = package + '.'

        if clazz is not None:
            count = ref.text.count(clazz)
            if count < 1:
                addition += clazz + '.'
            elif member is not None and member.startswith(clazz) and count < 2:
                addition += clazz + '.'

        ref.text = addition + ref.text

        if member is not None and member.endswith(')') and not \
            ref.text.endswith(')'):
            ref.text += '()'

    def _is_linked_ref(self, parent):
        if parent.tag != 'a':
            return False
        else:
            href = parent.get('href')
            return href is not None and href.startswith('../')


    # TODO debug parentheses if there are none for methods!


def save_file(tree):
    '''Temporary function to help me debug the transformer!'''
    s = etree.tostring(tree, pretty_print=True)
    f = open('/home/barthelemy/temp/toto.html', 'w')
    f.write(s)
    f.close()
