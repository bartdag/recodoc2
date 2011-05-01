from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from channel.actions import toc_refresh


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--cname', action='store', dest='bname',
            default='-1', help='Channel name'),

    )
    help = "Refresh/Init Channel Table of Contents"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        cname = smart_decode(options.get('cname'))
        toc_refresh(pname, cname)
