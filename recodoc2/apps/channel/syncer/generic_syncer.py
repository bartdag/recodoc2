from __future__ import unicode_literals
import os.path
from docutil.url_util import get_safe_local_id, get_relative_url
from docutil.commands_util import download_file, download_html_tree
from project.models import RecoDocError
from channel.models import TocSection, TocEntry


class MessageSyncer(object):

    reverse_entries = True

    def _get_section_urls(self, channel_url):
        raise RecoDocError('Must be implemented by syncer')

    def toc_refresh(self, model):
        size = len(model.toc_sections)
        section_urls = self._get_section_urls(model.url)
        sections_size = len(section_urls)
        if sections_size <= 0:
            return

        if size > 0:
            model.toc_sections[-1].downloaded = False

        # We assume that the sections are always returned in the same order!
        index = size
        for section_url in section_urls[size:]:
            model.toc_sections.append(TocSection(index, section_url))
            index += 1

    def _parse_toc_entries(self, page_url, tree):
        raise RecoDocError('Must be implemented by syncer')

    def _get_next_toc_page(self, page_url, tree):
        raise RecoDocError('Must be implemented by syncer')

    def _sort_section_entries(self, pages):
        entry_urls = []
        if self.reverse_entries:
            reverse = lambda l: reversed(l)
        else:
            reverse = lambda l: l

        for entries in reverse(pages):
            entry_urls.extend(reverse(entries))

        return entry_urls

    def toc_download_section(self, model, section):
        pages = []
        page_url = section.url
        while page_url is not None:
            tree = download_html_tree(page_url)
            entry_urls = self._parse_toc_entries(page_url, tree)
            pages.append(entry_urls)
            page_url = self._get_next_toc_page(page_url, tree)

        entry_urls = self._sort_section_entries(pages)
        e_index = 1000 * section.index
        for entry_url in entry_urls:
            model.entries.append(TocEntry(e_index, entry_url))
            e_index += 1
        section.downloaded = True

    def download_entry(self, entry, path):
        uid = get_safe_local_id(entry.url)
        new_path = os.path.join(path, uid)
        download_file(entry.url, new_path)
        relative_path = get_relative_url(new_path)
        entry.local_paths = [relative_path]
        entry.downloaded = True


class ThreadSyncer(object):

    reverse_entries = False

    def _get_section_url(self, index):
        raise RecoDocError('Must be implemented by syncer')

    def _get_number_of_pages(self, url):
        raise RecoDocError('Must be implemented by syncer')

    def toc_refresh(self, model):
        size = len(model.toc_sections)
        page_number = self._get_number_of_pages(model.url)
        if page_number <= 0:
            return

        if size > 0:
            model.toc_sections[-1].downloaded = False

        # We assume that the sections are always returned in the same order!
        for index in xrange(size, page_number):
            section_url = self._get_section_url(model.url, index)
            model.toc_sections.append(TocSection(index, section_url))
            index += 1

    def _parse_toc_entries(self, page_url, tree):
        raise RecoDocError('Must be implemented by syncer')

    def toc_download_section(self, model, section):
        page_url = section.url
        tree = download_html_tree(page_url)
        entry_urls = self._parse_toc_entries(page_url, tree)

        if self.reverse_entries:
            entry_urls.reverse()

        e_index = 1000 * section.index
        for entry_url in entry_urls:
            model.entries.append(TocEntry(e_index, entry_url))
            e_index += 1
        section.downloaded = True

    def _get_next_entry_url(self, url, next_page_id, tree):
        raise RecoDocError('Must be implemented by syncer')

    def download_entry(self, entry, path):
        local_paths = []
        next_url = entry.url
        page_id = 0

        while next_url is not None:
            uid = get_safe_local_id(next_url, '_page{0}'.format(page_id))
            new_path = os.path.join(path, uid)
            download_file(next_url, new_path)
            relative_path = get_relative_url(new_path)
            local_paths.append(relative_path)
            tree = download_html_tree(new_path)
            page_id += 1
            next_url = self._get_next_entry_url(next_url, page_id, tree)

        entry.downloaded = True
        entry.local_paths = local_paths
