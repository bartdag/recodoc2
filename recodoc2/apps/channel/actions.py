from __future__ import unicode_literals
import os
import logging
from django.conf import settings
from django.db import transaction

from docutil.progress_monitor import CLIProgressMonitor
from docutil.commands_util import mkdir_safe, dump_model, load_model,\
    import_clazz
from project.models import Project
from project.actions import STHREAD_PATH
from channel.parser import generic_parser
from channel.models import SupportChannel, SupportChannelStatus,\
        SupportThread, Message


logger = logging.getLogger("recodoc.channel.actions")


def get_channel_path(pname, cname=None, root=False):
    if root:
        chan_key = ''
    else:
        chan_key = cname
    basepath = settings.PROJECT_FS_ROOT
    chan_path = os.path.join(basepath, pname, STHREAD_PATH, chan_key)
    return chan_path


def create_channel_local(pname, cname, syncer, url):
    channel_path = get_channel_path(pname, cname)
    mkdir_safe(channel_path)
    status = SupportChannelStatus(syncer, url)
    dump_model(status, pname, STHREAD_PATH, cname)


def create_channel_db(pname, channel_fullname, channel_dir_name, syncer,
        parser, url=''):
    project = Project.objects.get(dir_name=pname)
    channel = SupportChannel(name=channel_fullname,
            dir_name=channel_dir_name,
            project=project,
            url=url,
            parser=parser,
            syncer=syncer)
    channel.save()


def list_channels_db(pname):
    channels = []
    for channel in SupportChannel.objects.filter(project__dir_name=pname):
        channels.append(
                '{0}: {1} ({2})'.format(channel.pk, channel.name, channel.url))
    return channels


def list_channels_local(pname):
    channel_path = get_channel_path(pname, root=True)
    local_channels = []
    for member in os.listdir(channel_path):
        if os.path.isdir(os.path.join(channel_path, member)):
            local_channels.append(member)
    return local_channels


def clear_channel_elements(pname, cname):
    channel = SupportChannel.objects.filter(project__dir_name=pname).\
            get(dir_name=cname)
    query = Message.objects.filter(sthread__channel=channel)
    print('Deleting {0} messages'.format(query.count()))
    for message in query.all():
        message.code_references.all().delete()
        message.code_snippets.all().delete()
        message.delete()
    SupportThread.objects.filter(channel=channel).delete()


def toc_view(pname, cname):
    model = load_model(pname, STHREAD_PATH, cname)
    size = len(model.toc_sections)
    downloaded = sum(
            (1 for section in model.toc_sections if section.downloaded))
    last_d = -1
    for section in model.toc_sections:
        if section.downloaded:
            last_d = section.index
        else:
            break

    print('Table of Content Status for {0}'.format(cname))
    print('Number of sections: {0}'.format(size))
    print('Number of downloaded sections: {0}'.format(downloaded))
    print('Last downloaded section index: {0}'.format(last_d))


def toc_refresh(pname, cname):
    model = load_model(pname, STHREAD_PATH, cname)
    try:
        syncer = import_clazz(model.syncer_clazz)()
        syncer.toc_refresh(model)
        dump_model(model, pname, STHREAD_PATH, cname)
    except Exception:
        logger.exception('Error while refreshing toc')


def toc_download_section(pname, cname, start=None, end=None, force=False):
    model = load_model(pname, STHREAD_PATH, cname)
    syncer = import_clazz(model.syncer_clazz)()
    for section in model.toc_sections:
        index = section.index
        if start is not None and start > index:
            continue
        elif end is not None and end <= index:
            continue
        elif section.downloaded and not force:
            continue
        try:
            syncer.toc_download_section(model, section)
            dump_model(model, pname, STHREAD_PATH, cname)
        except Exception:
            logger.exception('Error while downloading toc section')


def toc_view_entries(pname, cname):
    model = load_model(pname, STHREAD_PATH, cname)
    size = len(model.entries)
    downloaded = sum(
            (1 for entry in model.entries if entry.downloaded))
    last_d = -1
    for entry in model.entries:
        if entry.downloaded:
            last_d = entry.index
        else:
            break

    print('Table of Content Entries Status for {0}'.format(cname))
    print('Number of entries: {0}'.format(size))
    print('Number of downloaded entries: {0}'.format(downloaded))
    print('Last downloaded entry index: {0}'.format(last_d))


def toc_download_entries(pname, cname, start=None, end=None, force=False):
    model = load_model(pname, STHREAD_PATH, cname)
    channel_path = get_channel_path(pname, cname)
    syncer = import_clazz(model.syncer_clazz)()
    for entry in model.entries:
        index = entry.index
        if start is not None and start > index:
            continue
        elif end is not None and end <= index:
            continue
        elif entry.downloaded and not force:
            continue
        try:
            syncer.download_entry(entry, channel_path)
            dump_model(model, pname, STHREAD_PATH, cname)
        except Exception:
            logger.exception('Error while downloading entry')


@transaction.autocommit
def parse_channel(pname, cname, parse_refs=True):
    model = load_model(pname, STHREAD_PATH, cname)
    channel = SupportChannel.objects.filter(project__dir_name=pname).\
            get(dir_name=cname)
    pm = CLIProgressMonitor()
    generic_parser.parse_channel(channel, model, progress_monitor=pm,
            parse_refs=parse_refs)
    return channel


def post_process_channel(pname, cname):
    pass
