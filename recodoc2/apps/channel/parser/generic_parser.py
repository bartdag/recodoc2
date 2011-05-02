from __future__ import unicode_literals

import logging
import os
import multiprocessing
from traceback import print_exc
from django.db import connection
from django.conf import settings
from docutil.etree_util import get_word_count_text
from docutil.progress_monitor import NullProgressMonitor
from docutil.commands_util import chunk_it, import_clazz, download_html_tree
from project.models import Person
from channel.models import SupportChannel, SupportThread, Message


DEFAULT_POOL_SIZE = 4
BUCKET_PER_WORKER = 25

logger = logging.getLogger("recodoc.channel.parser.generic")


def sub_process_parse(einput):
    try:
        # Unecessary if already closed by parent process.
        # But it's ok to be sure.
        connection.close()
        (parser_cls, channel_pk, entry_chunk, parse_refs, lock) = einput

        parser = import_clazz(parser_cls)(channel_pk, parse_refs, lock)
        for entry_input in entry_chunk:
            if entry_input is not None:
                (local_paths, url) = entry_input
                # Check if downloaded
                if local_paths is not None or len(local_paths) > 0:
                    parser.parse_entry(local_paths, url)
        return True
    except Exception:
        print_exc()
        return False
    finally:
        # Manually close this connection
        connection.close()


def parse_channel(channel, model, pool_size=DEFAULT_POOL_SIZE,
        progress_monitor=NullProgressMonitor(), parse_refs=True):
    manager = multiprocessing.Manager()
    lock = manager.RLock()
    work_units = pool_size * BUCKET_PER_WORKER

    # Prepare Input
    entries = [(entry.local_paths, entry.url) for entry in model.entries]
    entries_chunks = chunk_it(entries, work_units)
    inputs = []
    for entry_chunk in entries_chunks:
        inputs.append((channel.parser, channel.pk, entry_chunk, parse_refs,
            lock))

    # Close connection to allow the new processes to create their own
    connection.close()

    progress_monitor.start('Parsing Channel Entries', len(inputs))
    progress_monitor.info('Sending {0} chunks to worker pool'
            .format(len(inputs)))
    pool = multiprocessing.Pool(pool_size)
    for result in pool.imap_unordered(sub_process_parse, inputs,
            BUCKET_PER_WORKER):
        progress_monitor.work('Parsed a chunk', 1)

    pool.close()
    progress_monitor.done()


class ParserLoad(object):

    def __init__(self):
        self.tree = None
        self.entry = None
        self.sub_entries = None


class GenericParser(object):

    def __init__(self, channel_pk, parse_refs, lock):
        self.lock = lock
        self.channel = SupportChannel.objects.get(pk=channel_pk)
        self.parse_refs = parse_refs

    def parse_entry(self, local_paths, url):
        load = ParserLoad()
        for i, local_path in enumerate(local_paths):
            path = os.path.join(settings.PROJECT_FS_ROOT, local_path)
            load.tree = download_html_tree(path)
            self._parse_entry(path, local_path, url, i, load)

    def _get_author(self, nickname, lock=None):
        with lock:
            try:
                author = Person.objects.get(nickname=nickname)
            except:
                author = Person(nickname=nickname)
                author.save()
        return author


class GenericMailParser(GenericParser):

    xtitle = None
    '''XPath to find the message title. Required'''

    xauthor = None
    '''XPath to find the message author. Required'''

    xdate = None
    '''XPath to find the message date. Required'''

    xcontent = None
    '''XPath to find the message content. Required'''

    def __init__(self, channel_pk, parse_refs, lock):
        super(GenericMailParser, self).__init__(channel_pk, parse_refs, lock)

    def _parse_entry(self, path, relative_path, url, index, load):
        message = Message(url=url, file_path=relative_path)

        message.title = self._process_title(message, load)

        author_text = self._process_author(message, load)
        if author_text is not None:
            message.author = self._get_author(author_text, self.lock)

        message.msg_date = self._process_date(message, load)

        ucontent = self._process_content(message, load)
        message.word_count = get_word_count_text(ucontent)
        message.save()

        if self.parse_refs:
            self._process_references(message, load, ucontent)

    def _process_title(self, message, load):
        title = self.xtitle.get_text_from_parent(load.tree)
        if title is None or title == '':
            title = 'Default Title'
            logger.warning('No title for message {0}'
                    .format(message.file_path))
        return title

    def _process_author(self, message, load):
        author_text = self.xauthor.get_text_from_parent(load.tree)
        author_text = author_text.replace('&lt;', '<')
        index = author_text.find('<')
        if index > -1:
            return author_text[:index].strip()
        else:
            return author_text.strip()

    def _process_date(self, message, load):
        date_text = self.xdate.get_text_from_parent(load.tree).strip()
        date = self._process_date_text(message, load, date_text)
        return date

    def _process_date_text(self, message, load, date_text):
        pass

    def _process_content(self, message, load):
        ucontent = self.xcontent.get_text_from_parent(load.tree).strip()
        return ucontent

    def _process_references(self, message, load, ucontent):
        pass


class GenericThreadParser(GenericParser):

    def __init__(self, channel_pk, parse_refs, lock):
        super(GenericThreadParser, self).__init__(channel_pk, parse_refs, lock)

    def _parse_entry(self, path, relative_path, url, index, load):
        pass
