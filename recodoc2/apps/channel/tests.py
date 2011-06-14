from __future__ import unicode_literals
import os
import logging
import unittest
from datetime import datetime
from django.test import TestCase, TransactionTestCase
from django.conf import settings
from django.db import transaction

from docutil.commands_util import load_model
from docutil.test_util import clean_test_dir
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db, STHREAD_PATH
from codebase.models import CodeElementKind, SingleCodeReference, CodeSnippet
from codebase.actions import create_code_element_kinds
from channel.models import SupportChannel, Message
from channel.actions import create_channel_local, create_channel_db,\
        list_channels_db, list_channels_local, get_channel_path, toc_refresh,\
        toc_download_section, toc_download_entries, parse_channel,\
        post_process_channel


class ChannelSetup(TestCase):
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
        create_channel_local('project1', 'coreforum', 'foo.syncer', 'foo.com')
        create_channel_local('project1', 'webforum', 'foo.syncer', 'foo.com')
        path = get_channel_path('project1', root=True)
        self.assertEqual(2, len(os.listdir(path)))

    def test_list_doc_local(self):
        create_channel_local('project1', 'coreforum', 'foo.syncer',
                'http://foo')
        create_channel_local('project1', 'webforum', 'foo.syncer',
                'http://foo')
        self.assertEqual(2, len(list_channels_local('project1')))

    def test_create_doc_db(self):
        create_channel_db('project1', 'cf', 'coreforum', 'foo.syncer',
                'foo.parser', 'http://yo.com')
        create_channel_db('project1', 'wf', 'webforum', 'foo.syncer',
                'foo.parser', 'http://yo.com')
        self.assertEqual(2, SupportChannel.objects.count())

    def test_list_doc_db(self):
        create_channel_db('project1', 'cf', 'coreforum', 'foo.syncer',
                'foo.parser', 'http://yo.com')
        create_channel_db('project1', 'wf', 'webforum', 'foo.syncer',
                'foo.parser', 'http://yo.com')
        self.assertEqual(2, len(list_channels_db('project1')))

    #@unittest.skip('Usually works.')
    def test_apache_syncer(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.ApacheMailSyncer', 'foo.parser',
                'http://mail-archives.apache.org/mod_mbox/hc-httpclient-users/'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.ApacheMailSyncer',
                'http://mail-archives.apache.org/mod_mbox/hc-httpclient-users/'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertEqual(
                'http://mail-archives.apache.org/mod_mbox/hc-httpclient-users/200410.mbox/date',
                model.toc_sections[0].url)
        self.assertFalse(model.toc_sections[0].downloaded)
        self.assertTrue(len(model.toc_sections) >= 79)
        for i in xrange(0, 79):
            self.assertEqual(i, model.toc_sections[i].index)

        toc_download_section(pname, cname, start=0, end=4)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertTrue(model.toc_sections[0].downloaded)
        self.assertTrue(model.toc_sections[1].downloaded)
        self.assertTrue(model.toc_sections[2].downloaded)
        self.assertTrue(model.toc_sections[3].downloaded)
        self.assertFalse(model.toc_sections[4].downloaded)
        self.assertEqual(316, len(model.entries))
        self.assertEqual(0, model.entries[0].index)
        self.assertFalse(model.entries[0].downloaded)
        self.assertEqual(1000, model.entries[17].index)
        self.assertEqual(1001, model.entries[18].index)
        self.assertTrue(model.entries[18].url.find('xbox.localdomain') > -1)

        toc_download_entries(pname, cname, 0, 1)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertTrue(model.entries[0].downloaded)
        self.assertFalse(model.entries[1].downloaded)
        path = os.path.join(settings.PROJECT_FS_ROOT,
                model.entries[0].local_paths[0])
        self.assertTrue(os.path.exists(path))

    #@unittest.skip('Usually works.')
    def test_phpbb_syncer(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.PHPBBForumSyncer', 'foo.parser',
                'https://forum.hibernate.org/viewforum.php?f=1'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.PHPBBForumSyncer',
                'https://forum.hibernate.org/viewforum.php?f=1'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertEqual(
                'https://forum.hibernate.org/viewforum.php?f=1&sd=a&start=0',
                model.toc_sections[0].url)
        self.assertFalse(model.toc_sections[0].downloaded)
        self.assertTrue(len(model.toc_sections) > 2349)
        for i in xrange(0, 2349):
            self.assertEqual(i, model.toc_sections[i].index)

        toc_download_section(pname, cname, start=0, end=4)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertTrue(model.toc_sections[0].downloaded)
        self.assertTrue(model.toc_sections[1].downloaded)
        self.assertTrue(model.toc_sections[2].downloaded)
        self.assertTrue(model.toc_sections[3].downloaded)
        self.assertFalse(model.toc_sections[4].downloaded)
        self.assertEqual(100, len(model.entries))
        self.assertEqual(0, model.entries[0].index)
        self.assertFalse(model.entries[0].downloaded)
        self.assertEqual(1000, model.entries[25].index)
        self.assertEqual(1001, model.entries[26].index)
        self.assertTrue(model.entries[26].url.find('t=59') > -1)

        toc_download_entries(pname, cname, 1024, 1025)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertTrue(model.entries[49].downloaded)
        self.assertFalse(model.entries[50].downloaded)
        path = os.path.join(settings.PROJECT_FS_ROOT,
                model.entries[49].local_paths[0])
        self.assertTrue(os.path.exists(path))
        path = os.path.join(settings.PROJECT_FS_ROOT,
                model.entries[49].local_paths[1])
        self.assertTrue(os.path.exists(path))

    #@unittest.skip('Usually works.')
    def test_fudeclipse_syncer(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.FUDEclipseForumSyncer',
                'foo.parser',
                'http://www.eclipse.org/forums/index.php/sf/thread/13/'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.FUDEclipseForumSyncer',
                'http://www.eclipse.org/forums/index.php/sf/thread/13/'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertEqual(
                'http://www.eclipse.org/forums/index.php/sf/thread/13/1/0/',
                model.toc_sections[0].url)
        self.assertFalse(model.toc_sections[0].downloaded)

        self.assertTrue(len(model.toc_sections) >= 247)
        for i in xrange(0, 247):
            self.assertEqual(i, model.toc_sections[i].index)

        toc_download_section(pname, cname, start=0, end=4)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertTrue(model.toc_sections[0].downloaded)
        self.assertTrue(model.toc_sections[1].downloaded)
        self.assertTrue(model.toc_sections[2].downloaded)
        self.assertTrue(model.toc_sections[3].downloaded)
        self.assertFalse(model.toc_sections[4].downloaded)

        self.assertEqual(160, len(model.entries))
        self.assertEqual(0, model.entries[0].index)
        self.assertFalse(model.entries[0].downloaded)
        self.assertEqual(1000, model.entries[40].index)
        self.assertEqual(1001, model.entries[41].index)
        #self.assertTrue(model.entries[26].url.find('t=59') > -1)

        toc_download_entries(pname, cname, 1039, 1040)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertTrue(model.entries[79].downloaded)
        self.assertFalse(model.entries[80].downloaded)
        path = os.path.join(settings.PROJECT_FS_ROOT,
                model.entries[79].local_paths[0])
        self.assertTrue(os.path.exists(path))

class ChannelParserTest(TransactionTestCase):
    @transaction.commit_on_success
    def setUp(self):
        logging.basicConfig(level=logging.WARNING)
        settings.PROJECT_FS_ROOT = settings.PROJECT_FS_ROOT_TEST
        create_code_element_kinds()
        create_project_local('project1')
        create_project_db('Project 1', 'http://www.example1.com', 'project1')
        create_release_db('project1', '3.0', True)
        create_release_db('project1', '3.1')

    @transaction.commit_on_success
    def tearDown(self):
        Project.objects.all().delete()
        CodeElementKind.objects.all().delete()
        SingleCodeReference.objects.all().delete()
        CodeSnippet.objects.all().delete()
        clean_test_dir()

    @transaction.autocommit
    def test_apache_parser(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.ApacheMailSyncer', 
                'channel.parser.common_parsers.ApacheMailParser',
                'http://mail-archives.apache.org/mod_mbox/hc-httpclient-users/'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.ApacheMailSyncer',
                'http://mail-archives.apache.org/mod_mbox/hc-httpclient-users/'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        toc_download_section(pname, cname, start=0, end=1)
        toc_download_entries(pname, cname, 9, 99)
        parse_channel(pname, cname, True)
        self.assertEqual(8, Message.objects.all().count())
        messages = list(Message.objects.all())
        for message in messages:
            print('{0} by {1} on {2} (wc: {3})'.format(
                message.title, message.author, message.msg_date,
                message.word_count))
            print('  {0} snippets and {1} references'.format(
                message.code_snippets.count(),
                message.code_references.count()))
            print('  Snippets:')
            for code_snippet in message.code_snippets.all():
                print('    {0}'.format(code_snippet.language))

            for ref in message.code_references.all():
                print('    {0}: {1}'.format(ref.kind_hint.kind, ref.content))

        
        # Test Snippets
        third_to_last = messages[-3]
        self.assertEqual('l', third_to_last.code_snippets.all()[0].language)
        self.assertEqual('jx', third_to_last.code_snippets.all()[1].language)

        # Test Refs
        fourth_to_last = messages[-4]
        refs = [ref.content.strip() for ref in
                fourth_to_last.code_references.all()]
        self.assertEqual(4, len(refs))
        self.assertTrue('EasySSLProtocolSocketFactory' in refs)
        self.assertTrue('SSL' in refs)

        # Test Post-Processing!
        channel = post_process_channel(pname, cname)
        self.assertEqual(4, channel.threads.count())

        second_thread = channel.threads.all()[1]
        self.assertEqual(3, second_thread.messages.count())

        indexes = [msg.index for msg in second_thread.messages.all()]
        self.assertEqual([0, 1, 2], indexes)
        self.assertFalse(second_thread.messages.all()[0].title.lower()
                .startswith('re'))
        self.assertTrue(second_thread.messages.all()[1].title.lower()
                .startswith('re'))

    @transaction.autocommit
    def test_phpbb_parser(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.PHPBBForumSyncer',
                'channel.parser.common_parsers.PHPBBForumParser',
                'https://forum.hibernate.org/viewforum.php?f=1'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.PHPBBForumSyncer',
                'https://forum.hibernate.org/viewforum.php?f=1'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        toc_download_section(pname, cname, start=0, end=2)
        toc_download_entries(pname, cname, 1023, 1025)
        parse_channel(pname, cname, True)
        self.assertEqual(23, Message.objects.all().count())
        messages = list(Message.objects.all())
        for message in messages:
            print(message.url)
            print('{0} by {1} on {2} (wc: {3})'.format(
                message.title, message.author, message.msg_date,
                message.word_count))
            print('  {0} snippets and {1} references'.format(
                message.code_snippets.count(),
                message.code_references.count()))
            print('  Snippets:')
            for code_snippet in message.code_snippets.all():
                print('    {0}'.format(code_snippet.language))

            for ref in message.code_references.all():
                print('    {0}: {1}'.format(ref.kind_hint.kind, ref.content))
        
        # Test Snippets
        first_message = messages[0]
        self.assertEqual('x', first_message.code_snippets.all()[0].language)

        # Test Author
        self.assertEqual(first_message.author.nickname, 'mhellkamp')

        # Test Date
        self.assertEqual(first_message.msg_date, datetime(2003, 8, 29, 10, 16))

        # Test Refs
        second_message = messages[1]
        refs = [ref.content.strip() for ref in
                second_message.code_references.all()]
        # Title is not counted.
        self.assertEqual(4, len(refs))
        self.assertTrue('DBCP' in refs)
        self.assertTrue('C3P0' in refs)

    @transaction.autocommit
    def test_fudeclipse_parser(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.FUDEclipseForumSyncer',
                'channel.parser.common_parsers.FUDEclipseForumParser',
                'http://www.eclipse.org/forums/index.php/sf/thread/59/'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.FUDEclipseForumSyncer',
                'http://www.eclipse.org/forums/index.php/sf/thread/59/'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        toc_download_section(pname, cname, start=0, end=2)
        toc_download_entries(pname, cname, 0, 6)
        parse_channel(pname, cname, True)
        self.assertEqual(18, Message.objects.all().count())
        messages = list(Message.objects.all())
        for message in messages:
            print('{0} by {1} on {2} (wc: {3})'.format(
                message.title, message.author, message.msg_date,
                message.word_count))
            print('  {0} snippets and {1} references'.format(
                message.code_snippets.count(),
                message.code_references.count()))
            print('  Snippets:')
            for code_snippet in message.code_snippets.all():
                print('    {0}'.format(code_snippet.language))

            for ref in message.code_references.all():
                print('    {0}: {1}'.format(ref.kind_hint.kind, ref.content))
        
        first_message = messages[0]

        # Test Title
        self.assertEqual(first_message.title, 
            'looping back to a previous step')

        # Test Author
        self.assertEqual(first_message.author.nickname, 'No real name')

        # Test Date
        self.assertEqual(first_message.msg_date, datetime(2010, 8, 26, 7, 50))

        # Test Refs
        refs = [ref.content.strip() for ref in
                first_message.code_references.all()]
        self.assertEqual(3, len(refs))
        self.assertTrue('ActivityElements' in refs)
