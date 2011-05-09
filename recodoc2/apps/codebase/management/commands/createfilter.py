from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import create_filter_file


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--file', action='store', dest='file',
            default='-1', help='File to store filters'),
        make_option('--url', action='store', dest='url',
            default='-1', help='Javadoc page URL'),
    )
    help = "Create a filter file"

    @recocommand
    def handle_noargs(self, **options):
        file_path = smart_decode(options.get('file'))
        url = smart_decode(options.get('url'))
        create_filter_file(file_path, url)

