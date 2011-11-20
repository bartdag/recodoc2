from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from doc.actions import show_new_new_links


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--dname', action='store', dest='dname',
            default='-1', help='Document name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='CodeBase name'),
        make_option('--release1', action='store', dest='release1',
            default='-1', help='Project Release'),
        make_option('--release2', action='store', dest='release2',
            default='-1', help='Project Release'),
    )
    help = "Diff links from 2 documents"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        dname = smart_decode(options.get('dname'))
        bname = smart_decode(options.get('bname'))
        release1 = smart_decode(options.get('release1'))
        release2 = smart_decode(options.get('release2'))
        show_new_new_links(pname, bname, dname, release1, release2)
