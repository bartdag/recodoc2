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
from codebase.actions import create_code_element_kinds
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db, DOC_PATH
from doc.actions import create_doc_local, get_doc_path, list_doc_local,\
                            create_doc_db, list_doc_db, sync_doc,\
                            clear_doc_elements, parse_doc, diff_doc
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

    #@unittest.skip('Usually works.')
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

    #@unittest.skip('Usually works.')
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

    def test_doc_differ(self):
        doc1 = create_doc_db('project1', 'manual', '3.0', '', 'foo.syncer',
                'foo.parser')
        doc2 = create_doc_db('project1', 'manual', '3.1', '', 'foo.syncer',
                'foo.parser')

        page1 = Page(
                document=doc1,
                title='Chapter 1. Element Reconstruction')
        page1.save()
        page2 = Page(
                document=doc1,
                title='Chapter 2. On the FooBart Method')
        page2.save()
        page3 = Page(
                document=doc1,
                title='Chapter 3. Mapping Inheritance and MetaData')
        page3.save()
        page4 = Page(
                document=doc1,
                title='Chapter 4. Object Query Language Reference')
        page4.save()
        section11 = Section(
                page=page1,
                number='1.1',
                title='1.1 Element Section 1'
                )
        section11.save()
        section111 = Section(
                page=page1,
                parent=section11,
                number='1.1.1',
                title='1.1.1. Internal'
                )
        section111.save()
        section12 = Section(
                page=page1,
                number='1.2',
                title='1.2 Reconstructing Element',
                )
        section12.save()
        section121 = Section(
                page=page1,
                parent=section12,
                number='1.2.1',
                title='1.2.1. Reconstruction SubElement'
                )
        section121.save()
        section122 = Section(
                page=page1,
                parent=section12,
                number='1.2.2',
                title='1.2.2. Internal'
                )
        section122.save()
        section21 = Section(
                page=page2,
                number='2.1',
                title='2.1 FooBart Usage'
                )
        section21.save()
        section211 = Section(
                page=page2,
                parent=section21,
                number='2.1.1',
                title='2.1.1. Internal'
                )
        section211.save()
        section22 = Section(
                page=page2,
                number='2.2',
                title='2.2 FizzBuzz Example',
                )
        section22.save()
        section31 = Section(
                page=page3,
                number='3.1',
                title='3.1 Mapping Inheritance'
                )
        section31.save()
        section311 = Section(
                page=page3,
                parent=section31,
                number='3.1.1',
                title='3.1.1. Internal'
                )
        section311.save()
        section41 = Section(
                page=page4,
                number='4.1',
                title='4.1 OQL Basics'
                )
        section41.save()

        page1 = Page(
                document=doc2,
                title='Chapter 1. Element Reconstruction')
        page1.save()
        page3 = Page(
                document=doc2,
                title='Chapter 2. Mapping Inheritance and MetaData')
        page3.save()
        page5 = Page(
                document=doc2,
                title='Chapter 3. Saving the World, one Section at a time')
        page5.save()
        page4 = Page(
                document=doc2,
                title='Chapter 4. Object Query Language Reference')
        page4.save()
        section11 = Section(
                page=page1,
                number='1.1',
                title='1.1 Element Section 1'
                )
        section11.save()
        section111 = Section(
                page=page1,
                parent=section11,
                number='1.1.1',
                title='1.1.1. Internal'
                )
        section111.save()
        section12 = Section(
                page=page1,
                number='1.2',
                title='1.2 Reconstructing Element',
                )
        section12.save()
        section122 = Section(
                page=page1,
                parent=section12,
                number='1.2.1',
                title='1.2.1. Internal'
                )
        section122.save()
        section13 = Section(
                page=page1,
                number='1.3',
                title='1.3 New Influences on Element Section 1'
                )
        section13.save()
        section131 = Section(
                page=page1,
                parent=section13,
                number='1.3.1',
                title='1.3.1. Internal'
                )
        section131.save()
        section31 = Section(
                page=page3,
                number='2.1',
                title='2.1 Mapping Inheritance'
                )
        section31.save()
        section311 = Section(
                page=page3,
                parent=section31,
                number='2.1.1',
                title='2.1.1. Internal'
                )
        section311.save()
        section41 = Section(
                page=page4,
                number='4.1',
                title='4.1 OQL Basics'
                )
        section41.save()
        section51 = Section(
                page=page5,
                number='3.1',
                title='3.1 World Hello!'
                )
        section51.save()

        ddiff = diff_doc('project1', 'manual', '3.0', '3.1')
        self.assertEqual(1, ddiff.removed_pages.count())
        self.assertEqual(1, ddiff.added_pages.count())
        self.assertEqual(4, ddiff.pages_size_from)
        self.assertEqual(4, ddiff.pages_size_from)
        for page_match in ddiff.page_matches.all():
            print('{0} -> {1} : {2}'.format(
                page_match.page_from.title,
                page_match.page_to.title,
                page_match.confidence))
        for section_match in ddiff.section_matches.all():
            print('{0} -> {1} : {2}'.format(
                section_match.section_from.title,
                section_match.section_to.title,
                section_match.confidence))


class DocParserTest(TransactionTestCase):
    @transaction.commit_on_success
    def setUp(self):
        logging.basicConfig(level=logging.WARNING)
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST
        create_project_local('project1')
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')
        create_code_element_kinds()

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
        self.assertEqual(182, section.word_count)
        self.assertEqual('2.3.', section.parent.number)

        # With code snippets:
        section = Section.objects.filter(page=page).filter(
                number='2.5.').all()[0]
        self.assertEqual('2.5. Socket factories', section.title)
        self.assertEqual(110, section.word_count)
        self.assertEqual('2.', section.parent.number)
        self.assertTrue(section.parent.parent is None)

    #@unittest.skip('Usually works.')
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
        self.assertEqual(51, section.word_count)
        self.assertEqual('22.', section.parent.number)
        self.assertTrue(section.parent.parent is None)

    #@unittest.skip('Usually works.')
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
        self.assertTrue(276, section.word_count)
        self.assertEqual('12.3.', section.parent.number)

        section = Section.objects.filter(page=page).filter(
                number='12.5.').all()[0]
        self.assertEqual('12.5. Connection release modes', section.title)
        self.assertEqual(371, section.word_count)
        self.assertEqual('12.', section.parent.number)
        self.assertTrue(section.parent.parent is None)

    #@unittest.skip('Usually works.')
    def test_maven_parse_joda162_doc(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'joda162doc',
            'index.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        create_doc_db('project1', 'manual', '3.0', '',
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'doc.parser.common_parsers.MavenParser')
        print('Syncing doc')
        sync_doc(pname, dname, release)
        print('Synced doc')

        document = parse_doc(pname, dname, release, False)
        
        page = Page.objects.filter(document=document).filter(
                title='User Guide').all()[0]
        self.assertEqual('/html/body', page.xpath)
        self.assertEqual(35, page.sections.count())

        section = Section.objects.filter(page=page).filter(
                title='Direct access').all()[0]
        self.assertEqual('Direct access', section.title)
        self.assertEqual(110, section.word_count)
        self.assertEqual('', section.number)
        self.assertEqual('Input and Output', section.parent.title)
        self.assertEqual(162, section.parent.word_count)

        section = Section.objects.filter(page=page).filter(
                title='Advanced features').all()[0]
        self.assertEqual('Advanced features', section.title)
        self.assertEqual(2, section.word_count)
        self.assertTrue(section.parent is None)

    #@unittest.skip('Usually works.')
    def test_maven_parse_htclient_doc(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'httpclient31doc',
            'userguide.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        create_doc_db('project1', 'manual', '3.0', '',
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'doc.parser.common_parsers.MavenParser')
        print('Syncing doc')
        sync_doc(pname, dname, release)
        print('Synced doc')

        document = parse_doc(pname, dname, release, False)
        
        page = Page.objects.filter(document=document).filter(
                title='HttpClient exception handling guide').all()[0]
        self.assertEqual('/html/body', page.xpath)
        self.assertEqual(22, page.sections.count())

        section = Section.objects.filter(page=page).filter(
                title='Idempotent methods').all()[0]
        self.assertEqual('Idempotent methods', section.title)
        self.assertEqual(113, section.word_count)
        self.assertEqual('', section.number)
        self.assertEqual('HTTP transport safety', section.parent.title)

        section = Section.objects.filter(page=page).filter(
                title='Custom exception handler').all()[0]
        self.assertEqual('Custom exception handler', section.title)
        self.assertEqual('', section.number)
        self.assertEqual(132, section.word_count)
        self.assertTrue(section.parent is None)

    #@unittest.skip('Usually works.')
    def test_maven_parse_joda162_doc_code(self):
        pname = 'project1'
        release = '3.0'
        dname = 'manual'
        test_doc = os.path.join(settings.TESTDATA, 'joda162doc',
            'index.html')
        test_doc = os.path.normpath(test_doc)
        create_doc_local(pname, dname, release,
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'file://' + test_doc) 
        create_doc_db('project1', 'manual', '3.0', '',
                'doc.syncer.generic_syncer.SingleURLSyncer',
                'doc.parser.common_parsers.MavenParser')
        print('Syncing doc')
        sync_doc(pname, dname, release)
        print('Synced doc')

        document = parse_doc(pname, dname, release, True)
        
        page = Page.objects.filter(document=document).filter(
                title='User Guide').all()[0]

        section = Section.objects.filter(page=page).filter(
                title='Direct access').all()[0]
        self.assertEqual(0, section.title_references.count())
        # Only 2, because small references are not added! Yay!
        self.assertEqual(2, section.code_references.count())
        self.assertEqual(1, section.code_snippets.count())
        
        section = Section.objects.filter(page=page).filter(
                title='Using a MutableDateTime').all()[0]
        self.assertEqual(1, section.title_references.count())
        # Include the ref in the title too!
        self.assertEqual(2, section.code_references.count())
        self.assertEqual(1, section.code_snippets.count())

    @unittest.skip('Usually works.')
    def test_docbook_parse_hib3_doc_code(self):
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

        document = parse_doc(pname, dname, release, True)
        
        page = Page.objects.filter(document=document).filter(
                title='Chapter 12. Transactions and Concurrency').all()[0]

        section = Section.objects.filter(page=page).filter(
                number='12.3.4.').all()[0]
        self.assertEqual(0, section.title_references.count())
        self.assertEqual(13, section.code_references.count())
        self.assertEqual(0, section.code_snippets.count())

        section = Section.objects.filter(page=page).filter(
                number='12.3.3.').all()[0]
        self.assertEqual(0, section.title_references.count())
        self.assertEqual(12, section.code_references.count())
        self.assertEqual(1, section.code_snippets.count())
