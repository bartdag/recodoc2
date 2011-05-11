from __future__ import unicode_literals
from django.db import models
from django.contrib.contenttypes import generic
from project.models import Project, Person, SourceElement
from codebase.models import SingleCodeReference, CodeSnippet
# Create your models here.


class SupportChannel(models.Model):

    name = models.CharField(max_length=500, null=True, blank=True)
    '''at'''

    dir_name = models.CharField(max_length=200)
    '''at'''

    url = models.URLField(max_length=500)
    '''at'''

    project = models.ForeignKey(Project, null=True, blank=True,
        related_name='channels')
    '''at'''

    parser = models.CharField(max_length=500, null=True, blank=True)
    '''Python FQN of the Parser class for this channel.'''

    syncer = models.CharField(max_length=500, null=True, blank=True)
    '''Python FQN of the Syncer class for this channel'''

    def __unicode__(self):
        return self.name + ' - ' + self.project.name


class SupportThread(models.Model):
    url = models.URLField(null=True, blank=True, max_length=500)
    '''att.'''

    file_path = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    title = models.CharField(max_length=500, default='', null=True, blank=True)
    '''at'''

    #thread_id = models.CharField(max_length=500, null=True, blank=True)
    #'''at'''

    pages = models.IntegerField(default=1)
    '''Number of pages in support thread.'''

    first_date = models.DateTimeField(null=True, blank=True)
    '''at'''

    last_date = models.DateTimeField(null=True, blank=True)
    '''at'''

    channel = models.ForeignKey(SupportChannel, null=True, blank=True,
            related_name='threads')
    '''at'''

    code_references = generic.GenericRelation(SingleCodeReference,
            content_type_field='global_content_type',
            object_id_field='global_object_id')
    '''att.'''

    def __unicode__(self):
        return self.title

    class Meta:
        order_with_respect_to = 'channel'
        ordering = ['first_date']


class Message(SourceElement):

    title = models.CharField(max_length=500, null=True, blank=True)
    '''at'''

    index = models.IntegerField(default=-1)
    '''Index of the message in the thread. 0-based.'''

    msg_date = models.DateTimeField(null=True, blank=True)
    '''at'''

    author = models.ForeignKey(Person, null=True, blank=True)
    '''at'''

    sthread = models.ForeignKey(SupportThread, null=True, blank=True,
            related_name='messages')
    '''at'''

    code_references = generic.GenericRelation(SingleCodeReference,
            content_type_field="local_content_type",
            object_id_field="local_object_id")
    '''at'''

    code_snippets = generic.GenericRelation(CodeSnippet,
            content_type_field="local_content_type",
            object_id_field="local_object_id")
    '''at'''

    word_count = models.PositiveIntegerField(default=0)
    '''att.'''

    def __unicode__(self):
        title = self.title
        if title == None:
            title = ''
        return title + ' (#' + str(self.index) + ')'

    class Meta:
        order_with_respect_to = 'sthread'
        ordering = ['index']


### SYNCER MODEL - NOT PERSISTED ###
class SupportChannelStatus(object):

    def __init__(self, syncer_clazz, url):
        self.syncer_clazz = syncer_clazz
        self.url = url
        self.toc_sections = []
        self.entries = []


class TocSection(object):

    def __init__(self, index, url):
        self.index = index
        self.url = url
        self.downloaded = False


class TocEntry(object):

    def __init__(self, index, url):
        self.index = index
        self.url = url
        self.downloaded = False
        self.local_paths = []
