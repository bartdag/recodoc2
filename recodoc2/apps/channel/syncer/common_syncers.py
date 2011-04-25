from __future__ import unicode_literals
import os
import urlparse
from lxml import etree
from docutil.commands_util import download_html_tree
from channel.syncer.generic_syncer import MessageSyncer


class ApacheMailSyncer(MessageSyncer):

    reverse_entries = False
    xsection_urls = etree.XPath('//td[@class="links"]/span/a[1]')
    xentries = etree.XPath('//td[@class="subject"]/a[1]')
    xnext_pages = etree.XPath('//th/a')

    def _get_section_urls(self, channel_url):
        tree = download_html_tree(channel_url)
        links = self.xsection_urls(tree)
        section_urls = []
        for link in reversed(links):
            url = link.attrib['href']
            # change "browser" for "date"
            url = os.path.join(os.path.split(url)[0], 'date')
            url = urlparse.urljoin(channel_url, url)
            section_urls.append(url)
        return section_urls

    def _parse_toc_entries(self, page_url, tree):
        links = self.xentries(tree)
        entry_urls = []
        for link in links:
            url = link.attrib['href']
            url = urlparse.urljoin(page_url, url)
            entry_urls.append(url)
        return entry_urls

    def _get_next_toc_page(self, page_url, tree):
        next_page_url = None
        for page_link in self.xnext_pages(tree):
            if page_link.text.find('Next') > -1:
                next_page_url = page_link.attrib['href']
                next_page_url = urlparse.urljoin(page_url, next_page_url)
                break
        return next_page_url
