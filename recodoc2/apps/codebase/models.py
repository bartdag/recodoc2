from __future__ import unicode_literals
from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from project.models import Project, ProjectRelease, SourceElement


LANGUAGES = [
    ('j','Java'),
    ('p','Python'),
    ('pr','Properties'),
    ('x','XML'),
    ('jx','Java Stack Trace'),
    ('l','Log Trace'),
    ('r','Previous Message'),
    ('o','Other'),
]
'''Language of an element'''

SOURCE_TYPE = (
    ('d','Document'),
    ('s','Support Channel'),
)


def add_language(lang_code, lang_name):
    global LANGUAGES
    found = False
    for (code, _) in LANGUAGES:
        if lang_code == code:
            found = True
            break
    if not found:
        LANGUAGES.append((lang_code, lang_name))


class CodeBase(models.Model):
    '''A codebase includes all the code of a project release'''
    
    project = models.ForeignKey(Project)
    '''att.'''
    name = models.CharField(max_length=500, null=True, blank=True)
    '''att.'''
    project_release = models.ForeignKey(ProjectRelease)
    '''att.'''
    
    def __unicode__(self):
        return self.name + ' - ' + self.project.name + ' ' + self.project_release.release
