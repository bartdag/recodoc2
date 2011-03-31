from __future__ import unicode_literals
import os
import shutil
import unittest
from django.test import TestCase
from django.conf import settings
from py4j.java_gateway import JavaGateway
from docutil.test_util import clean_test_dir
from codebase.models import CodeBase, CodeElementKind
from codebase.actions import start_eclipse, stop_eclipse, check_eclipse,\
                             create_code_db, create_code_local, list_code_db,\
                             list_code_local, link_eclipse, get_codebase_path,\
                             create_code_element_kinds
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db

class EclipseTest(TestCase):

    @unittest.skip('Usually works.')
    def testEclipse(self):
        pid = start_eclipse()
        self.assertTrue(check_eclipse())
        stop_eclipse(pid)


class CodeSetup(TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.pid = start_eclipse()

    @classmethod
    def tearDownClass(cls):
        stop_eclipse(cls.pid)

    def setUp(self):
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST
        create_project_local('project1')
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')

    def tearDown(self):
        for project in Project.objects.all():
            project.delete()
        clean_test_dir()

    def testCreateCodeDB(self):
        create_code_db('project1', 'core', '3.0')
        self.assertEqual(1, CodeBase.objects.all().count())

    def testCreateCodeLocal(self):
        create_code_local('project1', 'core', '3.0')
        create_code_local('project1', 'lib', '3.1')
        path = get_codebase_path('project1', root=True)
        self.assertEqual(2, len(os.listdir(path))) 

    def testListCodeLocal(self):
        self.assertEqual(0, len(list_code_local('project1')))
        create_code_local('project1', 'core', '3.0')
        self.assertEqual(1, len(list_code_local('project1')))
        create_code_local('project1', 'lib', '3.0')
        create_code_local('project1', 'core', '3.1')
        self.assertEqual(3, len(list_code_local('project1')))

    def testListCodeDB(self):
        self.assertEqual(0, len(list_code_db('project1')))
        create_code_db('project1', 'core', '3.0')
        self.assertEqual(1, len(list_code_db('project1')))
        create_code_db('project1', 'lib', '3.0')
        create_code_db('project1', 'core', '3.1')
        self.assertEqual(3, len(list_code_db('project1')))

    def testCreateCodeElementKinds(self):
        create_code_element_kinds()
        kind_count = CodeElementKind.objects.all().count()
        self.assertEqual(30, kind_count)

    def testLinkEclipseProject(self):
        create_code_local('project1', 'core', '3.0')
        to_path = get_codebase_path('project1','core','3.0')
        to_path = os.path.join(to_path, 'src')
        os.rmdir(to_path)
        from_path = os.path.join(settings.TESTDATA, 'testproject1', 'src')
        shutil.copytree(from_path, to_path)
        link_eclipse('project1', 'core', '3.0')

        gateway = JavaGateway()
        workspace = gateway.jvm.org.eclipse.core.resources.ResourcesPlugin.\
                getWorkspace()
        root = workspace.getRoot()
        pm = gateway.jvm.org.eclipse.core.runtime.NullProgressMonitor()
        project1 = root.getProject('project1core3.0')
        self.assertIsNotNone(project1)
        project1.delete(True, True, pm)
        gateway.close()

