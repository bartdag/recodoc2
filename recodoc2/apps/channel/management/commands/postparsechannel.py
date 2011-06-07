from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from channel.actions import post_process_channel
from optparse import make_option
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--cname', action='store', dest='cname',
            default='-1', help='Channel name'),
        make_option('--skip_refs', action='store_true', dest='skip_refs',
            default=False, help='Skip code reference identification'),
    )
    help = "Post Parse channel model"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        cname = smart_decode(options.get('cname'))
        post_process_channel(pname, cname)

