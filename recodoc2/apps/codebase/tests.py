from __future__ import unicode_literals
import logging
import os
import time
import shutil
import unittest
from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.db import transaction
from py4j.java_gateway import JavaGateway
from docutil.commands_util import get_encoding
from docutil.test_util import clean_test_dir
from codebase.models import CodeBase, CodeElementKind, CodeElement,\
                            MethodElement, CodeSnippet
from codebase.actions import start_eclipse, stop_eclipse, check_eclipse,\
                             create_code_db, create_code_local, list_code_db,\
                             list_code_local, link_eclipse, get_codebase_path,\
                             create_code_element_kinds, parse_code,\
                             clear_code_elements, get_project_code_words,\
                             diff_codebases, parse_snippets 
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db
from docutil.cache_util import clear_cache


class EclipseTest(TestCase):

    @unittest.skip('Usually works.')
    def testEclipse(self):
        start_eclipse()
        self.assertTrue(check_eclipse())
        stop_eclipse()


class CodeSetup(TestCase):

    @classmethod
    def setUpClass(cls):
        time.sleep(1)
        start_eclipse()

    @classmethod
    def tearDownClass(cls):
        stop_eclipse()

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
        to_path = get_codebase_path('project1', 'core', '3.0')
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
        time.sleep(1)
        gateway.close()


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
        from_path = os.path.join(settings.TESTDATA, 'testproject1', 'src')
        shutil.copytree(from_path, to_path)
        link_eclipse('project1', 'core', '3.0')

        create_code_local('project1', 'core', '3.1')
        to_path = get_codebase_path('project1', 'core', '3.1')
        to_path = os.path.join(to_path, 'src')
        os.rmdir(to_path)
        from_path = os.path.join(settings.TESTDATA, 'testproject2', 'src')
        shutil.copytree(from_path, to_path)
        link_eclipse('project1', 'core', '3.1')

    @classmethod
    def tearDownClass(cls):
        gateway = JavaGateway()
        workspace = gateway.jvm.org.eclipse.core.resources.ResourcesPlugin.\
                getWorkspace()
        root = workspace.getRoot()
        pm = gateway.jvm.org.eclipse.core.runtime.NullProgressMonitor()
        project1 = root.getProject('project1core3.0')
        project1.delete(True, True, pm)
        project1 = root.getProject('project1core3.1')
        project1.delete(True, True, pm)
        time.sleep(1)
        gateway.close()
        stop_eclipse()
        clean_test_dir()

    @transaction.commit_on_success
    def setUp(self):
        clear_cache()
        logging.basicConfig(level=logging.WARNING)
        create_code_element_kinds()
        self.project = create_project_db('Project 1', 'http://www.example1.com',
                'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')

    @transaction.commit_on_success
    def tearDown(self):
        Project.objects.all().delete()
        CodeElementKind.objects.all().delete()
        clear_cache()

    @transaction.autocommit
    def testCodeWords(self):
        create_code_db('project1', 'core', '3.0')

        parse_code('project1', 'core', '3.0', 'java')

        code_words =\
            get_project_code_words(Project.objects.get(dir_name='project1'))

        self.assertTrue('rootapplication' in code_words)
        self.assertTrue('tag2' in code_words)
        self.assertTrue('dog' not in code_words)
        self.assertEqual(12, len(code_words))

    @transaction.autocommit
    def testJavaDiff(self):
        create_code_db('project1', 'core', '3.0')
        create_code_db('project1', 'core', '3.1')
        parse_code('project1', 'core', '3.0', 'java')
        parse_code('project1', 'core', '3.1', 'java')
        cdiff = diff_codebases('project1', 'core', '3.0', '3.1')

        self.assertEqual(4, cdiff.packages_size_from)
        self.assertEqual(5, cdiff.packages_size_to)
        self.assertEqual(1, cdiff.added_packages.count())
        self.assertEqual(0, cdiff.removed_packages.count())

        self.assertEqual(20, cdiff.types_size_from)
        self.assertEqual(19, cdiff.types_size_to)
        self.assertEqual(1, cdiff.added_types.count())
        self.assertEqual(2, cdiff.removed_types.count())

        self.assertEqual(45, cdiff.methods_size_from)
        self.assertEqual(44, cdiff.methods_size_to)
        self.assertEqual(1, cdiff.added_methods.count())
        self.assertEqual(1, cdiff.removed_methods.count())

        self.assertEqual(3, cdiff.fields_size_from)
        self.assertEqual(4, cdiff.fields_size_to)
        self.assertEqual(0, cdiff.added_fields.count())
        self.assertEqual(0, cdiff.removed_fields.count())

        self.assertEqual(6, cdiff.ann_fields_size_from)
        self.assertEqual(5, cdiff.ann_fields_size_to)
        self.assertEqual(0, cdiff.added_ann_fields.count())
        self.assertEqual(1, cdiff.removed_ann_fields.count())

        self.assertEqual(5, cdiff.enum_values_size_from)
        self.assertEqual(7, cdiff.enum_values_size_to)
        self.assertEqual(0, cdiff.added_enum_values.count())
        self.assertEqual(0, cdiff.removed_enum_values.count())

    def load_snippets(self):
        from_path = os.path.join(settings.TESTDATA, 'snippets')
        snippets = []
        for i, path in enumerate(sorted(os.listdir(from_path))):
            if path.endswith('.java'):
                with open(os.path.join(from_path, path)) as f:
                    text = f.read()
                    encoding = get_encoding(text)
                    content = unicode(text, encoding)
                    snippet = CodeSnippet(
                        index = i,
                        project = self.project,
                        snippet_text = content,
                        language = 'j',
                        source = 'd',
                        )
                    snippet.save()
                    snippets.append(snippet)
                    
        return snippets

    @transaction.autocommit
    def testJavaSnippetParser(self):
        snippets = self.load_snippets()
        parse_snippets('project1', 'd', 'java')
        
        # s1.java
        snippet = CodeSnippet.objects.get(pk=snippets[0].pk)
        contents = [
                'T!T:zzzsnippet.A',
                'T!T:zzzsnippet.A',
                'M!M:zzzsnippet.A:A:java.lang.String',
                'M!M:zzzsnippet.A:foo',
                'M!M:UNKNOWNP.UNKNOWN:bar:int:boolean',
                'T!T:zzzsnippet.B',
                'M!M:zzzsnippet.B:baz:zzzsnippet.A',
                'T!T:py4j.C',
                'M!M:py4j.C:hello:java.lang.String',
                'T!T:java.lang.Object',
                'T!T:py4j.internal.D',
                'M!M:py4j.internal.D:D:zzzsnippet.A',
                'T!T:java.lang.System',
                'F!F:java.lang.System:java.io.PrintStream:out',
                'M!M:java.io.PrintStream:println:java.lang.String',
                ]
        self.assertEqual(len(contents),
                snippet.single_code_references.count())
        for content, ref in\
                zip(contents, snippet.single_code_references.order_by('index')):
            self.assertEqual(content, ref.content)

    @transaction.autocommit
    def testJavaCodeParser(self):
        create_code_db('project1', 'core', '3.0')

        codebase = parse_code('project1', 'core', '3.0', 'java')

        ### Test some Classes ###
        ce = CodeElement.objects.get(fqn='RootApplication')
        self.assertEqual('RootApplication', ce.simple_name)
        self.assertEqual('class', ce.kind.kind)

        ce2 = CodeElement.objects.get(fqn='p1.p2.Tag')
        self.assertTrue(ce2.abstract)

        # Test containees & containers
        self.assertEqual(1, ce.containees.count())
        self.assertEqual('package', ce.containers.all()[0].kind.kind)
        self.assertEqual('', ce.containers.all()[0].fqn)

        ce = CodeElement.objects.get(fqn='p1.Application')
        self.assertEqual('Application', ce.simple_name)
        self.assertEqual('class', ce.kind.kind)
        # Test containees & containers
        self.assertEqual(1, ce.containees.count())
        self.assertEqual('package', ce.containers.all()[0].kind.kind)
        self.assertEqual('p1', ce.containers.all()[0].fqn)

        self.assertEqual(2,
                CodeElement.objects.filter(simple_name='Application').count())

        # Test hierarchy
        ce = CodeElement.objects.get(fqn='p1.AnimalException')
        # Nothing because the parent is not in the codebase
        # (java.lang.Exception)
        self.assertEqual(0, ce.parents.count())

        ce = CodeElement.objects.get(fqn='p1.p2.Dog')
        fqns = [parent.fqn for parent in ce.parents.all()]
        self.assertTrue('p1.p2.Canidae' in fqns)
        self.assertTrue('p1.p2.Tag' in fqns)
        self.assertTrue('p1.p2.Tag2' in fqns)

        # Test internal classes
        ce = CodeElement.objects.get(fqn='p3.Special.InnerSpecial')
        self.assertEqual('InnerSpecial', ce.simple_name)
        self.assertEqual('p3.Special', ce.containers.all()[0].fqn)
        self.assertEqual('method1', ce.containees.all()[0].simple_name)
        self.assertEqual('p3.Special.InnerSpecial.method1',
                ce.containees.all()[0].fqn)

        ### Test some Methods and Parameters ###
        ce = CodeElement.objects.get(fqn='p1.BigCat.doSomething')
        method = ce.methodelement
        self.assertEqual(4, method.parameters_length)
        self.assertTrue(MethodElement.objects.filter(simple_name='doSomething')
                .filter(parameters_length=4).exists())
        self.assertEqual(4, ce.parameters().count())
        self.assertEqual('method', ce.kind.kind)
        # Test container
        self.assertEqual('p1.BigCat', ce.containers.all()[0].fqn)

        self.assertEqual('specials', ce.parameters().all()[3].simple_name)
        # Array info is stripped from type.
        self.assertEqual('byte', ce.parameters().all()[2].type_fqn)
        # Generic info is stripped from type
        self.assertEqual('java.util.List', ce.parameters().all()[3].type_fqn)
        self.assertEqual('method parameter',
                ce.parameters().all()[3].kind.kind)

        ce = CodeElement.objects.get(fqn='p1.Animal.getParents')
        self.assertEqual('java.util.Collection', ce.methodelement.return_fqn)
        self.assertEqual('method', ce.kind.kind)
        # Test container
        self.assertEqual('p1.Animal', ce.containers.all()[0].fqn)

        ce = CodeElement.objects.get(fqn='p1.Animal.run')
        self.assertEqual('void', ce.methodelement.return_fqn)
        self.assertEqual('method', ce.kind.kind)

        ### Test some Fields ###
        ce = CodeElement.objects.get(fqn='p1.Animal.MAX_AGE')
        self.assertEqual('MAX_AGE', ce.simple_name)
        self.assertEqual('int', ce.fieldelement.type_simple_name)
        self.assertEqual('int', ce.fieldelement.type_fqn)
        self.assertEqual('field', ce.kind.kind)
        # Test container
        self.assertEqual('p1.Animal', ce.containers.all()[0].fqn)

        ce = CodeElement.objects.get(fqn='p1.Cat.name')
        self.assertEqual('java.lang.String', ce.fieldelement.type_fqn)
        self.assertEqual('field', ce.kind.kind)
        # Test container
        self.assertEqual('p1.Cat', ce.containers.all()[0].fqn)

        ### Test some Enumerations ###
        ce = CodeElement.objects.get(fqn='p1.AnimalType')
        self.assertEqual('enumeration', ce.kind.kind)
        self.assertTrue(ce.kind.is_type)
        self.assertEqual('enumeration value',
                ce.containees.all()[0].kind.kind)
        self.assertEqual('p1.AnimalType',
                ce.containees.all()[0].fieldelement.type_fqn)
        simple_names = [v.simple_name for v in ce.containees.all()]
        self.assertTrue('NOT_SURE' in simple_names)
        self.assertEqual(3, len(simple_names))

        ce = CodeElement.objects.get(fqn='p1.SubAnimalType')
        self.assertEqual('enumeration', ce.kind.kind)
        self.assertTrue(ce.kind.is_type)
        simple_names = [v.simple_name for v in ce.containees.all()]
        self.assertTrue('SOFT' in simple_names)
        # Because it is private!
        self.assertTrue('SubAnimalType' not in simple_names)
        self.assertTrue('getOther' in simple_names)
        self.assertTrue('other' not in simple_names)
        self.assertEqual(3, len(simple_names))

        ### Test some Annotations ###
        ce = CodeElement.objects.get(fqn='p1.AnimalTag')
        self.assertEqual('annotation', ce.kind.kind)
        self.assertEqual('annotation field', ce.containees.all()[0].kind.kind)
        fooBar = ce.containees.filter(simple_name='fooBar').all()[0]
        self.assertEqual('java.lang.String', fooBar.fieldelement.type_fqn)
        self.assertEqual(6, ce.containees.count())

        self.assertEqual(109, codebase.code_elements.count())

        clear_code_elements('project1', 'core', '3.0', 'xml')
        self.assertEqual(109, codebase.code_elements.count())
        clear_code_elements('project1', 'core', '3.0')
        self.assertEqual(0, codebase.code_elements.count())
