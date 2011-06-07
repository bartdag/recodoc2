from __future__ import unicode_literals
import os
from django.test import TestCase
from django.conf import settings
from django.db import transaction
from docutil.test_util import clean_test_dir
from project.actions import create_project_local, create_project_db,\
                            list_projects_db, list_projects_local,\
                            create_release_db

from project.models import Project, ProjectRelease


class ProjectTest(TestCase):

    def setUp(self):
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST

    def tearDown(self):
        for project in Project.objects.all():
            project.delete()
        clean_test_dir()

    def testCreateProjectLocal(self):
        create_project_local('project1')
        create_project_local('project2')
        self.assertEqual(2, len(os.listdir(settings.PROJECT_FS_ROOT_TEST)))

    def testCreateProjectDB(self):
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_project_db('Project 2', 'http://www.example1.com', 'project2')
        self.assertEqual(2, Project.objects.count())

    def testCreateProjectRelease(self):
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')
        self.assertTrue(2, ProjectRelease.objects.count())

    def testCreateProjectDBNonUnique(self):
        create_project_db('Project 1', 'http://www.example1.com', 'project1')

        try:
            sid = transaction.savepoint()
            create_project_db('Project 1', 'http://www.example1.com',
                              'project2')
            self.fail('Should have failed!')
        except:
            transaction.savepoint_rollback(sid)
            self.assertTrue(True)

        try:
            sid = transaction.savepoint()
            create_project_db('Project 2', 'http://www.example1.com',
                              'project1')
            self.fail('Should have failed!')
        except:
            transaction.savepoint_rollback(sid)
            self.assertTrue(True)

        self.assertEqual(1, Project.objects.count())

    def testListProjectsLocal(self):
        create_project_local('project1')
        create_project_local('project2')
        self.assertEqual(2, len(list_projects_local()))

    def testListProjectsDB(self):
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_project_db('Project 2', 'http://www.example1.com', 'project2')
        self.assertEqual(2, len(list_projects_db()))
