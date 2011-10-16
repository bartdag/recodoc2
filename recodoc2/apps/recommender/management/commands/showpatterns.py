from __future__ import unicode_literals
from optparse import make_option
from django.core.management.base import NoArgsCommand

from docutil.commands_util import recocommand
from docutil.str_util import smart_decode
from recommender.actions import report_doc_patterns


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Code Base name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release'),
        make_option('--source', action='store', dest='source',
            default='d', help='Source of the resource (d or s)'),
        make_option('--pk', action='store', dest='pk',
            default='-1', help='PK of the resource'),
    )
    help = "Show documentation patterns"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        source = smart_decode(options.get('source'))
        pk = int(smart_decode(options.get('pk')))
        report_doc_patterns(pname, bname, release, source, pk)

