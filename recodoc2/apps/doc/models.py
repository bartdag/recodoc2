from __future__ import unicode_literals
from django.db import models
from django.contrib.contenttypes import generic

from project.models import ProjectRelease, SourceElement
from codebase.models import SingleCodeReference, CodeSnippet, CodeElementLink
from docutil.commands_util import import_clazz


class Document(models.Model):
    title = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    project_release = models.ForeignKey(ProjectRelease, null=True, blank=True,
            related_name='documents')
    '''att.'''

    parser = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    syncer = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    url = models.URLField(null=True, blank=True)
    '''att.'''

    word_count = models.IntegerField(default=0)
    '''att.'''

    references = generic.GenericRelation(SingleCodeReference,
            content_type_field="resource_content_type",
            object_id_field="resource_object_id",
            related_name="doc_refs")
    '''att.'''

    def __unicode__(self):
        return self.title + ' ' + str(self.project_release)

    class Meta:
        ordering = ['title']
        order_with_respect_to = 'project_release'


class Page(models.Model):
    url = models.URLField(null=True, blank=True, max_length=500)
    '''att.'''

    file_path = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    xpath = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    document = models.ForeignKey(Document, null=True, blank=True,
            related_name='pages')
    '''att.'''

    title = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    word_count = models.IntegerField(default=0)
    '''att.'''

    code_references = generic.GenericRelation(SingleCodeReference,
            content_type_field='global_content_type',
            object_id_field='global_object_id',
            related_name="page_refs")
    '''att.'''

    def get_text(self, complex_text=False):
        parser_clazz = self.document.parser
        doc_pk = self.document.pk
        parser = import_clazz(parser_clazz)(doc_pk)
        return parser.get_page_text(self, complex_text)

    def get_etree(self):
        parser_clazz = self.document.parser
        doc_pk = self.document.pk
        parser = import_clazz(parser_clazz)(doc_pk)
        return parser.get_page_etree(self)

    def __unicode__(self):
        return self.title

    class Meta:
        order_with_respect_to = 'document'
        ordering = ['title']


class Section(SourceElement):
    '''
    A section in a document
    '''

    title = models.CharField(max_length=500, blank=True, null=True)
    '''att.'''

    page = models.ForeignKey(Page, blank=True, null=True,
            related_name='sections')
    '''att.'''

    word_count = models.IntegerField(default=0)
    '''att.'''

    number = models.CharField(max_length=20, blank=True, null=True)
    '''Represent the section number, if available (e.g., 1.1)'''

    parent = models.ForeignKey('self', blank=True, null=True,
            related_name='children')
    '''att.'''

    title_references = generic.GenericRelation(SingleCodeReference,
            content_type_field="title_content_type",
            object_id_field="title_object_id",
            related_name="section_titles")
    '''att.'''

    code_references = generic.GenericRelation(SingleCodeReference,
            content_type_field="local_content_type",
            object_id_field="local_object_id",
            related_name="section_refs")
    '''att.'''

    code_snippets = generic.GenericRelation(CodeSnippet,
            content_type_field="local_content_type",
            object_id_field="local_object_id",
            related_name="section_snippets")
    '''att.'''

    def get_text(self, tree=None, complex_text=False):
        parser_clazz = self.page.document.parser
        doc_pk = self.page.document.pk
        parser = import_clazz(parser_clazz)(doc_pk)
        return parser.get_section_text(self, tree, complex_text)

    def __unicode__(self):
        return self.title

    class Meta:
        order_with_respect_to = 'page'
        ordering = ['title']


class DocDiff(models.Model):
    document_from = models.ForeignKey(Document, blank=True, null=True,
            related_name="diff_document_froms")
    '''att.'''

    document_to = models.ForeignKey(Document, blank=True, null=True,
            related_name="diff_document_tos")
    '''att.'''

    removed_pages = models.ManyToManyField(Page, blank=True, null=True,
            related_name="diff_removed_pages")
    '''att.'''

    added_pages = models.ManyToManyField(Page, blank=True, null=True,
            related_name="diff_added_pages")
    '''att.'''

    removed_sections = models.ManyToManyField(Section, blank=True, null=True,
            related_name="diff_removed_sections")
    '''att.'''

    added_sections = models.ManyToManyField(Section, blank=True, null=True,
            related_name="diff_added_sections")
    '''att.'''

    pages_size_from = models.IntegerField(default=0)
    '''att.'''

    pages_size_to = models.IntegerField(default=0)
    '''att.'''

    sections_size_from = models.IntegerField(default=0)
    '''att.'''

    sections_size_to = models.IntegerField(default=0)
    '''att.'''


    def __unicode__(self):
        return 'Diff {0} - {1}'.format(self.document_from, self.document_to)


class PageMatcher(models.Model):
    page_from = models.ForeignKey(Page, blank=True, null=True,
            related_name="match_froms")
    '''att.'''

    page_to = models.ForeignKey(Page, blank=True, null=True,
            related_name="match_tos")
    '''att.'''

    confidence = models.FloatField(default=0.0)
    '''att.'''

    refactored = models.BooleanField(default=False)
    '''att.'''

    diff = models.ForeignKey(DocDiff, blank=True, null=True,
            related_name="page_matches")
    '''att.'''



class SectionMatcher(models.Model):
    section_from = models.ForeignKey(Section, blank=True, null=True,
            related_name="match_froms")
    '''att.'''

    section_to = models.ForeignKey(Section, blank=True, null=True,
            related_name="match_tos")
    '''att.'''

    confidence = models.FloatField(default=0.0)
    '''att.'''

    refactored = models.BooleanField(default=False)
    '''att.'''

    diff = models.ForeignKey(DocDiff, blank=True, null=True,
            related_name="section_matches")
    '''att.'''



class SectionChanger(models.Model):
    section_from = models.ForeignKey(Section, blank=True, null=True,
            related_name="changed_froms")
    '''att.'''

    section_to = models.ForeignKey(Section, blank=True, null=True,
            related_name="changed_tos")
    '''att.'''

    words_from = models.IntegerField(default=0)
    '''att.'''

    words_to = models.IntegerField(default=0)
    '''att.'''

    change = models.FloatField(default=0.0)
    '''att.'''

    diff = models.ForeignKey(DocDiff, blank=True, null=True,
            related_name="section_changes")
    '''att.'''


class LinkChange(models.Model):
    diff = models.ForeignKey(DocDiff, blank=True, null=True,
            related_name="link_changes")
    '''att.'''

    from_matched_section = models.BooleanField(default=False)
    '''True if the link change came from a section that already existed in the
       previous release of the documentation.'''

    link_from = models.ForeignKey(CodeElementLink, blank=True, null=True,
            related_name="link_from_changes")
    '''att.'''

    link_to = models.ForeignKey(CodeElementLink, blank=True, null=True,
            related_name="link_to_changes")
    '''att.'''

    def __unicode__(self):
        msg = ''
        if self.link_from is not None:
            msg = self._get_message(self.link_from, 'removed')
        else:
            msg = self._get_message(self.link_to, 'added')

        return msg

    def _get_message(self, link, text):
        msg = '{0} {1}'.\
                format(link.code_element.human_string(), text)
        section_title = (link.code_reference.local_context.title)
        if self.from_matched_section:
            msg += ' from matched section {0}'.format(section_title)
        else:
            msg += ' from section {0}'.format(section_title)

        return msg


### SYNCER MODEL ###

class DocumentStatus(object):
    '''Contains the page that have been downloaded. Used by the syncer.
       Persisted in a pickle file, not in the db'''
    def __init__(self, syncer, input_url):
        self.syncer = syncer
        self.input_url = input_url

        # Key: page local url, then an instance of DocumentPage.
        self.pages = {}


class DocumentPage(object):
    '''Represents a documentation page. Used by the syncer.
    '''
    def __init__(self, url=None, local_url=None, links=None):
        self.url = url
        self.local_url = local_url
        if links is None:
            self.links = []
        else:
            self.links = links


class DocumentLink(object):
    '''Represents a link in a documentation page. Used by the syncer.
    '''
    def __init__(self, url, local_url):
        self.url = url
        self.local_url = local_url
