from __future__ import unicode_literals
from docutil.etree_util import HierarchyXPath, SingleXPath
import doc.parser.common_parsers as cp


class HTClientParser(cp.NewDocBookParser):

    xparagraphs = HierarchyXPath('.', './pre')

    def __init__(self, document_pk):
        super(HTClientParser, self).__init__(document_pk)

    def _process_init_page(self, page, load):
        load.mix_mode = True

    def _process_mix_mode_section(self, page, load, section):
        return section.number.startswith('6') and \
                not section.title.startswith('Chapter')


class HibernateParser(cp.NewDocBookParser):


    def __init__(self, document_pk):
        super(HibernateParser, self).__init__(document_pk)


class JodaParser(cp.MavenParser):

    xparagraphs = SingleXPath('.//pre')

    def _process_init_page(self, page, load):
        load.mix_mode = True

    def _process_mix_mode_section(self, page, load, section):
        return section.title.strip().lower() == 'upgrade'
