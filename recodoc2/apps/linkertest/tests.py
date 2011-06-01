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
import docutil.cache_util as cu
from doc.models import Page, Section
from doc.actions import create_doc_local, create_doc_db
from channel.models import SupportThread, Message
from channel.actions import create_channel_local, create_channel_db
from codebase.linker.generic_linker import DEBUG_LOG
from codebase.models import CodeElementKind, SingleCodeReference,\
        CodeSnippet, CodeElementFilter
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
        settings.DEBUG = True
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
        cu.clear_cache()
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
        self.method_kind = CodeElementKind.objects.get(kind='method')
        self.code_refs = []
        self.code_snippets = []

    @transaction.commit_on_success
    def tearDown(self):
        Project.objects.all().delete()
        CodeElementKind.objects.all().delete()
        cu.clear_cache()

    def create_codebase(self):
        self.codebase = create_code_db(self.pname, 'core', self.release)
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
                local_context=section1,
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

        coderef4 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='RecodocClient',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef4.save()
        self.code_refs.append(coderef4)

        coderef5 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='foo.RecodocClient',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef5.save()
        self.code_refs.append(coderef5)

        coderef6 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='callMethod1("hello")',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef6.save()
        self.code_refs.append(coderef6)

        coderef7 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='callMethod1("hello", 2)',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef7.save()
        self.code_refs.append(coderef7)

        coderef8 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='callMethod1(p3.Foo, p3.Bar)',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef8.save()
        self.code_refs.append(coderef8)

        coderef9 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='equals()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef9.save()
        self.code_refs.append(coderef9)

        coderef10 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='list.add(foo)',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef10.save()
        self.code_refs.append(coderef10)

        coderef11 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='list.add(foo)',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                parent_reference=coderef10,
                )
        coderef11.save()
        self.code_refs.append(coderef11)

        coderef12 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='nonexistentmethod',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                parent_reference=coderef10,
                )
        coderef12.save()
        self.code_refs.append(coderef12)

        coderef13 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='recodoc.callMethod10(foo)',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef13.save()
        self.code_refs.append(coderef13)

        coderef14 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='recodoc.callMethod10(foo)',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                parent_reference=coderef13,
                )
        coderef14.save()
        self.code_refs.append(coderef14)

        snippet_content = r'''

        @Annotation1
        public class FooBar {
          public void main(String arg) {
            System.out.println();
            RecodocClient obj = new RecodocClient();
            List list = null;
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

    def create_documentation2(self):
        page1 = Page.objects.get(title='HTTP Server')
        section1 = Section.objects.get(title='Implementing foo bar')
        section11 = Section.objects.get(number='1.1')
        section2 = Section.objects.get(number='2.')

    def parse_snippets(self):
        parse_snippets(self.pname, 'd', 'java')
        parse_snippets(self.pname, 's', 'java')

    def create_filters(self):
        afilter = CodeElementFilter(
                codebase=self.codebase,
                fqn='java.util.List',
                include_snippet=True,
                one_ref_only=False)
        afilter.save()
        afilter = CodeElementFilter(
                codebase=self.codebase,
                fqn='RecodocClient',
                include_snippet=False,
                one_ref_only=True)
        afilter.save()

    def test_linker(self):
        self.create_codebase()
        self.create_filters()
        self.create_documentation()
        self.create_channel()
        self.create_documentation2()
        self.parse_snippets()
        link_code(self.pname, 'core', self.release, 'javaclass', 'd',
                self.release)
        link_code(self.pname, 'core', self.release, 'javaclass', 's',
                None)
        link_code(self.pname, 'core', self.release, 'javapostclass', '',
                None)
        link_code(self.pname, 'core', self.release, 'javamethod', 'd',
                self.release)
        link_code(self.pname, 'core', self.release, 'javamethod', 's',
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

        # Test post-processing
        code_ref2 = self.code_refs[1]
        code_ref2 = SingleCodeReference.objects.get(pk=code_ref2.pk)
        self.assertEqual('highest_frequency',
                code_ref2.release_links.all()[0].first_link.rationale)

        self.assertEqual('heuristic_depth',
                code_ref3.release_links.all()[0].first_link.rationale)
        self.assertEqual('p1.Clazz1',
                code_ref3.release_links.all()[0]
                .first_link.code_element.fqn)
        self.assertEqual('heuristic_depth',
                code_ref4.release_links.all()[0].first_link.rationale)

        # Test type custom filter (single ref)
        code_ref6 = self.code_refs[5]
        code_ref6 = SingleCodeReference.objects.get(pk=code_ref6.pk)
        # Not reclassified because custom filtered!
        self.assertEqual(
                'class',
                code_ref6.kind_hint.kind)
        type_log = DEBUG_LOG[code_ref6.pk][0]
        self.assertEqual(0, type_log['final size'])
        self.assertTrue(type_log['custom filtered'])

        # Test type custom filter (compound ref)
        code_ref7 = self.code_refs[6]
        code_ref7 = SingleCodeReference.objects.get(pk=code_ref7.pk)
        self.assertEqual(
                'RecodocClient',
                code_ref7.release_links.all()[0]
                .first_link.code_element.simple_name)

        # Test List in snippet
        custom_filtered = []
        for code_ref in snippet2.single_code_references.all():
            if code_ref.content.find('List') > -1:
                if (len(DEBUG_LOG[code_ref.pk]) > 0):
                    custom_filtered.append(
                            DEBUG_LOG[code_ref.pk][0]['custom filtered'])
        self.assertEqual(1, len(custom_filtered))
        for customf in custom_filtered:
            self.assertTrue(customf)

        # Test RecodocClient in snippet
        custom_filtered = []
        for code_ref in snippet2.single_code_references.all():
            if code_ref.content.find('RecodocClient') > -1 and\
                code_ref.kind_hint.kind == 'class':
                if (len(DEBUG_LOG[code_ref.pk]) > 0):
                    custom_filtered.append(
                            DEBUG_LOG[code_ref.pk][0]['custom filtered'])
        self.assertEqual(2, len(custom_filtered))
        for customf in custom_filtered:
            self.assertFalse(customf)

        # Test method param number filter
        code_ref8 = self.code_refs[7]
        code_ref8 = SingleCodeReference.objects.get(pk=code_ref8.pk)
        self.assertEqual('callMethod1',
                code_ref8.release_links.all()[0]
                .first_link.code_element.simple_name)
        self.assertEqual(1,
                code_ref8.release_links.all()[0]
                .first_link.code_element.parameters().count())
        method_log = DEBUG_LOG[code_ref8.pk][0]
        self.assertTrue(method_log['ParameterNumberFilter'][0])

        # Test method param type filter
        code_ref9 = self.code_refs[8]
        code_ref9 = SingleCodeReference.objects.get(pk=code_ref9.pk)
        self.assertEqual('String',
                code_ref9.release_links.all()[0]
                .first_link.code_element.parameters()[0].type_simple_name)
        method_log = DEBUG_LOG[code_ref9.pk][0]
        self.assertTrue(method_log['ParameterTypeFilter'][0])

        # Test method param type package filter
        code_ref10 = self.code_refs[9]
        code_ref10 = SingleCodeReference.objects.get(pk=code_ref10.pk)
        self.assertEqual('p3.RecodocClient',
                code_ref10.release_links.all()[0]
                .first_link.code_element.parameters()[0].type_fqn)
        method_log = DEBUG_LOG[code_ref10.pk][0]
        self.assertTrue(method_log['ParameterTypeFilter'][0])

        # Test method object filter
        code_ref11 = self.code_refs[10]
        code_ref11 = SingleCodeReference.objects.get(pk=code_ref11.pk)
        method_log = DEBUG_LOG[code_ref11.pk][0]
        self.assertTrue(method_log['ObjectMethodsFilter'][0])
        self.assertEqual(0, method_log['final size'])

        # Test method custom filter
        code_ref13 = self.code_refs[12]
        code_ref13 = SingleCodeReference.objects.get(pk=code_ref13.pk)
        method_log = DEBUG_LOG[code_ref13.pk][0]
        self.assertTrue(method_log['custom filtered'])
        self.assertEqual(0, method_log['final size'])

        # Test filter decorator
        code_ref14 = self.code_refs[13]
        code_ref14 = SingleCodeReference.objects.get(pk=code_ref14.pk)
        method_log = DEBUG_LOG[code_ref14.pk][0]
        self.assertFalse(method_log['ParameterTypeFilter'][0])
        self.assertEqual(0, method_log['final size'])

        # Test name similarity
        code_ref16 = self.code_refs[15]
        code_ref16 = SingleCodeReference.objects.get(pk=code_ref16.pk)
        method_log = DEBUG_LOG[code_ref16.pk][0]
        self.assertTrue(method_log['ContextNameSimilarityFilter'][0])
        self.assertEqual('p3.RecodocClient',
                code_ref16.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])
