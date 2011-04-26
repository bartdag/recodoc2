from __future__ import unicode_literals
import os
import logging
import unittest
from django.test import TestCase, TransactionTestCase
from django.conf import settings

from docutil.commands_util import load_model
from docutil.test_util import clean_test_dir
from project.models import Project
from project.actions import create_project_local, create_project_db,\
                            create_release_db, STHREAD_PATH
from codebase.models import CodeElementKind, SingleCodeReference, CodeSnippet
from channel.models import SupportChannel
from channel.actions import create_channel_local, create_channel_db,\
        list_channels_db, list_channels_local, get_channel_path, toc_refresh,\
        toc_download_section, toc_download_entries


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
        self.assertEqual(79, len(model.toc_sections))
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

    def test_phpbb_syncer(self):
        create_channel_db('project1', 'cf', 'coreforum',
                'channel.syncer.common_syncers.PHPBBForumSyncer', 'foo.parser',
                'https://forum.hibernate.org/viewforum.php?f=1&start=0'
                )
        create_channel_local('project1', 'coreforum',
                'channel.syncer.common_syncers.PHPBBForumSyncer',
                'https://forum.hibernate.org/viewforum.php?f=1&start=0'
                )
        pname = 'project1'
        cname = 'coreforum'
        toc_refresh(pname, cname)
        model = load_model(pname, STHREAD_PATH, cname)
        self.assertEqual(
                'https://forum.hibernate.org/viewforum.php?f=1&sd=a&start=0',
                model.toc_sections[0].url)
        self.assertFalse(model.toc_sections[0].downloaded)
        self.assertEqual(2349, len(model.toc_sections))
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
