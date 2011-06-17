from __future__ import unicode_literals
from django.core.management.base import NoArgsCommand
from doc.actions import compute_family_coverage
from optparse import make_option
from docutil.commands_util import recocommand
from docutil.str_util import smart_decode


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--pname', action='store', dest='pname',
            default='-1', help='Project unix name'),
        make_option('--dname', action='store', dest='dname',
            default='-1', help='Document name'),
        make_option('--bname', action='store', dest='bname',
            default='-1', help='Codebase name'),
        make_option('--release', action='store', dest='release',
            default='-1', help='Project Release of Codebase'),
        make_option('--srelease', action='store', dest='srelease',
            default='-1', help='Project Release of Document'),
    )
    help = "Compute family coverage from a document"

    @recocommand
    def handle_noargs(self, **options):
        pname = smart_decode(options.get('pname'))
        dname = smart_decode(options.get('dname'))
        bname = smart_decode(options.get('bname'))
        release = smart_decode(options.get('release'))
        srelease = smart_decode(options.get('srelease'))
        compute_family_coverage(pname, bname, release, dname, srelease)
