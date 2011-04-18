from __future__ import unicode_literals
import os
from lxml import etree
from django.test import TestCase
from django.conf import settings
import docutil.url_util as uu
import docutil.commands_util as cc
import docutil.str_util as su
import docutil.cache_util as cu
import docutil.etree_util as eu


page_test = '''
<html>
<head>
<title>Hello World</title>
</head>
<body>
<h1>Hello World 2 3 4 <script>document.write('hello a')</script>5<h1>
<p>
<div>Hello</div>
<div>Yo <script> document.write(); document.write();</script>
deleitou
</div>
FooBar!
</p>
<p>
Hillo!
</p>
</body>
</html>
'''.encode('utf-8')

page_test2 = '''
<html>
<head>
<title>Hello World</title>
</head>
<body>
<h1>Hello World 2 3 4 <script>document.write('hello a')</script>5<h1>
<p>
<div>Hello</div>
<div>
Hello World <tt>foobar</tt>. This is nice. Yo.
</div>
<div>
Hello World <code>foo</code>. This is <code>foo</code>. Yo.
</div>
<div>
Hello World foo. This is <b>foo</b>. Yo.
</div>
FooBar!
</p>
</body>
</html>
'''.encode('utf-8')


class EtreeUtilTest(TestCase):
    @classmethod
    def setUpClass(self):
        self.test_doc = os.path.join(settings.TESTDATA, 'httpclient402doc',
            'connmgmt.html')
        page = open(self.test_doc)
        content = page.read()
        page.close()
        encoding = cc.get_encoding(content)
        self.parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
        self.tree = etree.fromstring(content, self.parser).getroottree()

    def test_xpathlist(self):
        xpathlist = eu.XPathList(['//h1[1]', '//title[1]', '//h2[1]'])
        element = xpathlist.get_element(self.tree)
        self.assertEqual('title', element.tag)
        self.assertEqual('Chapter 2. Connection management',
                xpathlist.get_text(element))
        self.assertEqual('Chapter 2. Connection management',
                xpathlist.get_text_from_parent(self.tree))
        self.assertEqual(1, len(xpathlist.get_elements(self.tree)))

    def text_xpath(self):
        xpath = eu.SingleXPath('//div[@class="section"]')
        self.assertEqual(12, len(xpath.get_elements(self.tree)))
        self.assertEqual('2.2. Connection persistence',
                xpath.get_text_from_parent(self.tree, 1))
        element = xpath.get_element(self.tree, 1)
        self.assertEqual('2.2. Connection persistence',
                xpath.get_text(element, 1))

    def test_hierarchy(self):
        xpath = eu.HierarchyXPath('//div[@class="chapter"]',
                'div[@class="section"]')
        text = xpath.get_text_from_parent(self.tree)
        self.assertEqual(39, len(text.split()))
        element = xpath.get_element(self.tree)
        self.assertEqual(2, len(xpath.get_element_as_list(element)))

    def test_word_count(self):
        encoding = cc.get_encoding(page_test)
        parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
        tree = etree.fromstring(page_test, parser).getroottree()
        eu.clean_tree(tree)

        h1 = eu.SingleXPath('//h1[1]')
        h1_element = h1.get_element(tree)
        wc = eu.get_word_count(h1.get_element_as_list(h1_element))
        print(h1.get_text(h1_element))
        self.assertEqual(6, wc)

        body = eu.SingleXPath('//body[1]')
        body_element = body.get_element(tree)
        wc = eu.get_word_count(body.get_element_as_list(body_element))
        print(body.get_text(body_element))
        self.assertEqual(11, wc)

    def test_get_text_context(self):
        encoding = cc.get_encoding(page_test2)
        parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
        tree = etree.fromstring(page_test2, parser).getroottree()
        eu.clean_tree(tree)
        
        tt = tree.xpath('//tt[1]')[0]
        text_context = eu.get_text_context(tt)
        self.assertEqual('Hello World foobar. This is nice. Yo.', text_context)

    def test_get_sentence(self):
        encoding = cc.get_encoding(page_test2)
        parser = etree.HTMLParser(remove_comments=True, encoding=encoding)
        tree = etree.fromstring(page_test2, parser).getroottree()
        eu.clean_tree(tree)
        
        tt = tree.xpath('//tt[1]')[0]
        text_context = eu.get_text_context(tt)
        sentence = eu.get_sentence(tt, 'foobar', text_context)
        self.assertEqual('Hello World foobar.', sentence)

        # Test when there are more than one match!
        code = tree.xpath('//code[2]')[0]
        text_context = eu.get_text_context(code)
        sentence = eu.get_sentence(code, 'foo', text_context)
        self.assertEqual('This is foo.', sentence)

        # Test when there are more than one match, but wrong markup (sorry...)
        b = tree.xpath('//b[1]')[0]
        text_context = eu.get_text_context(b)
        sentence = eu.get_sentence(b, 'foo', text_context)
        self.assertEqual('Hello World foo.', sentence)


class CommandsUtilTest(TestCase):
    def test_encoding(self):
        url = 'http://www.infobart.com/index.php/about/'
        file_from = \
            cc.get_file_from(url)
        content = file_from.read()
        encoding = cc.get_encoding(content)
        self.assertEqual(encoding, 'utf-8')
        self.assertTrue(len(content) > 0)
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

    def test_find_sentence(self):
        p1 = 'Hello world. This is luis. Come and get me.'
        index1 = p1.find('world')
        index2 = p1.find('is')
        index3 = p1.find('Come')
        self.assertEqual('Hello world.', su.find_sentence(p1, index1, index1 +
            len('world')))
        self.assertEqual('This is luis.', su.find_sentence(p1, index2, index2 +
            len('is')))
        self.assertEqual('Come and get me.', su.find_sentence(p1, index3, index3 +
            len('Come')))

        p2 = 'Hello world'
        self.assertEqual('Hello world', su.find_sentence(p2, 0, len('Hello')))


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
