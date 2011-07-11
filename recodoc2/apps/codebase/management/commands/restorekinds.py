from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import restore_kinds


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--source', action='store', dest='source',
            default='-1', help='Source of code references (optional)'),

    )
    help = "Restore reference kind"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        release = smart_decode(options.get('release'))
        source = smart_decode(options.get('source'))
        restore_kinds(pname, release, source)
