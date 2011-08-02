from __future__ import unicode_literals

from docutil.etree_util import SingleXPath
from traceback import print_exc
from lxml import etree
from copy import deepcopy


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
        text = self.xtext(elem).strip()
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
        elem.clear()
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
            elif name == 'annotation_type_optional_element_summary':
                if i > anno:
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
            member = href[hindex+1:].strip()
        else:
            member = None

        addition = package + '.'

        if clazz is not None:
            count = ref.text.count(clazz)
            if count < 1:
                addition += clazz + '.'
            elif member is not None and member.startswith(clazz) and count < 2:
                addition += clazz + '.'

        if member is not None and not ref.text.endswith(member):
            ref.text = package + '.' + clazz + '.' + member
        else:
            ref.text = addition + ref.text

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
