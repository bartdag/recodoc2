from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from recommender.actions import find_high_level_links_msg


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--src-pk', action='store', dest='src_pk',
            default='d', help='PK of the source'),
        make_option('--dst-pk', action='store', dest='dst_pk',
            default='-1', help='PK of the destination'),
        make_option('--msg-level', action='store_true', dest='msg_level',
            default=False, help='at message level (otherwise: thread)'),
        make_option('--no-snippet', action='store_true', dest='no_snippet',
            default=False, help='only inlined reference'),
        make_option('--size', action='store', dest='size',
            default='-1', help='minimum number of common elements'),
    )
    help = "Find high level links"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        src_pk = int(smart_decode(options.get('src_pk')))
        dst_pk = int(smart_decode(options.get('dst_pk')))
        msg_level = options.get('msg_level', False)
        no_snippet = options.get('no_snippet', False)
        size = int(smart_decode(options.get('size')))
        find_high_level_links_msg(pname, bname, release, src_pk, dst_pk,
                msg_level, no_snippet, size)
