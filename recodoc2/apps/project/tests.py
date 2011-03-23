from __future__ import unicode_literals
import os
from django.test import TestCase
from django.conf import settings
from docutil.test_util import clean_test_dir
from project.actions import create_project_local, create_project_db,\
                            list_projects_db, list_projects_local


class ProjectTest(TestCase):

    def setUp(self):
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST

    def tearDown(self):
        clean_test_dir()

    def testCreateProjectLocal(self):
        create_project_local('project1')
        create_project_local('project2')
        self.assertEqual(2, len(os.listdir(settings.PROJECT_FS_ROOT_TEST)))
