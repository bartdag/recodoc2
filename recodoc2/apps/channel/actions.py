from __future__ import unicode_literals
import os
from django.conf import settings

from docutil.commands_util import mkdir_safe, dump_model, load_model,\
    import_clazz
from project.models import Project
from project.actions import STHREAD_PATH
from channel.models import SupportChannel, SupportChannelStatus


def get_channel_path(pname, cname=None, root=False):
    if root:
        chan_key = ''
    else:
        chan_key = cname
    basepath = settings.PROJECT_FS_ROOT
    chan_path = os.path.join(basepath, pname, STHREAD_PATH, chan_key)
    return chan_path


def create_channel_local(pname, channel_name, syncer):
    channel_path = get_channel_path(pname, channel_name)
    mkdir_safe(channel_path)
    status = SupportChannelStatus(syncer)
    dump_model(status, pname, STHREAD_PATH, channel_name)


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
