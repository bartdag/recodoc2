from __future__ import unicode_literals
import os
import codecs
from multiprocessing.pool import Pool
from traceback import print_exc
from lxml import etree
from django.db import transaction, connection
from django.conf import settings
from docutil.etree_util import XTEXT, get_word_count
from docutil.url_util import get_relative_url
from docutil.commands_util import chunk_it, import_clazz
from docutil.progress_monitor import NullProgressMonitor
from doc.models import Document, Page, Section

DEFAULT_POOL_SIZE = 4

@transaction.autocommit
def sub_process_parse(pinput):
    try:
        # Unecessary if already closed by parent process.
        # But it's ok to be sure.
        connection.close()
        (parser_clazz, doc_pk, pages) = pinput
        parser = import_clazz(parser_clazz)(doc_pk)
        for (local_path, page_url) in pages:
            parser.parse_page(local_path, page_url)
        return True
    except Exception:
        print_exc()
        return False
    finally:
        # Manually close this connection
        connection.close()


@transaction.autocommit
def parse(document, pages, progress_monitor=NullProgressMonitor(),
        pool_size = DEFAULT_POOL_SIZE):
    progress_monitor.start('Parsing Pages', pool_size + 1)

    # Prepare input
    pages = [(page.local_url, page.url) for page in
            pages.values()]
    pages_chunks = chunk_it(pages, pool_size)
    inputs = []
    for pages_chunk in pages_chunks:
        inputs.append((document.parser, document.pk, pages_chunk))

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


class GenericParser(object):
    
    POOL_SIZE = 4

    xtext = XTEXT

    xbody = etree.XPath("//body[1]")
    '''Page body'''

    xtitle = etree.XPath("//h1[1]")
    '''Page title'''

    def __init__(self, document_pk):
        self.document = Document.objects.get(pk=document_pk)

    def parse_page(self, page_local_path, page_url):
        try:
            relative_url = get_relative_url(settings.PROJECT_FS_ROOT,
                        page_local_path)
            page = Page(url=page_url,
                    file_path=relative_url,
                    document=self.document)
            page.save()
            load = ParserLoad()

            self._build_code_words(load)
            self._process_page(page, load)
        except Exception:
            print_exc()

    def _build_code_words(self, load):
        # Build code words and put it in self.load
        pass

    def _process_page(self, page, load):
        parser = etree.HTMLParser(remove_comments=True, encoding='utf8')
        page_path = os.path.join(settings.PROJECT_FS_ROOT, page.file_path)
        page_file = codecs.open(page_path, encoding='utf8')
        load.tree = etree.parse(page_file, parser)
        page_file.close()
        
        page.title = self._process_page_title(page, load)
        
        body = self.xbody(load.tree)[0] 
        page.word_count = get_word_count(body)
        page.xpath = load.tree.getpath(body)
        page.save()

        self._process_init_page(page, load)
        self._process_sections(page, load)

    def _process_page_title(self, page, load):
        pass

    def _process_init_page(self, page, load):
        pass

    def _process_sections(page, load):
        pass

