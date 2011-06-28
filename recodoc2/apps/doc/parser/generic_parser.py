from __future__ import unicode_literals
import os
import logging
from multiprocessing.pool import Pool
from traceback import print_exc
from lxml import etree
from django.db import transaction, connection
from django.conf import settings
from docutil.str_util import clean_breaks
from docutil.etree_util import clean_tree, get_word_count, XPathList,\
        SingleXPath, get_word_count_text, get_text_context, get_sentence
from docutil.url_util import get_relative_url, get_path
from docutil.commands_util import chunk_it, import_clazz, get_encoding
from docutil.progress_monitor import NullProgressMonitor
from codebase.models import DOCUMENT_SOURCE
from codebase.actions import get_project_code_words, get_default_kind_dict,\
        parse_single_code_references, get_java_strategies,\
        get_default_filters, classify_code_snippet
from doc.models import Document, Page, Section

DEFAULT_POOL_SIZE = 4

logger = logging.getLogger("recodoc.doc.parser.generic")


@transaction.autocommit
def sub_process_parse(pinput):
    try:
        # Unecessary if already closed by parent process.
        # But it's ok to be sure.
        #print('In subprocess')
        connection.close()
        (parser_clazz, doc_pk, parse_refs, pages) = pinput
        parser = import_clazz(parser_clazz)(doc_pk)
        #print('Got input')
        print('Input: {0}'.format(pinput))
        for page_input in pages:
            #print('Considering page {0}'.format(page_input))
            if page_input is not None:
                (local_path, page_url) = page_input
                print('Parsing {0}'.format(page_url))
                parser.parse_page(local_path, page_url, parse_refs)
                print('Parsed {0}'.format(page_url))
        #print('Returning True')
        return True
    except Exception:
        print_exc()
        #print('Returning False')
        return False
    finally:
        # Manually close this connection
        #print('Closing connection')
        connection.close()


@transaction.autocommit
def parse(document, pages, parse_refs=True,
        progress_monitor=NullProgressMonitor(),
        pool_size=DEFAULT_POOL_SIZE):
    progress_monitor.start('Parsing Pages', pool_size + 1)

    progress_monitor.info('Building code words cache')
    get_project_code_words(document.project_release.project)

    # Prepare input
    pages = [(page.local_url, page.url) for page in
            pages.values() if page.local_url is not None]
    pages_chunks = chunk_it(pages, pool_size)
    inputs = []
    for pages_chunk in pages_chunks:
        inputs.append((document.parser, document.pk, parse_refs, pages_chunk))

    # Close connection to allow the new processes to create their own.
    connection.close()

    # Split work
    progress_monitor.info('Sending {0} chunks to worker pool'
            .format(len(inputs)))
    pool = Pool(pool_size)
    for result in pool.imap_unordered(sub_process_parse, inputs, 1):
        progress_monitor.work('Parsed 1/{0} of the pages'.\
                format(pool_size), 1)

    # Word Count
    word_count = 0
    for page in document.pages.all():
        word_count += page.word_count
    document.word_count = word_count
    document.save()
    progress_monitor.work('Counted Total Words', 1)

    pool.close()
    progress_monitor.done()


class ParserLoad(object):
    def __init__(self):
        self.tree = None
        self.code_words = None
        self.sections = None
        self.parse_refs = True
        self.mix_mode = False


class GenericParser(object):

    POOL_SIZE = 4

    xbody = SingleXPath("//body[1]")
    '''Page body'''

    xtitles = XPathList(['//h1[1]', '//title[1]', '//h2[1]'])
    '''Page title'''

    xtopsection = None
    '''XPath to find the top-level section. Optional'''

    xsections = None
    '''XPath to find the sections in a page. Required'''

    xsectiontitle = None
    '''XPath to find a section title. Required'''

    xcoderef = None
    '''XPath to find single code references. Required'''

    xcoderef_url = None
    '''Text that must be found in a url to be considered a coderef.
       Optional'''

    xsnippet = None
    '''XPath to find code snippets. Required'''

    xparagraphs = None
    '''XPath to find the text minus the snippets in a section. Required only
       if mix_mode=True'''

    def __init__(self, document_pk):
        self.document = Document.objects.get(pk=document_pk)
        self.kinds = get_default_kind_dict()
        self.kind_strategies = get_java_strategies()

    def parse_page(self, page_local_path, page_url, parse_refs=True):
        try:
            print('Starting parser {0}'.format(page_url))
            relative_url = get_relative_url(get_path(page_local_path))
            page = Page(url=page_url,
                    file_path=relative_url,
                    document=self.document)
            page.save()
            print('After save {0}'.format(page_url))
            load = ParserLoad()
            load.parse_refs = parse_refs

            self._build_code_words(load)
            print('Parser will be processing page {0}'.format(page_url))
            self._process_page(page, load)
            print('Parser processed page {0}'.format(page_url))
        except Exception:
            print('An exception occurred in the parser {0}'.format(page_url))
            print_exc()

    def _build_code_words(self, load):
        # Build code words and put it in self.load
        load.code_words = \
            get_project_code_words(self.document.project_release.project)

    def _process_page(self, page, load):
        print('step 1 {0}'.format(page.url))
        page_path = os.path.join(settings.PROJECT_FS_ROOT, page.file_path)
        page_file = open(page_path)
        content = page_file.read()
        page_file.close()
        encoding = get_encoding(content)
        parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
        load.tree = etree.fromstring(content, parser).getroottree()
        clean_tree(load.tree)

        page.title = self._process_page_title(page, load)
        page.title = clean_breaks(page.title, True)

        body = self.xbody.get_element(load.tree)
        body_elements = self.xbody.get_element_as_list(body)
        page.word_count = get_word_count(body_elements)
        page.xpath = load.tree.getpath(body)
        page.save()

        self._process_init_page(page, load)
        check = self._check_parser(page, load)
        if not check:
            return
        self._process_sections(page, load)

    def _process_page_title(self, page, load):
        title = self.xtitles.get_text_from_parent(load.tree)
        if title is None or title == '':
            title = 'Default Title'
            logger.warning('No title for page {0}'.format(page.file_path))
        return title

    def _process_init_page(self, page, load):
        pass

    def _check_parser(self, page, load):
        check = True

        if self.xsections is None:
            logger.error('xsections field needs to be defined.')
            return False
        elif self.xsectiontitle is None:
            logger.error('xsectiontitle field needs to be defined.')
            return False
        elif self.xparagraphs is None and load.mix_mode:
            logger.error('xparagraphs needs to be defined if mix_mode is on')

        return check

    def _process_sections(self, page, load):
        print('step 2 {0}'.format(page.url))
        sections = []
        sections_number = {}

        if self.xtopsection is not None:
            section_element = self.xtopsection.get_element(load.tree)
            if section_element is not None and self._is_top_section(page, load,
                    section_element):
                text = self.xtopsection.get_text(section_element)
                section = self._create_section(page, load, section_element,
                        text)
                if section is not None:
                    sections.append(section)
                    sections_number[section.number] = section

        section_elements = self.xsections.get_elements(load.tree)
        for section_element in section_elements:
            if self._is_section(page, load, section_element):
                text = self.xsections.get_text(section_element)
                section = self._create_section(page, load, section_element,
                        text)
                if section is not None:
                    sections.append(section)
                    sections_number[section.number] = section

        self._find_section_parent(page, load, sections, sections_number)

        if load.parse_refs:
            self._parse_section_references(page, load, sections)

    def _is_top_section(self, page, load, section_element):
        '''Indicates whether or not an element is a top section.'''
        return True

    def _is_section(self, page, load, section_element):
        '''Indicates whether or not an element is a section.'''
        return True

    def _create_section(self, page, load, section_element, text):
        tree = load.tree
        title = \
            self.xsectiontitle.get_text_from_parent(section_element).strip()
        xpath = tree.getpath(section_element)
        number = \
            self._get_section_number(page, load, section_element, title,
                xpath).strip()
        word_count = get_word_count_text(text)
        section = Section(
                page=page,
                title=title,
                xpath=xpath,
                file_path=page.file_path,
                url=page.url,
                number=number,
                word_count=word_count)
        section.save()
        return section

    def _get_section_number(self, page, load, section_element, title, xpath):
        '''Returns the section number (e.g., 1.2.3.) of a section.'''
        return '1'

    def _find_section_parent(self, page, load, sections, sections_number):
        pass

    def _parse_section_references(self, page, load, sections):
        print('step 3 {0}'.format(page.url))
        s_code_references = []
        snippets = []

        # get code references
        code_ref_elements = self.xcoderef.get_elements(load.tree)
        for i, code_ref_element in enumerate(code_ref_elements):
            self._add_code_ref(i, code_ref_element, page, load,
                    s_code_references)

        # get snippets
        snippet_elements = self.xsnippet.get_elements(load.tree)
        for i, snippet_element in enumerate(snippet_elements):
            self._add_code_snippet(i, snippet_element, page, load, snippets)

        # Find section for each code reference
        for code_reference in s_code_references:
            self._find_section(code_reference, sections, page, load)

        # Find snippet for each code reference
        for snippet in snippets:
            self._find_section(snippet, sections, page, load)

        # Process sections' title
        for section in sections:
            self._process_title_references(page, load, section)

        # If mix mode, analyze the text of each section.
        if load.mix_mode:
            for section in sections:
                if self._process_mix_mode_section(page, load, section):
                    self._process_mix_mode(page, load, section)

    def _is_valid_code_ref(self, code_ref_element, load):
        if code_ref_element.tag == 'a':
            if code_ref_element.getparent().tag == 'pre':
                return False
            if 'href' not in code_ref_element.attrib:
                return False
            elif len(code_ref_element) > 0 and code_ref_element[0].tag in \
                    {'tt', 'code', 'pre', 'span', 'em', 'b', 'strong', 'i'}:
                return False
            elif self.xcoderef_url is not None and \
                    code_ref_element.attrib['href'].\
                    find(self.xcoderef_url) == -1:
                return False
        return True

    def _add_code_ref(self, index, code_ref_element, page, load,
            s_code_references):

        # If the code ref is a link, filter the link to ensure that
        # it is a real code ref.
        if not self._is_valid_code_ref(code_ref_element, load):
            return

        text = self.xcoderef.get_text(code_ref_element)
        text = clean_breaks(text).strip()

        # Not significant
        if len(text) < 2 or text.isdigit():
            return

        text_context = get_text_context(code_ref_element)
        sentence = get_sentence(code_ref_element, text, text_context)

        (text, kind_hint) = self._get_code_ref_kind(code_ref_element, text)

        xpath = load.tree.getpath(code_ref_element)
        for code in parse_single_code_references(text, kind_hint,
                self.kind_strategies, self.kinds):
            code.xpath = xpath
            code.file_path = page.file_path
            code.source = DOCUMENT_SOURCE
            code.index = index
            code.sentence = sentence
            code.paragraph = text_context
            code.project = self.document.project_release.project
            code.project_release = self.document.project_release
            code.resource = self.document
            code.save()
            s_code_references.append(code)

    def _add_code_snippet(self, index, snippet_element, page, load, snippets):
        text = self.xsnippet.get_text(snippet_element)
        xpath = load.tree.getpath(snippet_element)
        snippet = classify_code_snippet(text, get_default_filters())

        if snippet is None:
            return

        snippet.xpath = xpath
        snippet.file_path = page.file_path
        snippet.source = DOCUMENT_SOURCE
        snippet.index = index
        snippet.project = self.document.project_release.project
        snippet.project_release = self.document.project_release
        snippet.resource = self.document
        snippet.save()
        snippets.append(snippet)

    def _find_section(self, reference, sections, page, load):
        parent_section = None
        max_len = 0

        for section in sections:
            section_len = len(section.xpath)
            if reference.xpath.startswith(section.xpath) and \
               section_len > max_len:
                    parent_section = section
                    max_len = section_len

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

    def _process_title_references(self, page, load, section):
        text_context = section.title
        sentence = section.title

        kind_hint = self.kinds['unknown']
        xpath = section.xpath
        for code in parse_single_code_references(sentence, kind_hint,
                self.kind_strategies, self.kinds, strict=True):
            code.xpath = xpath
            code.file_path = page.file_path
            code.source = DOCUMENT_SOURCE
            code.index = -100000
            code.sentence = sentence
            code.paragraph = text_context
            code.project = self.document.project_release.project
            code.project_release = self.document.project_release
            code.title_context = section
            code.local_context = section
            code.mid_context = self._get_mid_context(section)
            code.global_context = page
            code.resource = self.document
            code.save()

    def _process_mix_mode_section(self, page, load, section):
        return True

    def _process_mix_mode(self, page, load, section):
        section_element = load.tree.xpath(section.xpath)[0]
        section_text = self.xparagraphs.get_text(section_element)
        section_refs = section.code_references.all()
        existing_refs = [code_ref.content for code_ref in section_refs]
        kind_hint = self.kinds['unknown']
        mid_context = self._get_mid_context(section)
        for i, code in enumerate(
                parse_single_code_references(
                    section_text, kind_hint, self.kind_strategies,
                    self.kinds, find_context=True, strict=True,
                    existing_refs=existing_refs)):
            code.xpath = section.xpath
            code.file_path = page.file_path
            code.index = 1000 + i
            code.project = self.document.project_release.project
            code.project_release = self.document.project_release
            code.local_context = section
            code.mid_context = mid_context
            code.global_context = page
            code.resource = self.document
            code.save()

    def _get_code_ref_kind(self, code_ref_tag, text):
        kind_hint = self.kinds['unknown']

        if 'class' in code_ref_tag.attrib:
            clazz = code_ref_tag.attrib['class']
            if clazz.find('method') > -1:
                kind_hint = self.kinds['method']
            elif clazz.find('class') > -1 or clazz.find('interface') > -1 or \
                 clazz.find('type') > -1:
                kind_hint = self.kinds['class']

        return (text, kind_hint)

    def _get_mid_context(self, section):
        '''Returns mid-level sections.
           e.g., {3., 3.1, 3.1.1} will return 3.1
        '''
        if section is None:
            return None
        elif section.parent is None:
            return None
        if section.parent.parent is None:
            return section.parent
        else:
            return self._get_mid_context(section.parent)
