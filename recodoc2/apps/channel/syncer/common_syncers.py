from __future__ import unicode_literals
import os
import urlparse
import re
from lxml import etree
from docutil.etree_util import get_text
from docutil.commands_util import download_html_tree
from channel.syncer.generic_syncer import MessageSyncer, ThreadSyncer


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


class PHPBBForumSyncer(ThreadSyncer):
    ENTRY_PER_PAGE = 25

    section_url = \
    '{0}&sd=a&start={1}'

    xnumber_pages = etree.XPath('//td[@class="nav"]/strong[2]')

    xentries = etree.XPath('//tr/td[@class="row1"][2]/a')

    xnext_links = etree.XPath('//td[@class="gensmall"]/b/a')


    def _get_section_url(self, base_url, index):
        url = self.section_url.format(base_url, self.ENTRY_PER_PAGE * index)
        return url

    def _get_number_of_pages(self, url):
        tree = download_html_tree(url)
        number_of_pages = self.xnumber_pages(tree)
        if len(number_of_pages) == 0:
            return 1
        else:
            number = number_of_pages[0].text.strip()
            return int(number)

    def _parse_toc_entries(self, page_url, tree):
        entry_urls = []
        links = self.xentries(tree)
        size = len(links)
        for link in links[size - self.ENTRY_PER_PAGE:]:
            url = urlparse.urljoin(page_url, link.attrib['href'])
            entry_urls.append(url)
        return entry_urls

    def _get_next_entry_url(self, url, next_page_id, tree):
        next_links = self.xnext_links(tree)
        next_url = None
        for link in next_links:
            if link.text.strip().lower() == 'next':
                next_url = urlparse.urljoin(url, link.attrib['href'])
                break
        return next_url


class FUDEclipseForumSyncer(ThreadSyncer):
    
    ENTRY_PER_PAGE = 40

    section_url = '{0}1/{1}/'

    xnumber_pages =\
            etree.XPath('//table[@class="wa"]//td[@class="vt"]/span[1]')

    xtext = etree.XPath('string()')

    xentries = etree.XPath('//table[@class="pad"]//a[@class="big"]')

    xnext_links = None

    page_regex = re.compile(r'Pages \((\d+)\)')

    def _get_number_of_pages(self, url):
        tree = download_html_tree(url)
        number_of_pages = self.xnumber_pages(tree)
        if len(number_of_pages) == 0:
            return 1
        else:
            number_element = number_of_pages[0]
            number = get_text(number_element)
            match = self.page_regex.search(number)
            if match:
                return int(match.group(1))
            else:
                return 1

    def _get_section_url(self, base_url, index):
        url = self.section_url.format(base_url, index * self.ENTRY_PER_PAGE)
        return url

    def _parse_toc_entries(self, page_url, tree):
        entry_urls = []
        links = self.xentries(tree)
        for link in links:
            url = urlparse.urljoin('http://www.eclipse.org/forums/',
                    link.attrib['href'])
            print(url)
            entry_urls.append(url)
        return entry_urls

    def _get_next_entry_url(self, url, next_page_id, tree):
        # It seems that all messages are presented on the same page.
        return None
