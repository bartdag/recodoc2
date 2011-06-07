from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from channel.actions import toc_download_entries


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--cname', action='store', dest='cname',
            default='-1', help='Channel name'),
        make_option('--start', action='store', type="int", dest='start',
            default=-1, help='Section lower bound'),
        make_option('--end', action='store', type="int", dest='end',
            default=-1, help='Section upper bound'),
        make_option('--force', action='store_true', dest='force',
            default=False,
            help='Download entries even if already downloaded'),

    )
    help = "Download Channel Table of Contents Entries"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        cname = smart_decode(options.get('cname'))
        start = options.get('start')
        end = options.get('end')
        if start == -1:
            start = None
        if end == -1:
            end = None
        force = options.get('force')
        toc_download_entries(pname, cname, start, end, force)
