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
import codebase.linker.context as ctx
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
        DEBUG_LOG.clear()
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
        DEBUG_LOG.clear()

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
            RecodocClient rc = new RecodocClient();
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

        thread3 = SupportThread(
                title='Random Question',
                channel=channel)
        thread3.save()

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
        
        message5 = Message(
                title='Random Question',
                index=0,
                sthread=thread3
                )
        message5.save()

        message6 = Message(
                title='RE: RE: HTTP Server Question',
                index=0,
                sthread=thread1
                )
        message6.save()

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

        # Index = 14
        coderef13 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='recodoc.callMethod10(foo)',
                source='s',
                kind_hint=self.class_kind,
                local_context=message5,
                global_context=thread3,
                )
        coderef13.save()
        self.code_refs.append(coderef13)

        # Index = 15
        coderef14 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='recodoc.callMethod10(foo)',
                source='s',
                kind_hint=self.method_kind,
                local_context=message5,
                global_context=thread3,
                parent_reference=coderef13,
                )
        coderef14.save()
        self.code_refs.append(coderef14)

        coderef15 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='getClient2()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef15.save()
        self.code_refs.append(coderef15)

        # Index = 17
        coderef16 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='method100()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef16.save()
        self.code_refs.append(coderef16)

        coderef17 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='method200()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef17.save()
        self.code_refs.append(coderef17)

        snippet_content = r'''

        @Annotation1
        public class FooBar extends FooBarSuper {
          public void main(String arg) {
            System.out.println();
            RecodocClient obj = new RecodocClient();
            List list = null;
            aFoo.callMethod10();
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
        #section2 = Section.objects.get(number='2.')

        # Index = 19
        coderef1 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='ChildClazz',
                source='d',
                kind_hint=self.class_kind,
                local_context=section11,
                mid_context=section1,
                global_context=page1
                )
        coderef1.save()
        self.code_refs.append(coderef1)

    def create_channel2(self):
        thread1 = SupportThread.objects.get(title='HTTP Server Question')
        message2 = Message.objects.get(title='RE: HTTP Server Question')
        thread2 = SupportThread.objects.get(title='Http client question')
        message4 = Message.objects.get(title='RE: Http client question')
        message5 = Message.objects.get(title='RE: RE: HTTP Server Question')

        # Index = 20
        coderef1 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='GeneralClient.getClient2()',
                source='s',
                kind_hint=self.class_kind,
                local_context=message2,
                global_context=thread1,
                )
        coderef1.save()
        self.code_refs.append(coderef1)

        coderef2 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='GeneralClient.getClient2()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                parent_reference=coderef1,
                )
        coderef2.save()
        self.code_refs.append(coderef2)

        # Index = 22
        coderef3 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='RecodocClient.getClient2()',
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
                content='RecodocClient.getClient2()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message2,
                global_context=thread1,
                parent_reference=coderef3,
                )
        coderef4.save()
        self.code_refs.append(coderef4)

        # Index = 24
        coderef5 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='callMethod10()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message4,
                global_context=thread2,
                )
        coderef5.save()
        self.code_refs.append(coderef5)

        # Index = 25
        coderef6 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='callMethod10()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message5,
                global_context=thread1,
                )
        coderef6.save()
        self.code_refs.append(coderef6)

        # Index = 26
        coderef7 = SingleCodeReference(
                project=self.project,
                project_release=self.releasedb,
                content='callMethod1000()',
                source='s',
                kind_hint=self.method_kind,
                local_context=message5,
                global_context=thread1,
                )
        coderef7.save()
        self.code_refs.append(coderef7)

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

    def test_context(self):
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
        
        code_ref20 = self.code_refs[19]
        code_ref20 = SingleCodeReference.objects.get(pk=code_ref20.pk)

        print('DEBUG CONTEXT')
        print(code_ref20.content)

        # Local Context
        context_types = ctx.get_context_types(
                code_ref20.local_object_id,
                code_ref20.source,
                ctx.local_filter,
                self.codebase,
                ctx.LOCAL)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertTrue('p1.ChildClazz' in fqn)
        self.assertEqual(1, len(fqn))

        context_types = ctx.get_context_types_hierarchy(
                code_ref20.local_object_id,
                code_ref20.source,
                ctx.local_filter,
                self.codebase,
                ctx.LOCAL)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertTrue('p1.InterfaceClazz' in fqn)
        self.assertEqual(3, len(fqn))

        # Mid Context
        context_types = ctx.get_context_types(
                code_ref20.mid_object_id,
                code_ref20.source,
                ctx.mid_filter,
                self.codebase,
                ctx.MIDDLE)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(3, len(fqn))
        self.assertTrue('p1.ChildClazz' in fqn)
        self.assertTrue('p1.Annotation1' in fqn)
        self.assertTrue('p1.Annotation2' in fqn)

        context_types = ctx.get_context_types_hierarchy(
                code_ref20.mid_object_id,
                code_ref20.source,
                ctx.mid_filter,
                self.codebase,
                ctx.MIDDLE)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(5, len(fqn))
        self.assertTrue('p1.InterfaceClazz' in fqn)

        # Global Context
        context_types = ctx.get_context_types(
                code_ref20.global_object_id,
                code_ref20.source,
                ctx.global_filter,
                self.codebase,
                ctx.GLOBAL)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(3, len(fqn))
        self.assertTrue('p1.Annotation2' in fqn)

        context_types = ctx.get_context_types_hierarchy(
                code_ref20.global_object_id,
                code_ref20.source,
                ctx.global_filter,
                self.codebase,
                ctx.GLOBAL)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(5, len(fqn))
        self.assertTrue('p1.InterfaceClazz' in fqn)

        # Snippet
        snippet1 = self.code_snippets[0]
        context_types = ctx.get_context_types(
                snippet1.pk,
                snippet1.source,
                ctx.snippet_filter,
                self.codebase,
                ctx.SNIPPET)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(2, len(fqn))
        self.assertTrue('p3.RecodocClient' in fqn)

        context_types = ctx.get_context_types_hierarchy(
                snippet1.pk,
                snippet1.source,
                ctx.snippet_filter,
                self.codebase,
                ctx.SNIPPET)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(5, len(fqn))
        self.assertTrue('p3.IGeneralClient' in fqn)

        # Return Type
        link_code(self.pname, 'core', self.release, 'javamethod', 'd',
                self.release)
        link_code(self.pname, 'core', self.release, 'javamethod', 's',
                None)
        code_ref14 = self.code_refs[13]
        code_ref14 = SingleCodeReference.objects.get(pk=code_ref14.pk)
        context_types = ctx.get_context_return_types(
                code_ref14.local_object_id,
                code_ref14.source,
                ctx.local_filter,
                self.codebase,
                ctx.LOCAL)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(1, len(fqn))
        self.assertTrue('p3.RecodocClient2' in fqn)

        context_types = ctx.get_context_return_types_hierarchy(
                code_ref14.local_object_id,
                code_ref14.source,
                ctx.local_filter,
                self.codebase,
                ctx.LOCAL)
        fqn = [context_type.fqn for context_type in context_types]
        print(fqn)
        self.assertEqual(2, len(fqn))
        self.assertTrue('p3.RecodocClient2Parent' in fqn)

    def test_linker(self):
        self.create_codebase()
        self.create_filters()
        self.create_documentation()
        self.create_channel()
        self.create_documentation2()
        self.create_channel2()
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

        # Test immediate context filter
        code_ref22 = self.code_refs[21]
        code_ref22 = SingleCodeReference.objects.get(pk=code_ref22.pk)
        method_log = DEBUG_LOG[code_ref22.pk][0]
        self.assertTrue(method_log['ImmediateContextFilter'][0])
        self.assertEqual('p3.GeneralClient',
                code_ref22.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])

        code_ref24 = self.code_refs[23]
        code_ref24 = SingleCodeReference.objects.get(pk=code_ref24.pk)
        method_log = DEBUG_LOG[code_ref24.pk][0]
        self.assertTrue(method_log['ImmediateContextHierarchyFilter'][0])
        self.assertEqual('p3.GeneralClient',
                code_ref24.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])

        # Test global filter
        code_ref25 = self.code_refs[24]
        code_ref25 = SingleCodeReference.objects.get(pk=code_ref25.pk)
        method_log = DEBUG_LOG[code_ref25.pk][0]
        self.assertTrue(method_log['globContextFilter'][0])
        self.assertEqual('p3.RecodocClient',
                code_ref25.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])

        # Test snippet filter
        snippet2 = self.code_snippets[1]
        snippet2 = CodeSnippet.objects.get(pk=snippet2.pk)
        method_ref = None
        for code_ref in snippet2.single_code_references.all():
            if code_ref.kind_hint.pk == self.method_kind.pk and\
                    code_ref.content.find('callMethod10') > -1:
                method_ref = code_ref
                break
        method_log = DEBUG_LOG[method_ref.pk][0]
        self.assertTrue(method_log['snipContextFilter'][0])
        self.assertEqual('p3.RecodocClient',
                method_ref.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])

        # Test return type
        code_ref18 = self.code_refs[17]
        code_ref18 = SingleCodeReference.objects.get(pk=code_ref18.pk)
        method_log = DEBUG_LOG[code_ref18.pk][0]
        self.assertTrue(method_log['locReturnContextFilter'][0])
        self.assertEqual('p3.RecodocClient2',
                code_ref18.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])

        # Test return type hierarchy
        code_ref19 = self.code_refs[18]
        code_ref19 = SingleCodeReference.objects.get(pk=code_ref19.pk)
        method_log = DEBUG_LOG[code_ref19.pk][0]
        self.assertTrue(method_log['locReturnContextFilterHierarchy'][0])
        self.assertEqual('p3.RecodocClient2Parent',
                code_ref19.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(1, method_log['final size'])

        # Test global filter
        code_ref26 = self.code_refs[25]
        code_ref26 = SingleCodeReference.objects.get(pk=code_ref26.pk)
        method_log = DEBUG_LOG[code_ref26.pk][0]
        print(method_log)
        self.assertTrue(method_log['AbstractTypeFilter'][0])
        self.assertEqual('p3.RecodocClient',
                code_ref26.release_links.all()[0]
                .first_link.code_element.containers.all()[0].fqn)
        self.assertEqual(2, method_log['final size'])
