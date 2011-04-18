from __future__ import unicode_literals
from django.test import TestCase
import codeutil.java_element as je


# A few tests for some tricky RE. Nothing more.
class JavaElementRETest(TestCase):

    def test_methods(self):
        s1 = 'new p1.Clazz("hello", 2, arg1)'
        self.assertIsNotNone(je.CONSTRUCTOR_CALL_RE.match(s1))
        self.assertIsNone(je.ANONYMOUS_CLASS_DECLARATION_RE.match(s1))

    def test_types(self):
        s1 = 'end of sentence. Hello World! This is FooBar'
        it = je.TYPE_IN_MIDDLE.finditer(s1)
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
