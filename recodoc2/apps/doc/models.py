from __future__ import unicode_literals
from django.db import models
from django.contrib.contenttypes import generic

from project.models import ProjectRelease, SourceElement
from codebase.models import SingleCodeReference, CodeSnippet


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
            object_id_field='global_object_id')
    '''att.'''

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
            related_name="titles")
    '''att.'''

    code_references = generic.GenericRelation(SingleCodeReference,
            content_type_field="local_content_type",
            object_id_field="local_object_id",
            related_name="refs")
    '''att.'''

    code_snippets = generic.GenericRelation(CodeSnippet,
            content_type_field="local_content_type",
            object_id_field="local_object_id")
    '''att.'''

    def __unicode__(self):
        return self.title

    class Meta:
        order_with_respect_to = 'page'
        ordering = ['title']


class DocDiff(models.Model):
    document_from = models.ForeignKey(Document, blank=True, null=True,
            related_name="diff_document_froms")
    document_to = models.ForeignKey(Document, blank=True, null=True,
            related_name="diff_document_tos")
    removed_pages = models.ManyToManyField(Page, blank=True, null=True,
            related_name="diff_removed_pages")
    added_pages = models.ManyToManyField(Page, blank=True, null=True,
            related_name="diff_added_pages")
    removed_sections = models.ManyToManyField(Section, blank=True, null=True,
            related_name="diff_removed_sections")
    added_sections = models.ManyToManyField(Section, blank=True, null=True,
            related_name="diff_added_sections")
    pages_size_from = models.IntegerField(default=0)
    pages_size_to = models.IntegerField(default=0)
    sections_size_from = models.IntegerField(default=0)
    sections_size_to = models.IntegerField(default=0)


class PageMatcher(models.Model):
    page_from = models.ForeignKey(Page, blank=True, null=True,
            related_name="match_froms")
    page_to = models.ForeignKey(Page, blank=True, null=True,
            related_name="match_tos")
    refactored = models.BooleanField(default=False)
    diff = models.ForeignKey(DocDiff, blank=True, null=True,
            related_name="page_matches")


class SectionMatcher(models.Model):
    section_from = models.ForeignKey(Section, blank=True, null=True,
            related_name="match_froms")
    section_to = models.ForeignKey(Section, blank=True, null=True,
            related_name="match_tos")
    refactored = models.BooleanField(default=False)
    diff = models.ForeignKey(DocDiff, blank=True, null=True,
            related_name="section_matches")


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
