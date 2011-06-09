from __future__ import unicode_literals

import logging
import os
import multiprocessing
from traceback import print_exc
from django.db import connection
from django.conf import settings
from docutil.str_util import clean_breaks, get_paragraphs, filter_paragraphs,\
        REPLY_LANGUAGE, merge_lines
from docutil.etree_util import get_word_count_text
from docutil.progress_monitor import NullProgressMonitor
from docutil.commands_util import chunk_it, import_clazz, download_html_tree
from project.models import Person
from codebase.actions import get_default_p_classifiers,\
        get_default_kind_dict, get_java_strategies,\
        parse_single_code_references, get_project_code_words
from codebase.models import CHANNEL_SOURCE, CodeSnippet
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
                if local_paths is not None and len(local_paths) > 0:
                    parser.parse_entry(local_paths, url)
        return True
    except Exception:
        print_exc()
        return False
    finally:
        # Manually close this connection
        connection.close()


def debug_channel(channel, model, progress_monitor=NullProgressMonitor(),
        parse_refs=True, entry_url=None):
    manager = multiprocessing.Manager()
    lock = manager.RLock()
    work_units = BUCKET_PER_WORKER

    # Prepare Input
    entries = []
    for entry in model.entries:
        if entry.url == entry_url:
            entries.append((entry.local_paths, entry.url))
            entry.parsed = True
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
    pool = multiprocessing.Pool(1)
    for result in pool.imap_unordered(sub_process_parse, inputs,
            BUCKET_PER_WORKER):
        progress_monitor.work('Parsed a chunk', 1)

    pool.close()
    progress_monitor.done()


def parse_channel(channel, model, pool_size=DEFAULT_POOL_SIZE,
        progress_monitor=NullProgressMonitor(), parse_refs=True):
    manager = multiprocessing.Manager()
    lock = manager.RLock()
    work_units = pool_size * BUCKET_PER_WORKER

    # Prepare Input
    entries = []
    for entry in model.entries:
        if not entry.parsed:
            entries.append((entry.local_paths, entry.url))
            entry.parsed = True
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
        self.sub_entries = []
        self.code_words = None
        self.entry_element = None


class GenericParser(object):

    LINE_THRESHOLD = settings.CHANNEL_LINE_THRESHOLD

    xtitle = None
    '''XPath to find the message title. Required'''

    xauthor = None
    '''XPath to find the message author. Required'''

    xdate = None
    '''XPath to find the message date. Required'''

    xcontent = None
    '''XPath to find the message content. Required'''

    def __init__(self, channel_pk, parse_refs, lock):
        self.lock = lock
        self.channel = SupportChannel.objects.get(pk=channel_pk)
        self.parse_refs = parse_refs
        self.kinds = get_default_kind_dict()
        self.kind_strategies = get_java_strategies()

    def _build_code_words(self, load):
        # Build code words and put it in self.load
        load.code_words = \
            get_project_code_words(self.channel.project)

    def parse_entry(self, local_paths, url):
        load = ParserLoad()
        self._build_code_words(load)
        self._pre_parse_entry(load, local_paths, url)

        for i, local_path in enumerate(local_paths):
            path = os.path.join(settings.PROJECT_FS_ROOT, local_path)
            load.tree = download_html_tree(path)
            self._parse_entry(path, local_path, url, i, load)

        self._post_parse_entry(load)

    def _pre_parse_entry(self, load, local_paths, url):
        pass

    def _post_parse_entry(self, load):
        pass

    def _parse_message(self, path, relative_path, url, index, load):
        message = Message(url=url, file_path=relative_path)
        message.index = index

        message.title = self._process_title(message, load)[0:500]
        if len(message.title) > 500:
            print('LONG TITLE: {0}'.format(message.title))
            message.title = message.title[0:500]

        author_text = self._process_author(message, load)
        if author_text is not None:
            message.author = self._get_author(author_text, self.lock)

        message.msg_date = self._process_date(message, load)

        ucontent = self._process_content(message, load)

        #print(url)
        #print('CONTENT DEBUG:\n {0}'.format(ucontent))

        message.word_count = get_word_count_text(ucontent)

        if load.entry is not None:
            message.sthread = load.entry

        message.save()

        load.sub_entries.append(message)

        if self.parse_refs:
            self._process_references(message, load, ucontent)

    def _process_title(self, message, load):
        title = self.xtitle.get_text_from_parent(load.entry_element)
        if title is None or title.strip() == '':
            title = 'Default Title'
            logger.warning('No title for message {0}'
                    .format(message.file_path))
        return title

    def _process_author(self, message, load):
        author_text = self.xauthor.get_text_from_parent(load.entry_element)
        author_text = author_text.replace('&lt;', '<')
        index = author_text.find('<')
        if index > -1:
            return author_text[:index].strip()
        else:
            return author_text.strip()

    def _process_date(self, message, load):
        date_text = self.xdate.get_text_from_parent(load.entry_element).strip()
        date = self._process_date_text(message, load, date_text)
        return date

    def _process_date_text(self, message, load, date_text):
        pass

    def _get_author(self, nickname, lock=None):
        with lock:
            try:
                author = Person.objects.get(nickname=nickname)
            except:
                author = Person(nickname=nickname)
                author.save()
        return author

    def _skip_message(self, paragraphs):
        count = sum((len(paragraph) for paragraph in paragraphs))
        return (count, count > self.LINE_THRESHOLD)

    def _process_content(self, message, load):
        ucontent = self.xcontent.get_text_from_parent(load.entry_element)\
                .strip()
        return ucontent

    def _process_references(self, message, load, ucontent):
        lines = self._get_lines(message, load, ucontent)
        paragraphs = get_paragraphs(lines)

        (count, skip) = self._skip_message(paragraphs)
        if skip:
            logger.warning('Skipping message {0}:{1}. {2} lines'
                    .format(message.pk, message.url, count))
            return

        self._process_title_references(message, load)
        (text_paragraphs, snippets) = filter_paragraphs(paragraphs,
                get_default_p_classifiers())
        self._parse_paragraphs(message, load, text_paragraphs)
        self._save_snippets(message, load, snippets)

    def _get_lines(self, message, load, ucontent):
        lines = []

        if not message.title.lower().strip().startswith('re:'):
            lines.append(clean_breaks(message.title))
            lines.append('')

        new_content = ucontent.replace('\r', '').replace('\t', ' ')
        content_lines = new_content.split('\n')
        for content_line in content_lines:
            content_line = content_line.replace('&lt;', '<')\
                    .replace('&gt;', '>')
            if not self._uninteresting_line(content_line):
                lines.append(content_line)

        return lines

    def _uninteresting_line(self, line):
        line = line.strip()
        if line.startswith('From: ') or line.startswith('To: ') or \
                line.startswith('Sent: ') or line.startswith('Subject: '):
            return True
        elif line.startswith('To unsubscribe, e-mail:'):
            return True
        elif line.startswith('For additional commands,'):
            return True
        else:
            return False

    def _process_title_references(self, message, load):
        text_context = message.title
        sentence = message.title

        kind_hint = self.kinds['unknown']
        xpath = message.xpath
        for code in parse_single_code_references(sentence, kind_hint,
                self.kind_strategies, self.kinds, strict=True):
            code.xpath = xpath
            code.file_path = message.file_path
            code.source = CHANNEL_SOURCE
            code.index = -1
            code.sentence = sentence
            code.paragraph = text_context
            code.title_context = message
            code.local_context = message
            if load.entry is not None:
                code.global_context = load.entry
            code.save()

    def _parse_paragraphs(self, message, load, text_paragraphs):
        for para_index, paragraph in enumerate(text_paragraphs):
            text = merge_lines(paragraph, False)
            kind_hint = self.kinds['unknown']
            for i, code in enumerate(
                    parse_single_code_references(
                        text, kind_hint, self.kind_strategies,
                        self.kinds, find_context=True, strict=True,
                        code_words=load.code_words)):
                code.file_path = message.file_path
                code.url = message.url
                code.index = i + (para_index * 1000)
                code.project = self.channel.project
                code.local_context = message
                if load.entry is not None:
                    code.global_context = load.entry
                code.save()

    def _save_snippets(self, message, load, snippets):
        for index, (snippet, language) in enumerate(snippets):
            if language == REPLY_LANGUAGE:
                continue
            text = merge_lines(snippet)
            code = CodeSnippet(
                    file_path=message.file_path,
                    url=message.url,
                    language=language,
                    source=CHANNEL_SOURCE,
                    snippet_text=text,
                    index=index)
            code.local_context = message

            if load.entry is not None:
                code.global_context = load.entry

            code.project = self.channel.project
            code.save()


class GenericMailParser(GenericParser):

    def __init__(self, channel_pk, parse_refs, lock):
        super(GenericMailParser, self).__init__(channel_pk, parse_refs, lock)

    def _parse_entry(self, path, relative_path, url, index, load):
        load.entry_element = load.tree
        self._parse_message(path, relative_path, url, index, load)


class GenericThreadParser(GenericParser):

    xmessages = None
    '''XPath to find messages in a thread. Required'''

    msg_per_page = 10
    '''Constant used to determine the index of the messages'''

    def __init__(self, channel_pk, parse_refs, lock):
        super(GenericThreadParser, self).__init__(channel_pk, parse_refs, lock)

    def _pre_parse_entry(self, load, local_paths, url):
        sthread = SupportThread(
                url=url,
                file_path=local_paths[0],
                pages=len(local_paths),
                channel=self.channel
                )
        sthread.save()
        load.entry = sthread

    def _post_parse_entry(self, load):
        sthread = load.entry
        if len(load.sub_entries) > 0:
            sthread.title = load.sub_entries[0].title
            sthread.first_date = load.sub_entries[0].msg_date
            sthread.last_date = load.sub_entries[-1].msg_date
        sthread.save()

    def _get_messages(self, load):
        message_elements = self.xmessages.get_elements(load.tree)
        return message_elements
        
    def _parse_entry(self, path, relative_path, url, index, load):
        message_elements = self._get_messages(load)
        for i, message_element in enumerate(message_elements):
            load.entry_element = message_element
            msg_index = (index * self.msg_per_page) + i
            self._parse_message(path, relative_path, url, msg_index, load)

    def _process_content(self, message, load):
        try:
            ucontent = self.xcontent.get_text_from_parent(load.entry_element,
                    complex_text=True).strip()
        except Exception:
            print_exc()
            ucontent = ''
        return ucontent
        #return ucontent.replace('\n','\n\n')
