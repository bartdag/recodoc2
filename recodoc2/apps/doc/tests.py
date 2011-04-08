from __future__ import unicode_literals
from urlparse import urlparse
import logging
import os
import unittest
from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.db import transaction

from docutil.commands_util import load_model
from docutil.test_util import clean_test_dir
from codebase.models import CodeElementKind, SingleCodeReference, CodeSnippet
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db, DOC_PATH
from doc.actions import create_doc_local, get_doc_path, list_doc_local,\
                            create_doc_db, list_doc_db, sync_doc,\
                            clear_doc_elements, parse_doc
from doc.models import Document


class DocSetup(TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.WARNING)
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST
        create_project_local('project1')
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')

    def tearDown(self):
        Project.objects.all().delete()
        CodeElementKind.objects.all().delete()
        SingleCodeReference.objects.all().delete()
        CodeSnippet.objects.all().delete()
        clean_test_dir()

    def test_create_doc_local(self):
        create_doc_local('project1', 'manual', '3.0', 'foo.syncer')
        create_doc_local('project1', 'manual', '3.1', 'foo.syncer')
        path = get_doc_path('project1', root=True)
        self.assertEqual(2, len(os.listdir(path)))

    def test_list_doc_local(self):
        create_doc_local('project1', 'manual', '3.0', 'foo.syncer')
        create_doc_local('project1', 'manual', '3.1', 'foo.syncer')
        self.assertEqual(2, len(list_doc_local('project1')))

    def test_create_doc_db(self):
        create_doc_db('project1', 'manual', '3.0', '', 'foo.syncer',
                'foo.parser')
        create_doc_db('project1', 'manual', '3.1', '', 'foo.syncer',
                'foo.parser')
        self.assertEqual(2, Document.objects.count())

    def test_list_doc_db(self):
        create_doc_db('project1', 'manual', '3.0', '', 'foo.syncer',
                'foo.parser')
        create_doc_db('project1', 'manual', '3.1', '', 'foo.syncer',
                'foo.parser')
        self.assertEqual(2, len(list_doc_db('project1')))

    @unittest.skip('Usually works.')
    def test_sync_doc_remote(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'http://hc.apache.org/httpcomponents-client-ga/tutorial/html/index.html')
        sync_doc(pname, dname, release)
        doc_key = dname + release
        model = load_model(pname, DOC_PATH, doc_key)
        self.assertEqual(9, len(model.pages))
        for page_key in model.pages:
            path = urlparse(page_key).path
            self.assertTrue(os.path.exists(path))

    def test_sync_doc_local(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'httpclient402doc',
            'index.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        sync_doc(pname, dname, release)
        doc_key = dname + release
        model = load_model(pname, DOC_PATH, doc_key)
        self.assertEqual(8, len(model.pages))
        for page_key in model.pages:
            path = urlparse(page_key).path
            self.assertTrue(os.path.exists(path))


class DocParser(TransactionTestCase):
    @transaction.commit_on_success
    def setUp(self):
        logging.basicConfig(level=logging.WARNING)
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST
        create_project_local('project1')
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')

    @transaction.commit_on_success
    def tearDown(self):
        Project.objects.all().delete()
        CodeElementKind.objects.all().delete()
        SingleCodeReference.objects.all().delete()
        CodeSnippet.objects.all().delete()
        clean_test_dir()

    @transaction.autocommit
    def test_generic_parse_doc(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'httpclient402doc',
            'index.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        create_doc_db('project1', 'manual', '3.0', '',
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'doc.parser.generic_parser.GenericParser')
        sync_doc(pname, dname, release)
        parse_doc(pname, dname, release)
