from __future__ import unicode_literals

import logging
import re
from datetime import datetime
from docutil.str_util import get_month_as_int
from docutil.etree_util import SingleXPath, HierarchyXPath
from channel.parser.generic_parser import GenericMailParser,\
    GenericThreadParser

logger = logging.getLogger("recodoc.doc.parser.common")


class ApacheMailParser(GenericMailParser):
    xtitle = SingleXPath('//tr[@class="subject"]/td[2]')

    xauthor = SingleXPath('//tr[@class="from"]/td[2]')

    xdate = SingleXPath('//tr[@class="date"]/td[2]')

    xcontent = SingleXPath('//tr[@class="contents"]//pre')

    date_regex = re.compile(r'''
    (?P<day>\d{2})\s
    (?P<month>\w{3})\s
    (?P<year>\d{4})\s
    (?P<hour>\d{2}):
    (?P<minute>\d{2}):
    (?P<second>\d{2})
    ''', re.VERBOSE)

    def __init__(self, channel_pk, parse_refs, lock):
        super(ApacheMailParser, self).__init__(channel_pk, parse_refs, lock)

    def _process_date_text(self, message, load, date_text):
        match = self.date_regex.search(date_text)
        if match is None:
            logger.error('This date text does not match expected pattern: {0}'
                    .format(date_text))
            return None

        date = datetime(
                int(match.group('year')),
                get_month_as_int(match.group('month')),
                int(match.group('day')),
                int(match.group('hour')),
                int(match.group('minute')),
                int(match.group('second'))
                )

        return date


class PHPBBForumParser(GenericThreadParser):

    xmessages = SingleXPath('//div[@id="pagecontent"]/table[@class="tablebg"]')

    xtitle = SingleXPath('.//td[@class="gensmall"]/div[1]')

    xauthor = SingleXPath('.//b[@class="postauthor"]')

    xdate = SingleXPath('.//td[@class="gensmall"]/div[2]')

    xcontent = HierarchyXPath('.//div[@class="postbody"]',
            './/div[@class="codetitle"] | .//div[@class="quotetitle"] |'
            './/div[@class="quotecontent"]')

    msg_per_page = 15

    title_prefix = 'Post subject:'

    title_length = len(title_prefix)

    date_regex = re.compile(r'''
    (?P<month>\w{3})\s
    (?P<day>\d{2}),\s
    (?P<year>\d{4})\s
    (?P<hour>\d{1,2}):
    (?P<minute>\d{2})\s
    (?P<pm>\w{2})
    ''', re.VERBOSE)

    def __init__(self, channel_pk, parse_refs, lock):
        super(PHPBBForumParser, self).__init__(channel_pk, parse_refs, lock)

    def _get_messages(self, load):
        message_elements = self.xmessages.get_elements(load.tree)
        if len(message_elements) > 0:
            # This is because the first and last table are for display
            # purpose...
            message_elements = message_elements[1:-1]
        return message_elements

    def _process_title(self, message, load):
        title = self.xtitle.get_text_from_parent(load.entry_element)
        if title is None or title.strip() == '':
            title = 'Default Title'
            logger.warning('No title for message {0}'
                    .format(message.file_path))
        else:
            title = title.strip()
            index = title.find(self.title_prefix)
            if index > -1:
                title = title[index + self.title_length:].strip()

        return title

    def _process_date_text(self, message, load, date_text):
        match = self.date_regex.search(date_text)
        if match is None:
            logger.error('This date text does not match expected pattern: {0}'
                    .format(date_text))
            return None

        hour = int(match.group('hour'))

        if match.group('pm').lower() == 'pm' and hour < 12:
            hour += 12

        date = datetime(
                int(match.group('year')),
                get_month_as_int(match.group('month')),
                int(match.group('day')),
                hour,
                int(match.group('minute')),
                )

        return date


class FUDEclipseForumParser(GenericThreadParser):
    
    xmessages = SingleXPath('//table[@class="MsgTable"]')

    xtitle = SingleXPath('.//a[@class="MsgSubText"]')

    xauthor = SingleXPath(
            './/table[@class="ContentTable"]//td[@class="msgud"]/a[1]')

    xdate = SingleXPath('.//span[@class="DateText"]')

    # Here we do not remove blockquote and cite, because they are
    # sometimes used to post code. Yeah. Great :-(
    xcontent = HierarchyXPath('.//span[@class="MsgBodyText"]',
            './/div[@class="codehead"]')

    date_regex = re.compile(r'''
        (?P<dayweek>\w{3}),\s
        (?P<day>\d{2})\s
        (?P<month>\w+)\s
        (?P<year>\d{4})\s
        (?P<hour>\d{2}):
        (?P<minute>\d{2})
        ''', re.VERBOSE)

    def __init__(self, channel_pk, parse_refs, lock):
        super(FUDEclipseForumParser, self).__init__(channel_pk, parse_refs, lock)

    def _process_date_text(self, message, load, date_text):
        match = self.date_regex.search(date_text)
        if match is None:
            logger.error('This date text does not match expected pattern: {0}'
                    .format(date_text))
            return None

        date = datetime(
                int(match.group('year')),
                get_month_as_int(match.group('month')),
                int(match.group('day')),
                int(match.group('hour')),
                int(match.group('minute')),
                )

        return date
