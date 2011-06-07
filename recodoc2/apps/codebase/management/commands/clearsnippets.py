from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import clear_snippets


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--language', action='store', dest='language',
            default='j', help='Language of the snippets to delete.'),
        make_option('--source', action='store', dest='source',
            default='d', help='Source of snippets (s or d)'),

    )
    help = "Delete single references parsed from snippets"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        language = smart_decode(options.get('language'))
        source = smart_decode(options.get('source'))
        clear_snippets(pname, language, source)
