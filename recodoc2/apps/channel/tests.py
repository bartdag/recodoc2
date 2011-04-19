from __future__ import unicode_literals
import os
import logging
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
        list_channels_db, list_channels_local, get_channel_path


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
        create_channel_local('project1', 'coreforum', 'foo.syncer')
        create_channel_local('project1', 'webforum', 'foo.syncer')
        path = get_channel_path('project1', root=True)
        self.assertEqual(2, len(os.listdir(path)))

    def test_list_doc_local(self):
        create_channel_local('project1', 'coreforum', 'foo.syncer')
        create_channel_local('project1', 'webforum', 'foo.syncer')
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
