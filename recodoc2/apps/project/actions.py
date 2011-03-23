from __future__ import unicode_literals
from django.conf import settings
from docutil.commands_util import mkdir_safe
from project.models import Project, ProjectRelease
import os

CLONE_PATH = 'clone'
DOC_PATH = 'doc'
STHREAD_PATH = 'support'
CODEBASE_PATH = 'code'
NOT_INITIALIZED = 'not initialized'


def create_project_local(dir_name):
    '''Create a project directory structure on the filesystem'''
    basepath = settings.PROJECT_FS_ROOT
    project_path = os.path.join(basepath, dir_name)
    mkdir_safe(project_path)
    mkdir_safe(os.path.join(project_path, DOC_PATH))
    mkdir_safe(os.path.join(project_path, STHREAD_PATH))
    mkdir_safe(os.path.join(project_path, CODEBASE_PATH))


def create_project_db(project_name, url, dir_name):
    project = Project(name=project_name, url=url, dir_name=dir_name)
    project.save()


def create_release_db(project_name, release_name, is_major=False):
    project = Project.objects.get(dir_name=project_name)
    release = ProjectRelease(project=project, release=release_name,
                             is_major=is_major)
    release.save()


def list_projects_db():
    projects = []
    for project in Project.objects.all():
        projects.append('{0}: {1} ({2})'.
                format(project.pk, project.name, project.dir_name))
    return projects


def list_projects_local():
    basepath = settings.PROJECT_FS_ROOT
    local_projects = []
    for member in os.listdir(basepath):
        if os.path.isdir(os.path.join(basepath, member)):
            local_projects.append(member)
    return local_projects
