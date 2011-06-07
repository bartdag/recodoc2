from __future__ import unicode_literals
from django.db import models


class RecoDocError(Exception):
    """Exception thrown when a problem occurs with Py4J."""
    pass


class Project(models.Model):
    '''A project.'''

    name = models.CharField(max_length=255, unique=True)
    '''att.'''

    url = models.URLField()
    '''att.'''

    dir_name = models.CharField(max_length=20, unique=True, db_index=True)
    '''Directory name on the filesystem.'''

    def __unicode__(self):
        return self.name


class ProjectRelease(models.Model):
    '''A project has many releases. '''

    project = models.ForeignKey(Project)
    '''att.'''

    release = models.CharField(max_length=20)
    '''att.'''

    is_major = models.BooleanField(default=True)
    '''att.'''

    first_date = models.DateTimeField(null=True, blank=True)
    '''att.'''

    last_date = models.DateTimeField(null=True, blank=True)
    '''att.'''

    def __unicode__(self):
        return '{0} {1}'.format(self.project.name, self.release)


class Person(models.Model):
    '''A person asks and answers questions.'''

    name = models.CharField(max_length=255, null=True, blank=True, default='')
    '''real name. not used now.'''

    email = models.EmailField(null=True, blank=True)
    '''att.'''

    nickname = models.CharField(max_length=255, null=True, blank=True,
            default='', db_index=True)
    '''nickname used on forums'''

    contributor = models.BooleanField(default=False)
    ''' '''

    def __unicode__(self):
        name = self.name
        if name == None:
            name = '__NA__'
        nickname = self.nickname
        if nickname == None:
            nickname = ''
        return '{0} ({1})'.format(nickname, name)


class SourceElement(models.Model):
    '''A `SourceElement` represents anything that can be traced back to an
    HTML document (e.g., a word in the documentation, a message in a forum or
    a mailing list).'''

    url = models.URLField(null=True, blank=True, max_length=500)
    '''att.'''

    file_path = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    xpath = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''

    index_from = models.PositiveIntegerField(default=0, null=True, blank=True)
    '''att.'''

    index_to = models.PositiveIntegerField(default=0, null=True, blank=True)
    '''att.'''

    class Meta:
        abstract = True
