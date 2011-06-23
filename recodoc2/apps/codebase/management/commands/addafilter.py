from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from codebase.actions import add_a_filter


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--fqn', action='store', dest='fqn',
            default='-1', help='Filter Content'),
        make_option('--no-snippet', action='store_true', dest='no-snippet',
            default=False, help='Exclude snippets'),
        make_option('--one-ref-only', action='store_true', dest='one-ref-only',
            default=False, help='Only apply to single references'),
        make_option('--include-member', action='store_true',
            dest='include-member', default=False,
            help='Match members to this filter'),

    )
    help = "Create a filter"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        fqn = smart_decode(options.get('fqn'))
        add_a_filter(pname, bname, release, fqn, not options.get('no-snippet'),
            options.get('one-ref-only'), options.get('include-member'))
