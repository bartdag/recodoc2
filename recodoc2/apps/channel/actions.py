from __future__ import unicode_literals
import os
import logging
import codecs
import json
from traceback import print_exc
from django.conf import settings
from django.db import transaction

from docutil.str_util import get_original_title
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
    return channel


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
    model = load_model(pname, STHREAD_PATH, cname)
    for entry in model.entries:
        entry.parsed = False
    dump_model(model, pname, STHREAD_PATH, cname)

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

            print('Downloaded section {0}'.format(section.index))
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

            print('Downloaded {0}'.format(entry.url))
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
    dump_model(model, pname, STHREAD_PATH, cname)
    return channel


@transaction.autocommit
def debug_channel(pname, cname, parse_refs=True, entry_url=None):
    model = load_model(pname, STHREAD_PATH, cname)
    channel = SupportChannel.objects.filter(project__dir_name=pname).\
            get(dir_name=cname)
    pm = CLIProgressMonitor()
    generic_parser.debug_channel(channel, model, progress_monitor=pm,
            parse_refs=parse_refs, entry_url=entry_url)
    return channel


@transaction.autocommit
def post_process_channel(pname, cname):
    channel = SupportChannel.objects.filter(project__dir_name=pname).\
            get(dir_name=cname)
    progress_monitor = CLIProgressMonitor()

    query = Message.objects.filter(sthread__isnull=True)
    progress_monitor.start('Post Processing', query.count())
    for message in query.all():
        post_process_message(channel, message)
        progress_monitor.work('Post processed a message', 1)
    progress_monitor.done()

    progress_monitor.start('Post Porcessing Threads', channel.threads.count())
    for thread in channel.threads.iterator():
        post_process_thread(channel, thread)
        progress_monitor.work('Post processed a thread', 1)
    progress_monitor.done()

    query = Message.objects.filter(sthread__channel=channel)
    progress_monitor.start('Post Processing References', query.count())
    for message in query.all():
        post_process_message_refs(message)
        progress_monitor.work('Processed references', 1)
    progress_monitor.done()

    return channel


def json_snippet(pname, cname, output_path):
    channel = SupportChannel.objects.filter(project__dir_name=pname).\
            get(dir_name=cname)

    stack_traces = []

    for sthread in channel.threads.iterator():
        url = sthread.url
        for snippet in sthread.code_snippets.all():
            if snippet.language == 'jx':
                stack_traces.append((url, snippet.snippet_text))

    with codecs.open(output_path, 'w', 'utf8') as json_file:
        json.dump(stack_traces, json_file)


### INTERNAL FUNCTIONS ###

def show_message(msg_pk):
    message = Message.objects.get(pk=msg_pk)
    print(message.title)
    print(message.url)
    print('{0} - {1}'.format(message.index, message.author))
    print(message.word_count)
    print(message.pk)
    for code_reference in message.code_references.all():
        link = code_reference.first_link()
        if link is not None:
            link_str = link.code_element.human_string()
        else:
            link_str = ''
        print('{0};{1}'.format(code_reference.content, link_str))


def post_process_message(channel, message):
    original_title = get_original_title(message.title)

    potential_threads = SupportThread.objects.filter(channel=channel).\
            filter(title__iexact=original_title)
    count = potential_threads.count()

    if count == 1:
        potential_threads.all()[0].messages.add(message)
    elif count > 1:
        logger.warning("More than one thread for this title: {0}"
                .format(original_title))
        potential_threads.all()[0].messages.add(message)
    else:
        start_thread(original_title, message, channel)


def post_process_thread(channel, thread):
    messages = thread.messages.order_by('msg_date').all()
    last_index = -1
    for i, message in enumerate(messages):
        message.index = i
        if i > 0:
            try:
                message.title_code_references.all().delete()
            except Exception:
                pass
        message.save()
        last_index = i
    if last_index > -1:
        thread.first_date = messages[0].msg_date
        thread.last_date = messages[last_index].msg_date
    elif thread.last_date is None:
        logger.error('This thread {0} has no message!'.format(thread.pk))
        thread.first_date = None
        thread.last_date = None

    try:
        thread.save()
    except Exception:
        print('Error with these messages {0} and {1}, thread {2}'.\
                format(messages[0].pk, messages[last_index].pk, thread.pk))
        print_exc()


def start_thread(title, support_message, channel):
    # This is a thread!

    support_thread = SupportThread(
            title=title,
            url=support_message.url,
            file_path=support_message.file_path,
            channel=channel,
            pages=1)
    support_thread.save()
    support_message.index = 0
    support_message.save()
    support_thread.messages.add(support_message)


def post_process_message_refs(message):
    sthread = message.sthread
    for reference in message.code_references.all():
        reference.global_context = sthread
        reference.save()
    for snippet in message.code_snippets.all():
        snippet.global_context = sthread
        snippet.save()
