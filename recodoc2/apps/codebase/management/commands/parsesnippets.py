from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import parse_snippets


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--parser', action='store', dest='parser',
            default='java', help='Parser name used to parse snippets'),
        make_option('--source', action='store', dest='source',
            default='d', help='Source of snippets (s or d)'),

    )
    help = "Parse snippets"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        parser = smart_decode(options.get('parser'))
        source = smart_decode(options.get('source'))
        parse_snippets(pname, source, parser)
