from __future__ import unicode_literals
import os
import shutil
import logging
import time
from py4j.java_gateway import JavaGateway
from django.db import transaction
from django.test import TransactionTestCase
from django.conf import settings
from docutil.test_util import clean_test_dir
from doc.models import Page, Section
from doc.actions import create_doc_local, create_doc_db
from channel.models import SupportThread, Message
from channel.actions import create_channel_local, create_channel_db
from codebase.models import CodeElementKind, SingleCodeReference, CodeSnippet
from codebase.actions import start_eclipse, stop_eclipse,\
                             create_code_db, create_code_local,\
                             link_eclipse, get_codebase_path,\
                             create_code_element_kinds, parse_code,\
                             parse_snippets, link_code
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db


class CodeParserTest(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        time.sleep(1)
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST
        start_eclipse()
        create_project_local('project1')
        create_code_local('project1', 'core', '3.0')
        to_path = get_codebase_path('project1', 'core', '3.0')
        to_path = os.path.join(to_path, 'src')
        os.rmdir(to_path)
        from_path = os.path.join(settings.TESTDATA, 'testproject3', 'src')
        shutil.copytree(from_path, to_path)
        link_eclipse('project1', 'core', '3.0')

    @classmethod
    def tearDownClass(cls):
        gateway = JavaGateway()
        workspace = gateway.jvm.org.eclipse.core.resources.ResourcesPlugin.\
                getWorkspace()
        root = workspace.getRoot()
        pm = gateway.jvm.org.eclipse.core.runtime.NullProgressMonitor()
        project1 = root.getProject('project1core3.0')
        project1.delete(True, True, pm)
        time.sleep(1)
        gateway.close()
        stop_eclipse()
        clean_test_dir()

    @transaction.commit_on_success
    def setUp(self):
        self.pname = 'project1'
        self.release = '3.0'
        logging.basicConfig(level=logging.WARNING)
        create_code_element_kinds()
        self.project = create_project_db('Project 1',
                'http://www.example1.com', self.pname)
        self.releasedb = create_release_db(self.pname, self.release, True)
        create_release_db(self.pname, '3.1')
        self.ann_kind = CodeElementKind.objects.get(kind='annotation')
        self.class_kind = CodeElementKind.objects.get(kind='class')
        self.enum_kind = CodeElementKind.objects.get(kind='enumeration')
        self.code_refs = []
        self.code_snippets = []

    @transaction.commit_on_success
    def tearDown(self):
        Project.objects.all().delete()
        CodeElementKind.objects.all().delete()

    def create_codebase(self):
        create_code_db(self.pname, 'core', self.release)
        parse_code(self.pname, 'core', self.release, 'java')

    def create_documentation(self):
        create_doc_local(self.pname, 'manual', self.release, 'foo', 'url')
        doc = create_doc_db(self.pname, 'manual', self.release, 'url', 'foo',
                'foo')
        page1 = Page(document=doc, title='HTTP Server')
        page1.save()
        page2 = Page(document=doc, title='HTTP Client')
        page2.save()

        section1 = Section(page=page1, number='1.',
            title='Implementing foo bar')
        section1.save()
        section11 = Section(page=page1, number='1.1',
            title='Reference', parent=section1)
        section11.save()

        section2 = Section(page=page2, number='2.',
            title='Implementing the Client')
        section2.save()
        section21 = Section(page=page2, number='2.1',
            title='Implementing the Client Again')
        section21.save()

        coderef1 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='@p1.Annotation1',
                source='d',
                kind_hint=self.ann_kind,
                local_context=section1,
                mid_context=section1,
                global_context=page1
                )
        coderef1.save()
        self.code_refs.append(coderef1)

        coderef2 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='@Annotation2',
                source='d',
                kind_hint=self.ann_kind,
                local_context=section11,
                mid_context=section1,
                global_context=page1
                )
        coderef2.save()
        self.code_refs.append(coderef2)

        snippet_content = r'''

        @Annotation1
        public class FooBar {
          public void main(String arg) {
            System.out.println();
          }
        '''

        snippet1 = CodeSnippet(
                project=self.project,
                project_release=self.releasedb,
                language='j',
                source='d',
                snippet_text=snippet_content,
                local_context=section2,
                mid_context=section2,
                global_context=page2
                )
        snippet1.save()
        self.code_snippets.append(snippet1)

    def create_channel(self):
        create_channel_local(self.pname, 'usermail', 'foo', 'url')
        channel = create_channel_db(self.pname, 'user mail', 'usermail',
                'foo', 'foo', 'url')

        thread1 = SupportThread(
                title='HTTP Server Question',
                channel=channel)
        thread1.save()

        thread2 = SupportThread(
                title='Http client question',
                channel=channel)
        thread2.save()

        message1 = Message(
                title='HTTP Server Question',
                index=0,
                sthread=thread1
                )
        message1.save()

        message2 = Message(
                title='RE: HTTP Server Question',
                index=1,
                sthread=thread1
                )
        message2.save()

        message3 = Message(
                title='Http client question',
                index=0,
                sthread=thread2
                )
        message3.save()

        message4 = Message(
                title='RE: Http client question',
                index=1,
                sthread=thread2
                )
        message4.save()

        coderef1 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='clazz1',
                source='s',
                kind_hint=self.class_kind,
                local_context=message1,
                global_context=thread1
                )
        coderef1.save()
        self.code_refs.append(coderef1)

        coderef2 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='Enum1',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef2.save()
        self.code_refs.append(coderef2)

        coderef3 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='Disco',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef3.save()
        self.code_refs.append(coderef3)

        snippet_content = r'''

        @Annotation1
        public class FooBar {
          public void main(String arg) {
            System.out.println();
          }
        '''

        snippet1 = CodeSnippet(
                project=self.project,
                project_release=self.releasedb,
                language='j',
                source='s',
                snippet_text=snippet_content,
                local_context=message3,
                global_context=thread2
                )
        snippet1.save()
        self.code_snippets.append(snippet1)

    def parse_snippets(self):
        parse_snippets(self.pname, 'd', 'java')
        parse_snippets(self.pname, 's', 'java')

    def test_linker(self):
        self.create_codebase()
        self.create_documentation()
        self.create_channel()
        self.parse_snippets()
        link_code(self.pname, 'core', self.release, 'javaclass', 'd',
                self.release)
        link_code(self.pname, 'core', self.release, 'javaclass', 's',
                None)

        code_ref1 = self.code_refs[0]
        code_ref1 = SingleCodeReference.objects.get(pk=code_ref1.pk)
        self.assertEqual(
                'p1.Annotation1',
                code_ref1.release_links.all()[0].first_link.code_element.fqn)
        
        snippet2 = self.code_snippets[1]
        snippet2 = CodeSnippet.objects.get(pk=snippet2.pk)
        ann_ref = None
        for code_ref in snippet2.single_code_references.all():
            if code_ref.kind_hint.pk == self.ann_kind.pk:
                ann_ref = code_ref
                break

        self.assertEqual(
                'Annotation1',
                ann_ref.release_links.all()[0]
                    .first_link.code_element.simple_name)

        # Test class insensitive comparison
        code_ref3 = self.code_refs[2]
        code_ref3 = SingleCodeReference.objects.get(pk=code_ref3.pk)
        self.assertEqual(
                'Clazz1',
                code_ref3.release_links.all()[0]
                .first_link.code_element.simple_name)

        # Test enum in class.
        code_ref4 = self.code_refs[3]
        code_ref4 = SingleCodeReference.objects.get(pk=code_ref4.pk)
        self.assertEqual(
                'Enum1',
                code_ref4.release_links.all()[0]
                .first_link.code_element.simple_name)

        # Test reclassification
        code_ref5 = self.code_refs[4]
        code_ref5 = SingleCodeReference.objects.get(pk=code_ref5.pk)
        self.assertEqual(
                'unknown',
                code_ref5.kind_hint.kind)
