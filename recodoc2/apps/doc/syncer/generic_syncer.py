from __future__ import unicode_literals
import urllib2
import logging
from lxml import etree
from url_util import get_local_url, get_url_without_hash, ensure_path_exists,\
        get_path_from_url
from doc.models import DocumentPage, DocumentLink

class GenericSyncer(object):
    '''Generic Documentation Syncer responsible for downloading all the pages of a document.
    '''
    
    links = etree.XPath("//a")
    imgs = etree.XPath("//img")
    logger = logging.getLogger("docs.syncer.GenericSyncer")

    def __init__(self, input_urls, output_url, scope, prefix_avoid=None,
            suffix_avoid=None):
        '''
        :param input_urls: list of urls from which to start the search for
                           documentation pages.
        :output_url: url of the directory where the pages will be downloaded
        :scope: set of prefix strings: only pages matching at least one prefix
                will be downloaded. If empty, all encountered pages are
                downloaded.
        :prefix_avoid: set of prefix strings to avoid
        :suffix_avoid: set of suffix strings to avoid
        '''
        if isinstance(input_urls, basestring):
            self.input_urls = [input_urls]
        else:
            self.input_urls = input_urls
        self.output_url = output_url
        self.scope = scope
        if prefix_avoid is None:
            self.prefix_avoid = []
        else:
            self.prefix_avoid = prefix_avoid
        
        if suffix_avoid is None:
            self.suffix_avoid = []
        else:
            self.suffix_avoid = suffix_avoid
        
        self.pages = {}

    def sync(self):
        '''Main method of the syncer.
        
        :rtype: A dict of GenericPage indexed by their local url.
        '''
        for input_url in self.input_urls:
            try:
                page = self.process_page(input_url)
                self.pages[page.local_url] = page
                self.process_links(page)
            except:
                local_url = get_local_url(self.output_url,
                        get_url_without_hash(input_url))
                self.logger.exception(
                    'This page could not be downloaded: {0} in {1}'.format(
                        input_url, local_url))
                error_page = DocumentPage(input, None, [])
                self.pages[local_url] = error_page
        
        return self.pages

    def process_page(self, url):
        self.logger.info("Processing page: " + url)
        local_url = self.make_copy(get_url_without_hash(url))

        parser = etree.HTMLParser()
        local_page = urllib2.urlopen(local_url)
        tree = etree.parse(local_page, parser)

        links = self.process_page_links(tree, local_url, url)
        self.process_page_imgs(tree, url)
        
        local_page.close()
        page = DocumentPage(url, local_url, links)
        
        return page

    def make_copy(self, url_to_copy, binary=False):
        # Will probably need something more intelligent. Will do for now.
        #destination = urlparse.urljoin(self.input_url, url_to_copy)
        destination_url = get_local_url(self.output_url, url_to_copy)
        try:
            ensure_path_exists(destination_url)
        except:
            raise Exception('Could not make copy of %s in %s' % (url_to_copy, destination_url))
        download_file(url_to_copy, get_path_from_url(destination_url),force=False,binary=binary)
        return destination_url

    def process_links(self, page):
        '''
        Depth-first search.
        '''
        for link in page.links:
            if not self.in_scope(link):
                continue;
            elif not (link.local_url in self.pages):
                try:
                    page = self.process_page(link.url)
                    self.pages[page.local_url] = page
                    self.process_links(page)
                except:
                    local_url = get_local_url(self.output_url, get_url_without_hash(link.url))
                    self.logger.exception('This page could not be downloaded: %s in %s' % (link.url, local_url))
                    error_page = GenericPage(link.url, None, [])
                    self.pages[local_url] = error_page

    def _should_avoid(self, link):
        should_avoid = False
        
        for avoid in self.prefix_avoid:
            if link.startswith(avoid):
                should_avoid = True
                break
            
        if not should_avoid:
            for avoid in self.suffix_avoid:
                if link.endswith(avoid):
                    should_avoid = True
                    break
        
        return should_avoid

    def in_scope(self, link):
        in_scope = len(self.scope) == 0
        url = link.url

        for scope_item in self.scope:
            if url.startswith(scope_item):
                if self._should_avoid(url):
                    in_scope = False
                    break
                else: 
                    in_scope = True
                    break

        return in_scope

    def process_page_links(self, tree, local_url, url):
        link_tags = self.links(tree)
        links = []
        for link_tag in link_tags:
            attributes = link_tag.attrib
            href = ''
            if 'href' in attributes:
                href = attributes['href']
                link_url = get_url_without_hash(urlparse.urljoin(url, href))
                local_url_to = get_sanitized_url(get_local_url(self.output_url, link_url))
                link = GenericLink(link_url, local_url_to)
                links.append(link)
            else:
                continue
        return links
    
    def process_page_imgs(self, tree, url):
        img_tags = self.imgs(tree)
        for img_tag in img_tags:
            try:
                attributes = img_tag.attrib
                if 'src' in attributes:
                    src = attributes['src']
                    img_url = urlparse.urljoin(url, src)
                    self.make_copy(img_url, True)
                else:
                    continue
            except:
                self.logger.exception('This image could not be downloaded: %s in %s' % (urlparse.urljoin(url, src) , url))