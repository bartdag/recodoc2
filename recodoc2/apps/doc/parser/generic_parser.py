from __future__ import unicode_literals
import os
import logging
from multiprocessing.pool import Pool
from traceback import print_exc
from lxml import etree
from django.db import transaction, connection
from django.conf import settings
from docutil.etree_util import clean_tree, get_word_count, XPathList,\
        SingleXPath, HierarchyXPath, get_word_count_text
from docutil.url_util import get_relative_url
from docutil.commands_util import chunk_it, import_clazz, get_encoding
from docutil.progress_monitor import NullProgressMonitor
from codebase.actions import get_project_code_words
from doc.models import Document, Page, Section

DEFAULT_POOL_SIZE = 4

logger = logging.getLogger("recodoc.doc.parser.generic")


@transaction.autocommit
def sub_process_parse(pinput):
    try:
        # Unecessary if already closed by parent process.
        # But it's ok to be sure.
        connection.close()
        (parser_clazz, doc_pk, parse_refs, pages) = pinput
        parser = import_clazz(parser_clazz)(doc_pk)
        for page_input in pages:
            if page_input is not None:
                (local_path, page_url) = page_input
                parser.parse_page(local_path, page_url, parse_refs)
        return True
    except Exception:
        print_exc()
        return False
    finally:
        # Manually close this connection
        connection.close()


@transaction.autocommit
def parse(document, pages, parse_refs=True,
        progress_monitor=NullProgressMonitor(),
        pool_size=DEFAULT_POOL_SIZE):
    progress_monitor.start('Parsing Pages', pool_size + 1)

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


    def __init__(self, document_pk):
        self.document = Document.objects.get(pk=document_pk)

    def parse_page(self, page_local_path, page_url, parse_refs=True):
        try:
            relative_url = get_relative_url(settings.PROJECT_FS_ROOT,
                        page_local_path)
            page = Page(url=page_url,
                    file_path=relative_url,
                    document=self.document)
            page.save()
            load = ParserLoad()
            load.parse_refs = parse_refs

            self._build_code_words(load)
            self._process_page(page, load)
        except Exception:
            print_exc()

    def _build_code_words(self, load):
        # Build code words and put it in self.load
        load.code_words = \
            get_project_code_words(self.document.project_release.project)

    def _process_page(self, page, load):
        page_path = os.path.join(settings.PROJECT_FS_ROOT, page.file_path)
        page_file = open(page_path)
        content = page_file.read()
        page_file.close()
        encoding = get_encoding(content)
        parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
        load.tree = etree.fromstring(content, parser).getroottree()
        clean_tree(load.tree)

        page.title = self._process_page_title(page, load)

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

        return check

    def _process_sections(self, page, load):
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
            self._parse_code_references(page, load, sections)

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

    def _parse_section_references(page, load, sections):
        pass