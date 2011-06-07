from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from channel.actions import json_snippet
from optparse import make_option
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--cname', action='store', dest='cname',
            default='-1', help='Channel name'),
        make_option('--output', action='store', dest='output',
            default='-1', help='Output File Path'),
    )
    help = "Dumps (url, stack trace) tuples in a json file."

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        cname = smart_decode(options.get('cname'))
        output_path = smart_decode(options.get('output'))
        json_snippet(pname, cname, output_path)
