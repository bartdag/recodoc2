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
from doc.models import Document, Page, Section


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
    def test_docbook_parse_ht4_doc(self):
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
                'doc.parser.common_parsers.NewDocBookParser')
        sync_doc(pname, dname, release)
        document = parse_doc(pname, dname, release, False)
        
        page = Page.objects.filter(document=document).filter(
                title='Chapter 2. Connection management').all()[0]
        self.assertEqual('/html/body', page.xpath)
        self.assertEqual(23, page.sections.count())

        section = Section.objects.filter(page=page).filter(
                number='2.3.1.').all()[0]
        self.assertEqual('2.3.1. Route computation', section.title)
        self.assertEqual(180, section.word_count)
        self.assertEqual('2.3.', section.parent.number)

        # With code snippets:
        section = Section.objects.filter(page=page).filter(
                number='2.5.').all()[0]
        self.assertEqual('2.5. Socket factories', section.title)
        self.assertEqual(110, section.word_count)
        self.assertEqual('2.', section.parent.number)
        self.assertTrue(section.parent.parent is None)

    def test_docbook_parse_sp25_doc(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'spring25doc',
            'index.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        create_doc_db('project1', 'manual', '3.0', '',
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'doc.parser.common_parsers.NewDocBookParser')
        print('Syncing Doc')
        sync_doc(pname, dname, release)
        print('Synced Doc')

        document = parse_doc(pname, dname, release, False)
        
        page = Page.objects.filter(document=document).filter(
                title='Chapter 22. Email').all()[0]
        self.assertEqual('/html/body', page.xpath)
        self.assertEqual(11, page.sections.count())

        section = Section.objects.filter(page=page).filter(
                number='22.3.1.1.').all()[0]
        self.assertEqual('22.3.1.1. Attachments', section.title)
        self.assertEqual(78, section.word_count)
        self.assertEqual('22.3.1.', section.parent.number)

        section = Section.objects.filter(page=page).filter(
                number='22.2.').all()[0]
        self.assertEqual('22.2. Usage', section.title)
        self.assertEqual(50, section.word_count)
        self.assertEqual('22.', section.parent.number)
        self.assertTrue(section.parent.parent is None)

    def test_docbook_parse_hib3_doc(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'hib35doc',
            'index.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        create_doc_db('project1', 'manual', '3.0', '',
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'doc.parser.common_parsers.NewDocBookParser')
        print('Syncing doc')
        sync_doc(pname, dname, release)
        print('Synced doc')

        document = parse_doc(pname, dname, release, False)
        
        page = Page.objects.filter(document=document).filter(
                title='Chapter 12. Transactions and Concurrency').all()[0]
        self.assertEqual('/html/body', page.xpath)
        self.assertEqual(18, page.sections.count())

        section = Section.objects.filter(page=page).filter(
                number='12.3.4.').all()[0]
        self.assertEqual('12.3.4. Customizing automatic versioning', section.title)
        self.assertEqual(274, section.word_count)
        self.assertEqual('12.3.', section.parent.number)

        section = Section.objects.filter(page=page).filter(
                number='12.5.').all()[0]
        self.assertEqual('12.5. Connection release modes', section.title)
        self.assertEqual(361, section.word_count)
        self.assertEqual('12.', section.parent.number)
        self.assertTrue(section.parent.parent is None)
