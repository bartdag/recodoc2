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

    is_orphan = models.BooleanField(default=False)
    '''att.'''

    parent = models.ForeignKey('self', blank=True, null=True,
            related_name='children')

    '''att.'''

    code_references = generic.GenericRelation(SingleCodeReference,
            content_type_field="local_content_type",
            object_id_field="local_object_id")

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
    def __init__(self, url = None, local_url = None, links = None):
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
