from __future__ import unicode_literals
from django.test import TestCase
from docutil.java_util import clean_java_name


class JavaUtilTest(TestCase):
    def test_java_name(self):
        to_test = [
            ('java.lang.String', 'java.lang.String', 'String'),
            ('String', 'String', 'String'),
            ('p1.Foo$Fa', 'p1.Foo.Fa', 'Fa'),
            ('p1.Foo$Fa<p2.String,int>', 'p1.Foo.Fa', 'Fa'),
            ('p1.Bar[[]]', 'p1.Bar', 'Bar'),
            ]
        for (original, fqn, simple) in to_test:
            (simple2, fqn2) = clean_java_name(original)
            self.assertEqual(simple, simple2)
            self.assertEqual(fqn, fqn2)
