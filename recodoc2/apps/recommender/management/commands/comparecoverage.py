from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from recommender.actions import compare_coverage


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release1', action='store', dest='release1',
            default='-1', help='Project Release From'),
        make_option('--release2', action='store', dest='release2',
            default='-1', help='Project Release To'),
        make_option('--source', action='store', dest='source',
            default='d', help='Source of the resource (d or s)'),
        make_option('--pk', action='store', dest='pk',
            default='-1', help='PK of the resource'),
    )
    help = "Compare coverage of code element families"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release1 = smart_decode(options.get('release1'))
        release2 = smart_decode(options.get('release2'))
        source = smart_decode(options.get('source'))
        pk = int(smart_decode(options.get('pk')))
        compare_coverage(pname, bname, release1, release2, source, pk)
