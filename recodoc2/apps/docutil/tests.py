from __future__ import unicode_literals
from django.test import TestCase
from docutil.java_util import clean_java_name
import docutil.url_util as uu
import docutil.commands_util as cc
import docutil.str_util as su
import docutil.cache_util as cu


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


class CommandsUtilTest(TestCase):
    def test_encoding(self):
        url = 'http://www.infobart.com/index.php/about/'
        file_from = \
            cc.get_file_from(url)
        encoding = cc.get_encoding(file_from, url)
        self.assertEqual(encoding, 'UTF-8')
        self.assertTrue(len(file_from.read()) > 0)
        file_from.close()


class UrlUtilTest(TestCase):
    def test_check_url(self):
        self.assertTrue(uu.check_url('www.infobart.com', '/'))
        self.assertTrue(uu.check_url('www.infobart.com', '/', True))
        self.assertFalse(uu.check_url('www.infobart.com', '/foo/barbaz'))

    def test_sanitize_file_name(self):
        self.assertEqual(uu.sanitize_file_name('hello!/es'), 'hello----es')
        self.assertEqual(uu.sanitize_file_name('hello--'), 'hello--')

    def test_get_relative_url(self):
        self.assertEqual(uu.get_relative_url('/home/bart',
            '/home/bart/foo/bar.txt'), 'foo/bar.txt')
        self.assertEqual(uu.get_relative_url('/home/bart/',
            '/home/bart/foo/bar.txt'), 'foo/bar.txt')
        self.assertEqual(uu.get_relative_url('/',
            '/foo/bar.txt'), 'foo/bar.txt')
        self.assertEqual(uu.get_relative_url('/biz', '/foo/bar.txt'),
            '/foo/bar.txt')

    def test_is_local(self):
        self.assertTrue(uu.is_local('/foo/bar.txt'))
        self.assertTrue(uu.is_local('file:///foo/bar.txt'))
        self.assertFalse(uu.is_local('http://foo/bar.txt'))

    def test_is_absolute(self):
        self.assertTrue(uu.is_absolute('/foo/bar.txt'))
        self.assertTrue(uu.is_absolute('file:///foo/bar.txt'))
        self.assertFalse(uu.is_absolute('foo/bar.txt'))

    def get_url_without_hash(self):
        self.assertEqual(uu.get_url_without_hash('http://www.yo.com/foo#bar'),
                'http://www.you.com/foo')
        self.assertEqual(uu.get_url_without_hash('http://www.yo.com/foo'),
                'http://www.you.com/foo')

    def test_get_sanitized_file(self):
        self.assertEqual(uu.get_sanitized_file('file:///yo/bar.txt#foo?hello'),
                'bar.txt')
        self.assertEqual(uu.get_sanitized_file('bar'),
                'bar')

    def test_get_sanitized_local_url(self):
        self.assertEqual(uu.get_sanitized_url('/foo/bar'),
                'file:///foo/bar')
        self.assertEqual(uu.get_sanitized_url('file:///foo/bar'),
                'file:///foo/bar')
        self.assertEqual(uu.get_sanitized_url('http://foo/bar'),
                'http://foo/bar')
        self.assertEqual(uu.get_sanitized_url('foo/bar'),
                'foo/bar')

    def test_get_sanitized_directory(self):
        self.assertEqual(uu.get_sanitized_directory('/foo/bar'),
                '/foo/bar/')
        self.assertEqual(uu.get_sanitized_directory('/foo/bar/'),
                '/foo/bar/')

    def test_get_local_url(self):
        self.assertEqual(uu.get_local_url('/home/bart/doc',
            'http://doc.com/foo/bar.txt'), '/home/bart/doc/foo/bar.txt')
        self.assertEqual(uu.get_local_url('/home/bart/doc/',
            'http://doc.com/foo/bar/'),
            '/home/bart/doc/foo/bar/bar__root.html')
        self.assertEqual(uu.get_local_url('/home/bart/doc',
            'http://doc.com/'), '/home/bart/doc/root__root.html')


class StrUtilTest(TestCase):
    def test_tokenize(self):
        inputs = [
        ('Foo', ['Foo']),
        ('foo', ['foo']),
        ('fooBar', ['foo', 'Bar']),
        ('BarFooBaz', ['Bar', 'Foo', 'Baz']),
        ]

        for i in inputs:
            self.assertEqual(i[1], su.tokenize(i[0]))


def func1():
    return 3


def func2(arg1, arg2):
    return su.smart_decode(arg1 + arg2)


class CacheUtilTest(TestCase):
    def setUp(self):
        cu.clear_cache()
        cu.reset_cache_stats()

    def tearDown(self):
        cu.clear_cache()
        cu.reset_cache_stats()

    def test_empty_cache(self):
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))
        self.assertEqual(2, cu.cache_miss)
        self.assertEqual(2, cu.cache_total)

    def test_cache_hit(self):
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))
        self.assertEqual(2, cu.cache_miss)
        self.assertEqual(6, cu.cache_total)

    def test_cache_clear(self):
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))

        cu.clear_cache()
        
        self.assertEqual(3, cu.get_value(
            'p', 'k', func1, None))
        self.assertEqual('6', cu.get_value(
            'p', 'k2', func2, [1, 5]))
        self.assertEqual(4, cu.cache_miss)
        self.assertEqual(6, cu.cache_total)
