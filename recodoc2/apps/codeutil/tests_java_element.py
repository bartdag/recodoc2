from __future__ import unicode_literals
from django.test import TestCase
import docutil.str_util as su
import codeutil.java_element as je
from codebase.models import SingleCodeReference
import codebase.actions as ca

psc = ca.parse_single_code_references 

# A few tests for some tricky RE. Nothing more.
class JavaElementRETest(TestCase):

    def test_methods(self):
        s1 = 'new p1.Clazz("hello", 2, arg1)'
        self.assertIsNotNone(je.CONSTRUCTOR_CALL_RE.match(s1))
        self.assertIsNone(je.ANONYMOUS_CLASS_DECLARATION_RE.match(s1))

    def test_types(self):
        s1 = 'end of sentence. Hello World! This is FooBar'
        it = je.TYPE_IN_MIDDLE_RE.finditer(s1)
        match = it.next()
        self.assertEqual('.', match.group('dot'))
        self.assertEqual('Hello', match.group('class'))

        match = it.next()
        self.assertIsNone(match.group('dot'))
        self.assertEqual('World', match.group('class'))
        
        match = it.next()
        self.assertEqual('!', match.group('dot'))
        self.assertEqual('This', match.group('class'))
        
        match = it.next()
        self.assertIsNone(match.group('dot'))
        self.assertEqual('FooBar', match.group('class'))


class JavaElementFunctionsTest(TestCase):

    def test_java_name(self):
        to_test = [
            ('java.lang.String', 'java.lang.String', 'String'),
            ('String', 'String', 'String'),
            ('p1.Foo$Fa', 'p1.Foo.Fa', 'Fa'),
            ('p1.Foo$Fa<p2.String,int>', 'p1.Foo.Fa', 'Fa'),
            ('p1.Bar[[]]', 'p1.Bar', 'Bar'),
            ]
        for (original, fqn, simple) in to_test:
            (simple2, fqn2) = je.clean_java_name(original)
            self.assertEqual(simple, simple2)
            self.assertEqual(fqn, fqn2)


class JavaStrategyTest(TestCase):
    
    def setUp(self):
        ca.create_code_element_kinds()
        self.kinds = ca.get_default_kind_dict()
        self.strategies = ca.get_java_strategies()

    def tearDown(self):
        SingleCodeReference.objects.all().delete()

    def test_methods_method(self):
        text = 'foo(1, "hello")'
        refs = psc(text, self.kinds['method'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('foo(1, "hello")', refs[0].content)
        self.assertEqual('method', refs[0].kind_hint.kind)

        # With target
        text = 'com.Clazz.foo(1, "hello")'
        refs = psc(text, self.kinds['method'], self.strategies, self.kinds)
        self.assertEqual(2, len(refs))
        self.assertEqual('com.Clazz.foo(1, "hello")', refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual('com.Clazz.foo(1, "hello")', refs[1].content)
        self.assertEqual('method', refs[1].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[1].parent_reference.pk)

        # Call chain
        text = 'com.Clazz.foo(1, "hello").bar().baz(foo)'
        refs = psc(text, self.kinds['method'], self.strategies, self.kinds)
        self.assertEqual(4, len(refs))
        self.assertEqual(text, refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual(text, refs[1].content)
        self.assertEqual('method', refs[1].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[1].parent_reference.pk)
        self.assertEqual('bar()', refs[2].content)
        self.assertEqual('method', refs[2].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[2].parent_reference.pk)
        self.assertEqual('baz(foo)', refs[3].content)
        self.assertEqual('method', refs[3].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[3].parent_reference.pk)

    def test_methods_unknown(self):
        text = 'foo(1, "hello")'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('foo(1, "hello")', refs[0].content)
        self.assertEqual('method', refs[0].kind_hint.kind)

        # With target
        text = 'com.Clazz.foo(1, "hello")'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(2, len(refs))
        self.assertEqual('com.Clazz.foo(1, "hello")', refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual('com.Clazz.foo(1, "hello")', refs[1].content)
        self.assertEqual('method', refs[1].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[1].parent_reference.pk)

        # Call chain
        text = 'com.Clazz.foo(1, "hello").bar().baz(foo)'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(4, len(refs))
        self.assertEqual(text, refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual(text, refs[1].content)
        self.assertEqual('method', refs[1].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[1].parent_reference.pk)
        self.assertEqual(0, refs[1].child_index)
        self.assertEqual('bar()', refs[2].content)
        self.assertEqual('method', refs[2].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[2].parent_reference.pk)
        self.assertEqual(1, refs[2].child_index)
        self.assertEqual('baz(foo)', refs[3].content)
        self.assertEqual('method', refs[3].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[3].parent_reference.pk)
        self.assertEqual(2, refs[3].child_index)

    def test_fields_unknown(self):
        text = 'THIS_CONSTANT'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('THIS_CONSTANT', refs[0].content)
        self.assertEqual('field', refs[0].kind_hint.kind)

        text = 'com.Clazz.THIS_CONSTANT'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(2, len(refs))
        self.assertEqual('com.Clazz.THIS_CONSTANT', refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual('com.Clazz.THIS_CONSTANT', refs[1].content)
        self.assertEqual('field', refs[1].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[1].parent_reference.pk)

        text = 'com.Clazz.foo'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(2, len(refs))
        self.assertEqual('com.Clazz.foo', refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual('com.Clazz.foo', refs[1].content)
        self.assertEqual('field', refs[1].kind_hint.kind)
        self.assertEqual(refs[0].pk, refs[1].parent_reference.pk)

    def test_classes_class(self):
        # Because class is the forced hint.
        text = '123'
        refs = psc(text, self.kinds['class'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('123', refs[0].content)

        text = 'FooBar'
        refs = psc(text, self.kinds['class'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('FooBar', refs[0].content)

        text = 'java.util.ArrayList'
        refs = psc(text, self.kinds['class'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('java.util.ArrayList', refs[0].content)

        text = '@FooBar'
        refs = psc(text, self.kinds['class'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('@FooBar', refs[0].content)
        self.assertEqual('annotation', refs[0].kind_hint.kind)

        text = '@com.FooBar'
        refs = psc(text, self.kinds['class'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('@com.FooBar', refs[0].content)
        self.assertEqual('annotation', refs[0].kind_hint.kind)

    def test_classes_unknown(self):
        text = '123'
        refs = psc(text, self.kinds['class'], self.strategies, self.kinds,
                strict=True)
        self.assertEqual(0, len(refs))

        text = 'FooBar'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('FooBar', refs[0].content)

        text = 'java.util.ArrayList'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('java.util.ArrayList', refs[0].content)

        text = '@FooBar'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('@FooBar', refs[0].content)
        self.assertEqual('annotation', refs[0].kind_hint.kind)

        text = '@com.FooBar'
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds)
        self.assertEqual(1, len(refs))
        self.assertEqual('@com.FooBar', refs[0].content)
        self.assertEqual('annotation', refs[0].kind_hint.kind)

    def test_text(self):
        text = r'''
        The class FooBar and Boo is useful to call method m1("hello").
        You should know that FooBar.CONSTANT is fun, but @Bar and buz().baz(1)
        does not equal com.Baz.m2("", null).m3(CONST);
        '''
        text = su.clean_breaks(text).strip()
        refs = psc(text, self.kinds['unknown'], self.strategies, self.kinds,
                save_index=True)
        self.assertEqual(11, len(refs))

        self.assertEqual('FooBar', refs[0].content)
        self.assertEqual('class', refs[0].kind_hint.kind)
        self.assertEqual(0, refs[0].index)

        self.assertEqual('Boo', refs[1].content)
        self.assertEqual('class', refs[1].kind_hint.kind)
        self.assertEqual(1, refs[1].index)

        self.assertEqual('m1("hello")', refs[2].content)
        self.assertEqual('method', refs[2].kind_hint.kind)
        self.assertEqual(2, refs[2].index)

        self.assertEqual('FooBar.CONSTANT', refs[3].content)
        self.assertEqual('class', refs[3].kind_hint.kind)
        self.assertEqual(3, refs[3].index)

        self.assertEqual('FooBar.CONSTANT', refs[4].content)
        self.assertEqual('field', refs[4].kind_hint.kind)
        self.assertEqual(3, refs[4].index)

        self.assertEqual('@Bar', refs[5].content)
        self.assertEqual('annotation', refs[5].kind_hint.kind)
        self.assertEqual(4, refs[5].index)

        self.assertEqual('buz().baz(1)', refs[6].content)
        self.assertEqual('method', refs[6].kind_hint.kind)
        self.assertEqual(5, refs[6].index)

        self.assertEqual('baz(1)', refs[7].content)
        self.assertEqual('method', refs[7].kind_hint.kind)
        self.assertEqual(5, refs[7].index)

        self.assertEqual('com.Baz.m2("", null).m3(CONST);', refs[8].content)
        self.assertEqual('class', refs[8].kind_hint.kind)
        self.assertEqual(6, refs[8].index)

        self.assertEqual('com.Baz.m2("", null).m3(CONST);', refs[9].content)
        self.assertEqual('method', refs[9].kind_hint.kind)
        self.assertEqual(6, refs[9].index)

        self.assertEqual('m3(CONST);', refs[10].content)
        self.assertEqual('method', refs[10].kind_hint.kind)
        self.assertEqual(6, refs[10].index)
